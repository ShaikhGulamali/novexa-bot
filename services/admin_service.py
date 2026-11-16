"""Owner console data: guilds, buyers, orders, subscriptions and plan controls."""

import logging
from typing import Any, Dict, List, Optional

from database.database import db
from services.premium_service import premium_service

logger = logging.getLogger("novexa.admin")


class AdminService:
    async def snapshot(self, bot) -> Dict[str, Any]:
        guilds = list(getattr(bot, "guilds", []) or []) if bot else []
        total_members = sum(int(g.member_count or 0) for g in guilds)

        plans = await premium_service.get_plans()
        plan_by_id = {p["plan_id"]: p for p in plans}

        order_rows = await db.fetchall(
            "SELECT * FROM premium_orders ORDER BY created_at DESC LIMIT 200;"
        )
        orders: List[Dict[str, Any]] = []
        paid_count = 0
        revenue = 0.0
        for r in order_rows:
            d = dict(r)
            d["amount"] = float(d.get("amount") or 0)
            if str(d.get("status", "")).upper() == "PAID":
                paid_count += 1
                revenue += d["amount"]
            guild = bot.get_guild(int(d["guild_id"])) if (bot and d.get("guild_id")) else None
            d["guild_name"] = guild.name if guild else f"Guild {d.get('guild_id')}"
            plan = plan_by_id.get(d.get("plan_id"), {})
            d["plan_name"] = plan.get("name", str(d.get("plan_id", "")).title())
            user = bot.get_user(int(d["user_id"])) if (bot and d.get("user_id")) else None
            d["user_name"] = str(user) if user else f"User {d.get('user_id')}"
            orders.append(d)

        sub_rows = await db.fetchall(
            "SELECT * FROM premium_subscriptions WHERE UPPER(status) = 'ACTIVE' AND expires_at > CURRENT_TIMESTAMP ORDER BY expires_at ASC;"
        )
        active_by_guild: Dict[int, Dict[str, Any]] = {}
        for r in sub_rows:
            d = dict(r)
            gid = int(d["guild_id"])
            current = active_by_guild.get(gid)
            if current is None or str(d.get("expires_at")) > str(current.get("expires_at")):
                plan = plan_by_id.get(d.get("plan_id"), {})
                d["plan_name"] = plan.get("name", str(d.get("plan_id", "")).title())
                d["tier_level"] = int(plan.get("tier_level", 0))
                active_by_guild[gid] = d

        guild_rows: List[Dict[str, Any]] = []
        for g in sorted(guilds, key=lambda x: -(x.member_count or 0)):
            sub = active_by_guild.get(g.id)
            owner = bot.get_user(g.owner_id) if bot else None
            guild_rows.append({
                "id": str(g.id),
                "name": g.name,
                "members": int(g.member_count or 0),
                "owner_id": str(g.owner_id),
                "owner_name": str(owner) if owner else f"User {g.owner_id}",
                "plan": (sub or {}).get("plan_name"),
                "plan_id": (sub or {}).get("plan_id"),
                "expires_at": (sub or {}).get("expires_at"),
                "icon_url": str(g.icon.url) if getattr(g, "icon", None) else None,
            })

        buyer_rows = await db.fetchall(
            """
            SELECT user_id,
                   COUNT(*) AS orders,
                   SUM(CASE WHEN UPPER(status) = 'PAID' THEN amount ELSE 0 END) AS spend,
                   SUM(CASE WHEN UPPER(status) = 'PAID' THEN 1 ELSE 0 END) AS paid_orders,
                   MAX(created_at) AS last_order
            FROM premium_orders
            GROUP BY user_id
            ORDER BY spend DESC, last_order DESC
            LIMIT 200;
            """
        )
        buyers: List[Dict[str, Any]] = []
        for r in buyer_rows:
            d = dict(r)
            d["spend"] = float(d.get("spend") or 0)
            user = bot.get_user(int(d["user_id"])) if (bot and d.get("user_id")) else None
            d["user_name"] = str(user) if user else f"User {d.get('user_id')}"
            buyers.append(d)

        premium_guilds = sum(1 for g in guild_rows if g["plan"])
        return {
            "stats": {
                "guilds": len(guilds),
                "members": total_members,
                "premium_guilds": premium_guilds,
                "paid_orders": paid_count,
                "orders": len(orders),
                "revenue": revenue,
                "buyers": len(buyers),
            },
            "plans": plans,
            "orders": orders,
            "guilds": guild_rows,
            "buyers": buyers,
            "active_subs": [dict(r) for r in sub_rows],
        }


admin_service = AdminService()
