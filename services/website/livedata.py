"""NOVEXA - Live guild data for the web explorer (read-only views)."""

from __future__ import annotations

from typing import Any, Dict, List

import discord

from database.database import db


def _iso(dt) -> str:
    return dt.isoformat() if dt else ""


def guild_snapshot(guild: discord.Guild) -> Dict[str, Any]:
    text = sorted(guild.text_channels, key=lambda c: c.position)
    voice = sorted(guild.voice_channels, key=lambda c: c.position)
    cats = sorted(guild.categories, key=lambda c: c.position)
    roles = sorted([r for r in guild.roles if not r.is_default()], key=lambda r: r.position, reverse=True)
    members = guild.members
    bots = sum(1 for m in members if m.bot)
    online = sum(1 for m in members if m.status != discord.Status.offline)
    in_voice = sum(len(c.members) for c in voice)

    return {
        "id": str(guild.id),
        "name": guild.name,
        "icon": str(guild.icon.url) if guild.icon else None,
        "banner": str(guild.banner.url) if guild.banner else None,
        "owner_id": str(guild.owner_id),
        "created_at": _iso(guild.created_at),
        "member_count": guild.member_count or len(members),
        "online_count": online,
        "bot_count": bots,
        "boost_level": guild.premium_tier,
        "boost_count": guild.premium_subscription_count or 0,
        "verification_level": str(guild.verification_level.name).replace("_", " ").title(),
        "in_voice": in_voice,
        "emoji_count": len(guild.emojis),
        "sticker_count": len(guild.stickers),
        "text_channels": len(text),
        "voice_channels": len(voice),
        "role_count": len(roles),
        "channels": [
            {
                "id": str(c.id),
                "name": c.name,
                "type": "text" if isinstance(c, discord.TextChannel) else "voice" if isinstance(
                    c, discord.VoiceChannel) else "category",
                "category": c.category.name if getattr(c, "category", None) else None,
                "nsfw": bool(getattr(c, "nsfw", False)),
                "slowmode": getattr(c, "slowmode_delay", 0),
                "topic": getattr(c, "topic", None),
            }
            for c in (cats + text + voice)
        ],
        "roles": [
            {
                "id": str(r.id),
                "name": r.name,
                "color": f"#{r.color.value:06x}" if r.color.value else "#99aab5",
                "members": len(r.members),
                "position": r.position,
                "hoist": r.hoist,
                "mentionable": r.mentionable,
                "managed": r.managed,
            }
            for r in roles
        ],
        "voice_members": [
            {
                "channel": c.name,
                "members": [
                    {"id": str(m.id), "name": m.display_name, "mute": m.voice.mute if m.voice else False}
                    for m in c.members
                ],
            }
            for c in voice if c.members
        ],
    }


def member_rows(guild: discord.Guild) -> List[Dict[str, Any]]:
    rows = []
    for m in guild.members[:5000]:
        rows.append({
            "id": str(m.id),
            "name": m.name,
            "display": m.display_name,
            "avatar": str(m.display_avatar.url),
            "bot": m.bot,
            "joined_at": _iso(m.joined_at),
            "top_role": m.top_role.name if m.top_role and not m.top_role.is_default() else "—",
            "status": m.status.name,
        })
    rows.sort(key=lambda r: (r["bot"], r["joined_at"]))
    return rows


LEADERBOARD_QUERIES = {
    "wealth": ("SELECT user_id, (wallet + bank) AS score, wallet, bank, gems FROM economy_users "
               "WHERE guild_id = ? ORDER BY score DESC LIMIT 15", "Net Worth"),
    "hunters": ("SELECT user_id, hunts_count AS score FROM economy_users "
                "WHERE guild_id = ? ORDER BY score DESC LIMIT 15", "Hunts"),
    "battles": ("SELECT user_id, battles_won AS score FROM economy_users "
                "WHERE guild_id = ? ORDER BY score DESC LIMIT 15", "Battles Won"),
    "levels": ("SELECT user_id, level AS score, xp, messages_count FROM leveling "
               "WHERE guild_id = ? ORDER BY xp DESC LIMIT 15", "Level"),
}


async def leaderboard(guild: discord.Guild, kind: str) -> List[Dict[str, Any]]:
    spec = LEADERBOARD_QUERIES.get(kind)
    if not spec:
        return []
    query, _ = spec
    try:
        rows = await db.fetchall(query, (guild.id,))
    except Exception:
        return []
    out = []
    for idx, row in enumerate(rows, start=1):
        row = dict(row)
        uid = int(row["user_id"])
        member = guild.get_member(uid)
        out.append({
            "rank": idx,
            "user_id": str(uid),
            "name": member.display_name if member else f"User {uid}",
            "avatar": str(member.display_avatar.url) if member else None,
            "score": row.get("score", 0),
            "extra": {k: v for k, v in row.items() if k not in ("user_id", "score")},
        })
    return out
