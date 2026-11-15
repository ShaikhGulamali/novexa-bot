from dataclasses import dataclass
from typing import Optional, List
import datetime


@dataclass
class GuildSettings:
    guild_id: int
    prefix: str = "/"
    welcome_enabled: bool = True
    tickets_enabled: bool = True
    antinuke_enabled: bool = True
    music_enabled: bool = True
    leveling_enabled: bool = True
    economy_enabled: bool = True
    payments_enabled: bool = True
    logging_enabled: bool = True


@dataclass
class WelcomeConfig:
    guild_id: int
    channel_id: Optional[int] = None
    message_template: str = "Welcome {user} to **{server}**! You are member #{member_count}."
    embed_enabled: bool = True
    banner_enabled: bool = True
    background_url: str = ""
    leave_channel_id: Optional[int] = None
    leave_template: str = "{username} has left **{server}**."
    is_enabled: bool = True


@dataclass
class TicketPanel:
    panel_id: str
    guild_id: int
    channel_id: int
    message_id: Optional[int] = None
    title: str = "Support Ticket"
    description: str = "Click the button below to open a ticket."
    category_id: Optional[int] = None
    support_role_id: Optional[int] = None
    naming_scheme: str = "ticket-{number}"
    transcript_channel_id: Optional[int] = None


@dataclass
class Ticket:
    id: int
    guild_id: int
    channel_id: int
    ticket_number: int
    author_id: int
    claimed_by: Optional[int] = None
    status: str = "open"
    created_at: Optional[str] = None
    closed_at: Optional[str] = None
    reason: str = "General Support"


@dataclass
class AntiNukeConfig:
    guild_id: int
    enabled: bool = True
    punishment_type: str = "ban"  # 'ban', 'kick', 'quarantine'
    max_channel_deletions: int = 3
    max_channel_creations: int = 4
    max_role_deletions: int = 3
    max_role_creations: int = 4
    max_bans: int = 3
    max_kicks: int = 3
    max_webhook_creations: int = 2
    max_webhook_deletions: int = 2
    time_window: int = 30
    log_channel_id: Optional[int] = None


@dataclass
class VerificationConfig:
    guild_id: int
    enabled: bool = False
    channel_id: Optional[int] = None
    verified_role_id: Optional[int] = None
    unverified_role_id: Optional[int] = None
    captcha_enabled: bool = False
    log_channel_id: Optional[int] = None


@dataclass
class UserProfile:
    guild_id: int
    user_id: int
    bio: str = "Hello! I am using Novexa."
    custom_color: str = "#5865F2"
    custom_avatar_url: str = ""
    custom_banner_url: str = ""
    background_url: str = ""


@dataclass
class LevelingData:
    guild_id: int
    user_id: int
    xp: int = 0
    level: int = 0
    last_xp_time: float = 0.0


@dataclass
class EconomyData:
    guild_id: int
    user_id: int
    wallet: int = 100
    bank: int = 500
    last_daily: float = 0.0


@dataclass
class PaymentConfig:
    guild_id: int
    upi_id: str = ""
    qr_image_url: str = ""
    instructions: str = "Scan QR or send UPI to the address above. Submit your reference ID & screenshot for verification."
    staff_role_id: Optional[int] = None
    log_channel_id: Optional[int] = None


@dataclass
class PaymentRecord:
    id: int
    guild_id: int
    user_id: int
    amount: str
    reference_id: str
    screenshot_url: str
    status: str = "pending"
    notes: str = ""
    reviewed_by: Optional[int] = None
    created_at: Optional[str] = None
    reviewed_at: Optional[str] = None


@dataclass
class AIChannelConfig:
    channel_id: int
    guild_id: int
    mode: str = "coding_assistant"
    auto_thread: bool = False
    added_by: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class AIGuildConfig:
    guild_id: int
    provider: str = "gemini"
    model: str = "gemini-1.5-flash"
    language: str = "English"
    response_style: str = "detailed"
    user_limit_hourly: int = 30
    cooldown_seconds: int = 3
    system_prompt: str = ""
    created_at: Optional[str] = None


@dataclass
class EconomyUser:
    guild_id: int
    user_id: int
    wallet: int = 500
    bank: int = 1000
    gems: int = 10
    xp: int = 0
    level: int = 1
    reputation: int = 0
    daily_streak: int = 0
    last_daily: float = 0.0
    last_weekly: float = 0.0
    last_monthly: float = 0.0
    last_work: float = 0.0
    last_crime: float = 0.0
    last_slut: float = 0.0
    last_rep: float = 0.0
    last_hunt: float = 0.0
    last_battle: float = 0.0
    total_earned: int = 0
    total_spent: int = 0
    commands_used: int = 0
    hunts_count: int = 0
    battles_won: int = 0
    battles_lost: int = 0
    gambles_won: int = 0
    gambles_lost: int = 0
    is_banned: int = 0
    created_at: Optional[str] = None


@dataclass
class EconomyItem:
    item_id: str
    name: str
    description: str
    category: str
    rarity: str
    buy_price: int = 0
    sell_price: int = 0
    gem_price: int = 0
    attack_bonus: int = 0
    defense_bonus: int = 0
    hunt_luck: int = 0
    consumable: int = 0
    max_stack: int = 999
    icon: str = "📦"
    slot: Optional[str] = None
    special_ability: str = ""


@dataclass
class EconomyAnimal:
    animal_id: str
    name: str
    emoji: str
    rarity: str
    base_value: int
    base_xp: int
    catch_weight: int
    ability: str = ""
    description: str = ""


@dataclass
class EconomyPet:
    pet_type: str
    name: str
    emoji: str
    rarity: str
    bonus_type: str
    bonus_value: float
    description: str


@dataclass
class PublicAISettings:
    guild_id: int
    is_enabled: bool = True
    provider: str = "gemini"
    model: str = "gemini-1.5-flash"
    cooldown_seconds: int = 3
    hourly_limit: int = 50
    system_prompt: str = ""
    created_at: Optional[str] = None



