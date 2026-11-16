import os
import re
import sqlite3
import urllib.parse
from pathlib import Path
from typing import Any, List, Optional, Tuple, Dict, Union
import aiosqlite
import logging
import shutil
import datetime
from config import DATABASE_PATH, DATABASE_BACKUP_DIR, DATABASE_URL

try:
    import asyncpg
except ImportError:
    asyncpg = None

logger = logging.getLogger("novexa.database")


def mask_database_url(url: str) -> str:
    """Mask password in PostgreSQL URL for log safety."""
    if not url:
        return "<EMPTY_DATABASE_URL>"
    try:
        parsed = urllib.parse.urlsplit(url)
        netloc = parsed.netloc
        if "@" in netloc:
            creds, host = netloc.split("@", 1)
            if ":" in creds:
                user, _ = creds.split(":", 1)
                netloc = f"{user}:***@{host}"
            else:
                netloc = f"{creds}:***@{host}"
        return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    except Exception:
        return "postgresql://***:***@<hidden_host>/<hidden_db>"


class PGExecutionResult:
    """Cursor-compatible result object for PostgreSQL execution."""

    def __init__(self, lastrowid: Optional[int] = None, rowcount: int = 0, status: str = ""):
        self.lastrowid = lastrowid
        self.rowcount = rowcount
        self.status = status

    def __repr__(self):
        return f"<PGExecutionResult lastrowid={self.lastrowid} rowcount={self.rowcount}>"


class SQLCompatibilityAdapter:
    """Zero-overhead SQL translation engine converting SQLite syntax to PostgreSQL."""

    REPLACE_TARGETS = {
        "antinuke_whitelist": ("guild_id", "target_id"),
        "security_approved_bots": ("guild_id", "bot_id"),
        "welcome_config": ("guild_id",),
        "antinuke_config": ("guild_id",),
        "ai_channels": ("channel_id",),
        "cloned_templates": ("template_id",),
    }

    TABLES_WITH_SERIAL_ID = {
        "antinuke_whitelist", "security_approved_bots", "security_audit_logs",
        "whitelist_audit", "antispam_exemptions", "tickets", "moderation_logs",
        "warnings", "payment_records", "premium_subscriptions", "reaction_roles",
        "auto_responders", "music_history", "ai_memory", "ai_usage", "ai_logs",
        "public_ai_conversations", "public_ai_usage", "economy_transactions",
        "economy_inventory", "economy_user_animals", "economy_user_pets",
        "economy_battles", "economy_relationships", "economy_friends",
        "economy_channel_settings", "config_audit_logs", "server_clone_history"
    }

    @classmethod
    def replace_placeholders(cls, sql: str) -> str:
        """Replace unquoted ? with $1, $2, $3... for asyncpg."""
        out = []
        param_idx = 1
        in_single = False
        in_double = False
        i = 0
        n = len(sql)
        while i < n:
            ch = sql[i]
            if ch == "'" and not in_double:
                in_single = not in_single
                out.append(ch)
            elif ch == '"' and not in_single:
                in_double = not in_double
                out.append(ch)
            elif ch == '?' and not in_single and not in_double:
                out.append(f"${param_idx}")
                param_idx += 1
            else:
                out.append(ch)
            i += 1
        return "".join(out)

    @classmethod
    def sanitize_parameters(cls, parameters: Union[Tuple[Any, ...], List[Any]]) -> List[Any]:
        """Convert booleans to integer 0/1 to match INTEGER columns in PostgreSQL."""
        sanitized = []
        for p in parameters:
            if isinstance(p, bool):
                sanitized.append(1 if p else 0)
            else:
                sanitized.append(p)
        return sanitized

    @classmethod
    def extract_rowcount(cls, status: str) -> int:
        """Extract modified row count from PostgreSQL command status string."""
        if not status:
            return 0
        parts = status.strip().split()
        if parts and parts[-1].isdigit():
            return int(parts[-1])
        return 0

    @classmethod
    def translate_to_postgres(cls, query: str, parameters: Tuple[Any, ...] = ()) -> Tuple[str, bool]:
        """Convert SQLite-specific syntax to standard PostgreSQL. Returns (pg_query, expects_returning_id)."""
        sql = query.strip()
        expects_returning_id = False

        # 1. PRAGMA bypass
        if sql.upper().startswith("PRAGMA"):
            return "SELECT 1;", False

        # 2. Translate datetime('now', '-1 hour')
        sql = re.sub(r"datetime\(\s*'now'\s*,\s*'-1 hour'\s*\)", "(NOW() - INTERVAL '1 hour')", sql, flags=re.IGNORECASE)
        sql = re.sub(r"datetime\(\s*'now'\s*\)", "NOW()", sql, flags=re.IGNORECASE)

        # 3. Handle INSERT OR IGNORE
        if re.search(r"INSERT\s+OR\s+IGNORE\s+INTO\s+", sql, re.IGNORECASE):
            sql = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO\s+", "INSERT INTO ", sql, count=1, flags=re.IGNORECASE)
            sql_clean = sql.rstrip(";\n\t ")
            sql = sql_clean + " ON CONFLICT DO NOTHING"

        # 4. Handle INSERT OR REPLACE
        replace_match = re.search(r"INSERT\s+OR\s+REPLACE\s+INTO\s+([^\s\(]+)\s*\(([^\)]+)\)\s*VALUES\s*\(([^\)]+)\)", sql, re.IGNORECASE)
        if replace_match:
            tbl = replace_match.group(1).strip('"` ')
            cols = [c.strip('"` ') for c in replace_match.group(2).split(",")]
            conflict_cols = cls.REPLACE_TARGETS.get(tbl.lower())
            if conflict_cols:
                conflict_clause = ", ".join(f'"{c}"' for c in conflict_cols)
                update_cols = [c for c in cols if c.lower() not in [x.lower() for x in conflict_cols]]
                if update_cols:
                    update_clause = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
                    conflict_sql = f" ON CONFLICT ({conflict_clause}) DO UPDATE SET {update_clause}"
                else:
                    conflict_sql = f" ON CONFLICT ({conflict_clause}) DO NOTHING"
                sql = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO\s+", "INSERT INTO ", sql, count=1, flags=re.IGNORECASE)
                sql_clean = sql.rstrip(";\n\t ")
                sql = sql_clean + conflict_sql

        # 5. Check if query is an INSERT that could return serial ID
        insert_match = re.search(r"^INSERT\s+INTO\s+([^\s\(]+)", sql, re.IGNORECASE)
        if insert_match and "RETURNING" not in sql.upper() and "ON CONFLICT DO NOTHING" not in sql.upper():
            tbl_name = insert_match.group(1).strip('"` ')
            if tbl_name.lower() in cls.TABLES_WITH_SERIAL_ID:
                sql = sql.rstrip(";\n\t ") + ' RETURNING "id"'
                expects_returning_id = True

        # 6. Replace ? with $1, $2, ...
        sql = cls.replace_placeholders(sql)

        # Guarantee trailing semicolon
        if not sql.endswith(";"):
            sql += ";"

        return sql, expects_returning_id


