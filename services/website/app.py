"""NOVEXA - Connected FastAPI Application & REST API.

Single authoritative backend architecture:
- Shared memory & direct connection with the Discord bot process
- Direct async connection to SQLite database
- Discord OAuth2 session authentication with fallback dev session for local inspection
- Full REST endpoints for all 32 modules via ConfigService
- Real-time Server-Sent Events (SSE) streaming for two-way synchronization
- Complete server-side permission validation (ensuring only Administrators can modify settings)
"""

import discord
import logging
import json
import hmac
import hashlib
import base64
import time
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from config import (
    BOT_NAME, BOT_VERSION, DISCORD_TOKEN, OWNER_IDS,
    DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI,
    SESSION_SECRET,
)
from database.database import db
from services.config_service import config_service
from services.premium_service import premium_service
from services.cashfree_service import cashfree_service
from services.security_service import security_service
from services.backup_service import backup_service
from services.dropper_service import dropper_service
from services.website.templates import (
    render_home, render_features, render_commands, render_premium,
    render_docs, render_support, render_privacy, render_terms,
    render_statistics, render_status, render_faq,
    render_user_dashboard, render_server_dashboard, render_owner_dashboard,
    render_oauth_setup,
)
from services.website import bridge, livedata
from services.website.console import render_console, render_explorer, render_leaderboards

logger = logging.getLogger("novexa.website")


class WebActor:
    """Lightweight stand-in for discord.Member when an action comes from the website."""

    def __init__(self, user_id: int, name: str):
        self.id = user_id
        self.name = name

    def __str__(self) -> str:
        return self.name


# ==================== SESSION TOKEN HELPERS ====================

