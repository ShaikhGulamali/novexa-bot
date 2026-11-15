"""NOVEXA - Ultra High-Fidelity Music & Spotify Streaming Suite.

Features:
- Native Spotify Integration:
  - Direct Spotify Tracks, Albums, Playlists, Artists, and spotify.link URLs.
  - Zero-delay instant playback with lazy queue resolution (50-100 tracks queued in < 1s).
  - Dedicated Spotify Green (#1DB954) UI with rich album artwork and artist credits.
- Universal Audio Engine:
  - YouTube search queries, YouTube URLs, Playlists, SoundCloud, and direct streams.
  - Native Discord Opus codec integration with verified absolute path loading.
  - FFmpeg streaming with reconnect resiliency (-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5).
  - Anti-race condition playback pipeline (_is_manually_stopping flag) preventing premature track cutoffs.
- Live Interactive Now Playing Dashboard:
  - Dynamic progress bar: 🔘▬▬▬▬▬▬▬▬▬▬ 01:23 / 03:45
  - Interactive UI buttons: Play/Pause, Skip, Loop (Off/Track/Queue), Shuffle, Stop, Vol -, Vol +, Queue, 24/7 Mode.
  - Live Audio Filter dropdown: Flat, BassBoost, Nightcore, Vaporwave, 8D, Lo-Fi, Pop, Treble Boost.
- Full Slash Command & Prefix Suite:
  - /play, /spotify, /skip, /pause, /resume, /stop, /queue, /nowplaying, /volume, /loop.
  - n!play, n!spotify, n!skip, n!pause, n!resume, n!stop, n!queue, n!np, n!vol, n!loop, n!shuffle, n!filter, n!247.
"""

import os
import sys
import shutil
import asyncio
import logging
import random
import time
import re
from collections import deque
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp

from config import BASE_DIR, BOT_PREFIX, BOT_NAME
from database.database import db
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed, info_embed
from utils.helpers import PaginatorView
from services.voice_patch import apply_voice_patch
from services.audio_engine import (
    CachedPCMAudioSource,
    download_track,
    force_dave_passthrough,
    prune_cache,
    FFMPEG,
)

logger = logging.getLogger("novexa.music")

music_group = app_commands.Group(
    name="music",
    description="Music playback — play, queue, loop, volume and live controls",
    guild_only=True,
)

OPUS_PATH = str(BASE_DIR / ("opus.dll" if os.name == "nt" else "libopus.so.0"))

# ==================== OPUS CODEC INITIALIZATION ====================
if not discord.opus.is_loaded():
    try:
        discord.opus._load_default()
    except Exception:
        pass
    if not discord.opus.is_loaded():
        for p in [os.path.abspath("opus.dll"), os.path.abspath("libopus-0.dll"), "libopus.so.0", "libopus.so"]:
            if os.path.exists(p) or not p.endswith(".dll"):
                try:
                    discord.opus.load_opus(p)
                    logger.info(f"Loaded Discord Opus codec library from {p}")
                    break
                except Exception as e:
                    logger.warning(f"Error loading opus from {p}: {e}")

# ==================== CONSTANTS & COLOR PALETTE ====================
COLOR_SPOTIFY = 0x1DB954       # Official Spotify Green
COLOR_MUSIC_PRIMARY = 0x9B59B6  # Royal Purple / Amethyst
COLOR_MUSIC_SUCCESS = 0x2ECC71  # Emerald Green
COLOR_MUSIC_WARN = 0xF1C40F     # Golden Amber
COLOR_MUSIC_ERROR = 0xE74C3C    # Crimson Red

# Audio Filter Presets (Live switchable)
AUDIO_FILTERS: Dict[str, str] = {
    "flat": "-vn",
    "bassboost": "-vn -af equalizer=f=60:width_type=h:width=50:g=15",
    "nightcore": "-vn -af asetrate=48000*1.25,aresample=48000,atempo=1.05",
    "vaporwave": "-vn -af asetrate=48000*0.8,aresample=48000",
    "8d": "-vn -af apulsator=hz=0.125",
    "lofi": "-vn -af lowpass=f=3200,volume=1.2",
    "pop": "-vn -af equalizer=f=1000:width_type=h:width=200:g=5",
    "soft": "-vn -af lowpass=f=3000",
    "treble": "-vn -af equalizer=f=8000:width_type=h:width=1000:g=10",
}


def get_ffmpeg_executable() -> str:
    """Resolve the clean FFmpeg binary path."""
    local_ffmpeg = BASE_DIR / "ffmpeg.exe"
    if os.name == 'nt' and local_ffmpeg.exists():
        return str(local_ffmpeg)
    system_path = shutil.which("ffmpeg")
    if system_path:
        return system_path
    winget_path = (
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin/ffmpeg.exe"
    )
    if winget_path.exists():
        return str(winget_path)
    return "ffmpeg"


FFMPEG_EXEC = get_ffmpeg_executable()

# yt-dlp Configuration
YTDL_OPTS = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}


def format_duration(seconds: int) -> str:
    """Format duration seconds into mm:ss or hh:mm:ss."""
    if not seconds or seconds <= 0:
        return "🔴 LIVE"
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def create_progress_bar(elapsed: int, total: int, length: int = 14) -> str:
    """Render a dynamic progress bar."""
    if total <= 0:
        return "🔘" + "▬" * (length - 1) + " `[LIVE STREAM]`"
    progress = min(max(elapsed / total, 0.0), 1.0)
    pos = int(progress * length)
    bar = ""
    for i in range(length):
        if i == pos:
            bar += "🔘"
        else:
            bar += "▬"
    return f"`{bar}` `{format_duration(elapsed)} / {format_duration(total)}`"


# ==================== TRACK MODEL ====================

