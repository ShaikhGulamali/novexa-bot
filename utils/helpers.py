import re
import html
import discord
from typing import Optional, List
from datetime import datetime, timezone


def format_template(template: str, member: discord.Member) -> str:
    """Format template strings with member and server variables."""
    guild = member.guild if hasattr(member, "guild") else None
    created_str = member.created_at.strftime('%b %d, %Y') if hasattr(member, "created_at") and member.created_at else "Unknown"
    joined_str = member.joined_at.strftime('%b %d, %Y') if hasattr(member, "joined_at") and member.joined_at else "Today"
    icon_url = guild.icon.url if (guild and guild.icon) else ""

    replacements = {
        "{user}": member.mention,
        "{username}": member.name,
        "{user_id}": str(member.id),
        "{server}": guild.name if guild else "Server",
        "{server_id}": str(guild.id) if guild else "0",
        "{member_count}": str(guild.member_count) if guild else "1",
        "{avatar}": member.display_avatar.url,
        "{user_avatar}": member.display_avatar.url,
        "{server_icon}": icon_url,
        "{created_at}": created_str,
        "{joined_at}": joined_str,
    }
    result = template
    for key, val in replacements.items():
        result = result.replace(key, str(val))
    return result


def parse_time(duration_str: str) -> Optional[int]:
    """Parse time string like '10s', '15m', '2h', '7d' into integer seconds."""
    pattern = r"^(\d+)([smhdw])$"
    match = re.match(pattern, duration_str.lower().strip())
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 604800,
    }
    return value * multipliers[unit]


def format_duration(seconds: int) -> str:
    """Format seconds into readable string (e.g. 1h 30m)."""
    if seconds <= 0:
        return "0s"
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 and not parts:
        parts.append(f"{secs}s")
    return " ".join(parts) or "0s"


def generate_html_transcript(
    guild: discord.Guild,
    channel: discord.TextChannel,
    messages: List[discord.Message],
    ticket_author: Optional[discord.User] = None,
) -> str:
    """Generate a self-contained, responsive, dark-mode Discord-styled HTML transcript."""
    messages_html = []
    for msg in messages:
        # Avatar
        avatar_url = msg.author.display_avatar.url
        author_name = html.escape(msg.author.display_name)
        timestamp_str = msg.created_at.strftime("%b %d, %Y %I:%M %p UTC")
        content_html = html.escape(msg.clean_content).replace("\n", "<br>")

        attachments_html = ""
        for att in msg.attachments:
            if any(att.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):
                attachments_html += f'<div class="attachment"><img src="{att.url}" alt="{att.filename}" style="max-width: 400px; max-height: 300px; border-radius: 8px; margin-top: 6px;"/></div>'
            else:
                attachments_html += f'<div class="attachment"><a href="{att.url}" target="_blank" class="file-link">📎 {html.escape(att.filename)} ({round(att.size / 1024, 1)} KB)</a></div>'

        embeds_html = ""
        for emb in msg.embeds:
            title = f'<div class="embed-title">{html.escape(emb.title)}</div>' if emb.title else ""
            desc = f'<div class="embed-desc">{html.escape(emb.description)}</div>' if emb.description else ""
            embeds_html += f'<div class="embed-box">{title}{desc}</div>'

        msg_block = f"""
        <div class="message">
            <img class="avatar" src="{avatar_url}" alt="Avatar">
            <div class="message-body">
                <div class="message-header">
                    <span class="author-name">{author_name}</span>
                    <span class="timestamp">{timestamp_str}</span>
                </div>
                <div class="content">{content_html}</div>
                {attachments_html}
                {embeds_html}
            </div>
        </div>
        """
        messages_html.append(msg_block)

    full_messages_str = "\n".join(messages_html)
    generation_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    creator_tag = html.escape(str(ticket_author)) if ticket_author else "Unknown"

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ticket Transcript - {html.escape(channel.name)}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: #313338;
            color: #DBDEE1;
            font-family: 'gg sans', 'Noto Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-size: 14px;
            line-height: 1.4;
            padding: 24px;
        }}
        .header {{
            background-color: #2B2D31;
            border: 1px solid #1E1F22;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }}
        .header h1 {{
            color: #F2F3F5;
            font-size: 20px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-top: 12px;
            font-size: 13px;
            color: #949BA4;
        }}
        .meta-item b {{ color: #F2F3F5; }}
        .chat-container {{
            background-color: #2B2D31;
            border-radius: 8px;
            padding: 16px;
        }}
        .message {{
            display: flex;
            gap: 16px;
            padding: 8px 12px;
            margin-bottom: 4px;
            border-radius: 4px;
            transition: background 0.1s;
        }}
        .message:hover {{
            background-color: #2E3035;
        }}
        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            flex-shrink: 0;
            background-color: #1E1F22;
        }}
        .message-body {{
            flex-grow: 1;
        }}
        .message-header {{
            display: flex;
            align-items: baseline;
            gap: 8px;
            margin-bottom: 4px;
        }}
        .author-name {{
            font-weight: 600;
            color: #F2F3F5;
        }}
        .timestamp {{
            font-size: 11px;
            color: #949BA4;
        }}
        .content {{
            word-break: break-word;
            color: #DBDEE1;
        }}
        .file-link {{
            color: #00A8FC;
            text-decoration: none;
            display: inline-block;
            margin-top: 6px;
        }}
        .file-link:hover {{ text-decoration: underline; }}
        .embed-box {{
            background-color: #1E1F22;
            border-left: 4px solid #5865F2;
            border-radius: 4px;
            padding: 10px 14px;
            margin-top: 8px;
            max-width: 520px;
        }}
        .embed-title {{
            font-weight: 600;
            color: #F2F3F5;
            margin-bottom: 4px;
        }}
        .embed-desc {{
            color: #B5BAC1;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📁 Ticket Transcript: #{html.escape(channel.name)}</h1>
        <div class="meta-grid">
            <div class="meta-item">Server: <b>{html.escape(guild.name)}</b></div>
            <div class="meta-item">Author: <b>{creator_tag}</b></div>
            <div class="meta-item">Total Messages: <b>{len(messages)}</b></div>
            <div class="meta-item">Exported At: <b>{generation_time}</b></div>
        </div>
    </div>
    <div class="chat-container">
        {full_messages_str if messages else '<div style="color: #949BA4; text-align: center; padding: 20px;">No messages recorded in this ticket.</div>'}
    </div>
</body>
</html>
"""
    return html_doc


class PaginatorView(discord.ui.View):
    """Reusable interactive pagination view for embeds."""

    def __init__(self, pages: List[discord.Embed], author_id: int, timeout: float = 120.0):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.author_id = author_id
        self.current_page = 0
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.btn_first.disabled = self.current_page == 0
        self.btn_prev.disabled = self.current_page == 0
        self.btn_next.disabled = self.current_page == len(self.pages) - 1
        self.btn_last.disabled = self.current_page == len(self.pages) - 1
        self.btn_count.label = f"{self.current_page + 1}/{len(self.pages)}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot control this pagination view.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
    async def btn_first(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def btn_count(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
    async def btn_last(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = len(self.pages) - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

