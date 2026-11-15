"""NOVEXA Audio Engine — fresh, self-contained playback pipeline.

Design:
1. Resolve metadata with yt-dlp, then DOWNLOAD the audio to a local cache file.
   Streaming googlevideo URLs are the #1 cause of silent/partial playback: the
   URL expires, throttles, or returns a container ffmpeg cannot demux mid-stream.
   A local file removes the network from the playback path entirely.
2. Decode the file with ffmpeg into raw 48 kHz / 16-bit / stereo PCM inside a
   pre-buffered AudioSource (0.6 s read-ahead, exact 3840-byte frames).
3. Apply the DAVE passthrough patch so Discord accepts the voice packets.
   Without it the bot connects, reports "playing", and transmits silence.
4. Emit telemetry: first frame, peak amplitude, frame count. Silence is never
   invisible again.
"""

import asyncio
import ctypes
import logging
import os
import platform
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

import discord

logger = logging.getLogger("novexa.audio")

FRAME_SIZE = 3840  # 48000 Hz * 2 ch * 2 bytes * 0.02 s
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache" / "audio"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ==================== DAVE E2EE GUARD ====================

def _enable_high_precision_timer():
    if platform.system() != "Windows":
        return
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
        logger.info("[AUDIO] Windows timer resolution set to 1ms")
    except Exception as e:
        logger.debug(f"[AUDIO] timer resolution: {e}")


def force_dave_passthrough(voice_client: Optional[discord.VoiceClient], seconds: int = 300) -> bool:
    """Force the voice session into plaintext passthrough so packets are accepted.

    discord.py only arms this for 10 seconds on a downgrade. A track longer than
    that keeps sending after the session flips back to 'ready but not encrypting',
    and Discord silently drops everything after the first ten seconds.
    """
    if not voice_client:
        return False
    state = getattr(voice_client, "_connection", None)
    session = getattr(state, "dave_session", None) if state else None
    if not session:
        return False
    try:
        session.set_passthrough_mode(True, seconds)
        logger.info(
            "[AUDIO] DAVE passthrough armed (%ss) | ready=%s",
            seconds,
            getattr(session, "ready", None),
        )
        return True
    except Exception as e:
        logger.warning(f"[AUDIO] DAVE passthrough failed: {e}")
        return False


