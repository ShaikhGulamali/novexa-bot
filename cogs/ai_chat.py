"""NOVEXA - AI Chat Engine.

Features:
- Per-channel AI chat with no mention required: once a channel is set up, every
  human message in it is answered by NOVEXA AI.
- Persistent per-channel conversation memory plus long-term server facts, so the
  bot keeps context about the server across restarts.
- Multi-provider backend (Groq / Gemini / OpenAI / OpenRouter / DeepSeek) with
  automatic fallback when the primary provider fails.
- Identity is locked to NOVEXA: the model is instructed never to present itself
  as ChatGPT, OpenAI, Groq, Gemini or any other product.
- Commands:
    /ai setup <channel>        enable AI in a channel
    /ai remove <channel>       disable AI in a channel
    /ai list                   show configured channels
    /ai model <provider> <model>
    /ai persona <text>         custom personality overlay
    /ai remember <fact>        store a long-term server fact
    /ai forget                 clear stored facts
    /ai reset [channel]        clear conversation memory
    /ai status                 show configuration and memory counters
    /ai ask <question>         one-off question without setup
"""

import asyncio
import datetime
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from config import (
    AI_API_KEY,
    AI_BASE_URL,
    AI_COOLDOWN_SECONDS,
    AI_DEFAULT_USER_LIMIT_HOURLY,
    AI_MAX_CONTEXT_MESSAGES,
    BOT_NAME,
    BOT_PREFIX,
    DEEPSEEK_API_KEY,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_PROVIDER,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
)
from database.database import db
from utils.embeds import error_embed, info_embed, success_embed

logger = logging.getLogger("novexa.ai_chat")

OPENAI_STYLE_ENDPOINTS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", GROQ_API_KEY),
    "openai": (AI_BASE_URL or "https://api.openai.com/v1/chat/completions", OPENAI_API_KEY or AI_API_KEY),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", OPENROUTER_API_KEY),
    "deepseek": ("https://api.deepseek.com/v1/chat/completions", DEEPSEEK_API_KEY),
}

FALLBACK_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "openai": "gpt-4o-mini",
    "openrouter": "openai/gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "gemini": "gemini-2.0-flash",
}

IDENTITY_RULES = (
    "You are NOVEXA AI, the built-in AI assistant of the Discord server \"{server}\". "
    "You ARE NOVEXA. Never say you are ChatGPT, GPT, OpenAI, Groq, Gemini, DeepSeek, Claude, "
    "Llama or any other product or company. Never mention the underlying model or provider. "
    "If asked who you are, answer that you are NOVEXA AI, this server's assistant. "
    "Answer every question fully and directly: facts, maths, coding, troubleshooting, advice, "
    "creative writing — whatever is asked, give a complete, correct, useful answer with the steps "
    "or code when steps or code are needed. Use Discord markdown: short paragraphs, bullet lists, "
    "and fenced code blocks with a language tag. Never reply with a refusal template, never add "
    "unrequested safety disclaimers, and never invent limits you do not have. "
    "Detect the language the user writes in (English, Hindi, Hinglish, or any other) and reply in "
    "that same language and register."
)


