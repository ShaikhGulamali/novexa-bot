"""Premium subscription engine: Cashfree checkout, instant grant, Discord role sync."""

import asyncio
import json
import logging
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import discord

from database.database import db
from services.cashfree_service import cashfree_service, CashfreeError
from services.config_service import config_service

logger = logging.getLogger("novexa.premium")

BILLING_DAYS = 30

PLAN_SEEDS: List[Dict[str, Any]] = [
    {
        "plan_id": "silver",
        "name": "Silver VIP",
        "description": "Priority anti-nuke response, 10 recovery backups and 150 daily AI requests.",
        "price_inr": 299,
        "tier_level": 1,
        "max_backups": 10,
        "max_ai_daily": 150,
        "tier_color": "#94A3B8",
        "audit_retention_days": 30,
        "perks": [
            "Priority Anti-Nuke Response",
            "Up to 10 Disaster Recovery Backups",
            "150 Daily Autonomous AI Requests",
            "30-Day Audit Log History",
            "Silver Discord Role & Badge",
        ],
        "role_names": ["🥈 Silver", "Silver", "Silver VIP"],
    },
    {
        "plan_id": "gold",
        "name": "Gold Elite",
        "description": "Sub-second anti-nuke interception, 25 backups, 500 daily AI requests and 24/7 voice.",
        "price_inr": 599,
        "tier_level": 2,
        "max_backups": 25,
        "max_ai_daily": 500,
        "tier_color": "#FF2D55",
        "audit_retention_days": 90,
        "perks": [
            "Instant Sub-Second Anti-Nuke Interception",
            "Up to 25 Disaster Recovery Backups",
            "500 Daily AI Coding Requests",
            "24/7 Dedicated Voice Mode",
            "90-Day Audit Log History",
            "Gold Discord Role & Status",
        ],
        "role_names": ["🥇 Gold", "Gold", "Gold Elite"],
    },
    {
        "plan_id": "platinum",
        "name": "Platinum Ultimate",
        "description": "Unlimited backups, 2,000 daily AI requests, custom branding and a personal concierge.",
        "price_inr": 999,
        "tier_level": 3,
        "max_backups": 0,
        "max_ai_daily": 2000,
        "tier_color": "#FBBF24",
        "audit_retention_days": 365,
        "perks": [
            "Ultimate Protection & Instant Lockdown",
            "Unlimited Disaster Recovery Backups",
            "2,000 Daily AI Coding Requests",
            "Custom Welcome Canvas Branding",
            "365-Day Extended Audit Retention",
            "Personal VIP Support Concierge",
            "Platinum Discord Role & Badge",
        ],
        "role_names": ["💎 Platinum", "Platinum", "Platinum Ultimate"],
    },
]