async def wait_for_voice(voice_client: discord.VoiceClient, timeout: float = 10.0) -> bool:
    """Wait until the voice websocket handshake finished, then arm passthrough."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if voice_client.is_connected():
            force_dave_passthrough(voice_client)
            return True
        await asyncio.sleep(0.25)
    return False


# ==================== CACHE ====================

def prune_cache(max_age_days: float = 2.0, max_files: int = 120):
    """Delete stale audio files so the cache folder cannot grow forever."""
    try:
        files = sorted(CACHE_DIR.glob("*"), key=lambda p: p.stat().st_mtime)
    except Exception:
        return
    cutoff = time.time() - max_age_days * 86400
    for path in files[:-max_files] if len(files) > max_files else []:
        try:
            path.unlink()
        except Exception:
            pass
    for path in files:
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except Exception:
            pass


def download_track(ydl_opts: dict, target: str) -> Optional[Tuple[str, dict]]:
    """Blocking yt-dlp download. Returns (filepath, info) or None."""
    import yt_dlp

    opts = dict(ydl_opts)
    opts.update(
        {
            "format": "bestaudio/best",
            "outtmpl": str(CACHE_DIR / "%(id)s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "restrictfilenames": True,
            "prefer_ffmpeg": True,
            "cachedir": str(CACHE_DIR / ".ytdl"),
        }
    )
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(target, download=True)
            if not info:
                return None
            entry = info["entries"][0] if "entries" in info and info["entries"] else info
            path = ydl.prepare_filename(entry)
            if not os.path.exists(path):
                candidates = sorted(CACHE_DIR.glob(f"{entry.get('id', '')}.*"), key=os.path.getmtime)
                if not candidates:
                    return None
                path = str(candidates[-1])
            if os.path.getsize(path) < 4096:
                try:
                    os.remove(path)
                except Exception:
                    pass
                return None
            return path, entry
    except Exception as e:
        logger.error(f"[AUDIO] download failed for {target}: {e}")
        return None


# ==================== PCM SOURCE ====================

class CachedPCMAudioSource(discord.AudioSource):
    """Pre-buffered ffmpeg decode of a local file, with live telemetry."""

    def __init__(
        self,
        filepath: str,
        ffmpeg_executable: str,
        filter_args: str = "-vn",
        volume: float = 1.0,
        start_offset: float = 0.0,
    ):
        self.filepath = filepath
        self.volume = max(0.0, min(float(volume), 2.0))
        self.frames = 0
        self.peak = 0
        self._closed = False
        self._stop = threading.Event()
        self._buffer: queue.Queue = queue.Queue(maxsize=200)

        args = [
            ffmpeg_executable,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
        ]
        if start_offset and start_offset > 0:
            args.extend(["-ss", f"{start_offset:.3f}"])
        if filter_args:
            args.extend(filter_args.split())
        args.extend(
            [
                "-i", filepath,
                "-vn",
                "-f", "s16le",
                "-ar", "48000",
                "-ac", "2",
                "-blocksize", str(FRAME_SIZE),
                "pipe:1",
            ]
        )

        self._args = args
        self.process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
        )
        self._reader = threading.Thread(target=self._read_loop, daemon=True, name="novexa-pcm")
        self._reader.start()

        # 0.5s of read-ahead before the first frame reaches Discord
        deadline = time.perf_counter() + 0.5
        while self._buffer.qsize() < 25 and time.perf_counter() < deadline:
            if self._stop.is_set() or self.process.poll() is not None:
                break
            time.sleep(0.01)

        logger.info(
            "[AUDIO] ffmpeg pid=%s prebuffered=%d frames (%.2fs)",
            self.process.pid,
            self._buffer.qsize(),
            self._buffer.qsize() * 0.02,
        )
        if self.process.poll() is not None and self._buffer.empty():
            err = b""
            try:
                err = self.process.stderr.read(600) or b""
            except Exception:
                pass
            logger.error("[AUDIO] ffmpeg produced no audio: %s", err.decode("utf-8", "ignore").strip()[:400])

    def _read_loop(self):
        try:
            while not self._stop.is_set():
                chunk = self.process.stdout.read(FRAME_SIZE) if self.process.stdout else b""
                if not chunk:
                    break
                while len(chunk) < FRAME_SIZE:
                    more = self.process.stdout.read(FRAME_SIZE - len(chunk))
                    if not more:
                        break
                    chunk += more
                if len(chunk) < FRAME_SIZE:
                    chunk = chunk.ljust(FRAME_SIZE, b"\x00")
                while not self._stop.is_set():
                    try:
                        self._buffer.put(chunk, timeout=0.1)
                        break
                    except queue.Full:
                        continue
        except Exception as e:
            logger.debug(f"[AUDIO] reader loop: {e}")
        finally:
            try:
                self._buffer.put_nowait(None)
            except queue.Full:
                pass

    def read(self) -> bytes:
        if self._closed:
            return b""
        try:
            chunk = self._buffer.get(timeout=2.0)
        except queue.Empty:
            logger.warning("[AUDIO] buffer underrun")
            return b"\x00" * FRAME_SIZE
        if chunk is None:
            return b""
        self.frames += 1
        if self.frames == 1:
            logger.info("[AUDIO] first frame transmitted")
        if self.frames % 250 == 0:
            logger.info("[AUDIO] %d frames sent (~%.0fs of audio)", self.frames, self.frames * 0.02)
        if self.volume != 1.0:
            chunk = _scale_pcm(chunk, self.volume)
        if self.frames % 100 == 0:
            self.peak = max(self.peak, _peak(chunk))
        return chunk

    def is_opus(self) -> bool:
        return False

    def cleanup(self):
        if self._closed:
            return
        self._closed = True
        self._stop.set()
        if self.process:
            try:
                self.process.kill()
            except Exception:
                pass
            try:
                self.process.wait(timeout=1.0)
            except Exception:
                pass
        logger.info(
            "[AUDIO] playback ended | frames=%d (~%.0fs) peak=%d (%s)",
            self.frames,
            self.frames * 0.02,
            self.peak,
            "SILENT OUTPUT" if self.peak == 0 else "signal present",
        )


def _peak(pcm: bytes) -> int:
    try:
        import audioop

        return audioop.max(pcm, 2)
    except Exception:
        peak = 0
        for i in range(0, len(pcm) - 1, 2):
            sample = int.from_bytes(pcm[i:i + 2], "little", signed=True)
            if abs(sample) > peak:
                peak = abs(sample)
        return peak


def _scale_pcm(pcm: bytes, volume: float) -> bytes:
    try:
        import audioop

        return audioop.mul(pcm, 2, volume)
    except Exception:
        import array

        samples = array.array("h", pcm)
        for i, s in enumerate(samples):
            samples[i] = max(-32768, min(32767, int(s * volume)))
        return samples.tobytes()


def resolve_ffmpeg() -> str:
    local = Path(__file__).resolve().parent.parent / "ffmpeg.exe"
    if local.exists():
        return str(local)
    found = shutil.which("ffmpeg")
    return found or "ffmpeg"


FFMPEG = resolve_ffmpeg()