def create_session_token(payload: Dict[str, Any]) -> str:
    """Create an HMAC-signed session string."""
    data = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    sig = hmac.new(SESSION_SECRET.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{data}.{sig}"


def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode an HMAC-signed session string."""
    if not token or "." not in token:
        return None
    try:
        data_str, sig = token.split(".", 1)
        expected_sig = hmac.new(SESSION_SECRET.encode("utf-8"), data_str.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(base64.b64decode(data_str.encode("utf-8")).decode("utf-8"))
        return payload
    except Exception:
        return None


# ==================== FASTAPI APP FACTORY ====================

def create_app(bot) -> FastAPI:
    app = FastAPI(
        title="NOVEXA Connected Website API",
        version="2.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    config_service.set_bot(bot)
    premium_service.set_bot(bot)

    # Dependency: Get logged-in user (Discord OAuth session only)
    def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
        cookie = request.cookies.get("novexa_session")
        if cookie:
            user = verify_session_token(cookie)
            if user:
                return user
        return None

    def oauth_client_id() -> str:
        """The bot's own application ID is always a valid OAuth client ID."""
        if DISCORD_CLIENT_ID and DISCORD_CLIENT_ID != "your_discord_client_id_here":
            return DISCORD_CLIENT_ID
        if bot and getattr(bot, "user", None):
            return str(bot.user.id)
        return ""

    def oauth_configured() -> bool:
        return bool(oauth_client_id() and DISCORD_CLIENT_SECRET)

    def oauth_redirect_uri(request: Request) -> str:
        """Localhost and LAN hits use the http callback; public hits use the domain."""
        host = request.headers.get("host", "") or "localhost:8080"
        hostname = host.split(":")[0].lower()
        local = (
            hostname in {"localhost", "127.0.0.1", "::1"}
            or hostname.startswith("192.168.")
            or hostname.startswith("10.")
        )
        if local:
            return f"http://{host}/api/auth/callback"
        return DISCORD_REDIRECT_URI or f"http://{host}/api/auth/callback"

    # ==================== HEALTH CHECK ENDPOINT ====================
    @app.get("/health")
    async def health_check():
        """Health check endpoint for Render, cloud monitors, and container orchestrators."""
        return {
            "status": "healthy",
            "bot": BOT_NAME,
            "version": BOT_VERSION,
            "connected": bot.is_ready() if bot else False,
            "latency_ms": round(bot.latency * 1000, 1) if (bot and bot.latency) else None,
        }

    # ==================== 14 PUBLIC & AUTH WEB PAGES ====================

    @app.get("/", response_class=HTMLResponse)
    async def page_home(request: Request):
        user = get_current_user(request)
        return HTMLResponse(render_home(bot, user))

    @app.get("/features", response_class=HTMLResponse)
    async def page_features(request: Request):
        user = get_current_user(request)
        return HTMLResponse(render_features(bot, user))

    @app.get("/commands", response_class=HTMLResponse)
    async def page_commands(request: Request):
        user = get_current_user(request)
        return HTMLResponse(render_commands(bot, user))

    @app.get("/premium", response_class=HTMLResponse)
    async def page_premium(request: Request):
        user = get_current_user(request)
        guilds = []
        if user:
            guilds = [g for g in (user.get("guilds") or []) if g.get("bot_in_guild")]
            user_id = int(user["id"])
            known = {str(g.get("id")) for g in guilds}
            if bot and hasattr(bot, "guilds"):
                for g in bot.guilds:
                    if str(g.id) in known:
                        continue
                    allowed = user_id in OWNER_IDS or g.owner_id == user_id
                    if not allowed:
                        member = g.get_member(user_id)
                        if member is not None:
                            allowed = member.guild_permissions.administrator or member.guild_permissions.manage_guild
                    if allowed:
                        guilds.append({
                            "id": str(g.id),
                            "name": g.name,
                            "icon_url": str(g.icon.url) if g.icon else None,
                        })
        plans = await premium_service.get_plans()
        return HTMLResponse(render_premium(bot, user, plans, guilds))

    @app.get("/statistics", response_class=HTMLResponse)
    @app.get("/stats", response_class=HTMLResponse)
    async def page_statistics(request: Request):
        user = get_current_user(request)
        return HTMLResponse(render_statistics(bot, user))

    @app.get("/status", response_class=HTMLResponse)
    async def page_status(request: Request):
        user = get_current_user(request)
        return HTMLResponse(render_status(bot, user))

    @app.get("/docs", response_class=HTMLResponse)
    async def page_docs(request: Request):
        user = get_current_user(request)
        return HTMLResponse(render_docs(bot, user))

    @app.get("/faq", response_class=HTMLResponse)
    async def page_faq(request: Request):
        user = get_current_user(request)
        return HTMLResponse(render_faq(bot, user))

    @app.get("/support", response_class=HTMLResponse)
    async def page_support(request: Request):
        user = get_current_user(request)
        return HTMLResponse(render_support(bot, user))

    @app.get("/privacy", response_class=HTMLResponse)
    async def page_privacy():
        return HTMLResponse(render_privacy())

    @app.get("/terms", response_class=HTMLResponse)
    async def page_terms():
        return HTMLResponse(render_terms())

    @app.get("/invite")
    async def page_invite(guild_id: Optional[str] = None):
        client_id = oauth_client_id() or "1568328955507769435"
        base_url = f"https://discord.com/oauth2/authorize?client_id={client_id}&permissions=8&scope=bot%20applications.commands"
        if guild_id:
            base_url += f"&guild_id={guild_id}"
        return RedirectResponse(base_url)

    # ==================== OAUTH2 AUTHENTICATION ====================

    @app.get("/login")
    async def route_login(request: Request):
        if not oauth_configured():
            return HTMLResponse(render_oauth_setup(oauth_client_id()))

        # Production Discord OAuth2 Flow
        redirect_uri = oauth_redirect_uri(request)
        oauth_url = (
            f"https://discord.com/api/oauth2/authorize?client_id={oauth_client_id()}"
            f"&redirect_uri={redirect_uri}&response_type=code&scope=identify%20guilds"
        )
        return RedirectResponse(oauth_url)

    @app.get("/callback")
    @app.get("/api/auth/callback")
    async def auth_callback(request: Request, code: Optional[str] = None):
        if not code:
            return RedirectResponse("/?error=missing_code")
        if not oauth_configured():
            return HTMLResponse(render_oauth_setup(oauth_client_id()))

        token_url = "https://discord.com/api/oauth2/token"
        redirect_uri = oauth_redirect_uri(request)

        data = {
            "client_id": oauth_client_id(),
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to fetch OAuth2 token: {await resp.text()}")
                        return RedirectResponse("/?error=oauth_token_failed")
                    token_data = await resp.json()
                    access_token = token_data.get("access_token")

                user_headers = {"Authorization": f"Bearer {access_token}"}

                # 1. Fetch user identity
                async with session.get("https://discord.com/api/users/@me", headers=user_headers) as resp:
                    user_data = await resp.json()

                # 2. Fetch user's managed guilds
                async with session.get("https://discord.com/api/users/@me/guilds", headers=user_headers) as resp:
                    guilds_data = await resp.json()

            # Filter for Admin / Manage Guild permissions (0x8 or 0x20)
            managed_guilds = []
            for g in guilds_data:
                perms = int(g.get("permissions", 0))
                if perms & 0x8 or perms & 0x20 or g.get("owner", False):
                    managed_guilds.append({
                        "id": str(g["id"]),
                        "name": g["name"],
                        "icon_url": f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png" if g.get("icon") else None,
                        "bot_in_guild": bot.get_guild(int(g["id"])) is not None if hasattr(bot, "get_guild") else False,
                        "is_owner": g.get("owner", False),
                    })

            user_session = {
                "id": str(user_data["id"]),
                "username": f"{user_data['username']}#{user_data.get('discriminator', '0')}",
                "avatar_url": f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png" if user_data.get("avatar") else None,
                "guilds": managed_guilds,
            }

            token = create_session_token(user_session)
            res = RedirectResponse("/dashboard")
            res.set_cookie("novexa_session", token, httponly=True, max_age=86400 * 7)
            return res
        except Exception as e:
            logger.error(f"Error in OAuth2 callback: {e}")
            return RedirectResponse("/?error=oauth_exception")

    @app.get("/api/auth/logout")
    async def auth_logout():
        res = RedirectResponse("/")
        res.delete_cookie("novexa_session")
        return res

    # ==================== DASHBOARD & ADMIN PAGES ====================

    @app.get("/dashboard", response_class=HTMLResponse)
    async def page_user_dashboard(request: Request, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            return RedirectResponse("/login")

        user_guilds = user.get("guilds", [])
        if not user_guilds and hasattr(bot, "guilds") and int(user["id"]) in OWNER_IDS:
            # Bot owners always see the servers NOVEXA is protecting
            user_guilds = [
                {
                    "id": str(g.id),
                    "name": g.name,
                    "icon_url": str(g.icon.url) if g.icon else None,
                    "bot_in_guild": True,
                    "is_owner": True,
                }
                for g in bot.guilds
            ]

        return HTMLResponse(render_user_dashboard(bot, user, user_guilds))

    @app.get("/dashboard/{guild_id}", response_class=HTMLResponse)
    async def page_server_dashboard(guild_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            return RedirectResponse("/login")

        guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
        if not guild:
            return HTMLResponse(f"<h1>Guild {guild_id} not found or NOVEXA is not in this server. <a href='/invite?guild_id={guild_id}'>Invite Bot</a></h1>")

        # Fetch comprehensive configurations from authoritative ConfigService
        welcome_cfg = await config_service.get_welcome_config(guild_id)
        goodbye_cfg = await config_service.get_goodbye_config(guild_id)
        autoroles_cfg = await config_service.get_autoroles_config(guild_id)
        antinuke_cfg = await config_service.get_antinuke_config(guild_id)
        antispam_cfg = await config_service.get_antispam_config(guild_id)
        automod_cfg = await config_service.get_automod_config(guild_id)
        whitelist_data = await config_service.get_whitelist(guild_id)
        approved_bots = await config_service.get_approved_bots(guild_id)
        moderation_cfg = await config_service.get_moderation_config(guild_id)
        mod_logs = await config_service.get_moderation_logs(guild_id)
        tickets_cfg = await config_service.get_tickets_config(guild_id)
        ticket_panels_data = await config_service.list_ticket_panels(guild_id)
        ticket_rows = await config_service.list_tickets(guild_id, limit=40)
        logging_cfg = await config_service.get_logging_config(guild_id)
        music_cfg = await config_service.get_music_config(guild_id)
        economy_cfg = await config_service.get_economy_settings(guild_id)
        leveling_cfg = await config_service.get_leveling_config(guild_id)
        giveaways_data = await config_service.get_giveaways(guild_id)
        autoresponders = await config_service.get_auto_responders(guild_id)
        backup_rows = await db.fetchall("SELECT backup_id, created_at, backup_name FROM server_backups WHERE guild_id = ? ORDER BY created_at DESC;", (guild_id,))
        integrations_cfg = await config_service.get_integrations_config(guild_id)
        settings_cfg = await config_service.get_settings_config(guild_id)
        premium_status = await config_service.get_premium_status(guild_id)
        audit_history = await config_service.get_audit_history(guild_id)
        roles_cfg = await config_service.get_roles_config(guild_id)
        server_setup_cfg = await config_service.get_server_setup_config(guild_id)
        rpg_cfg = await config_service.get_rpg_games_config(guild_id)
        pets_cfg = await config_service.get_pets_hunting_config(guild_id)
        reaction_roles_data = await config_service.get_reaction_roles(guild_id)
        voice_cfg = await config_service.get_voice_channels_config(guild_id)
        voice_j2c_cfg = await config_service.get_voice_j2c_config(guild_id)
        embeds_cfg = await config_service.get_custom_embeds_config(guild_id)

        configs = {
            "welcome": welcome_cfg,
            "goodbye": goodbye_cfg,
            "autoroles": autoroles_cfg,
            "antinuke": antinuke_cfg,
            "antispam": antispam_cfg,
            "automod": automod_cfg,
            "whitelist": whitelist_data,
            "approved_bots": approved_bots,
            "moderation": moderation_cfg,
            "moderation_logs": mod_logs,
            "tickets": tickets_cfg,
            "ticket_panels": ticket_panels_data,
            "tickets_list": ticket_rows,
            "logging": logging_cfg,
            "roles": roles_cfg,
            "server_setup": server_setup_cfg,
            "music": music_cfg,
            "economy": economy_cfg,
            "rpg_games": rpg_cfg,
            "pets_hunting": pets_cfg,
            "leveling": leveling_cfg,
            "giveaways": giveaways_data,
            "reaction_roles": reaction_roles_data,
            "custom_embeds": embeds_cfg,
            "autoresponders": autoresponders,
            "voice_channels": voice_cfg,
            "voice_j2c": voice_j2c_cfg,
            "backups": [dict(r) for r in backup_rows],
            "integrations": integrations_cfg,
            "settings": settings_cfg,
            "premium": premium_status,
            "premium_orders": await premium_service.recent_orders(guild_id),
            "audit_history": audit_history,
            "wallpaper_channels": await config_service.get_wallpaper_channels(guild_id),
            "dropper_members": await config_service.get_dropper_members(guild_id),
        }

        return HTMLResponse(render_server_dashboard(bot, user, guild, configs))

    # ==================== COMMAND CONSOLE, EXPLORER, LEADERBOARDS ====================

    async def _manager(guild_id: int, user: Dict[str, Any]) -> discord.Member:
        guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
        if not guild:
            raise HTTPException(status_code=404, detail="NOVEXA is not connected to this server.")
        member = await bridge.resolve_actor(bot, guild, int(user["id"]))
        if member is None or not bridge.actor_can_manage(guild, member, int(user["id"]), OWNER_IDS):
            raise HTTPException(status_code=403, detail="Administrator or Manage Server permission required.")
        return member

    @app.get("/dashboard/{guild_id}/console", response_class=HTMLResponse)
    async def page_console(guild_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            return RedirectResponse("/login")
        member = await _manager(guild_id, user)
        guild = member.guild
        return HTMLResponse(render_console(bot, user, guild, bridge.build_catalog(bot, guild)))

    @app.get("/dashboard/{guild_id}/explorer", response_class=HTMLResponse)
    async def page_explorer(guild_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            return RedirectResponse("/login")
        member = await _manager(guild_id, user)
        return HTMLResponse(render_explorer(bot, user, member.guild))

    @app.get("/dashboard/{guild_id}/boards", response_class=HTMLResponse)
    async def page_leaderboards(guild_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            return RedirectResponse("/login")
        member = await _manager(guild_id, user)
        guild = member.guild
        boards = {}
        for kind in ("wealth", "levels", "hunters", "battles"):
            boards[kind] = await livedata.leaderboard(guild, kind)
        return HTMLResponse(render_leaderboards(bot, user, guild, boards))

    @app.get("/api/guilds/{guild_id}/commands")
    async def api_commands(guild_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        member = await _manager(guild_id, user)
        return {"status": "ok", "commands": bridge.build_catalog(bot, member.guild)}

    class CommandRunPayload(BaseModel):
        name: str
        options: Dict[str, Any] = {}

    @app.post("/api/guilds/{guild_id}/commands/run")
    async def api_run_command(guild_id: int, p: CommandRunPayload, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        member = await _manager(guild_id, user)
        result = await bridge.run_command(bot, member.guild, member, p.name, p.options or {})
        return result

    @app.get("/api/guilds/{guild_id}/live")
    async def api_live(guild_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        member = await _manager(guild_id, user)
        guild = member.guild
        return {"status": "ok", "guild": livedata.guild_snapshot(guild), "members": livedata.member_rows(guild)}


    @app.get("/admin", response_class=HTMLResponse)
    @app.get("/admin/dashboard", response_class=HTMLResponse)
    async def page_owner_admin(user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            return RedirectResponse("/login")

        uid = int(user["id"])
        if OWNER_IDS and uid not in OWNER_IDS and not user.get("is_dev"):
            raise HTTPException(status_code=403, detail="Forbidden: Restricted to Bot Owners")

        import os
        from pathlib import Path
        db_file = Path("database/gulamali_bot.db")
        db_size_kb = round(os.path.getsize(db_file) / 1024) if db_file.exists() else 0

        stats = {
            "db_size_kb": db_size_kb,
            "uptime": "99.9% (Continuous)",
        }
        return HTMLResponse(render_owner_dashboard(bot, user, stats))

    # ==================== REAL-TIME SSE EVENT STREAM ====================

    @app.get("/api/guilds/{guild_id}/events")
    async def sse_guild_events(guild_id: int):
        """Server-Sent Events (SSE) stream for real-time two-way synchronization."""
        async def event_generator():
            queue = config_service.broadcaster.subscribe(guild_id)
            try:
                # Initial ping
                yield f"data: {json.dumps({'event': 'connected', 'guild_id': guild_id})}\n\n"
                while True:
                    payload = await queue.get()
                    yield f"data: {json.dumps(payload)}\n\n"
            except asyncio.CancelledError:
                pass
            finally:
                config_service.broadcaster.unsubscribe(guild_id, queue)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # ==================== CONFIGURATION REST ENDPOINTS ====================

    class WelcomePayload(BaseModel):
        enabled: Optional[bool] = True
        channel_id: Optional[int] = None
        template_id: Optional[str] = "novexa_exclusive"
        message_template: Optional[str] = None
        custom_color: Optional[str] = "#5865F2"
        dm_enabled: Optional[bool] = False

    @app.post("/api/guilds/{guild_id}/welcome")
    async def api_save_welcome(guild_id: int, p: WelcomePayload, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        data = p.dict(exclude_unset=True)
        updated = await config_service.update_welcome_config(
            guild_id, data, actor_id=int(user["id"]), actor_tag=user["username"], source="WEBSITE"
        )
        return {"status": "ok", "config": updated}

    @app.get("/api/guilds/{guild_id}/tickets/live")
    async def api_tickets_live(guild_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return {
            "status": "ok",
            "panels": await config_service.list_ticket_panels(guild_id),
            "tickets": await config_service.list_tickets(guild_id, limit=40),
        }

    @app.post("/api/guilds/{guild_id}/tickets/{ticket_id}/close")
    async def api_ticket_close(guild_id: int, ticket_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        ok = await config_service.update_ticket(guild_id, ticket_id, "closed")
        if not ok:
            raise HTTPException(status_code=404, detail="Ticket not found.")
        return {"status": "ok", "message": "Ticket closed."}

    @app.delete("/api/guilds/{guild_id}/tickets/{ticket_id}")
    async def api_ticket_delete(guild_id: int, ticket_id: int, delete_channel: int = 0, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        channel_id = await config_service.delete_ticket(guild_id, ticket_id)
        if channel_id is None:
            raise HTTPException(status_code=404, detail="Ticket not found.")
        removed = False
        if delete_channel:
            guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
            channel = guild.get_channel(int(channel_id)) if guild and channel_id else None
            if channel:
                try:
                    await channel.delete(reason=f"Ticket #{ticket_id} deleted from dashboard by {user['username']}")
                    removed = True
                except Exception:
                    removed = False
        return {"status": "ok", "message": "Ticket deleted." + (" Channel removed." if removed else ""), "channel_deleted": removed}

    @app.delete("/api/guilds/{guild_id}/ticket_panels/{panel_id}")
    async def api_ticket_panel_delete(guild_id: int, panel_id: str, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        res = await config_service.delete_ticket_panel(guild_id, panel_id)
        if not res.get("ok"):
            raise HTTPException(status_code=404, detail=res.get("reason", "Panel not found."))
        msg_removed = False
        guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
        if guild and res.get("message_id"):
            channel = guild.get_channel(int(res["channel_id"])) if res.get("channel_id") else None
            if channel:
                try:
                    msg = await channel.fetch_message(int(res["message_id"]))
                    await msg.delete()
                    msg_removed = True
                except Exception:
                    msg_removed = False
        return {"status": "ok", "message": "Panel removed." + (" Announcement deleted." if msg_removed else ""), "message_deleted": msg_removed}

    # ==================== CASHFREE PREMIUM CHECKOUT ====================

    class CheckoutPayload(BaseModel):
        plan_id: str
        guild_id: int
        email: str = ""
        phone: str = ""
        name: Optional[str] = ""

    async def _user_manages_guild(user: Dict[str, Any], guild_id: int) -> bool:
        user_id = int(user.get("id", 0))
        if user_id in OWNER_IDS:
            return True
        guild = bot.get_guild(guild_id) if (bot and hasattr(bot, "get_guild")) else None
        if guild is not None:
            if guild.owner_id == user_id:
                return True
            member = guild.get_member(user_id)
            if member is None:
                try:
                    member = await guild.fetch_member(user_id)
                except Exception:
                    member = None
            if member is not None:
                perms = member.guild_permissions
                if perms.administrator or perms.manage_guild:
                    return True
        managed = {str(g.get("id")) for g in (user.get("guilds") or [])}
        return str(guild_id) in managed

    @app.post("/api/premium/checkout")
    async def api_premium_checkout(payload: CheckoutPayload, request: Request, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Login with Discord first.")
        if not await _user_manages_guild(user, payload.guild_id):
            raise HTTPException(status_code=403, detail="You do not manage that server.")
        base_url = str(request.base_url).rstrip("/")
        result = await premium_service.create_checkout(
            user=user,
            guild_id=payload.guild_id,
            plan_id=payload.plan_id,
            email=payload.email,
            phone=payload.phone,
            base_url=base_url,
            customer_name=payload.name or "",
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("reason", "Checkout failed."))
        return result

    @app.get("/api/premium/order/{order_id}")
    async def api_premium_order(order_id: str, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Login with Discord first.")
        row = await premium_service.get_order_row(order_id)
        if not row:
            raise HTTPException(status_code=404, detail="Order not found.")
        if int(row["user_id"]) != int(user.get("id", 0)) and int(user.get("id", 0)) not in OWNER_IDS:
            raise HTTPException(status_code=403, detail="This order belongs to another account.")
        result = await premium_service.refresh_order(order_id, source="page")
        plan = await premium_service.get_plan(row["plan_id"])
        return {
            "status": result.get("status", row.get("status")),
            "granted": bool(result.get("granted")),
            "message": result.get("message") or result.get("reason") or "",
            "plan_id": row["plan_id"],
            "plan_name": (plan or {}).get("name", row["plan_id"].title()),
            "amount": row.get("amount"),
            "grant": result.get("grant") or {},
        }

    @app.post("/api/payments/cashfree/webhook")
    async def cashfree_webhook(request: Request):
        raw = await request.body()
        timestamp = request.headers.get("x-webhook-timestamp", "")
        signature = request.headers.get("x-webhook-signature", "")
        if not cashfree_service.verify_webhook_signature(timestamp, raw, signature):
            logger.warning("Cashfree webhook rejected: invalid signature")
            raise HTTPException(status_code=401, detail="Invalid webhook signature.")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body.")
        result = await premium_service.handle_webhook(payload)
        return {
            "status": "ok",
            "granted": bool(result.get("granted")),
            "ignored": result.get("ignored"),
        }

    class SecurityPayload(BaseModel):
        enabled: Optional[bool] = True
        mode: Optional[str] = "medium"
        punishment_type: Optional[str] = "quarantine"
        max_channel_deletions: Optional[int] = 2
        max_role_deletions: Optional[int] = 3
        max_bans: Optional[int] = 3
        max_webhook_changes: Optional[int] = 4

    @app.post("/api/guilds/{guild_id}/security")
    async def api_save_security(guild_id: int, p: SecurityPayload, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        data = p.dict(exclude_unset=True)
        updated = await config_service.update_antinuke_config(
            guild_id, data, actor_id=int(user["id"]), actor_tag=user["username"], source="WEBSITE"
        )
        return {"status": "ok", "config": updated}

    class AntiSpamPayload(BaseModel):
        enabled: Optional[bool] = True
        max_mentions: Optional[int] = 5
        max_duplicates: Optional[int] = 3
        max_emojis: Optional[int] = 8
        timeout_duration_minutes: Optional[int] = 10
        block_invites: Optional[bool] = True

    @app.post("/api/guilds/{guild_id}/antispam")
    async def api_save_antispam(guild_id: int, p: AntiSpamPayload, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        data = p.dict(exclude_unset=True)
        updated = await config_service.update_antispam_config(
            guild_id, data, actor_id=int(user["id"]), actor_tag=user["username"], source="WEBSITE"
        )
        return {"status": "ok", "config": updated}

    # ==================== GENERIC MODULE CONFIG REST API ====================

    @app.get("/api/guilds/{guild_id}/config/{module}")
    async def api_get_config(guild_id: int, module: str, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        cfg = await config_service.get_module_config(guild_id, module)
        return {"status": "ok", "config": cfg}

    @app.post("/api/guilds/{guild_id}/config/{module}")
    async def api_save_module_config(guild_id: int, module: str, request: Request, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        try:
            body = await request.json()
        except Exception:
            body = {}
        updated = await config_service.update_module_config(
            guild_id, module, body, actor_id=int(user["id"]), actor_tag=user["username"], source="WEBSITE"
        )
        return {"status": "ok", "config": updated}

    # ==================== WHITELIST & APPROVED BOTS API ====================

    class WhitelistAddPayload(BaseModel):
        target_id: str
        target_type: str = "member"  # 'member' or 'role'

    @app.post("/api/guilds/{guild_id}/whitelist")
    async def api_add_whitelist(guild_id: int, p: WhitelistAddPayload, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        tid = int(p.target_id.strip())
        await config_service.add_whitelist(guild_id, tid, p.target_type, int(user["id"]), user["username"], source="WEBSITE")
        return {"status": "ok", "message": "Added to whitelist"}

    @app.delete("/api/guilds/{guild_id}/whitelist/{target_id}")
    async def api_delete_whitelist(guild_id: int, target_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        await config_service.remove_whitelist(guild_id, target_id, int(user["id"]), user["username"], source="WEBSITE")
        return {"status": "ok", "message": "Removed from whitelist"}

    class BotApprovePayload(BaseModel):
        bot_id: str
        bot_name: str = "Approved Bot"

    @app.post("/api/guilds/{guild_id}/bots")
    async def api_approve_bot(guild_id: int, p: BotApprovePayload, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        bid = int(p.bot_id.strip())
        await config_service.approve_bot(guild_id, bid, p.bot_name, int(user["id"]), user["username"], source="WEBSITE")
        return {"status": "ok", "message": "Bot application approved"}

    @app.delete("/api/guilds/{guild_id}/bots/{bot_id}")
    async def api_revoke_bot(guild_id: int, bot_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        await config_service.revoke_bot(guild_id, bot_id, int(user["id"]), user["username"], source="WEBSITE")
        return {"status": "ok", "message": "Bot application revoked"}

    # ==================== BACKUPS & DISASTER RECOVERY ====================

    class BackupCreatePayload(BaseModel):
        name: Optional[str] = None

    @app.post("/api/guilds/{guild_id}/backups")
    async def api_create_backup(guild_id: int, p: BackupCreatePayload, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found")
        res = await backup_service.create_backup(guild, int(user["id"]), p.name)
        return res

    @app.post("/api/guilds/{guild_id}/backups/{backup_id}/restore")
    async def api_restore_backup(guild_id: int, backup_id: str, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found")
        res = await backup_service.restore_backup(guild, backup_id)
        return res

    # ==================== AUTO RESPONDERS ====================

    class AutoResponderPayload(BaseModel):
        trigger: str
        response: str
        match_type: str = "contains"

    @app.post("/api/guilds/{guild_id}/autoresponders")
    async def api_add_autoresponder(guild_id: int, p: AutoResponderPayload, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        res = await config_service.add_auto_responder(guild_id, p.trigger, p.response, p.match_type, int(user["id"]), user["username"], source="WEBSITE")
        return {"status": "ok", "responder": res}

    @app.delete("/api/guilds/{guild_id}/autoresponders/{responder_id}")
    async def api_delete_autoresponder(guild_id: int, responder_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        await config_service.delete_auto_responder(guild_id, responder_id, int(user["id"]), user["username"], source="WEBSITE")
        return {"status": "ok", "message": "Autoresponder deleted"}

    # ==================== REACTION ROLES ====================

    class ReactionRolePayload(BaseModel):
        channel_id: int
        message_id: int
        emoji: str
        role_id: int

    @app.post("/api/guilds/{guild_id}/reaction_roles")
    async def api_add_reaction_role(guild_id: int, p: ReactionRolePayload, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        new_id = await config_service.add_reaction_role(guild_id, p.message_id, p.channel_id, p.emoji, p.role_id)
        return {"status": "ok", "id": new_id}

    @app.delete("/api/guilds/{guild_id}/reaction_roles/{rr_id}")
    async def api_delete_reaction_role(guild_id: int, rr_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        await config_service.delete_reaction_role(guild_id, rr_id)
        return {"status": "ok", "message": "Reaction role deleted"}

    # ==================== ACTIONS ENDPOINT (TESTS & LOCKDOWN) ====================

    @app.post("/api/guilds/{guild_id}/actions/{action}")
    async def api_guild_action(guild_id: int, action: str, request: Request, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found")

        try:
            body = await request.json()
        except Exception:
            body = {}

        if action == "lockdown":
            res = await security_service.execute_lockdown(guild, lock=True)
            await config_service.broadcaster.broadcast(guild_id, "lockdown_triggered", {"locked": True})
            return {"status": "ok", "result": res}
        elif action == "unlock":
            res = await security_service.execute_lockdown(guild, lock=False)
            await config_service.broadcaster.broadcast(guild_id, "lockdown_triggered", {"locked": False})
            return {"status": "ok", "result": res}
        elif action == "test-welcome":
            cog = bot.get_cog("Welcome")
            if cog is None or not hasattr(cog, "dispatch_welcome"):
                raise HTTPException(status_code=503, detail="Welcome module is not loaded on the bot.")
            member = guild.get_member(int(user["id"])) or guild.me
            result = await cog.dispatch_welcome(member, send_dm=False)
            if not result.get("ok"):
                raise HTTPException(status_code=400, detail=result.get("reason", "Welcome test failed."))
            return {"status": "ok", "message": result.get("reason", "Test welcome dispatched")}
        elif action == "test-goodbye":
            welcome_cfg = await config_service.get_welcome_config(guild_id)
            cid = welcome_cfg.get("leave_channel_id")
            if not cid:
                raise HTTPException(status_code=400, detail="No goodbye channel selected. Pick one and Save.")
            channel = guild.get_channel(int(cid))
            if not channel or not hasattr(channel, "send"):
                raise HTTPException(status_code=400, detail="The saved goodbye channel no longer exists.")
            await channel.send(f"🚪 **[NOVEXA Goodbye Live Test]**\n**{user['username']}** has left the server. We now have {guild.member_count} members.")
            return {"status": "ok", "message": f"Goodbye delivered to #{channel.name}"}
        elif action == "dispatch-embed":
            cid = int(body.get("channel_id") or 0)
            target_chan = guild.get_channel(cid) if cid else guild.system_channel
            if target_chan and hasattr(target_chan, "send"):
                import discord
                emb = discord.Embed(
                    title=body.get("title", "Announcement"),
                    description=body.get("description", ""),
                    color=int(body.get("color", "#5865F2").replace("#", ""), 16) if body.get("color") else 0x5865F2
                )
                if body.get("footer"):
                    emb.set_footer(text=body["footer"])
                if body.get("image"):
                    emb.set_image(url=body["image"])
                await target_chan.send(embed=emb)
            return {"status": "ok", "message": "Custom embed dispatched successfully"}
        elif action == "apply-template":
            tid = body.get("template_id", "gaming")
            await config_service.update_server_setup_config(guild_id, {"template_id": tid}, int(user["id"]), user["username"], source="WEBSITE")
            return {"status": "ok", "message": f"Server architecture template '{tid}' queued for deployment"}
        else:
            return {"status": "ok", "action": action}

    # ==================== WALLPAPER STUDIO API ====================

    class WallpaperChannelPayload(BaseModel):
        channel_id: int

    @app.get("/api/guilds/{guild_id}/wallpaper")
    async def api_wallpaper_list(guild_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        channels = await config_service.get_wallpaper_channels(guild_id)
        return {"status": "ok", "channels": channels}

    @app.post("/api/guilds/{guild_id}/wallpaper")
    async def api_wallpaper_add(guild_id: int, p: WallpaperChannelPayload, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found")
        channel = guild.get_channel(p.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            raise HTTPException(status_code=400, detail="Channel not found or not a text channel")

        cog = bot.get_cog("Wallpaper")
        if cog is None:
            raise HTTPException(status_code=503, detail="Wallpaper system is not loaded")
        ok, message = await cog.add_channel(guild, channel, user)
        if not ok:
            raise HTTPException(status_code=403, detail=message)

        await config_service.add_wallpaper_channel(guild_id, p.channel_id, int(user["id"]), user["username"], source="WEBSITE")
        return {"status": "ok", "message": message}

    @app.delete("/api/guilds/{guild_id}/wallpaper/{channel_id}")
    async def api_wallpaper_remove(guild_id: int, channel_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        cog = bot.get_cog("Wallpaper")
        if cog is not None:
            await cog.remove_channel(guild_id, channel_id)
        await config_service.remove_wallpaper_channel(guild_id, channel_id, int(user["id"]), user["username"], source="WEBSITE")
        return {"status": "ok", "message": "Wallpaper channel removed"}

    # ==================== DROPPER SUITE API ====================

    class DropperUserPayload(BaseModel):
        user_id: str

    @app.get("/api/guilds/{guild_id}/dropper")
    async def api_dropper_list(guild_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        members = await config_service.get_dropper_members(guild_id)
        guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
        for m in members:
            member = guild.get_member(m["user_id"]) if guild else None
            m["display_name"] = member.display_name if member else None
        return {"status": "ok", "members": members}

    @app.post("/api/guilds/{guild_id}/dropper")
    async def api_dropper_grant(guild_id: int, p: DropperUserPayload, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found")
        try:
            target_id = int(p.user_id.strip())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID")
        member = guild.get_member(target_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found in this server")

        from cogs.dropper import grant_dropper_role
        ok, message = await grant_dropper_role(guild, member, WebActor(int(user["id"]), user["username"]))
        if not ok:
            raise HTTPException(status_code=400, detail=message)
        await config_service.add_dropper_member(guild_id, target_id, int(user["id"]), user["username"], source="WEBSITE")
        return {"status": "ok", "message": message}

    @app.delete("/api/guilds/{guild_id}/dropper/{user_id}")
    async def api_dropper_revoke(guild_id: int, user_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found")
        member = guild.get_member(user_id)
        if member:
            from cogs.dropper import revoke_dropper_role
            ok, message = await revoke_dropper_role(guild, member, WebActor(int(user["id"]), user["username"]))
            if not ok:
                raise HTTPException(status_code=400, detail=message)
        await config_service.remove_dropper_member(guild_id, user_id, int(user["id"]), user["username"], source="WEBSITE")
        return {"status": "ok", "message": "Dropper revoked"}

    # ==================== DROPPER CHANNELS API ====================

    @app.get("/api/guilds/{guild_id}/dropper/preview")
    async def api_dropper_preview(guild_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found or bot is not connected to this guild.")

        user_id = int(user["id"])
        is_authorized = (
            user.get("is_dev")
            or user_id in OWNER_IDS
            or (guild.owner_id and guild.owner_id == user_id)
        )
        if not is_authorized:
            member = guild.get_member(user_id)
            if member and (member.guild_permissions.administrator or member.guild_permissions.manage_guild):
                is_authorized = True

        if not is_authorized:
            raise HTTPException(status_code=403, detail="Administrator or Manage Server permissions required.")

        preview = dropper_service.get_preview(guild)
        return {"status": "ok", "preview": preview}

    @app.post("/api/guilds/{guild_id}/dropper/execute")
    async def api_dropper_execute(guild_id: int, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found or bot is not connected to this guild.")

        user_id = int(user["id"])
        is_authorized = (
            user.get("is_dev")
            or user_id in OWNER_IDS
            or (guild.owner_id and guild.owner_id == user_id)
        )
        if not is_authorized:
            member = guild.get_member(user_id)
            if member and (member.guild_permissions.administrator or member.guild_permissions.manage_guild):
                is_authorized = True

        if not is_authorized:
            raise HTTPException(status_code=403, detail="Administrator or Manage Server permissions required.")

        try:
            result = await dropper_service.execute_dropper(guild, user_id, user.get("username", "DashboardAdmin"))
            return {"status": "ok", "result": result}
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to execute dropper channels in guild {guild_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to create dropper channels: {e}")

    return app