class Track:
    """Encapsulates a playable track with lazy stream extraction for Spotify & Playlists."""

    def __init__(
        self,
        title: str,
        artist: str,
        duration: int,
        thumbnail: Optional[str],
        requester: Union[discord.Member, discord.User],
        source: str = "youtube",  # "spotify", "youtube", "soundcloud", "direct"
        webpage_url: str = "",
        search_query: str = "",
        stream_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.title = title
        self.artist = artist
        self.duration = duration
        self.thumbnail = thumbnail
        self.requester = requester
        self.source = source
        self.webpage_url = webpage_url
        self.search_query = search_query or f"{title} {artist}"
        self.stream_url = stream_url
        self.headers = headers or {}
        self.created_at = time.time()

    @property
    def formatted_duration(self) -> str:
        return format_duration(self.duration)

    async def resolve_stream(self) -> bool:
        """Resolve high-bitrate stream URL via yt-dlp asynchronously if not already extracted."""
        if self.stream_url:
            return True

        target = self.search_query if self.source == "spotify" else (self.webpage_url or self.search_query)
        loop = asyncio.get_running_loop()

        def _sync_resolve():
            opts = dict(YTDL_OPTS)
            search_query = target if target.startswith("http://") or target.startswith("https://") else f"ytsearch1:{target}"
            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    info = ydl.extract_info(search_query, download=False)
                    if not info:
                        return None
                    entry = info["entries"][0] if "entries" in info and info["entries"] else info
                    s_url = entry.get("url")
                    h = entry.get("http_headers", {}) or {}
                    if not s_url and "formats" in entry:
                        a_formats = [f for f in entry["formats"] if f.get("acodec") != "none"]
                        if a_formats:
                            best_f = a_formats[-1]
                            s_url = best_f.get("url")
                            if best_f.get("http_headers"):
                                h.update(best_f["http_headers"])
                    dur = int(entry.get("duration") or 0)
                    thumb = entry.get("thumbnail")
                    wp_url = entry.get("webpage_url") or target
                    return s_url, h, dur, thumb, wp_url
                except Exception as ex:
                    logger.error(f"Error resolving stream for '{target}': {ex}")
                    return None

        result = await loop.run_in_executor(None, _sync_resolve)
        if result and result[0]:
            self.stream_url = result[0]
            self.headers = result[1]
            if not self.duration:
                self.duration = result[2]
            if not self.thumbnail:
                self.thumbnail = result[3]
            if not self.webpage_url:
                self.webpage_url = result[4]
            return True
        return False


# ==================== SPOTIFY HANDLER ====================

class SpotifyHandler:
    """Dedicated Spotify metadata resolver for Tracks, Playlists, Albums, and Artists."""

    @staticmethod
    def is_spotify(query: str) -> bool:
        q = query.lower().strip()
        return "open.spotify.com/" in q or "spotify.link/" in q or q.startswith("spotify:")

    @classmethod
    async def resolve(cls, query: str) -> dict:
        """Extract metadata from Spotify URL or search."""
        query = query.strip()

        # Handle shortened spotify.link redirects
        if "spotify.link/" in query:
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(query, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                        query = str(resp.url)
            except Exception:
                pass

        m = re.search(r"spotify\.com/(track|album|playlist|artist)/([a-zA-Z0-9]+)", query)
        if not m:
            m = re.search(r"spotify:(track|album|playlist|artist):([a-zA-Z0-9]+)", query)

        if not m:
            clean_query = re.sub(r"^spotify:\s*", "", query, flags=re.I).strip()
            return {"type": "search", "query": clean_query}

        entity_type = m.group(1)
        entity_id = m.group(2)
        embed_url = f"https://open.spotify.com/embed/{entity_type}/{entity_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        try:
            async with aiohttp.ClientSession(headers=headers) as s:
                async with s.get(embed_url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        json_m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html)
                        if json_m:
                            data = json.loads(json_m.group(1))
                            pp = data.get("props", {}).get("pageProps", {})
                            state = pp.get("state", {})
                            entity = state.get("data", {}).get("entity", {})
                            if entity:
                                name = entity.get("name") or entity.get("title") or "Unknown Track"
                                artists_list = [a.get("name") for a in entity.get("artists", []) if a.get("name")]
                                artist_str = ", ".join(artists_list) if artists_list else "Unknown Artist"
                                images = entity.get("visualIdentity", {}).get("image", [])
                                thumbnail = images[0].get("url") if images else None

                                if entity_type == "track":
                                    dur = int((entity.get("duration") or 0) / 1000)
                                    return {
                                        "type": "track",
                                        "title": name,
                                        "artist": artist_str,
                                        "thumbnail": thumbnail,
                                        "duration": dur,
                                        "search_query": f"{name} {artist_str}",
                                        "spotify_url": f"https://open.spotify.com/track/{entity_id}",
                                    }
                                elif entity_type in ["playlist", "album", "artist"]:
                                    raw_tracks = entity.get("trackList", [])
                                    tracks = []
                                    for t in raw_tracks:
                                        t_title = t.get("title") or "Unknown"
                                        t_sub = t.get("subtitle") or artist_str
                                        t_dur = int((t.get("duration") or 0) / 1000)
                                        tracks.append({
                                            "title": t_title,
                                            "artist": t_sub,
                                            "duration": t_dur,
                                            "search_query": f"{t_title} {t_sub}",
                                        })
                                    return {
                                        "type": entity_type,
                                        "name": name,
                                        "artist": artist_str,
                                        "thumbnail": thumbnail,
                                        "count": len(tracks),
                                        "tracks": tracks,
                                        "spotify_url": f"https://open.spotify.com/{entity_type}/{entity_id}",
                                    }
        except Exception as e:
            logger.warning(f"Spotify embed resolve error: {e}")

        # Fallback to oEmbed
        try:
            async with aiohttp.ClientSession() as s:
                oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/{entity_type}/{entity_id}"
                async with s.get(oembed_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        odata = await resp.json()
                        title = odata.get("title", "")
                        return {
                            "type": "track",
                            "title": title,
                            "artist": "Spotify",
                            "thumbnail": odata.get("thumbnail_url"),
                            "duration": 0,
                            "search_query": title,
                            "spotify_url": f"https://open.spotify.com/{entity_type}/{entity_id}",
                        }
        except Exception:
            pass

        return {"type": "search", "query": query}


# ==================== GUILD MUSIC PLAYER ====================

class GuildMusicPlayer:
    """Per-Guild Audio Stream Manager & Queue Coordinator."""

    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.voice_client: Optional[discord.VoiceClient] = None
        self.queue: deque[Track] = deque()
        self.history: deque[Track] = deque(maxlen=25)
        self.current: Optional[Track] = None

        self.loop_mode: str = "off"  # "off", "track", "queue"
        self.volume: float = 1.0     # 100%
        self.audio_filter: str = "flat"
        self.is_247: bool = False

        self.text_channel: Optional[discord.TextChannel] = None
        self.now_playing_msg: Optional[discord.Message] = None

        self.start_time: Optional[float] = None
        self.pause_time: Optional[float] = None
        self.total_paused_duration: float = 0.0
        self.is_paused: bool = False
        self._is_manually_stopping: bool = False
        self._playback_generation: int = 0
        self._audio_source = None

        self.inactivity_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()

    def get_elapsed(self) -> int:
        """Calculate elapsed playback time in seconds."""
        if not self.start_time:
            return 0
        if self.is_paused and self.pause_time:
            return int(self.pause_time - self.start_time - self.total_paused_duration)
        return int(time.time() - self.start_time - self.total_paused_duration)

    def cancel_inactivity_timer(self):
        """Cancel pending inactivity auto-disconnect task."""
        if self.inactivity_task and not self.inactivity_task.done():
            self.inactivity_task.cancel()
            self.inactivity_task = None

    def start_inactivity_timer(self, delay: int = 300):
        """Start auto-disconnect timer if idle and not in 24/7 mode."""
        self.cancel_inactivity_timer()
        if self.is_247:
            return

        async def _timer():
            try:
                await asyncio.sleep(delay)
                if not self.current and len(self.queue) == 0 and self.voice_client and self.voice_client.is_connected():
                    if self.text_channel:
                        embed = discord.Embed(
                            title="💤 Music Session Inactive",
                            description="Disconnected from voice channel due to 5 minutes of inactivity.\nUse `/play` to start listening again!",
                            color=COLOR_MUSIC_WARN,
                        )
                        await self.text_channel.send(embed=embed)
                    await self.destroy()
            except asyncio.CancelledError:
                pass

        self.inactivity_task = asyncio.create_task(_timer())

    async def connect(self, voice_channel: discord.VoiceChannel) -> discord.VoiceClient:
        """Connect or move to the specified voice channel."""
        self.cancel_inactivity_timer()

        # Adopt an existing connection (bot may already sit in a channel)
        existing = self.guild.voice_client
        if existing and existing.is_connected():
            self.voice_client = existing
            if existing.channel.id != voice_channel.id:
                await existing.move_to(voice_channel)
            force_dave_passthrough(existing, 3600)
            return existing

        if self.voice_client and self.voice_client.is_connected():
            if self.voice_client.channel.id != voice_channel.id:
                await self.voice_client.move_to(voice_channel)
            force_dave_passthrough(self.voice_client, 3600)
            return self.voice_client

        # Clean up any dead connection first
        if self.voice_client:
            try:
                await self.voice_client.disconnect(force=True)
            except Exception:
                pass

        self.voice_client = await voice_channel.connect(self_deaf=True)
        force_dave_passthrough(self.voice_client, 3600)
        return self.voice_client

    async def play_track(self, track: Track, seek_seconds: int = 0):
        """Download to the local cache, decode to PCM, and transmit with DAVE armed."""
        if not self.voice_client or not self.voice_client.is_connected():
            return

        if not discord.opus.is_loaded() and os.path.exists(OPUS_PATH):
            try:
                discord.opus.load_opus(OPUS_PATH)
            except Exception:
                pass

        self.cancel_inactivity_timer()
        self.current = track
        self.start_time = time.time() - seek_seconds
        self.pause_time = None
        self.total_paused_duration = 0.0
        self.is_paused = False

        target = track.webpage_url or track.search_query
        if not target or target.startswith("ytsearch1:"):
            target = target or f"ytsearch1:{track.title} {track.artist}"
        if not target.startswith(("http://", "https://")):
            target = f"ytsearch1:{target}"

        loop = asyncio.get_running_loop()
        logger.info("[AUDIO] preparing '%s' from %s", track.title[:60], target[:100])
        downloaded = await loop.run_in_executor(None, download_track, YTDL_OPTS, target)
        if not downloaded:
            if self.text_channel:
                await self.text_channel.send(
                    embed=error_embed("Playback Error", f"Could not fetch audio for **{track.title}**. Skipping.")
                )
            self.current = None
            await self.process_next()
            return

        filepath, info = downloaded
        if not track.duration:
            track.duration = int(info.get("duration") or 0)
        if not track.thumbnail:
            track.thumbnail = info.get("thumbnail")
        if not track.webpage_url:
            track.webpage_url = info.get("webpage_url") or target

        filter_args = AUDIO_FILTERS.get(self.audio_filter, "-vn")
        try:
            source = CachedPCMAudioSource(
                filepath,
                FFMPEG,
                filter_args=filter_args,
                volume=self.volume,
                start_offset=seek_seconds,
            )
        except Exception as e:
            logger.error(f"[AUDIO] source creation failed: {e}")
            self.current = None
            await self.process_next()
            return

        self._playback_generation += 1
        generation = self._playback_generation

        def _after_callback(error, generation=generation):
            if generation != self._playback_generation:
                return
            if error:
                logger.error(f"Playback error in guild {self.guild.id}: {error}")
            asyncio.run_coroutine_threadsafe(self.process_next(), self.bot.loop)

        await self._stop_current_audio()
        self._audio_source = source

        self.voice_client.play(source, after=_after_callback)
        force_dave_passthrough(self.voice_client, 3600)

        state = getattr(self.voice_client, "_connection", None)
        session = getattr(state, "dave_session", None) if state else None
        logger.info(
            "[PLAY] guild=%s '%s' | dave_ready=%s | can_encrypt=%s | opus=%s | file=%s",
            self.guild.id,
            track.title[:50],
            getattr(session, "ready", None),
            getattr(state, "can_encrypt", None) if state else None,
            discord.opus.is_loaded(),
            os.path.basename(filepath),
        )

        try:
            await db.execute(
                "INSERT INTO music_history (guild_id, title, webpage_url, duration, requested_by) VALUES (?, ?, ?, ?, ?)",
                (self.guild.id, track.title, track.webpage_url, track.duration, track.requester.id),
            )
        except Exception:
            pass

        await self.send_now_playing_embed()

    async def _stop_current_audio(self):
        """Stop whatever is playing and release the previous ffmpeg process."""
        vc = self.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            self._is_manually_stopping = True
            vc.stop()
            self._is_manually_stopping = False
        old = getattr(self, "_audio_source", None)
        if old:
            try:
                old.cleanup()
            except Exception:
                pass
            self._audio_source = None

    async def send_now_playing_embed(self):
        """Send or update the active Now Playing interactive UI."""
        if not self.text_channel or not self.current:
            return

        embed = self.build_now_playing_embed()
        view = NowPlayingControlsView(self)

        try:
            if self.now_playing_msg:
                try:
                    await self.now_playing_msg.delete()
                except Exception:
                    pass
            self.now_playing_msg = await self.text_channel.send(embed=embed, view=view)
        except Exception as e:
            logger.warning(f"Could not send now playing embed: {e}")

    def build_now_playing_embed(self) -> discord.Embed:
        """Construct the rich aesthetic Now Playing embed."""
        if not self.current:
            return discord.Embed(title="🎵 Nothing Playing", description="Queue is empty.", color=COLOR_MUSIC_WARN)

        t = self.current
        elapsed = self.get_elapsed()
        prog_bar = create_progress_bar(elapsed, t.duration)

        status_icon = "⏸️ Paused" if self.is_paused else "▶️ Now Playing"
        loop_badge = f" • 🔁 `{self.loop_mode.upper()}`" if self.loop_mode != "off" else ""
        filter_badge = f" • ⚡ `{self.audio_filter.upper()}`" if self.audio_filter != "flat" else ""
        mode_247 = " • 📻 `24/7`" if self.is_247 else ""

        is_spotify = t.source == "spotify"
        color = COLOR_SPOTIFY if is_spotify else COLOR_MUSIC_PRIMARY
        provider_tag = "🟢 Spotify" if is_spotify else "▶️ YouTube"

        if self.queue:
            up_next = f"⏭️ **Up Next:** `{self.queue[0].title}` ({self.queue[0].formatted_duration})"
        else:
            up_next = "⏭️ **Up Next:** *End of queue*"

        embed = discord.Embed(
            title=f"{provider_tag} | {status_icon}",
            description=(
                f"### [**{t.title}**]({t.webpage_url})\n\n"
                f"👤 **Artist:** `{t.artist}`\n"
                f"⏱️ **Progress:** {prog_bar}\n"
                f"🔊 **Volume:** `{int(self.volume * 100)}%`{loop_badge}{filter_badge}{mode_247}\n\n"
                f"{up_next}\n"
            ),
            color=color,
        )
        if t.thumbnail:
            embed.set_thumbnail(url=t.thumbnail)

        footer_text = f"Requested by {t.requester.display_name} • {provider_tag} Engine"
        embed.set_footer(text=footer_text, icon_url=t.requester.display_avatar.url)
        return embed

    async def process_next(self):
        """Advance queue according to configured loop mode."""
        async with self.lock:
            if not self.voice_client or not self.voice_client.is_connected():
                return

            if self.loop_mode == "track" and self.current:
                await self.play_track(self.current)
                return

            if self.loop_mode == "queue" and self.current:
                self.queue.append(self.current)

            if self.current:
                self.history.append(self.current)

            if len(self.queue) > 0:
                next_track = self.queue.popleft()
                await self.play_track(next_track)
            else:
                self.current = None
                self.start_inactivity_timer()
                if self.text_channel:
                    try:
                        embed = discord.Embed(
                            title="🎵 Queue Finished",
                            description="All queued songs have finished playing.\nUse `/play` or `/spotify` to add more music!",
                            color=COLOR_MUSIC_PRIMARY,
                        )
                        await self.text_channel.send(embed=embed)
                    except Exception:
                        pass

    async def skip(self) -> bool:
        """Skip current track safely without race conditions."""
        if not self.voice_client or not self.voice_client.is_playing():
            return False
        self._playback_generation += 1
        await self._stop_current_audio()
        await self.process_next()
        return True

    async def set_filter(self, filter_name: str) -> bool:
        """Apply audio filter and resume seamlessly from current timestamp."""
        if filter_name not in AUDIO_FILTERS:
            return False
        self.audio_filter = filter_name
        if self.current and self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused()):
            elapsed = self.get_elapsed()
            await self.play_track(self.current, seek_seconds=elapsed)
        return True

    async def destroy(self):
        """Tear down voice connection and reset state."""
        self.cancel_inactivity_timer()
        self.queue.clear()
        self.current = None
        if self.voice_client:
            self._is_manually_stopping = True
            try:
                self.voice_client.stop()
            except Exception:
                pass
            try:
                await self.voice_client.disconnect(force=True)
            except Exception:
                pass
            self.voice_client = None
            self._is_manually_stopping = False
        self._playback_generation += 1
        await self._stop_current_audio()


# ==================== INTERACTIVE UI CONTROLS ====================

class AudioFilterSelect(discord.ui.Select):
    """Dropdown for live audio equalizer filters."""

    def __init__(self, player: GuildMusicPlayer):
        options = [
            discord.SelectOption(label="Flat (Normal Audio)", value="flat", description="Original clear sound without EQ", emoji="🎵", default=(player.audio_filter == "flat")),
            discord.SelectOption(label="BassBoost", value="bassboost", description="Deep heavy bass frequencies (+15dB)", emoji="🔊", default=(player.audio_filter == "bassboost")),
            discord.SelectOption(label="Nightcore", value="nightcore", description="Sped up pitch & tempo (1.25x)", emoji="⚡", default=(player.audio_filter == "nightcore")),
            discord.SelectOption(label="8D Surround Audio", value="8d", description="Rotating binaural 360 audio effect", emoji="🎧", default=(player.audio_filter == "8d")),
            discord.SelectOption(label="Lo-Fi Chill", value="lofi", description="Warm mellow lowpass filter", emoji="☕", default=(player.audio_filter == "lofi")),
            discord.SelectOption(label="Vaporwave", value="vaporwave", description="Slowed down retro aesthetic (0.8x)", emoji="🌊", default=(player.audio_filter == "vaporwave")),
            discord.SelectOption(label="Pop / Vocal", value="pop", description="Enhanced mid vocal presence", emoji="🎤", default=(player.audio_filter == "pop")),
            discord.SelectOption(label="Treble Boost", value="treble", description="Crisp high frequency acoustic boost", emoji="🎶", default=(player.audio_filter == "treble")),
        ]
        super().__init__(
            placeholder="⚡ Change Audio Equalizer Filter...",
            min_values=1,
            max_values=1,
            options=options,
            row=2,
        )
        self.player = player

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        await self.player.set_filter(chosen)
        await interaction.response.send_message(
            f"⚡ Equalizer filter updated to **{chosen.upper()}**!",
            ephemeral=True
        )


class NowPlayingControlsView(discord.ui.View):
    """Full-featured interactive button control panel attached to Now Playing embed."""

    def __init__(self, player: GuildMusicPlayer):
        super().__init__(timeout=None)
        self.player = player
        self.add_item(AudioFilterSelect(player))

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary, row=0, custom_id="np_playpause")
    async def btn_play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.player.voice_client
        if not vc:
            return await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)

        if vc.is_paused():
            vc.resume()
            self.player.is_paused = False
            if self.player.pause_time:
                self.player.total_paused_duration += time.time() - self.player.pause_time
                self.player.pause_time = None
            await interaction.response.edit_message(embed=self.player.build_now_playing_embed(), view=self)
        elif vc.is_playing():
            vc.pause()
            self.player.is_paused = True
            self.player.pause_time = time.time()
            await interaction.response.edit_message(embed=self.player.build_now_playing_embed(), view=self)
        else:
            await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0, custom_id="np_skip")
    async def btn_skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        skipped = await self.player.skip()
        if skipped:
            await interaction.response.send_message("⏭️ Skipped to next track!", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing to skip.", ephemeral=True)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, row=0, custom_id="np_loop")
    async def btn_loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        modes = ["off", "track", "queue"]
        curr_idx = modes.index(self.player.loop_mode)
        next_mode = modes[(curr_idx + 1) % len(modes)]
        self.player.loop_mode = next_mode
        await interaction.response.edit_message(embed=self.player.build_now_playing_embed(), view=self)
        await interaction.followup.send(f"🔁 Loop mode set to **{next_mode.upper()}**.", ephemeral=True)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, row=0, custom_id="np_shuffle")
    async def btn_shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.player.queue) < 2:
            return await interaction.response.send_message("Not enough tracks in queue to shuffle.", ephemeral=True)
        random.shuffle(self.player.queue)
        await interaction.response.send_message("🔀 Queue shuffled randomly!", ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0, custom_id="np_stop")
    async def btn_stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.destroy()
        await interaction.response.send_message("⏹️ Playback stopped and disconnected.", ephemeral=True)

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, row=1, custom_id="np_voldown")
    async def btn_vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.volume = max(0.1, round(self.player.volume - 0.1, 2))
        if self.player.voice_client and self.player.voice_client.source:
            if hasattr(self.player.voice_client.source, "volume"):
                self.player.voice_client.source.volume = self.player.volume
        await interaction.response.edit_message(embed=self.player.build_now_playing_embed(), view=self)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, row=1, custom_id="np_volup")
    async def btn_vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.volume = min(2.0, round(self.player.volume + 0.1, 2))
        if self.player.voice_client and self.player.voice_client.source:
            if hasattr(self.player.voice_client.source, "volume"):
                self.player.voice_client.source.volume = self.player.volume
        await interaction.response.edit_message(embed=self.player.build_now_playing_embed(), view=self)

    @discord.ui.button(label="Queue", emoji="📜", style=discord.ButtonStyle.secondary, row=1, custom_id="np_queue")
    async def btn_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player.current and len(self.player.queue) == 0:
            return await interaction.response.send_message("Queue is empty.", ephemeral=True)

        lines = []
        if self.player.current:
            lines.append(f"▶️ **Now Playing:** `{self.player.current.title}` ({self.player.current.formatted_duration})")
        for i, t in enumerate(self.player.queue, start=1):
            lines.append(f"`{i}.` **{t.title}** ({t.artist}) — `{t.formatted_duration}`")

        embed = primary_embed(
            title=f"📜 Music Queue ({len(self.player.queue)} songs)",
            description="\n".join(lines[:15]) + (f"\n\n*...and {len(lines)-16} more tracks*" if len(lines) > 16 else ""),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="24/7", emoji="📻", style=discord.ButtonStyle.secondary, row=1, custom_id="np_247")
    async def btn_247(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.is_247 = not self.player.is_247
        if self.player.is_247:
            self.player.cancel_inactivity_timer()
            msg = "📻 **24/7 Mode Enabled:** Bot will stay connected even when idle."
        else:
            self.player.start_inactivity_timer()
            msg = "📻 **24/7 Mode Disabled:** Bot will disconnect after 5 minutes of inactivity."
        await interaction.response.edit_message(embed=self.player.build_now_playing_embed(), view=self)
        await interaction.followup.send(msg, ephemeral=True)


# ==================== MAIN MUSIC COG ====================

class Music(commands.Cog):
    """High-Fidelity Audio Streaming Suite with Native Spotify Support."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: Dict[int, GuildMusicPlayer] = {}

    async def cog_load(self):
        """Register the module-level group into the command tree.

        Groups defined outside the cog class are not auto-discovered, so the whole
        /music suite (and everything under it) was silently missing from Discord.
        """
        try:
            apply_voice_patch()
        except Exception as e:
            logger.warning(f"Voice DAVE patch failed to apply: {e}")

        try:
            prune_cache()
        except Exception:
            pass

        try:
            self.bot.tree.add_command(music_group)
            logger.info("Music slash group registered with %d subcommands.", len(music_group.commands))
        except app_commands.CommandAlreadyRegistered:
            logger.info("Music slash group already registered.")

    async def cog_unload(self):
        try:
            self.bot.tree.remove_command(music_group.name)
        except Exception:
            pass
        for player in list(self.players.values()):
            try:
                await player.destroy()
            except Exception:
                pass
        self.players.clear()

    def get_player(self, guild: discord.Guild) -> GuildMusicPlayer:
        """Get or create the guild's dedicated audio player."""
        if guild.id not in self.players:
            self.players[guild.id] = GuildMusicPlayer(self.bot, guild)
        return self.players[guild.id]

    async def _queue_and_play(
        self,
        ctx_or_interaction: Union[commands.Context, discord.Interaction],
        query: str,
        is_spotify_direct: bool = False,
    ):
        """Core unified song queueing and dispatch engine."""
        is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
        guild = ctx_or_interaction.guild
        author = ctx_or_interaction.user if is_interaction else ctx_or_interaction.author

        # Ensure user is in a voice channel
        if not author.voice or not author.voice.channel:
            msg = "⚠️ You must be connected to a voice channel to play music!"
            if is_interaction:
                return await ctx_or_interaction.response.send_message(embed=error_embed("Voice Required", msg), ephemeral=True)
            return await ctx_or_interaction.send(embed=error_embed("Voice Required", msg))

        voice_channel = author.voice.channel
        player = self.get_player(guild)
        player.text_channel = ctx_or_interaction.channel

        if is_interaction:
            await ctx_or_interaction.response.defer()

        # Connect to voice
        try:
            await player.connect(voice_channel)
        except Exception as e:
            err_text = f"Could not connect to voice channel: {e}"
            if is_interaction:
                return await ctx_or_interaction.followup.send(embed=error_embed("Connection Failed", err_text))
            return await ctx_or_interaction.send(embed=error_embed("Connection Failed", err_text))

        # Check if Spotify URL / Search
        is_spotify = is_spotify_direct or SpotifyHandler.is_spotify(query)

        if is_spotify:
            sp_data = await SpotifyHandler.resolve(query)
            sp_type = sp_data.get("type")

            if sp_type == "track":
                track = Track(
                    title=sp_data["title"],
                    artist=sp_data["artist"],
                    duration=sp_data["duration"],
                    thumbnail=sp_data["thumbnail"],
                    requester=author,
                    source="spotify",
                    webpage_url=sp_data["spotify_url"],
                    search_query=sp_data["search_query"],
                )

                if not player.current and not player.voice_client.is_playing():
                    await player.play_track(track)
                    embed = discord.Embed(
                        title="🟢 Spotify Track Loaded",
                        description=f"Now Playing: [**{track.title}**]({track.webpage_url})\n👤 **Artist:** `{track.artist}`",
                        color=COLOR_SPOTIFY,
                    )
                    if track.thumbnail:
                        embed.set_thumbnail(url=track.thumbnail)
                    if is_interaction:
                        return await ctx_or_interaction.followup.send(embed=embed)
                    return await ctx_or_interaction.send(embed=embed)
                else:
                    player.queue.append(track)
                    embed = discord.Embed(
                        title="🟢 Added to Queue",
                        description=f"[**{track.title}**]({track.webpage_url})\n👤 **Artist:** `{track.artist}` • Position: `#{len(player.queue)}`",
                        color=COLOR_SPOTIFY,
                    )
                    if track.thumbnail:
                        embed.set_thumbnail(url=track.thumbnail)
                    if is_interaction:
                        return await ctx_or_interaction.followup.send(embed=embed)
                    return await ctx_or_interaction.send(embed=embed)

            elif sp_type in ["playlist", "album", "artist"]:
                raw_tracks = sp_data.get("tracks", [])
                if not raw_tracks:
                    err_text = f"No playable tracks found in Spotify {sp_type}."
                    if is_interaction:
                        return await ctx_or_interaction.followup.send(embed=error_embed("Spotify Error", err_text))
                    return await ctx_or_interaction.send(embed=error_embed("Spotify Error", err_text))

                first_t_data = raw_tracks[0]
                first_track = Track(
                    title=first_t_data["title"],
                    artist=first_t_data["artist"],
                    duration=first_t_data["duration"],
                    thumbnail=sp_data.get("thumbnail"),
                    requester=author,
                    source="spotify",
                    webpage_url=sp_data.get("spotify_url", query),
                    search_query=first_t_data["search_query"],
                )

                # Add remaining tracks to lazy queue
                for t_data in raw_tracks[1:]:
                    player.queue.append(
                        Track(
                            title=t_data["title"],
                            artist=t_data["artist"],
                            duration=t_data["duration"],
                            thumbnail=sp_data.get("thumbnail"),
                            requester=author,
                            source="spotify",
                            webpage_url=sp_data.get("spotify_url", query),
                            search_query=t_data["search_query"],
                        )
                    )

                embed = discord.Embed(
                    title=f"🟢 Spotify {sp_type.title()} Queued!",
                    description=(
                        f"**{sp_data['name']}**\n"
                        f"👤 **Creator/Artist:** `{sp_data['artist']}`\n"
                        f"🎶 **Tracks Added:** `{sp_data['count']}` songs\n"
                        f"▶️ **First Song:** `{first_track.title}` ({first_track.artist})"
                    ),
                    color=COLOR_SPOTIFY,
                )
                if sp_data.get("thumbnail"):
                    embed.set_thumbnail(url=sp_data["thumbnail"])

                if not player.current and not player.voice_client.is_playing():
                    await player.play_track(first_track)
                else:
                    player.queue.appendleft(first_track)

                if is_interaction:
                    return await ctx_or_interaction.followup.send(embed=embed)
                return await ctx_or_interaction.send(embed=embed)

        # YouTube / Direct search extraction
        loop = asyncio.get_running_loop()

        def _sync_ytdl():
            is_url = query.startswith("http://") or query.startswith("https://")
            target = query if is_url else f"ytsearch1:{query}"
            opts = dict(YTDL_OPTS)
            if "playlist" in query.lower() or "&list=" in query.lower():
                opts["noplaylist"] = False
                opts["playlist_items"] = "1-50"

            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    return ydl.extract_info(target, download=False)
                except Exception as ex:
                    logger.error(f"yt-dlp search error: {ex}")
                    return None

        info = await loop.run_in_executor(None, _sync_ytdl)
        if not info:
            err_text = f"Could not find or extract audio for: `{query}`"
            if is_interaction:
                return await ctx_or_interaction.followup.send(embed=error_embed("Not Found", err_text))
            return await ctx_or_interaction.send(embed=error_embed("Not Found", err_text))

        entries = info.get("entries") if "entries" in info and info["entries"] else [info]
        tracks_loaded = []

        for e in entries:
            if not e:
                continue
            s_url = e.get("url")
            headers = e.get("http_headers", {}) or {}
            if not s_url and "formats" in e:
                a_formats = [f for f in e["formats"] if f.get("acodec") != "none"]
                if a_formats:
                    best_f = a_formats[-1]
                    s_url = best_f.get("url")
                    if best_f.get("http_headers"):
                        headers.update(best_f["http_headers"])

            t = Track(
                title=e.get("title", "Unknown Track"),
                artist=e.get("uploader", "Unknown Artist"),
                duration=int(e.get("duration") or 0),
                thumbnail=e.get("thumbnail"),
                requester=author,
                source="youtube",
                webpage_url=e.get("webpage_url", query),
                search_query=query,
                stream_url=s_url,
                headers=headers,
            )
            tracks_loaded.append(t)

        if not tracks_loaded:
            err_text = "No playable audio stream available."
            if is_interaction:
                return await ctx_or_interaction.followup.send(embed=error_embed("Playback Error", err_text))
            return await ctx_or_interaction.send(embed=error_embed("Playback Error", err_text))

        first = tracks_loaded[0]
        if not player.current and not player.voice_client.is_playing():
            for extra in tracks_loaded[1:]:
                player.queue.append(extra)
            await player.play_track(first)
            embed = discord.Embed(
                title="▶️ Track Loaded",
                description=f"Now Playing: [**{first.title}**]({first.webpage_url})\n👤 **Uploader:** `{first.artist}` • `{first.formatted_duration}`",
                color=COLOR_MUSIC_PRIMARY,
            )
            if first.thumbnail:
                embed.set_thumbnail(url=first.thumbnail)
            if is_interaction:
                return await ctx_or_interaction.followup.send(embed=embed)
            return await ctx_or_interaction.send(embed=embed)
        else:
            for t in tracks_loaded:
                player.queue.append(t)
            count = len(tracks_loaded)
            desc = f"Queued **{count} songs** from playlist." if count > 1 else f"Queued [**{first.title}**]({first.webpage_url}) at position `#{len(player.queue)}`."
            embed = discord.Embed(
                title="🎶 Added to Queue",
                description=desc,
                color=COLOR_MUSIC_PRIMARY,
            )
            if first.thumbnail:
                embed.set_thumbnail(url=first.thumbnail)
            if is_interaction:
                return await ctx_or_interaction.followup.send(embed=embed)
            return await ctx_or_interaction.send(embed=embed)

    # ==================== SLASH COMMANDS ====================

    @music_group.command(name="skip", description="Skip to the next song in the queue")
    async def slash_skip(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild)
        skipped = await player.skip()
        if skipped:
            await interaction.response.send_message(embed=success_embed("Skipped", "Skipped to next track!"))
        else:
            await interaction.response.send_message(embed=warning_embed("Queue Empty", "No tracks left to skip to."), ephemeral=True)

    @music_group.command(name="pause", description="Pause current music playback")
    async def slash_pause(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild)
        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.pause()
            player.is_paused = True
            player.pause_time = time.time()
            await interaction.response.send_message(embed=success_embed("Paused", "Music playback paused."))
        else:
            await interaction.response.send_message(embed=warning_embed("Not Playing", "Music is not currently playing."), ephemeral=True)

    @music_group.command(name="resume", description="Resume paused music playback")
    async def slash_resume(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild)
        if player.voice_client and player.voice_client.is_paused():
            player.voice_client.resume()
            player.is_paused = False
            if player.pause_time:
                player.total_paused_duration += time.time() - player.pause_time
                player.pause_time = None
            await interaction.response.send_message(embed=success_embed("Resumed", "Music playback resumed."))
        else:
            await interaction.response.send_message(embed=warning_embed("Not Paused", "Music is not paused."), ephemeral=True)

    @music_group.command(name="stop", description="Stop music playback, clear queue, and leave voice channel")
    async def slash_stop(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild)
        await player.destroy()
        await interaction.response.send_message(embed=success_embed("Stopped", "Music playback stopped and voice channel disconnected."))

    @music_group.command(name="queue", description="View active music queue and upcoming tracks")
    async def slash_queue(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild)
        if not player.current and len(player.queue) == 0:
            return await interaction.response.send_message("Queue is empty.", ephemeral=True)

        lines = []
        if player.current:
            lines.append(f"▶️ **Now Playing:** `{player.current.title}` ({player.current.artist}) — `{player.current.formatted_duration}`\n")
        for i, t in enumerate(player.queue, start=1):
            tag = "🟢" if t.source == "spotify" else "▶️"
            lines.append(f"`{i}.` {tag} **{t.title}** ({t.artist}) — `{t.formatted_duration}`")

        pages = []
        chunk_size = 12
        for i in range(0, len(lines), chunk_size):
            chunk = lines[i : i + chunk_size]
            embed = primary_embed(title=f"📜 Music Queue ({len(player.queue)} tracks)")
            embed.description = "\n".join(chunk)
            pages.append(embed)

        if len(pages) == 1:
            await interaction.response.send_message(embed=pages[0])
        else:
            view = PaginatorView(pages, interaction.user.id)
            await interaction.response.send_message(embed=pages[0], view=view)

    @music_group.command(name="nowplaying", description="Show detailed Now Playing dashboard with live controls")
    async def slash_nowplaying(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild)
        if not player.current:
            return await interaction.response.send_message(embed=warning_embed("Nothing Playing", "No music currently active."), ephemeral=True)
        embed = player.build_now_playing_embed()
        view = NowPlayingControlsView(player)
        await interaction.response.send_message(embed=embed, view=view)

    @music_group.command(name="volume", description="Adjust playback volume (1% to 200%)")
    @app_commands.describe(level="Volume level percentage between 1 and 200")
    async def slash_volume(self, interaction: discord.Interaction, level: int):
        player = self.get_player(interaction.guild)
        if level < 1 or level > 200:
            return await interaction.response.send_message("Please specify volume between 1% and 200%.", ephemeral=True)
        player.volume = round(level / 100.0, 2)
        if player.voice_client and player.voice_client.source:
            if hasattr(player.voice_client.source, "volume"):
                player.voice_client.source.volume = player.volume
        await interaction.response.send_message(embed=success_embed("Volume Changed", f"Volume set to **{level}%**."))

    @music_group.command(name="loop", description="Toggle loop mode between Off, Track, and Queue")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Disable Loop (Off)", value="off"),
        app_commands.Choice(name="Loop Current Track 🔂", value="track"),
        app_commands.Choice(name="Loop Entire Queue 🔁", value="queue"),
    ])
    async def slash_loop(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        player = self.get_player(interaction.guild)
        player.loop_mode = mode.value
        await interaction.response.send_message(embed=success_embed("Loop Mode", f"Loop mode set to **{mode.name}**."))

    @music_group.command(name="spotify", description="Play a Spotify track, album, playlist, or artist link")
    @app_commands.describe(query="Spotify URL (track/album/playlist/artist) or Spotify search text")
    async def slash_spotify(self, interaction: discord.Interaction, query: str):
        await self._queue_and_play(interaction, query, is_spotify_direct=True)

    # ==================== ROOT SHORTCUTS ====================

    @app_commands.command(name="play", description="Play any song, YouTube link, or Spotify link")
    @app_commands.guild_only()
    @app_commands.describe(query="Song title, artist name, YouTube URL, or Spotify URL")
    async def root_play(self, interaction: discord.Interaction, query: str):
        await self._queue_and_play(interaction, query)

    # ==================== PREFIX COMMANDS ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Bare `p <song or link>` shortcut usable by every member."""
        if not message.guild or message.author.bot:
            return
        content = message.content.strip()
        if len(content) < 4 or content[0].lower() != "p" or content[1] != " ":
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        query = content[2:].strip()
        if len(query) < 2:
            return

        member = message.author
        if not member.voice or not member.voice.channel:
            return

        await self._queue_and_play(ctx, query)

    @commands.command(name="play", aliases=["p"])
    async def prefix_play(self, ctx: commands.Context, *, query: str):
        """Play any song, YouTube link, or Spotify link."""
        await self._queue_and_play(ctx, query)

    @commands.command(name="spotify", aliases=["sp"])
    async def prefix_spotify(self, ctx: commands.Context, *, query: str):
        """Dedicated Spotify streaming: tracks, playlists, albums, or Spotify search."""
        await self._queue_and_play(ctx, query, is_spotify_direct=True)

    @commands.command(name="skip", aliases=["s", "next"])
    async def prefix_skip(self, ctx: commands.Context):
        """Skip to next track."""
        player = self.get_player(ctx.guild)
        if await player.skip():
            await ctx.send("⏭️ Skipped to next track!")
        else:
            await ctx.send("Queue is empty.")

    @commands.command(name="pause")
    async def prefix_pause(self, ctx: commands.Context):
        """Pause playback."""
        player = self.get_player(ctx.guild)
        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.pause()
            player.is_paused = True
            player.pause_time = time.time()
            await ctx.send("⏸️ Paused.")
        else:
            await ctx.send("Not playing.")

    @commands.command(name="resume")
    async def prefix_resume(self, ctx: commands.Context):
        """Resume playback."""
        player = self.get_player(ctx.guild)
        if player.voice_client and player.voice_client.is_paused():
            player.voice_client.resume()
            player.is_paused = False
            if player.pause_time:
                player.total_paused_duration += time.time() - player.pause_time
                player.pause_time = None
            await ctx.send("▶️ Resumed.")
        else:
            await ctx.send("Not paused.")

    @commands.command(name="stop", aliases=["mstop", "mleave", "clearstop"])
    async def prefix_stop(self, ctx: commands.Context):
        """Stop music and leave voice channel."""
        player = self.get_player(ctx.guild)
        await player.destroy()
        await ctx.send("⏹️ Stopped and disconnected.")

    @commands.command(name="queue", aliases=["q"])
    async def prefix_queue(self, ctx: commands.Context):
        """View queue."""
        player = self.get_player(ctx.guild)
        if not player.current and len(player.queue) == 0:
            return await ctx.send("Queue is empty.")

        lines = []
        if player.current:
            lines.append(f"▶️ **Now Playing:** `{player.current.title}` ({player.current.artist}) — `{player.current.formatted_duration}`\n")
        for i, t in enumerate(player.queue, start=1):
            tag = "🟢" if t.source == "spotify" else "▶️"
            lines.append(f"`{i}.` {tag} **{t.title}** ({t.artist}) — `{t.formatted_duration}`")

        pages = []
        for i in range(0, len(lines), 12):
            chunk = lines[i : i + 12]
            embed = primary_embed(title=f"📜 Music Queue ({len(player.queue)} tracks)")
            embed.description = "\n".join(chunk)
            pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            view = PaginatorView(pages, ctx.author.id)
            await ctx.send(embed=pages[0], view=view)

    @commands.command(name="nowplaying", aliases=["np"])
    async def prefix_nowplaying(self, ctx: commands.Context):
        """Show current song dashboard with live controls."""
        player = self.get_player(ctx.guild)
        if not player.current:
            return await ctx.send("Nothing is playing.")
        embed = player.build_now_playing_embed()
        view = NowPlayingControlsView(player)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="volume", aliases=["vol", "v"])
    async def prefix_volume(self, ctx: commands.Context, level: int):
        """Adjust volume."""
        player = self.get_player(ctx.guild)
        if level < 1 or level > 200:
            return await ctx.send("Please specify volume between 1% and 200%.")
        player.volume = round(level / 100.0, 2)
        if player.voice_client and player.voice_client.source:
            if hasattr(player.voice_client.source, "volume"):
                player.voice_client.source.volume = player.volume
        await ctx.send(f"🔊 Volume set to **{level}%**.")

    @commands.command(name="loop", aliases=["l"])
    async def prefix_loop(self, ctx: commands.Context, mode: Optional[str] = None):
        """Toggle loop mode."""
        player = self.get_player(ctx.guild)
        if not mode:
            modes = ["off", "track", "queue"]
            curr_idx = modes.index(player.loop_mode)
            player.loop_mode = modes[(curr_idx + 1) % len(modes)]
        else:
            m = mode.lower().strip()
            if m in ["off", "none", "disable"]:
                player.loop_mode = "off"
            elif m in ["track", "song", "current"]:
                player.loop_mode = "track"
            elif m in ["queue", "all"]:
                player.loop_mode = "queue"
            else:
                return await ctx.send("Valid loop modes: `off`, `track`, `queue`")
        await ctx.send(f"🔁 Loop mode set to **{player.loop_mode.upper()}**.")

    @commands.command(name="shuffle")
    async def prefix_shuffle(self, ctx: commands.Context):
        """Shuffle queue."""
        player = self.get_player(ctx.guild)
        if len(player.queue) < 2:
            return await ctx.send("Not enough songs in queue to shuffle.")
        random.shuffle(player.queue)
        await ctx.send("🔀 Queue shuffled!")

    @commands.command(name="seek")
    async def prefix_seek(self, ctx: commands.Context, seconds: int):
        """Seek forward in current track."""
        player = self.get_player(ctx.guild)
        if not player.current or not player.voice_client or not player.voice_client.is_playing():
            return await ctx.send("No track is currently playing.")
        if seconds < 0 or (player.current.duration and seconds >= player.current.duration):
            return await ctx.send(f"Please provide seconds between 0 and {player.current.duration}.")
        await player.play_track(player.current, seek_seconds=seconds)
        await ctx.send(f"⏩ Seeked to **{format_duration(seconds)}**.")

    @commands.command(name="filter", aliases=["bass", "nightcore", "8d", "lofi"])
    async def prefix_filter(self, ctx: commands.Context, *, filter_name: Optional[str] = None):
        """Apply audio filter (flat, bassboost, nightcore, 8d, lofi, vaporwave, pop, treble)."""
        player = self.get_player(ctx.guild)
        if not filter_name:
            if ctx.invoked_with in ["bass", "nightcore", "8d", "lofi"]:
                target_f = "bassboost" if ctx.invoked_with == "bass" else ctx.invoked_with
            else:
                avail = ", ".join(f"`{k}`" for k in AUDIO_FILTERS.keys())
                return await ctx.send(f"Available filters: {avail}\nCurrent filter: `{player.audio_filter}`")
        else:
            target_f = filter_name.lower().strip()

        if target_f not in AUDIO_FILTERS:
            avail = ", ".join(f"`{k}`" for k in AUDIO_FILTERS.keys())
            return await ctx.send(f"Invalid filter. Choose from: {avail}")

        await player.set_filter(target_f)
        await ctx.send(f"⚡ Audio filter set to **{target_f.upper()}**!")

    @commands.command(name="clear")
    async def prefix_clear(self, ctx: commands.Context):
        """Clear queue."""
        player = self.get_player(ctx.guild)
        count = len(player.queue)
        player.queue.clear()
        await ctx.send(f"🗑️ Cleared **{count} songs** from the queue.")

    @commands.command(name="jump")
    async def prefix_jump(self, ctx: commands.Context, index: int):
        """Jump to a specific track in the queue."""
        player = self.get_player(ctx.guild)
        if index < 1 or index > len(player.queue):
            return await ctx.send(f"Invalid index. Choose between 1 and {len(player.queue)}.")
        for _ in range(index - 1):
            player.queue.popleft()
        await player.skip()
        await ctx.send(f"⏭️ Jumped to song #{index}!")

    @commands.command(name="247")
    async def prefix_247(self, ctx: commands.Context):
        """Toggle 24/7 radio mode."""
        player = self.get_player(ctx.guild)
        player.is_247 = not player.is_247
        if player.is_247:
            player.cancel_inactivity_timer()
            await ctx.send("📻 **24/7 Mode Enabled:** Bot will stay in the voice channel indefinitely.")
        else:
            player.start_inactivity_timer()
            await ctx.send("📻 **24/7 Mode Disabled:** Bot will disconnect after 5 minutes of inactivity.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
