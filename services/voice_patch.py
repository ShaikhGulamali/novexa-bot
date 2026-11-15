"""NOVEXA voice fixes for discord.py: DAVE passthrough arming + protocol logging.

Why this exists
---------------
Discord requires the DAVE (E2EE) handshake for voice. discord.py 2.7.1 only calls
`DaveSession.execute_transition` when it exists and arms passthrough for 10 seconds
on a session downgrade, which is not enough:

* A `DaveSession` starts in `pending` and never reaches `ready` unless transitions
  are signalled into it, so `can_encrypt` stays False and opus frames go out as
  plain RTP, which Discord drops -> the bot reports playing but is silent.
* The 10 second passthrough window expires mid-track.

So: always signal transitions into the session, arm passthrough for the whole
connection, renew it periodically, and log the voice protocol state so silence is
never invisible again.
"""

import asyncio
import ctypes
import logging
import platform
import struct

import discord  # noqa: F401  (ensures discord is initialised before patching)
from discord.gateway import DiscordVoiceWebSocket
from discord.voice_state import VoiceConnectionState

logger = logging.getLogger("novexa.voice_patch")

_PATCHED = False
_PASSTHROUGH_SECONDS = 7200
_KEEPALIVE: dict = {}


def _timer_resolution():
    if platform.system() != "Windows":
        return
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
        logger.info("[VOICE] timer resolution 1ms")
    except Exception as e:
        logger.debug(f"[VOICE] timer resolution: {e}")


def _arm(state, reason: str = ""):
    session = getattr(state, "dave_session", None)
    if not session:
        return
    try:
        session.set_passthrough_mode(True, _PASSTHROUGH_SECONDS)
    except Exception as e:
        logger.debug(f"[VOICE] passthrough arm failed ({reason}): {e}")


def _log_state(state, reason: str):
    session = getattr(state, "dave_session", None)
    logger.info(
        "[VOICE] %s | dave_ver=%s ready=%s encrypt=%s status=%s",
        reason,
        getattr(state, "dave_protocol_version", None),
        getattr(session, "ready", None) if session else None,
        getattr(state, "can_encrypt", None),
        getattr(session, "status", None) if session else None,
    )


def _keepalive(state):
    key = getattr(state.guild, "id", id(state))
    task = _KEEPALIVE.get(key)
    if task and not task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    async def _run():
        while True:
            await asyncio.sleep(60)
            if not getattr(state, "dave_session", None):
                return
            if not getattr(state, "voice_client", None) or not state.voice_client.is_connected():
                return
            _arm(state, "keepalive")

    _KEEPALIVE[key] = loop.create_task(_run())


def apply_voice_patch():
    global _PATCHED
    if _PATCHED:
        return
    _timer_resolution()

    orig_received = DiscordVoiceWebSocket.received_message
    orig_binary = DiscordVoiceWebSocket.received_binary_message
    orig_transition = VoiceConnectionState._execute_transition
    orig_reinit = VoiceConnectionState.reinit_dave_session

    async def received_binary_message(self, msg: bytes):
        await orig_binary(self, msg)
        state = self._connection
        session = getattr(state, "dave_session", None) if state else None
        if not session:
            return

        # MLS commit / welcome carry the transition id; davey only becomes
        # encrypt-capable after the session is told to execute that transition.
        # discord.py never signals the session, so audio stays plaintext and the
        # receiver drops every packet -> "connected, playing, silent".
        if len(msg) > 4 and msg[2] in (
            DiscordVoiceWebSocket.MLS_ANNOUNCE_COMMIT_TRANSITION,
            DiscordVoiceWebSocket.MLS_WELCOME,
        ):
            transition_id = struct.unpack_from(">H", msg, 3)[0]
            try:
                # davey keeps its own transition map: prepare -> execute is what
                # actually installs the epoch key. Without it `ready` stays False,
                # `can_encrypt` stays False, packets go out unencrypted and the
                # listener hears nothing while the bot reports playing.
                session.prepare_transition(transition_id, state.dave_protocol_version or 1)
                session.execute_transition(transition_id)
                logger.info(
                    "[VOICE] session transition %s installed | ready=%s status=%s epoch=%s users=%d",
                    transition_id,
                    getattr(session, "ready", None),
                    getattr(session, "status", None),
                    getattr(session, "epoch", None),
                    len(session.get_user_ids() or []),
                )
            except Exception as e:
                logger.warning(f"[VOICE] transition {transition_id} install failed: {e}")

    async def received_message(self, msg):
        await orig_received(self, msg)
        op = msg.get("op")
        state = self._connection
        if not state or not getattr(state, "dave_session", None):
            return
        if op == DiscordVoiceWebSocket.DAVE_PREPARE_TRANSITION:
            # The library tracks the pending map; do not signal the session here.
            # Signalling prepare twice leaves davey stuck in `pending`.
            _arm(state, "prepare_transition")
            logger.info("[VOICE] prepare_transition %s", msg.get("d"))
        elif op == DiscordVoiceWebSocket.DAVE_EXECUTE_TRANSITION:
            data = msg.get("d") or {}
            logger.info("[VOICE] execute_transition id=%s", data.get("transition_id"))
        elif op in (
            DiscordVoiceWebSocket.DAVE_PREPARE_EPOCH,
            DiscordVoiceWebSocket.MLS_WELCOME,
            DiscordVoiceWebSocket.MLS_COMMIT_WELCOME,
            DiscordVoiceWebSocket.MLS_ANNOUNCE_COMMIT_TRANSITION,
        ):
            logger.info("[VOICE] mls op=%s", op)
            _arm(state, f"mls_{op}")
        if op in (DiscordVoiceWebSocket.DAVE_EXECUTE_TRANSITION, DiscordVoiceWebSocket.MLS_WELCOME):
            _log_state(state, f"op_{op}_post")

    async def execute_transition(self, transition_id: int):
        await orig_transition(self, transition_id)
        session = getattr(self, "dave_session", None)
        if session:
            try:
                # discord.py leaves the session unsignalled ("in the future, ...")
                session.execute_transition(transition_id)
                logger.info(
                    "[VOICE] session transition executed id=%s ready=%s status=%s",
                    transition_id,
                    getattr(session, "ready", None),
                    getattr(session, "status", None),
                )
            except Exception as e:
                logger.debug(f"[VOICE] session execute_transition: {e}")
            _arm(self, "execute_transition")
            _keepalive(self)

    async def reinit_dave_session(self):
        await orig_reinit(self)
        session = getattr(self, "dave_session", None)
        if session:
            _arm(self, "reinit")
            _log_state(self, "reinit")
            _keepalive(self)

    DiscordVoiceWebSocket.received_message = received_message
    DiscordVoiceWebSocket.received_binary_message = received_binary_message
    VoiceConnectionState._execute_transition = execute_transition
    VoiceConnectionState.reinit_dave_session = reinit_dave_session

    _PATCHED = True
    logger.info("[VOICE] DAVE patch applied (passthrough=%ss)", _PASSTHROUGH_SECONDS)
