import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Bot Identity
BOT_NAME = "NOVEXA"
BOT_VERSION = "2.0.0"
BOT_DESCRIPTION = "The Next-Generation All-in-One Multi-Guild Discord Bot"

# Secrets & Core Settings
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
BOT_PREFIX = os.getenv("BOT_PREFIX", "/")
OWNER_IDS = [int(oid.strip()) for oid in os.getenv("OWNER_IDS", "0").split(",") if oid.strip().isdigit()]

# AI Engine API Keys & Configurations
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER", "gemini")
DEFAULT_AI_MODEL = os.getenv("DEFAULT_AI_MODEL", "gemini-1.5-flash")
AI_MAX_CONTEXT_MESSAGES = int(os.getenv("AI_MAX_CONTEXT_MESSAGES", "8"))
AI_MEMORY_RETENTION_MINUTES = int(os.getenv("AI_MEMORY_RETENTION_MINUTES", "60"))
AI_DEFAULT_USER_LIMIT_HOURLY = int(os.getenv("AI_DEFAULT_USER_LIMIT_HOURLY", "30"))
AI_COOLDOWN_SECONDS = int(os.getenv("AI_COOLDOWN_SECONDS", "3"))
AI_MAX_ATTACHMENT_SIZE_MB = int(os.getenv("AI_MAX_ATTACHMENT_SIZE_MB", "8"))

# Image Generation (Wallpaper Studio)
POLLINATIONS_TOKEN = os.getenv("POLLINATIONS_TOKEN", "")

# Database Settings
DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "database" / "gulamali_bot.db")))
DATABASE_BACKUP_DIR = BASE_DIR / "logs" / "backups"

# Assets Directory
ASSETS_DIR = BASE_DIR / "assets"
WELCOME_ASSETS_DIR = ASSETS_DIR / "welcome"

# Visual Theme & Colors (Discord 24-bit Hex Colors)
COLOR_PRIMARY = 0x5865F2    # Blurple
COLOR_SUCCESS = 0x57F287    # Emerald Green
COLOR_ERROR = 0xED4245      # Crimson Red
COLOR_WARNING = 0xFEE75C    # Warm Gold / Yellow
COLOR_INFO = 0x5865F2       # Sky Info
COLOR_PREMIUM = 0xEB459E    # Fuchsia / Magenta
COLOR_DARK = 0x2B2D31       # Discord Dark Theme Canvas

# Dashboard & Discord OAuth2 Web Configuration
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8080/api/auth/callback")
SESSION_SECRET = os.getenv("SESSION_SECRET", "novexa_super_secret_session_key_2026")
DASHBOARD_PORT = int(os.getenv("PORT") or os.getenv("DASHBOARD_PORT", "8080"))
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")

# Ensure base dir is at top of PATH so ffmpeg is always found globally
os.environ["PATH"] = str(BASE_DIR) + os.pathsep + os.environ.get("PATH", "")

# FFmpeg Executable Resolution
LOCAL_FFMPEG = BASE_DIR / "ffmpeg.exe"
if os.name == "nt" and LOCAL_FFMPEG.exists():
    FFMPEG_EXECUTABLE = str(LOCAL_FFMPEG)
elif shutil.which("ffmpeg"):
    FFMPEG_EXECUTABLE = "ffmpeg"
else:
    try:
        import imageio_ffmpeg
        FFMPEG_EXECUTABLE = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG_EXECUTABLE = "ffmpeg"

DEFAULT_VOLUME = 1.00       # 100% default volume
MAX_QUEUE_SIZE = 250        # Max songs in queue
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -analyzeduration 0 -probesize 32768 -user_agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"',
    'options': '-vn',
}

# Ensure core directories exist
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
WELCOME_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)