TIER_ROLE_HINTS = {
    "silver": ["silver"],
    "gold": ["gold"],
    "platinum": ["platinum"],
}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class PremiumService:
    def __init__(self) -> None:
        self.bot = None
        self._locks: Dict[str, asyncio.Lock] = {}
        self._seeded = False

    def set_bot(self, bot) -> None:
        self.bot = bot

    # ==================== PLANS ====================

    async def ensure_seeded(self) -> None:
        if self._seeded:
            return
        for plan in PLAN_SEEDS:
            try:
                await db.execute(
                    """
                    INSERT INTO premium_plans
                        (plan_id, name, description, price_inr, billing_period, max_guilds, features_json,
                         tier_level, max_backups, max_ai_daily, tier_color, audit_retention_days, perks_json)
                    VALUES (?, ?, ?, ?, 'monthly', 1, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(plan_id) DO UPDATE SET
                        name = excluded.name,
                        description = excluded.description,
                        price_inr = excluded.price_inr,
                        tier_level = excluded.tier_level,
                        max_backups = excluded.max_backups,
                        max_ai_daily = excluded.max_ai_daily,
                        tier_color = excluded.tier_color,
                        audit_retention_days = excluded.audit_retention_days,
                        perks_json = excluded.perks_json
                    """,
                    (
                        plan["plan_id"],
                        plan["name"],
                        plan["description"],
                        float(plan["price_inr"]),
                        json.dumps(plan["perks"]),
                        plan["tier_level"],
                        plan["max_backups"],
                        plan["max_ai_daily"],
                        plan["tier_color"],
                        plan["audit_retention_days"],
                        json.dumps(plan["perks"]),
                    ),
                )
            except Exception as exc:
                logger.error(f"Failed to seed premium plan {plan['plan_id']}: {exc}")
        self._seeded = True

    async def get_plans(self) -> List[Dict[str, Any]]:
        await self.ensure_seeded()
        plans = await config_service.get_premium_plans()
        by_id = {p["plan_id"]: p for p in plans}
        merged: List[Dict[str, Any]] = []
        for seed in PLAN_SEEDS:
            row = by_id.get(seed["plan_id"], {})
            merged.append({
                **seed,
                "price_inr": float(row.get("price_inr", seed["price_inr"])),
                "name": row.get("name", seed["name"]),
                "description": row.get("description", seed["description"]),
                "tier_color": row.get("tier_color", seed["tier_color"]),
                "perks": seed["perks"],
            })
        return merged

    async def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        for plan in await self.get_plans():
            if plan["plan_id"] == plan_id:
                return plan
        return None

    # ==================== ORDERS ====================

    def _order_lock(self, order_id: str) -> asyncio.Lock:
        lock = self._locks.get(order_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[order_id] = lock
        return lock

    async def create_checkout(
        self,
        user: Dict[str, Any],
        guild_id: int,
        plan_id: str,
        email: str,
        phone: str,
        base_url: str,
        customer_name: str = "",
    ) -> Dict[str, Any]:
        if not cashfree_service.configured:
            return {"ok": False, "reason": "Cashfree is not configured on this server."}
        plan = await self.get_plan(plan_id)
        if not plan:
            return {"ok": False, "reason": "Unknown plan."}
        email = (email or "").strip()
        phone = (phone or "").strip()
        if not EMAIL_RE.match(email):
            return {"ok": False, "reason": "Enter a valid email address."}
        phone_digits = re.sub(r"\D", "", phone)
        if len(phone_digits) < 10:
            return {"ok": False, "reason": "Enter a valid phone number (10+ digits)."}
        guild = self.bot.get_guild(guild_id) if self.bot else None
        if guild is None:
            return {"ok": False, "reason": "NOVEXA is not in that server."}

        order_id = f"NVX{int(time.time())}{secrets.token_hex(3).upper()}"
        base_url = base_url.rstrip("/")
        return_url = f"{base_url}/premium?order_id={order_id}"
        notify_url = f"{base_url}/api/payments/cashfree/webhook"

        try:
            result = await cashfree_service.create_order(
                order_id=order_id,
                amount=plan["price_inr"],
                customer_id=str(user.get("id", "0"))[:50],
                customer_email=email,
                customer_phone=phone_digits[-12:],
                customer_name=(customer_name or user.get("username", "NOVEXA Customer"))[:100],
                return_url=return_url,
                notify_url=notify_url,
                note=f"NOVEXA {plan['name']} - {guild.name}",
            )
        except CashfreeError as exc:
            logger.error(f"Cashfree order creation failed: {exc}")
            return {"ok": False, "reason": str(exc)}

        session_id = result.get("payment_session_id")
        if not session_id:
            return {"ok": False, "reason": "Cashfree did not return a payment session."}

        await db.execute(
            """
            INSERT INTO premium_orders
                (order_id, guild_id, user_id, plan_id, amount, currency, status,
                 customer_email, customer_phone, created_at)
            VALUES (?, ?, ?, ?, ?, 'INR', 'CREATED', ?, ?, CURRENT_TIMESTAMP)
            """,
            (order_id, guild_id, int(user.get("id", 0)), plan_id, plan["price_inr"], email, phone_digits[-12:]),
        )

        return {
            "ok": True,
            "order_id": order_id,
            "payment_session_id": session_id,
            "amount": plan["price_inr"],
            "plan_id": plan_id,
            "plan_name": plan["name"],
            "mode": cashfree_service.mode,
        }

    async def get_order_row(self, order_id: str) -> Optional[Dict[str, Any]]:
        row = await db.fetchone("SELECT * FROM premium_orders WHERE order_id = ?;", (order_id,))
        return dict(row) if row else None

    async def refresh_order(self, order_id: str, source: str = "verify") -> Dict[str, Any]:
        lock = self._order_lock(order_id)
        async with lock:
            row = await self.get_order_row(order_id)
            if not row:
                return {"ok": False, "reason": "Order not found."}
            if row.get("granted"):
                return {"ok": True, "status": "PAID", "granted": True, "order": row, "message": "Premium already active."}
            if not cashfree_service.configured:
                return {"ok": False, "reason": "Cashfree is not configured."}

            try:
                remote = await cashfree_service.get_order(order_id)
            except CashfreeError as exc:
                logger.error(f"Cashfree order fetch failed for {order_id}: {exc}")
                return {"ok": False, "reason": str(exc)}

            status = str(remote.get("order_status", "")).upper()
            payment_id = ""
            payments = remote.get("payments") or []
            for p in payments:
                if str(p.get("payment_status", "")).upper() == "SUCCESS":
                    payment_id = str(p.get("cf_payment_id", ""))
                    break

            if status != "PAID":
                if status in {"EXPIRED", "TERMINATED"} and row.get("status") not in {"PAID"}:
                    await db.execute(
                        "UPDATE premium_orders SET status = ? WHERE order_id = ? AND granted = 0;",
                        (status, order_id),
                    )
                return {"ok": True, "status": status or row.get("status"), "granted": False, "order": row}

            await db.execute(
                """
                UPDATE premium_orders
                SET status = 'PAID', payment_id = ?, paid_at = CURRENT_TIMESTAMP
                WHERE order_id = ? AND granted = 0;
                """,
                (payment_id, order_id),
            )
            grant = await self.grant_premium(
                guild_id=int(row["guild_id"]),
                user_id=int(row["user_id"]),
                plan_id=row["plan_id"],
                order_id=order_id,
                source=source,
            )
            if grant.get("ok"):
                await db.execute("UPDATE premium_orders SET granted = 1 WHERE order_id = ?;", (order_id,))
                return {"ok": True, "status": "PAID", "granted": True, "grant": grant, "message": grant.get("message")}
            return {"ok": True, "status": "PAID", "granted": False, "grant": grant}

    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        event_type = str(payload.get("type", "")).upper()
        data = payload.get("data") or {}
        order = data.get("order") or {}
        payment = data.get("payment") or {}
        order_id = str(order.get("order_id", "") or "")
        if not order_id:
            return {"ok": False, "reason": "Missing order_id."}
        if event_type not in {"PAYMENT_SUCCESS_WEBHOOK", "PAYMENT_SUCCESS"}:
            if event_type in {"PAYMENT_FAILED_WEBHOOK", "PAYMENT_USER_DROPPED_WEBHOOK"}:
                await db.execute(
                    "UPDATE premium_orders SET status = ? WHERE order_id = ? AND granted = 0;",
                    ("FAILED" if "FAILED" in event_type else "USER_DROPPED", order_id),
                )
            return {"ok": True, "ignored": event_type}
        return await self.refresh_order(order_id, source="webhook")

    # ==================== GRANT ====================

    def _role_candidates(self, plan_id: str) -> List[str]:
        for seed in PLAN_SEEDS:
            if seed["plan_id"] == plan_id:
                return seed["role_names"]
        return []

    async def _find_or_create_role(self, guild: discord.Guild, plan: Dict[str, Any]) -> Optional[discord.Role]:
        wanted = [n.lower() for n in self._role_candidates(plan["plan_id"])]
        stripped = {re.sub(r"[^a-z ]", "", n).strip(): n for n in wanted}
        for role in guild.roles:
            name = role.name.lower()
            clean = re.sub(r"[^a-z ]", "", name).strip()
            if name in wanted or clean in stripped:
                return role
        for role in guild.roles:
            clean = re.sub(r"[^a-z ]", "", role.name.lower())
            for hint in TIER_ROLE_HINTS.get(plan["plan_id"], []):
                if hint in clean:
                    return role
        try:
            color_hex = plan.get("tier_color") or "#FF2D55"
            color = discord.Color(int(color_hex.lstrip("#"), 16))
        except Exception:
            color = discord.Color.default()
        try:
            return await guild.create_role(
                name=self._role_candidates(plan["plan_id"])[0],
                color=color,
                hoist=False,
                mentionable=False,
                reason=f"NOVEXA premium role for plan {plan['plan_id']}",
            )
        except Exception as exc:
            logger.warning(f"Could not create premium role in {guild.id}: {exc}")
            return None

    async def grant_premium(
        self,
        guild_id: int,
        user_id: int,
        plan_id: str,
        order_id: str,
        source: str = "cashfree",
    ) -> Dict[str, Any]:
        plan = await self.get_plan(plan_id)
        if not plan:
            return {"ok": False, "reason": "Unknown plan."}
        guild = self.bot.get_guild(guild_id) if self.bot else None
        if guild is None:
            return {"ok": False, "reason": "NOVEXA is not in that server."}

        now = datetime.now(timezone.utc)
        base = now
        existing = await db.fetchone(
            """
            SELECT * FROM premium_subscriptions
            WHERE guild_id = ? AND plan_id = ? AND status = 'ACTIVE' AND expires_at > CURRENT_TIMESTAMP
            ORDER BY expires_at DESC LIMIT 1;
            """,
            (guild_id, plan_id),
        )
        if existing:
            try:
                exp = existing["expires_at"]
                if isinstance(exp, str):
                    exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                else:
                    exp_dt = exp
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                base = max(now, exp_dt)
            except Exception:
                base = now
        expires_at = base + timedelta(days=BILLING_DAYS)

        await db.execute(
            "UPDATE premium_subscriptions SET status = 'REPLACED' WHERE guild_id = ? AND status = 'ACTIVE';",
            (guild_id,),
        )
        expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
        try:
            await db.execute(
                """
                INSERT INTO premium_subscriptions
                    (guild_id, plan_id, subscriber_user_id, status, started_at, expires_at, payment_ref)
                VALUES (?, ?, ?, 'ACTIVE', CURRENT_TIMESTAMP, ?, ?);
                """,
                (guild_id, plan_id, user_id, expires_str, order_id),
            )
        except Exception:
            # PostgreSQL legacy column names (user_id / starts_at)
            await db.execute(
                """
                INSERT INTO premium_subscriptions
                    (guild_id, plan_id, user_id, status, starts_at, expires_at, payment_ref)
                VALUES (?, ?, ?, 'ACTIVE', CURRENT_TIMESTAMP, ?, ?);
                """,
                (guild_id, plan_id, user_id, expires_str, order_id),
            )

        role_name = None
        role_ok = False
        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except Exception:
                member = None
        role = await self._find_or_create_role(guild, plan)
        if role:
            role_name = role.name
            if member is not None:
                try:
                    await member.add_roles(role, reason=f"NOVEXA {plan['name']} purchase ({order_id})")
                    role_ok = True
                except Exception as exc:
                    logger.warning(f"Role grant failed for {user_id} in {guild_id}: {exc}")
                try:
                    other_ids = [r.id for r in member.roles if r.id != role.id and any(
                        h in re.sub(r"[^a-z ]", "", r.name.lower()) for h in ("silver", "gold", "platinum")
                    )]
                    for rid in other_ids:
                        other = guild.get_role(rid)
                        if other:
                            await member.remove_roles(other, reason="NOVEXA premium tier upgrade")
                except Exception:
                    pass

        row = await self.get_order_row(order_id)
        amount = float(row["amount"]) if row else float(plan["price_inr"])
        try:
            await db.execute(
                """
                INSERT INTO payment_records
                    (guild_id, user_id, amount, currency, method, transaction_id, reference_id,
                     notes, status, verified_at)
                VALUES (?, ?, ?, 'INR', 'CASHFREE', ?, ?, ?, 'approved', CURRENT_TIMESTAMP);
                """,
                (
                    guild_id,
                    user_id,
                    amount,
                    (row or {}).get("payment_id", "") or "",
                    order_id,
                    f"Auto-granted {plan['name']} via {source}",
                ),
            )
        except Exception as exc:
            logger.warning(f"payment_records insert failed for {order_id}: {exc}")

        try:
            await config_service._log_audit(
                guild_id, "premium", "subscription", "", f"{plan_id} via {source}", user_id, "Cashfree", "CASHFREE"
            )
        except Exception:
            pass
        try:
            await config_service.broadcaster.broadcast(guild_id, "premium_updated", {"plan_id": plan_id, "expires_at": str(expires_at)})
        except Exception:
            pass

        if member is not None:
            try:
                expires_label = expires_at.strftime("%d %b %Y, %H:%M UTC")
                await member.send(
                    f"**{plan['name']} activated in {guild.name}**\n"
                    f"Amount paid: ₹{amount:.0f}\n"
                    f"Valid until: {expires_label}\n"
                    f"Role: {('@' + role_name) if role_ok else 'will be applied shortly'}\n"
                    f"Order: `{order_id}`\n\n"
                    f"Thanks for supporting NOVEXA."
                )
            except Exception:
                pass

        logger.info(f"Premium granted: {plan_id} to {user_id} in {guild_id} (order {order_id}, role_ok={role_ok})")
        return {
            "ok": True,
            "plan_id": plan_id,
            "plan_name": plan["name"],
            "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            "role": role_name,
            "role_assigned": role_ok,
            "message": f"{plan['name']} activated. Role: {role_name or 'n/a'}, valid until {expires_at.strftime('%d %b %Y')}.",
        }

    # ==================== READ ====================

    async def recent_orders(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        rows = await db.fetchall(
            "SELECT * FROM premium_orders WHERE guild_id = ? ORDER BY rowid DESC LIMIT ?;",
            (guild_id, limit),
        )
        return [dict(r) for r in rows]


premium_service = PremiumService()