class AIChat(commands.Cog):
    """NOVEXA AI — per-channel assistant with persistent server memory."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._channels: Dict[int, Dict[str, Any]] = {}
        self._cooldowns: Dict[int, float] = {}
        self._context_cache: Dict[int, Tuple[float, str]] = {}

    async def cog_load(self):
        try:
            rows = await db.fetchall(
                "SELECT channel_id, guild_id, added_by FROM ai_channels"
            )
            for row in rows:
                self._channels[row["channel_id"]] = {
                    "guild_id": row["guild_id"],
                    "added_by": row["added_by"],
                }
            logger.info(f"AI chat active in {len(self._channels)} channel(s).")
        except Exception as exc:
            logger.error(f"Could not load AI channels: {exc}", exc_info=True)

    # ==================== PROVIDERS ====================

    async def _openai_style(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, int]:
        endpoint, key = OPENAI_STYLE_ENDPOINTS[provider]
        if provider == "openai" and not endpoint.endswith("/chat/completions"):
            endpoint = endpoint.rstrip("/") + "/chat/completions"

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NovexaAI/1.0",
        }
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://novexa.local"
            headers["X-Title"] = "NOVEXA AI"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, headers=headers, json=payload) as resp:
                body = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}: {body[:300]}")
                data = json.loads(body)

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"empty completion: {body[:200]}")
        text = (choices[0].get("message") or {}).get("content") or ""
        tokens = int((data.get("usage") or {}).get("total_tokens") or 0)
        if not text.strip():
            raise RuntimeError("empty text in completion")
        return text.strip(), tokens

    async def _gemini(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, int]:
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        contents = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in messages
            if m["role"] != "system"
        ]
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            f"?key={GEMINI_API_KEY}"
        )
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NovexaAI/1.0"}
        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                body = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}: {body[:300]}")
                data = json.loads(body)

        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"no candidates: {body[:200]}")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts)
        tokens = int((data.get("usageMetadata") or {}).get("totalTokenCount") or 0)
        if not text.strip():
            raise RuntimeError("empty text in completion")
        return text.strip(), tokens

    async def _complete(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, int, str]:
        order = [provider] + [p for p in ("groq", "gemini", "openai", "openrouter", "deepseek") if p != provider]
        last_error = ""

        for name in order:
            if name == "gemini":
                if not GEMINI_API_KEY:
                    continue
                chosen = model if name == provider else FALLBACK_MODELS["gemini"]
                try:
                    text, tokens = await self._gemini(chosen, messages, temperature, max_tokens)
                    return text, tokens, name
                except Exception as exc:
                    last_error = f"{name}: {exc}"
                    logger.warning(f"AI provider {name} failed: {exc}")
                continue

            if name not in OPENAI_STYLE_ENDPOINTS or not OPENAI_STYLE_ENDPOINTS[name][1]:
                continue
            chosen = model if name == provider else FALLBACK_MODELS[name]
            try:
                text, tokens = await self._openai_style(name, chosen, messages, temperature, max_tokens)
                return text, tokens, name
            except Exception as exc:
                last_error = f"{name}: {exc}"
                logger.warning(f"AI provider {name} failed: {exc}")

        raise RuntimeError(last_error or "no AI provider key configured")

    # ==================== CONTEXT ====================

    async def _guild_context(self, guild: discord.Guild) -> str:
        cached = self._context_cache.get(guild.id)
        if cached and time.time() - cached[0] < 600:
            return cached[1]

        humans = sum(1 for m in guild.members if not m.bot) if guild.members else guild.member_count
        bots = sum(1 for m in guild.members if m.bot)
        top_roles = [r.name for r in list(reversed(guild.roles))[:12] if not r.is_default()]
        categories = [c.name for c in guild.categories][:12]
        owner = guild.owner.display_name if guild.owner else f"<@{guild.owner_id}>"

        facts_rows = await db.fetchall(
            "SELECT fact FROM ai_facts WHERE guild_id = ? ORDER BY id DESC LIMIT 40",
            (guild.id,),
        )
        facts = [row["fact"] for row in facts_rows]

        lines = [
            f"Server name: {guild.name}",
            f"Server ID: {guild.id}",
            f"Owner: {owner}",
            f"Created: {guild.created_at.strftime('%d %b %Y')}",
            f"Members: {humans} humans, {bots} bots",
            f"Boost level: {guild.premium_tier} ({guild.premium_subscription_count} boosts)",
            f"Verification level: {guild.verification_level.name}",
            f"Text channels: {len(guild.text_channels)} | Voice: {len(guild.voice_channels)} | Categories: {len(guild.categories)}",
            f"Roles: {', '.join(top_roles) or 'none'}",
            f"Categories: {', '.join(categories) or 'none'}",
        ]
        if facts:
            lines.append("Stored facts about this server:")
            lines.extend(f"- {fact}" for fact in facts)

        context = "\n".join(lines)
        self._context_cache[guild.id] = (time.time(), context)
        return context

    async def _history(self, guild: discord.Guild, channel_id: int) -> List[Dict[str, str]]:
        rows = await db.fetchall(
            "SELECT user_id, role, content FROM ai_memory WHERE channel_id = ? ORDER BY id DESC LIMIT ?",
            (channel_id, AI_MAX_CONTEXT_MESSAGES * 2),
        )
        messages: List[Dict[str, str]] = []
        for row in reversed(rows):
            content = row["content"]
            if row["role"] == "user":
                member = guild.get_member(row["user_id"]) if guild else None
                name = member.display_name if member else "user"
                content = f"{name}: {content}"
            messages.append({"role": row["role"], "content": content})
        return messages

    async def _remember(self, guild_id: int, channel_id: int, user_id: int, role: str, content: str):
        await db.execute(
            "INSERT INTO ai_memory (guild_id, channel_id, user_id, role, content) VALUES (?, ?, ?, ?, ?)",
            (guild_id, channel_id, user_id, role, content[:8000]),
        )
        row = await db.fetchone(
            "SELECT COUNT(*) AS c FROM ai_memory WHERE channel_id = ?", (channel_id,)
        )
        if row and row["c"] > 400:
            await db.execute(
                "DELETE FROM ai_memory WHERE channel_id = ? AND id NOT IN "
                "(SELECT id FROM ai_memory WHERE channel_id = ? ORDER BY id DESC LIMIT 200)",
                (channel_id, channel_id),
            )

    async def _ai_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT * FROM ai_config WHERE guild_id = ?", (guild_id,))
        if row:
            return dict(row)
        await db.execute(
            "INSERT INTO ai_config (guild_id, provider, model) VALUES (?, ?, ?)",
            (guild_id, DEFAULT_AI_PROVIDER, DEFAULT_AI_MODEL),
        )
        return {
            "guild_id": guild_id,
            "provider": DEFAULT_AI_PROVIDER,
            "model": DEFAULT_AI_MODEL,
            "temperature": 0.7,
            "max_tokens": 2048,
            "memory_enabled": 1,
            "is_enabled": 1,
            "persona": "",
        }

    def _system_prompt(self, guild: discord.Guild, channel: discord.abc.GuildChannel, context: str, persona: str) -> str:
        prompt = IDENTITY_RULES.format(server=guild.name)
        prompt += f"\n\nCurrent channel: #{getattr(channel, 'name', 'unknown')}"
        prompt += f"\nCurrent date: {datetime.datetime.now().strftime('%d %B %Y, %H:%M')} (server time)"
        prompt += f"\n\n{context}"
        if persona:
            prompt += f"\n\nAdditional instructions from the server admins:\n{persona}"
        return prompt

    def _cooldown_hit(self, user_id: int) -> bool:
        now = time.time()
        if now - self._cooldowns.get(user_id, 0.0) < AI_COOLDOWN_SECONDS:
            return True
        self._cooldowns[user_id] = now
        return False

    async def _hourly_limit_hit(self, guild_id: int, user_id: int) -> bool:
        cutoff = (
            datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            - datetime.timedelta(hours=1)
        ).strftime("%Y-%m-%d %H:%M:%S")
        row = await db.fetchone(
            "SELECT COUNT(*) AS c FROM ai_usage WHERE guild_id = ? AND user_id = ? AND timestamp >= ?",
            (guild_id, user_id, cutoff),
        )
        return bool(row and row["c"] >= AI_DEFAULT_USER_LIMIT_HOURLY)

    @staticmethod
    def _chunks(text: str, size: int = 1900) -> List[str]:
        chunks: List[str] = []
        remaining = text
        while len(remaining) > size:
            split = remaining.rfind("\n", 0, size)
            if split < size // 2:
                split = size
            chunks.append(remaining[:split])
            remaining = remaining[split:].lstrip("\n")
        if remaining:
            chunks.append(remaining)
        return chunks or [""]

    async def _produce(self, guild: discord.Guild, channel: discord.abc.GuildChannel, user: discord.abc.User,
                       prompt: str) -> Tuple[str, int, str, int]:
        cfg = await self._ai_config(guild.id)
        context = await self._guild_context(guild)
        history = await self._history(guild, channel.id) if cfg.get("memory_enabled", 1) else []

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self._system_prompt(guild, channel, context, cfg.get("persona") or "")}
        ]
        messages.extend(history)
        messages.append({"role": "user", "content": f"{user.display_name}: {prompt}"})

        started = time.perf_counter()
        text, tokens, used_provider = await self._complete(
            cfg.get("provider") or DEFAULT_AI_PROVIDER,
            cfg.get("model") or DEFAULT_AI_MODEL,
            messages,
            float(cfg.get("temperature") or 0.7),
            int(cfg.get("max_tokens") or 2048),
        )
        latency = int((time.perf_counter() - started) * 1000)

        await self._remember(guild.id, channel.id, user.id, "user", prompt)
        await self._remember(guild.id, channel.id, self.bot.user.id, "assistant", text)
        await db.execute(
            "INSERT INTO ai_usage (guild_id, user_id, model_used, tokens_used) VALUES (?, ?, ?, ?)",
            (guild.id, user.id, used_provider, tokens),
        )
        await db.execute(
            "INSERT INTO ai_logs (guild_id, user_id, channel_id, prompt, response_preview, tokens, latency_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (guild.id, user.id, channel.id, prompt[:1000], text[:300], tokens, latency),
        )
        return text, tokens, used_provider, latency

    # ==================== CHAT LISTENER ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        if not message.content or not message.content.strip():
            return
        if message.channel.id not in self._channels:
            return
        first_word = message.content.split(maxsplit=1)[0]
        if first_word.startswith(BOT_PREFIX) and self.bot.get_command(first_word[len(BOT_PREFIX):]):
            return

        cfg = await self._ai_config(message.guild.id)
        if not cfg.get("is_enabled", 1):
            return
        if self._cooldown_hit(message.author.id):
            return
        if await self._hourly_limit_hit(message.guild.id, message.author.id):
            return

        try:
            async with message.channel.typing():
                text, _tokens, _provider, _latency = await self._produce(
                    message.guild, message.channel, message.author, message.content.strip()[:4000]
                )
        except Exception as exc:
            logger.error(f"AI reply failed: {exc}", exc_info=True)
            try:
                await message.reply(
                    embed=error_embed("AI busy", "Model se jawab nahi aaya. Thodi der baad try karo."),
                    mention_author=False,
                    delete_after=12,
                )
            except discord.HTTPException:
                pass
            return

        chunks = self._chunks(text)
        try:
            first = await message.reply(
                chunks[0], mention_author=False, allowed_mentions=discord.AllowedMentions.none()
            )
            for chunk in chunks[1:]:
                await first.reply(
                    chunk, mention_author=False, allowed_mentions=discord.AllowedMentions.none()
                )
        except discord.HTTPException as exc:
            logger.warning(f"Could not deliver AI reply: {exc}")

    # ==================== COMMAND GROUP ====================

    ai_group = app_commands.Group(name="ai", description="NOVEXA AI chat assistant")

    @ai_group.command(name="setup", description="Enable NOVEXA AI in a channel (no mention needed)")
    @app_commands.describe(channel="Channel where AI should answer every message")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ai_setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if interaction.guild is None:
            return await interaction.response.send_message(
                embed=error_embed("Server only", "Ye command server me chalao."), ephemeral=True
            )

        await db.execute(
            "INSERT INTO ai_channels (channel_id, guild_id, added_by) VALUES (?, ?, ?) "
            "ON CONFLICT(channel_id) DO UPDATE SET guild_id = excluded.guild_id, added_by = excluded.added_by",
            (channel.id, interaction.guild_id, interaction.user.id),
        )
        await self._ai_config(interaction.guild_id)
        self._channels[channel.id] = {"guild_id": interaction.guild_id, "added_by": interaction.user.id}

        await interaction.response.send_message(
            embed=success_embed(
                "AI channel ready",
                f"{channel.mention} me ab har message ka jawab NOVEXA AI dega — mention ki zarurat nahi.\n"
                "Kisi aur channel me: `/ai setup #channel`. Band karna ho: `/ai remove`.",
            )
        )

    @ai_group.command(name="remove", description="Disable NOVEXA AI in a channel")
    @app_commands.describe(channel="Channel to disable")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ai_remove(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await db.execute("DELETE FROM ai_channels WHERE channel_id = ?", (channel.id,))
        self._channels.pop(channel.id, None)
        await interaction.response.send_message(
            embed=success_embed("AI channel removed", f"{channel.mention} me AI ab jawab nahi dega.")
        )

    @ai_group.command(name="list", description="Show channels where AI is active")
    async def ai_list(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message(
                embed=error_embed("Server only", "Ye command server me chalao."), ephemeral=True
            )
        rows = await db.fetchall(
            "SELECT channel_id FROM ai_channels WHERE guild_id = ?", (interaction.guild_id,)
        )
        if not rows:
            return await interaction.response.send_message(
                embed=info_embed("No AI channels", "Abhi koi channel set nahi hai. `/ai setup #channel` chalao."),
                ephemeral=True,
            )
        channels = " ".join(f"<#{row['channel_id']}>" for row in rows)
        cfg = await self._ai_config(interaction.guild_id)
        await interaction.response.send_message(
            embed=info_embed(
                "AI channels",
                f"{channels}\n\nProvider: `{cfg.get('provider')}`\nModel: `{cfg.get('model')}`\n"
                f"Persona: {'set' if cfg.get('persona') else 'default'}",
            ),
            ephemeral=True,
        )

    @ai_group.command(name="model", description="Choose the AI provider and model")
    @app_commands.describe(provider="Backend to use", model="Model id (leave blank for provider default)")
    @app_commands.choices(
        provider=[
            app_commands.Choice(name="Groq (fast, free)", value="groq"),
            app_commands.Choice(name="Google Gemini", value="gemini"),
            app_commands.Choice(name="OpenAI", value="openai"),
            app_commands.Choice(name="OpenRouter", value="openrouter"),
            app_commands.Choice(name="DeepSeek", value="deepseek"),
        ]
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ai_model(
        self,
        interaction: discord.Interaction,
        provider: str,
        model: Optional[str] = None,
    ):
        if provider not in FALLBACK_MODELS:
            return await interaction.response.send_message(
                embed=error_embed(
                    "Unknown provider",
                    f"Chuno: {', '.join(FALLBACK_MODELS)}",
                ),
                ephemeral=True,
            )
        await self._ai_config(interaction.guild_id)
        chosen_model = (model or FALLBACK_MODELS[provider]).strip()
        await db.execute(
            "UPDATE ai_config SET provider = ?, model = ? WHERE guild_id = ?",
            (provider, chosen_model, interaction.guild_id),
        )
        await interaction.response.send_message(
            embed=success_embed("AI model updated", f"Provider: `{provider}`\nModel: `{chosen_model}`")
        )

    @ai_group.command(name="persona", description="Give the AI a custom personality or extra rules")
    @app_commands.describe(text="Extra instructions; use 'clear' to reset")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ai_persona(self, interaction: discord.Interaction, text: str):
        persona = "" if text.strip().lower() in {"clear", "reset", "none"} else text.strip()[:1500]
        await self._ai_config(interaction.guild_id)
        await db.execute(
            "UPDATE ai_config SET persona = ? WHERE guild_id = ?", (persona, interaction.guild_id)
        )
        await interaction.response.send_message(
            embed=success_embed(
                "Persona updated",
                "Persona hata diya." if not persona else f"Ab AI iske hisaab se chalega:\n>>> {persona}",
            )
        )

    @ai_group.command(name="remember", description="Teach the AI a permanent fact about this server")
    @app_commands.describe(fact="Example: Owner ka naam Ali hai, server coding community hai")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ai_remember(self, interaction: discord.Interaction, fact: str):
        clean = fact.strip()[:500]
        if not clean:
            return await interaction.response.send_message(
                embed=error_embed("Empty fact", "Kuch likho pehle."), ephemeral=True
            )
        await db.execute(
            "INSERT INTO ai_facts (guild_id, fact, added_by) VALUES (?, ?, ?)",
            (interaction.guild_id, clean, interaction.user.id),
        )
        self._context_cache.pop(interaction.guild_id, None)
        await interaction.response.send_message(
            embed=success_embed("Yaad rakh liya", f"Har jawab me ye fact use hoga:\n>>> {clean}")
        )

    @ai_group.command(name="forget", description="Delete every stored server fact")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ai_forget(self, interaction: discord.Interaction):
        await db.execute("DELETE FROM ai_facts WHERE guild_id = ?", (interaction.guild_id,))
        self._context_cache.pop(interaction.guild_id, None)
        await interaction.response.send_message(
            embed=success_embed("Facts cleared", "Saare stored facts hata diye.")
        )

    @ai_group.command(name="reset", description="Clear conversation memory (channel or whole server)")
    @app_commands.describe(channel="Only this channel; leave blank to clear the whole server")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ai_reset(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        if channel:
            await db.execute(
                "DELETE FROM ai_memory WHERE guild_id = ? AND channel_id = ?",
                (interaction.guild_id, channel.id),
            )
            scope = channel.mention
        else:
            await db.execute("DELETE FROM ai_memory WHERE guild_id = ?", (interaction.guild_id,))
            scope = "poora server"
        await interaction.response.send_message(
            embed=success_embed("Memory cleared", f"{scope} ka conversation history saaf ho gaya.")
        )

    @ai_group.command(name="ask", description="Ask NOVEXA AI one question without configuring a channel")
    @app_commands.describe(question="Your question")
    async def ai_ask(self, interaction: discord.Interaction, question: str):
        if interaction.guild is None:
            return await interaction.response.send_message(
                embed=error_embed("Server only", "Ye command server me chalao."), ephemeral=True
            )
        if await self._hourly_limit_hit(interaction.guild_id, interaction.user.id):
            return await interaction.response.send_message(
                embed=error_embed("Hourly limit", "Aapka hourly AI limit khatam ho gaya hai."), ephemeral=True
            )
        await interaction.response.defer(thinking=True)
        try:
            text, _tokens, _provider, _latency = await self._produce(
                interaction.guild, interaction.channel, interaction.user, question.strip()[:4000]
            )
        except Exception as exc:
            logger.error(f"/ai ask failed: {exc}", exc_info=True)
            return await interaction.followup.send(
                embed=error_embed("AI busy", "Model se jawab nahi aaya. Thodi der baad try karo.")
            )
        await interaction.followup.send(self._chunks(text)[0])

    @ai_group.command(name="status", description="Show AI configuration, memory and usage")
    async def ai_status(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message(
                embed=error_embed("Server only", "Ye command server me chalao."), ephemeral=True
            )
        cfg = await self._ai_config(interaction.guild_id)
        mem = await db.fetchone(
            "SELECT COUNT(*) AS c FROM ai_memory WHERE guild_id = ?", (interaction.guild_id,)
        )
        facts = await db.fetchone(
            "SELECT COUNT(*) AS c FROM ai_facts WHERE guild_id = ?", (interaction.guild_id,)
        )
        used = await db.fetchone(
            "SELECT COUNT(*) AS c, COALESCE(SUM(tokens_used), 0) AS t FROM ai_usage WHERE guild_id = ?",
            (interaction.guild_id,),
        )
        channels = [cid for cid, meta in self._channels.items() if meta["guild_id"] == interaction.guild_id]
        text = [
            f"Provider: `{cfg.get('provider')}`",
            f"Model: `{cfg.get('model')}`",
            f"Enabled: `{'yes' if cfg.get('is_enabled', 1) else 'no'}`",
            f"Memory: `{mem['c'] if mem else 0}` messages",
            f"Facts: `{facts['c'] if facts else 0}`",
            f"Requests: `{used['c'] if used else 0}` | tokens: `{used['t'] if used else 0}`",
            f"Channels: {', '.join(f'<#{c}>' for c in channels) or 'none'}",
        ]
        await interaction.response.send_message(embed=info_embed("NOVEXA AI status", "\n".join(text)), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))