class DatabaseManager:
    """Production asynchronous dual-engine database manager for NOVEXA.

    Seamlessly supports both local SQLite and cloud PostgreSQL (Neon).
    When DATABASE_URL is present, connects to PostgreSQL with asyncpg connection pooling.
    When DATABASE_URL is absent, falls back to local SQLite (gulamali_bot.db).
    """

    def __init__(self, db_path: Path = DATABASE_PATH, database_url: str = DATABASE_URL):
        self.db_path = db_path
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self._connection: Optional[aiosqlite.Connection] = None
        self._pool: Optional[Any] = None  # asyncpg.Pool

    @property
    def is_postgres(self) -> bool:
        return bool(self.database_url and self.database_url.strip())

    async def connect(self) -> None:
        """Establish connection with active engine (PostgreSQL pool or SQLite connection)."""
        if self.is_postgres:
            if asyncpg is None:
                raise RuntimeError("asyncpg is required for PostgreSQL mode. Install with: pip install asyncpg")
            clean_url = self.database_url.replace("postgres://", "postgresql://")
            masked = mask_database_url(clean_url)
            logger.info(f"Connecting to PostgreSQL database pool at {masked}...")
            self._pool = await asyncpg.create_pool(clean_url, min_size=2, max_size=10, ssl="require")
            logger.info("PostgreSQL database pool connected successfully.")
            return

        # SQLite Mode
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA foreign_keys = ON;")
        await self._connection.execute("PRAGMA journal_mode = WAL;")
        await self._connection.execute("PRAGMA synchronous = NORMAL;")
        await self._connection.execute("PRAGMA temp_store = MEMORY;")
        await self._connection.execute("PRAGMA mmap_size = 268435456;")
        await self._connection.execute("PRAGMA cache_size = -64000;")
        logger.info(f"Database connected in SQLite mode at {self.db_path}")

    async def close(self) -> None:
        """Gracefully terminate database connections or connection pool."""
        if self.is_postgres and self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL database pool closed.")
            return

        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed.")

    @property
    def conn(self) -> aiosqlite.Connection:
        if self.is_postgres:
            raise RuntimeError("Direct 'conn' property is not supported in PostgreSQL mode. Use execute/fetch methods.")
        if self._connection is None:
            raise RuntimeError("Database connection has not been initialized. Call connect() first.")
        return self._connection

    async def execute(self, query: str, parameters: Tuple[Any, ...] = ()) -> Any:
        """Execute a single query with parameters."""
        if self.is_postgres:
            if query.strip().upper().startswith("PRAGMA"):
                return PGExecutionResult(rowcount=0, status="PRAGMA_IGNORED")
            pg_sql, expects_id = SQLCompatibilityAdapter.translate_to_postgres(query, parameters)
            sanitized = SQLCompatibilityAdapter.sanitize_parameters(parameters)
            async with self._pool.acquire() as connection:
                if expects_id:
                    row = await connection.fetchrow(pg_sql, *sanitized)
                    lastrowid = row[0] if row else None
                    return PGExecutionResult(lastrowid=lastrowid, rowcount=1, status="INSERT 1")
                else:
                    status = await connection.execute(pg_sql, *sanitized)
                    rowcount = SQLCompatibilityAdapter.extract_rowcount(status)
                    return PGExecutionResult(lastrowid=None, rowcount=rowcount, status=status)

        cursor = await self.conn.execute(query, parameters)
        await self.conn.commit()
        return cursor

    async def executemany(self, query: str, parameters: List[Tuple[Any, ...]]) -> Any:
        """Execute multiple parameter sets for a query."""
        if self.is_postgres:
            if not parameters:
                return PGExecutionResult(rowcount=0)
            pg_sql, _ = SQLCompatibilityAdapter.translate_to_postgres(query, parameters[0])
            sanitized_list = [SQLCompatibilityAdapter.sanitize_parameters(p) for p in parameters]
            async with self._pool.acquire() as connection:
                await connection.executemany(pg_sql, sanitized_list)
            return PGExecutionResult(rowcount=len(parameters), status=f"EXECUTEMANY {len(parameters)}")

        cursor = await self.conn.executemany(query, parameters)
        await self.conn.commit()
        return cursor

    async def fetchone(self, query: str, parameters: Tuple[Any, ...] = ()) -> Optional[Any]:
        """Fetch a single row."""
        if self.is_postgres:
            pg_sql, _ = SQLCompatibilityAdapter.translate_to_postgres(query, parameters)
            sanitized = SQLCompatibilityAdapter.sanitize_parameters(parameters)
            async with self._pool.acquire() as connection:
                return await connection.fetchrow(pg_sql, *sanitized)

        async with self.conn.execute(query, parameters) as cursor:
            return await cursor.fetchone()

    fetch_one = fetchone

    async def fetchall(self, query: str, parameters: Tuple[Any, ...] = ()) -> List[Any]:
        """Fetch all matching rows."""
        if self.is_postgres:
            pg_sql, _ = SQLCompatibilityAdapter.translate_to_postgres(query, parameters)
            sanitized = SQLCompatibilityAdapter.sanitize_parameters(parameters)
            async with self._pool.acquire() as connection:
                return await connection.fetch(pg_sql, *sanitized)

        async with self.conn.execute(query, parameters) as cursor:
            return await cursor.fetchall()

    fetch_all = fetchall

    async def init_schema(self) -> None:
        """Initialize all database tables with strict schema and indexes."""
        if self.is_postgres:
            schema_file = Path(__file__).resolve().parent / "postgres_schema.sql"
            if schema_file.exists():
                sql_content = schema_file.read_text(encoding="utf-8")
                async with self._pool.acquire() as connection:
                    await connection.execute(sql_content)
                logger.info("PostgreSQL database schema initialized from postgres_schema.sql.")
            return

        # SQLite Schema Initialization
        schema_sql = """
        -- Guild Core Settings
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            prefix TEXT DEFAULT '/',
            welcome_enabled INTEGER DEFAULT 1,
            tickets_enabled INTEGER DEFAULT 1,
            antinuke_enabled INTEGER DEFAULT 1,
            music_enabled INTEGER DEFAULT 1,
            leveling_enabled INTEGER DEFAULT 1,
            economy_enabled INTEGER DEFAULT 1,
            payments_enabled INTEGER DEFAULT 1,
            logging_enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Welcome System
        CREATE TABLE IF NOT EXISTS welcome_config (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            message_template TEXT DEFAULT 'Welcome {user} to **{server}**! You are member #{member_count}.',
            embed_enabled INTEGER DEFAULT 1,
            banner_enabled INTEGER DEFAULT 1,
            background_url TEXT DEFAULT '',
            leave_channel_id INTEGER,
            leave_template TEXT DEFAULT '{username} has left **{server}**.',
            is_enabled INTEGER DEFAULT 1,
            template_id TEXT DEFAULT 'novexa_exclusive',
            title TEXT DEFAULT 'Welcome to {server}!',
            custom_color TEXT DEFAULT '#5865F2',
            dm_enabled INTEGER DEFAULT 0,
            dm_template TEXT DEFAULT 'Welcome to **{server}**, {user}! Read our rules to get started.',
            autorole_enabled INTEGER DEFAULT 0,
            autorole_id INTEGER DEFAULT NULL
        );

        -- Ticket Panels and Active Tickets
        CREATE TABLE IF NOT EXISTS ticket_panels (
            panel_id TEXT PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            message_id INTEGER,
            title TEXT DEFAULT 'Support Ticket',
            description TEXT DEFAULT 'Click the button below to open a ticket.',
            category_id INTEGER,
            support_role_id INTEGER,
            naming_scheme TEXT DEFAULT 'ticket-{number}',
            transcript_channel_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            ticket_number INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            claimed_by INTEGER,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            reason TEXT DEFAULT 'General Support'
        );

        -- Anti-Nuke Engine Configuration
        CREATE TABLE IF NOT EXISTS antinuke_config (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            punishment_type TEXT DEFAULT 'ban',
            max_channel_deletions INTEGER DEFAULT 2,
            max_channel_creations INTEGER DEFAULT 3,
            max_role_deletions INTEGER DEFAULT 2,
            max_role_creations INTEGER DEFAULT 3,
            max_bans INTEGER DEFAULT 3,
            max_kicks INTEGER DEFAULT 4,
            max_webhook_creations INTEGER DEFAULT 2,
            max_webhook_deletions INTEGER DEFAULT 2,
            time_window INTEGER DEFAULT 10,
            log_channel_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS antinuke_whitelist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            target_type TEXT DEFAULT 'user',
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT,
            UNIQUE(guild_id, target_id)
        );

        -- User Profiles
        CREATE TABLE IF NOT EXISTS user_profiles (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            bio TEXT DEFAULT 'Hello! I am using Novexa.',
            custom_color TEXT DEFAULT '#5865F2',
            custom_avatar_url TEXT DEFAULT '',
            custom_banner_url TEXT DEFAULT '',
            background_url TEXT DEFAULT '',
            PRIMARY KEY (guild_id, user_id)
        );

        -- Leveling System
        CREATE TABLE IF NOT EXISTS leveling (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            messages_count INTEGER DEFAULT 0,
            last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_xp_time REAL DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        );

        -- Economy Engine
        CREATE TABLE IF NOT EXISTS economy (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            wallet REAL DEFAULT 0.0,
            bank REAL DEFAULT 0.0,
            bank_limit REAL DEFAULT 50000.0,
            last_daily TIMESTAMP,
            last_work TIMESTAMP,
            last_crime TIMESTAMP,
            streak INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        );

        -- Moderation Audit Logs
        CREATE TABLE IF NOT EXISTS moderation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            reason TEXT DEFAULT 'No reason provided.',
            duration INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT DEFAULT 'No reason provided.',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Payments, Subscriptions and Invoicing
        CREATE TABLE IF NOT EXISTS payments_config (
            guild_id INTEGER PRIMARY KEY,
            upi_id TEXT DEFAULT '',
            qr_code_url TEXT DEFAULT '',
            qr_image_url TEXT DEFAULT '',
            instructions TEXT DEFAULT '',
            staff_role_id INTEGER,
            paypal_email TEXT DEFAULT '',
            crypto_address TEXT DEFAULT '',
            log_channel_id INTEGER,
            is_enabled INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS payment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'INR',
            method TEXT DEFAULT 'UPI',
            transaction_id TEXT DEFAULT '',
            reference_id TEXT DEFAULT '',
            screenshot_url TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            proof_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified_by INTEGER,
            verified_at TIMESTAMP,
            reviewed_by INTEGER,
            reviewed_at TIMESTAMP
        );

        -- Reaction Roles & Utility
        CREATE TABLE IF NOT EXISTS reaction_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            emoji TEXT NOT NULL,
            role_id INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS auto_roles (
            guild_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            is_bot INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, role_id)
        );

        CREATE TABLE IF NOT EXISTS auto_responders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            trigger TEXT NOT NULL,
            response TEXT NOT NULL,
            match_type TEXT DEFAULT 'exact',
            created_by INTEGER
        );

        CREATE TABLE IF NOT EXISTS starboard_config (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            threshold INTEGER DEFAULT 3,
            star_count INTEGER DEFAULT 3,
            emoji TEXT DEFAULT '⭐',
            enabled INTEGER DEFAULT 1,
            is_enabled INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS starboard_messages (
            original_message_id INTEGER PRIMARY KEY,
            starboard_message_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            stars INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS giveaways (
            message_id INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            prize TEXT NOT NULL,
            winners_count INTEGER DEFAULT 1,
            end_time TIMESTAMP,
            ends_at TIMESTAMP,
            ended INTEGER DEFAULT 0,
            host_id INTEGER,
            created_by INTEGER,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS sticky_messages (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            last_message_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS birthdays (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            day INTEGER NOT NULL,
            month INTEGER NOT NULL,
            PRIMARY KEY (guild_id, user_id)
        );

        -- Logging Configuration
        CREATE TABLE IF NOT EXISTS logging_config (
            guild_id INTEGER PRIMARY KEY,
            category_id INTEGER,
            mod_logs_channel_id INTEGER,
            message_logs_channel_id INTEGER,
            server_logs_channel_id INTEGER,
            join_leave_channel_id INTEGER,
            errors_channel_id INTEGER,
            payment_activity_channel_id INTEGER,
            ticket_activity_channel_id INTEGER,
            voice_logs_channel_id INTEGER,
            member_logs_channel_id INTEGER,
            joins_channel_id INTEGER,
            leaves_channel_id INTEGER,
            message_deletes_channel_id INTEGER,
            message_edits_channel_id INTEGER,
            channel_changes_channel_id INTEGER,
            role_changes_channel_id INTEGER,
            antinuke_channel_id INTEGER,
            bans_channel_id INTEGER,
            kicks_channel_id INTEGER,
            timeouts_channel_id INTEGER,
            is_enabled INTEGER DEFAULT 1
        );

        -- Server Setups Tracking
        CREATE TABLE IF NOT EXISTS server_setups (
            guild_id INTEGER PRIMARY KEY,
            is_setup INTEGER DEFAULT 0,
            setup_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            template_id TEXT DEFAULT 'gaming',
            template_name TEXT DEFAULT '',
            server_name TEXT,
            created_categories TEXT DEFAULT '[]',
            created_channels TEXT DEFAULT '[]',
            created_roles TEXT DEFAULT '[]',
            welcome_channel_id INTEGER,
            exit_channel_id INTEGER,
            rules_channel_id INTEGER,
            ticket_category_id INTEGER,
            logging_channels TEXT DEFAULT '{}',
            setup_status TEXT DEFAULT 'pending',
            setup_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- AI Channel Configuration
        CREATE TABLE IF NOT EXISTS ai_channels (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            mode TEXT DEFAULT 'coding_assistant',
            auto_thread INTEGER DEFAULT 1,
            added_by INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- AI Global Configuration
        CREATE TABLE IF NOT EXISTS ai_config (
            guild_id INTEGER PRIMARY KEY,
            provider TEXT DEFAULT 'gemini',
            model TEXT DEFAULT 'gemini-1.5-flash',
            temperature REAL DEFAULT 0.7,
            max_tokens INTEGER DEFAULT 2048,
            memory_enabled INTEGER DEFAULT 1,
            vision_enabled INTEGER DEFAULT 1,
            is_enabled INTEGER DEFAULT 1,
            persona TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- AI Long-Term Server Facts
        CREATE TABLE IF NOT EXISTS ai_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            fact TEXT NOT NULL,
            added_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- AI Persistent Conversation Memory
        CREATE TABLE IF NOT EXISTS ai_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- AI Rate Limiting & Usage Tracking
        CREATE TABLE IF NOT EXISTS ai_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            model_used TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- AI Security & Action Logs
        CREATE TABLE IF NOT EXISTS ai_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            prompt TEXT NOT NULL,
            response_preview TEXT,
            has_code INTEGER DEFAULT 0,
            has_image INTEGER DEFAULT 0,
            tokens INTEGER DEFAULT 0,
            latency_ms INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Advanced Security & Approvals
        CREATE TABLE IF NOT EXISTS security_approved_bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            bot_id INTEGER NOT NULL,
            bot_name TEXT DEFAULT 'Unknown Bot',
            approved_by INTEGER NOT NULL,
            approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(guild_id, bot_id)
        );

        CREATE TABLE IF NOT EXISTS security_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            actor_id INTEGER NOT NULL,
            target_id INTEGER DEFAULT 0,
            target_name TEXT,
            action_type TEXT,
            action_taken TEXT NOT NULL,
            details TEXT DEFAULT '',
            executor_id INTEGER,
            executor_tag TEXT,
            severity TEXT DEFAULT 'HIGH',
            punishment_applied TEXT DEFAULT 'NONE',
            restored INTEGER DEFAULT 0,
            correlation_status TEXT DEFAULT 'EXACT_MATCH',
            latency_ms INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS server_backups (
            backup_id TEXT PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            creator_id INTEGER,
            created_by INTEGER,
            backup_name TEXT DEFAULT 'Automatic Snapshot',
            structure_json TEXT,
            data_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS whitelist_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            admin_id INTEGER,
            target_id INTEGER NOT NULL,
            target_type TEXT DEFAULT 'ALL',
            action TEXT NOT NULL,
            performed_by INTEGER,
            expires_at TIMESTAMP,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Economy Extended Tables
        CREATE TABLE IF NOT EXISTS economy_users (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            level INTEGER DEFAULT 1,
            xp BIGINT DEFAULT 0,
            wallet BIGINT DEFAULT 1000,
            bank BIGINT DEFAULT 0,
            bank_max BIGINT DEFAULT 50000,
            net_worth BIGINT DEFAULT 1000,
            reputation INTEGER DEFAULT 0,
            streak_daily INTEGER DEFAULT 0,
            last_daily TIMESTAMP,
            last_work TIMESTAMP,
            last_crime TIMESTAMP,
            last_rob TIMESTAMP,
            equipped_weapon TEXT DEFAULT NULL,
            equipped_armor TEXT DEFAULT NULL,
            equipped_pet TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            gems INTEGER DEFAULT 0,
            daily_streak INTEGER DEFAULT 0,
            last_weekly TIMESTAMP,
            last_monthly TIMESTAMP,
            last_slut TIMESTAMP,
            last_rep TIMESTAMP,
            last_hunt TIMESTAMP,
            last_battle TIMESTAMP,
            total_earned BIGINT DEFAULT 0,
            total_spent BIGINT DEFAULT 0,
            commands_used INTEGER DEFAULT 0,
            hunts_count INTEGER DEFAULT 0,
            battles_won INTEGER DEFAULT 0,
            battles_lost INTEGER DEFAULT 0,
            gambles_won INTEGER DEFAULT 0,
            gambles_lost INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            bio TEXT DEFAULT '',
            PRIMARY KEY (guild_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS economy_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            from_user_id INTEGER,
            to_user_id INTEGER,
            amount BIGINT NOT NULL,
            tx_type TEXT NOT NULL,
            currency_type TEXT DEFAULT 'coins',
            reason TEXT DEFAULT '',
            description TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS economy_items (
            item_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            rarity TEXT NOT NULL,
            buy_price INTEGER DEFAULT 0,
            sell_price INTEGER DEFAULT 0,
            gem_price INTEGER DEFAULT 0,
            attack_bonus INTEGER DEFAULT 0,
            defense_bonus INTEGER DEFAULT 0,
            hunt_luck INTEGER DEFAULT 0,
            consumable INTEGER DEFAULT 0,
            max_stack INTEGER DEFAULT 999,
            icon TEXT DEFAULT '📦',
            slot TEXT DEFAULT NULL,
            special_ability TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS economy_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            slot TEXT DEFAULT NULL,
            is_equipped INTEGER DEFAULT 0,
            UNIQUE (guild_id, user_id, item_id),
            FOREIGN KEY (item_id) REFERENCES economy_items(item_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS economy_animals (
            animal_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            emoji TEXT NOT NULL,
            rarity TEXT NOT NULL,
            base_value INTEGER NOT NULL,
            base_xp BIGINT NOT NULL,
            catch_weight INTEGER NOT NULL,
            ability TEXT DEFAULT '',
            description TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS economy_user_animals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            animal_id TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            is_favorite INTEGER DEFAULT 0,
            last_caught TIMESTAMP,
            acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(guild_id, user_id, animal_id),
            FOREIGN KEY (animal_id) REFERENCES economy_animals(animal_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS economy_pets (
            pet_type TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            emoji TEXT NOT NULL,
            rarity TEXT NOT NULL,
            bonus_type TEXT NOT NULL,
            bonus_value REAL NOT NULL,
            description TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS economy_user_pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            pet_type TEXT NOT NULL,
            nickname TEXT DEFAULT NULL,
            level INTEGER DEFAULT 1,
            xp BIGINT DEFAULT 0,
            hunger INTEGER DEFAULT 100,
            happiness INTEGER DEFAULT 100,
            is_active INTEGER DEFAULT 0,
            is_equipped INTEGER DEFAULT 0,
            last_fed TIMESTAMP,
            FOREIGN KEY (pet_type) REFERENCES economy_pets(pet_type) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS economy_battles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            challenger_id INTEGER NOT NULL,
            opponent_id INTEGER NOT NULL,
            bet_amount BIGINT DEFAULT 0,
            winner_id INTEGER DEFAULT NULL,
            loser_id INTEGER DEFAULT NULL,
            xp_awarded INTEGER DEFAULT 0,
            battle_log TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS economy_trades (
            trade_id TEXT PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            user1_offer TEXT DEFAULT '{}',
            user2_offer TEXT DEFAULT '{}',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS economy_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            status TEXT DEFAULT 'married',
            ring_item_id TEXT DEFAULT 'diamond_ring',
            married_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            love_points INTEGER DEFAULT 100,
            UNIQUE(guild_id, user1_id),
            UNIQUE(guild_id, user2_id)
        );

        CREATE TABLE IF NOT EXISTS economy_friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            friend_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(guild_id, user_id, friend_id)
        );

        CREATE TABLE IF NOT EXISTS economy_achievements (
            key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            icon TEXT DEFAULT '🏆',
            gem_reward INTEGER DEFAULT 5,
            coin_reward INTEGER DEFAULT 500
        );

        CREATE TABLE IF NOT EXISTS economy_user_achievements (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            achievement_key TEXT NOT NULL,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, user_id, achievement_key),
            FOREIGN KEY (achievement_key) REFERENCES economy_achievements(key) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS economy_guild_settings (
            guild_id INTEGER PRIMARY KEY,
            currency_name TEXT DEFAULT 'Coins',
            currency_symbol TEXT DEFAULT '🪙',
            starting_balance BIGINT DEFAULT 1000,
            work_min BIGINT DEFAULT 50,
            work_max BIGINT DEFAULT 250,
            crime_min BIGINT DEFAULT 100,
            crime_max BIGINT DEFAULT 500,
            rob_cooldown INTEGER DEFAULT 7200,
            xp_multiplier REAL DEFAULT 1.0,
            economy_enabled INTEGER DEFAULT 1,
            is_enabled INTEGER DEFAULT 1,
            daily_reward INTEGER DEFAULT 1000,
            daily_reward_min INTEGER DEFAULT 100,
            daily_reward_max INTEGER DEFAULT 500,
            streak_bonus_per_day INTEGER DEFAULT 25,
            work_cooldown INTEGER DEFAULT 300,
            crime_cooldown INTEGER DEFAULT 600,
            hunt_cooldown INTEGER DEFAULT 15,
            channel_enforcement INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS economy_channel_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            category_type TEXT NOT NULL,
            is_allowed INTEGER DEFAULT 1,
            UNIQUE(guild_id, channel_id, category_type)
        );

        CREATE TABLE IF NOT EXISTS public_ai_settings (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            default_personality TEXT DEFAULT 'helpful',
            model_tier TEXT DEFAULT 'standard',
            max_daily_messages INTEGER DEFAULT 100,
            reply_chance REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS public_ai_channels (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            allow_threads INTEGER DEFAULT 1,
            custom_persona TEXT DEFAULT '',
            added_by INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS public_ai_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            user_prompt TEXT NOT NULL,
            bot_reply TEXT NOT NULL,
            provider TEXT DEFAULT 'free',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS public_ai_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message_count INTEGER DEFAULT 1,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS antispam_config (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            max_messages INTEGER DEFAULT 5,
            per_seconds INTEGER DEFAULT 5,
            duplicate_threshold INTEGER DEFAULT 3,
            max_mentions INTEGER DEFAULT 5,
            max_emojis INTEGER DEFAULT 8,
            link_filter_enabled INTEGER DEFAULT 1,
            invite_filter_enabled INTEGER DEFAULT 1,
            punishment_type TEXT DEFAULT 'mute',
            mute_duration INTEGER DEFAULT 300,
            log_channel_id INTEGER DEFAULT NULL,
            caps_filter_enabled INTEGER DEFAULT 0,
            blocked_words TEXT DEFAULT '',
            attachment_spam_limit INTEGER DEFAULT 5,
            automod_action TEXT DEFAULT 'warn'
        );

        CREATE TABLE IF NOT EXISTS antispam_exemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            target_type TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS premium_plans (
            plan_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price_inr REAL NOT NULL,
            billing_period TEXT NOT NULL,
            max_guilds INTEGER DEFAULT 1,
            features_json TEXT NOT NULL,
            tier_level INTEGER DEFAULT 1,
            max_backups INTEGER DEFAULT 0,
            max_ai_daily INTEGER DEFAULT 0,
            tier_color TEXT DEFAULT '',
            max_custom_roles INTEGER DEFAULT 0,
            custom_embeds INTEGER DEFAULT 0,
            audit_retention_days INTEGER DEFAULT 30,
            custom_branding INTEGER DEFAULT 0,
            priority_support INTEGER DEFAULT 0,
            unlimited_backups INTEGER DEFAULT 0,
            ai_tokens_monthly INTEGER DEFAULT 0,
            perks_json TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS premium_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            plan_id TEXT NOT NULL,
            subscriber_user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            payment_ref TEXT DEFAULT '',
            FOREIGN KEY (plan_id) REFERENCES premium_plans(plan_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS config_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            module_name TEXT DEFAULT '',
            changed_by_user_id INTEGER DEFAULT 0,
            changes_json TEXT DEFAULT '{}',
            source TEXT DEFAULT 'web_dashboard',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cloned_templates (
            template_id TEXT PRIMARY KEY,
            source_guild_id INTEGER NOT NULL,
            source_guild_name TEXT NOT NULL,
            template_name TEXT NOT NULL,
            creator_id INTEGER NOT NULL,
            structure_json TEXT NOT NULL,
            is_public INTEGER DEFAULT 0,
            use_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS server_clone_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id TEXT,
            target_guild_id INTEGER,
            cloned_by_user_id INTEGER,
            source_guild_id INTEGER,
            source_guild_name TEXT,
            dest_guild_id INTEGER,
            dest_guild_name TEXT,
            user_id INTEGER,
            mode TEXT DEFAULT 'full',
            created_categories INTEGER DEFAULT 0,
            created_channels INTEGER DEFAULT 0,
            created_roles INTEGER DEFAULT 0,
            report_json TEXT,
            channels_created INTEGER DEFAULT 0,
            roles_created INTEGER DEFAULT 0,
            categories_created INTEGER DEFAULT 0,
            cloned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS owo_channels (
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            panel_message_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, channel_id)
        );

        CREATE TABLE IF NOT EXISTS mention_replies (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reply_message TEXT NOT NULL,
            embed_enabled INTEGER DEFAULT 1,
            is_enabled INTEGER DEFAULT 1,
            cooldown_seconds INTEGER DEFAULT 60,
            created_by INTEGER,
            PRIMARY KEY (guild_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS react_users (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            emoji TEXT NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            created_by INTEGER,
            PRIMARY KEY (guild_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS staff_config (
            guild_id INTEGER PRIMARY KEY,
            role_id INTEGER DEFAULT NULL,
            name_style TEXT DEFAULT 'staff',
            channels_list TEXT DEFAULT '[]',
            channels_json TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS server_staff (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            original_nick TEXT DEFAULT NULL,
            added_by INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS music_config (
            guild_id INTEGER PRIMARY KEY,
            default_volume REAL DEFAULT 1.0,
            is_247 INTEGER DEFAULT 0,
            text_channel_id INTEGER DEFAULT NULL,
            voice_channel_id INTEGER DEFAULT NULL,
            dj_role_id INTEGER DEFAULT NULL,
            audio_filter TEXT DEFAULT 'flat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS music_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            webpage_url TEXT NOT NULL,
            duration INTEGER DEFAULT 0,
            requested_by INTEGER NOT NULL,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS admin_config (
            guild_id INTEGER PRIMARY KEY,
            role_id INTEGER DEFAULT NULL,
            name_style TEXT DEFAULT 'crown',
            auto_sync_channels INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS server_admins (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            original_nick TEXT DEFAULT NULL,
            added_by INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, user_id)
        );

        -- Dropper Suite
        CREATE TABLE IF NOT EXISTS dropper_config (
            guild_id INTEGER PRIMARY KEY,
            role_id INTEGER NOT NULL,
            category_id INTEGER,
            channels_list TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS server_droppers (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            added_by INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, user_id)
        );

        -- AI Wallpaper Studio
        CREATE TABLE IF NOT EXISTS wallpaper_channels (
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, channel_id)
        );

        -- Temporary Voice Channels
        CREATE TABLE IF NOT EXISTS voice_config (
            guild_id INTEGER PRIMARY KEY,
            generator_channel_id INTEGER,
            category_id INTEGER,
            channel_name_format TEXT DEFAULT '🔊・{username}',
            default_user_limit INTEGER DEFAULT 0,
            default_bitrate INTEGER DEFAULT 64000,
            is_enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            delete_when_empty INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS active_temp_channels (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            control_panel_message_id INTEGER,
            is_locked INTEGER DEFAULT 0,
            is_hidden INTEGER DEFAULT 0,
            custom_status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Indexing for high-throughput queries
        CREATE INDEX IF NOT EXISTS idx_tickets_guild ON tickets(guild_id, status);
        CREATE INDEX IF NOT EXISTS idx_leveling_guild_xp ON leveling(guild_id, xp DESC);
        CREATE INDEX IF NOT EXISTS idx_moderation_guild_user ON moderation_logs(guild_id, user_id);
        CREATE INDEX IF NOT EXISTS idx_warnings_guild_user ON warnings(guild_id, user_id);
        CREATE INDEX IF NOT EXISTS idx_payment_records_guild ON payment_records(guild_id, status);
        CREATE INDEX IF NOT EXISTS idx_ai_channels_guild ON ai_channels(guild_id);
        CREATE INDEX IF NOT EXISTS idx_ai_memory_user ON ai_memory(guild_id, channel_id, user_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_ai_usage_guild ON ai_usage(guild_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_owo_channels_guild ON owo_channels(guild_id);
        CREATE INDEX IF NOT EXISTS idx_mention_replies_guild ON mention_replies(guild_id);
        CREATE INDEX IF NOT EXISTS idx_react_users_guild ON react_users(guild_id);
        CREATE INDEX IF NOT EXISTS idx_server_staff_guild ON server_staff(guild_id);
        CREATE INDEX IF NOT EXISTS idx_server_admins_guild ON server_admins(guild_id);
        CREATE INDEX IF NOT EXISTS idx_music_history_guild ON music_history(guild_id, played_at DESC);
        """
        await self.conn.executescript(schema_sql)
        await self.conn.commit()

        # Run database migrations from database/migrations/
        migrations_dir = Path(__file__).resolve().parent / "migrations"
        if migrations_dir.exists():
            for migration_file in sorted(migrations_dir.glob("*.sql")):
                try:
                    sql_content = migration_file.read_text(encoding="utf-8")
                    await self.conn.executescript(sql_content)
                    await self.conn.commit()
                except Exception as e:
                    logger.error(f"Error applying migration {migration_file.name}: {e}")

        # Database migrations / column safeguards
        safeguards = [
            ("server_setups", "ai_channel_id", "INTEGER DEFAULT NULL"),
            ("welcome_config", "template_id", "TEXT DEFAULT 'novexa_exclusive'"),
            ("welcome_config", "title", "TEXT DEFAULT 'Welcome to {server}!'"),
            ("welcome_config", "custom_color", "TEXT DEFAULT '#5865F2'"),
            ("welcome_config", "footer_text", "TEXT DEFAULT 'Member #{member_count} • NOVEXA'"),
            ("welcome_config", "message_enabled", "INTEGER DEFAULT 1"),
            ("welcome_config", "dm_enabled", "INTEGER DEFAULT 0"),
            ("welcome_config", "dm_template", "TEXT DEFAULT 'Welcome to **{server}**, {user}! We are thrilled to have you here.'"),
            ("welcome_config", "autorole_enabled", "INTEGER DEFAULT 0"),
            ("welcome_config", "autorole_id", "INTEGER DEFAULT NULL"),
            ("welcome_config", "goodbye_enabled", "INTEGER DEFAULT 1"),
            ("welcome_config", "goodbye_template_id", "TEXT DEFAULT 'minimal_dark'"),
            ("welcome_config", "goodbye_embed_enabled", "INTEGER DEFAULT 1"),
            ("welcome_config", "leave_embed_enabled", "INTEGER DEFAULT 1"),
            ("welcome_config", "leave_message_template", "TEXT DEFAULT NULL"),
            ("antinuke_config", "mode", "TEXT DEFAULT 'medium'"),
            ("antinuke_config", "max_channel_updates", "INTEGER DEFAULT 4"),
            ("antinuke_config", "max_role_updates", "INTEGER DEFAULT 4"),
            ("antinuke_config", "max_webhook_changes", "INTEGER DEFAULT 4"),
            ("antinuke_config", "max_permission_changes", "INTEGER DEFAULT 1"),
            ("antinuke_config", "bot_protection_enabled", "INTEGER DEFAULT 1"),
            ("antinuke_config", "raid_shield_enabled", "INTEGER DEFAULT 1"),
            ("antinuke_config", "raid_join_threshold", "INTEGER DEFAULT 6"),
            ("antinuke_config", "raid_window", "INTEGER DEFAULT 15"),
            ("antinuke_config", "raid_min_age_days", "INTEGER DEFAULT 7"),
            ("antispam_config", "caps_filter_enabled", "INTEGER DEFAULT 0"),
            ("antispam_config", "blocked_words", "TEXT DEFAULT ''"),
            ("antispam_config", "attachment_spam_limit", "INTEGER DEFAULT 5"),
            ("antispam_config", "automod_action", "TEXT DEFAULT 'warn'"),
            ("guild_settings", "mod_log_channel_id", "INTEGER DEFAULT NULL"),
            ("guild_settings", "dm_on_punish", "INTEGER DEFAULT 1"),
            ("guild_settings", "max_warnings_kick", "INTEGER DEFAULT 3"),
            ("guild_settings", "max_warnings_ban", "INTEGER DEFAULT 5"),
            ("guild_settings", "level_up_channel_id", "INTEGER DEFAULT NULL"),
            ("guild_settings", "xp_per_message", "INTEGER DEFAULT 15"),
            ("guild_settings", "xp_cooldown", "INTEGER DEFAULT 60"),
            ("security_audit_logs", "latency_ms", "INTEGER DEFAULT 0"),
            ("security_audit_logs", "correlation_status", "TEXT DEFAULT 'EXACT_MATCH'"),
            ("security_audit_logs", "severity", "TEXT DEFAULT 'HIGH'"),
            ("security_audit_logs", "punishment_applied", "TEXT DEFAULT 'NONE'"),
            ("security_audit_logs", "restored", "INTEGER DEFAULT 0"),
            ("logging_config", "voice_logs_channel_id", "INTEGER DEFAULT NULL"),
            ("logging_config", "member_logs_channel_id", "INTEGER DEFAULT NULL"),
            ("logging_config", "server_logs_channel_id", "INTEGER DEFAULT NULL"),
            ("logging_config", "category_id", "INTEGER DEFAULT NULL"),
            ("voice_config", "delete_when_empty", "INTEGER DEFAULT 1"),
            ("config_audit_logs", "actor_id", "INTEGER DEFAULT NULL"),
            ("config_audit_logs", "actor_tag", "TEXT DEFAULT NULL"),
            ("config_audit_logs", "module", "TEXT DEFAULT NULL"),
            ("config_audit_logs", "setting_key", "TEXT DEFAULT NULL"),
            ("config_audit_logs", "old_value", "TEXT DEFAULT NULL"),
            ("config_audit_logs", "new_value", "TEXT DEFAULT NULL"),
            ("security_audit_logs", "target_name", "TEXT DEFAULT NULL"),
            ("security_audit_logs", "action_type", "TEXT DEFAULT NULL"),
            ("economy_users", "last_weekly", "REAL DEFAULT 0"),
            ("economy_users", "last_monthly", "REAL DEFAULT 0"),
        ]
        for tbl, col, col_def in safeguards:
            try:
                await self.conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_def};")
                await self.conn.commit()
            except Exception:
                pass

        # Reconcile every table against the canonical schema so no code path
        # ever hits "no such column" against an older database file.
        await self._reconcile_columns(schema_sql)

        logger.info("Database schema initialized and verified in SQLite mode.")

    async def _reconcile_columns(self, schema_sql: str) -> None:
        """Add columns that exist in the canonical schema but not in the live DB."""
        if self.is_postgres:
            return
        expected: dict = {}
        try:
            model = sqlite3.connect(":memory:")
            try:
                model.executescript(schema_sql)
                tables = [
                    row[0]
                    for row in model.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                ]
                for table in tables:
                    expected[table] = list(model.execute(f'PRAGMA table_info("{table}")'))
            finally:
                model.close()
        except Exception as exc:
            logger.warning(f"Schema reconcile skipped: {exc}")
            return

        async with self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
            live_tables = {row[0] for row in await cursor.fetchall()}

        added = 0
        for table, columns in expected.items():
            if table not in live_tables:
                continue
            async with self.conn.execute(f'PRAGMA table_info("{table}")') as cursor:
                live_columns = {row[1] for row in await cursor.fetchall()}
            for _cid, name, ctype, _notnull, dflt, pk in columns:
                if name in live_columns or pk:
                    continue
                col_def = ctype or "TEXT"
                if dflt is not None:
                    col_def += f" DEFAULT {dflt}"
                try:
                    await self.conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {col_def}')
                    added += 1
                except Exception as exc:
                    logger.warning(f"Could not add column {table}.{name}: {exc}")
        await self.conn.commit()
        if added:
            logger.info(f"Schema reconciled: {added} missing column(s) added.")

    async def backup(self) -> Path:
        """Create a full timestamped snapshot backup of the database."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = DATABASE_BACKUP_DIR / f"backup_novexa_{timestamp}.db"
        DATABASE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        if not self.is_postgres:
            async with aiosqlite.connect(backup_path) as dest:
                await self.conn.backup(dest)
            logger.info(f"Database backup saved to {backup_path}")
        else:
            logger.info(f"Cloud PostgreSQL mode active. Snapshots are managed automatically via Neon.")
        return backup_path


# Global Database Singleton
db = DatabaseManager()
