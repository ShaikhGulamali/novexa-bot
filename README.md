# 👑 NOVEXA

> **The Next-Generation, Enterprise-Grade All-in-One Multi-Guild Discord Bot.**
> Built with **Python 3.12+**, **discord.py 2.x**, **aiosqlite**, **Pillow**, and **yt-dlp**.

---

## 🌟 Overview & Highlights

**NOVEXA** is a complete, production-ready Discord solution featuring multi-guild support, persistent database state management, high-performance visual image generation, advanced security suites, and intuitive interactive controls (buttons, modals, and dropdowns).

### 🚀 Key Modules
1. **Studio Welcome Suite (20 Templates)**: 20 professional visual themes (Minimal Welcome, Premium Blue, Cyberpunk, Neon Gaming, Purple Luxury, Gold VIP, Anime, Glassmorphism, Space, Futuristic AI, NOVEXA Exclusive, etc.) with real-time PIL dynamic banner rendering, circular glowing avatars, join counters, 10 template variables (`{user}`, `{username}`, `{user_id}`, `{server}`, `{server_id}`, `{member_count}`, `{avatar}`, `{server_icon}`, `{created_at}`, `{joined_at}`), auto-role assignment, and custom DM messages.
2. **Advanced Ticket System**: Persistent buttons (`Create`, `Close`, `Claim`, `Reopen`, `Delete`, `Add/Remove Member`, `Rename`), custom categories, staff assignment alerts, and **responsive dark-mode HTML transcript generator**.
3. **Anti-Nuke Raid Defense**: High-speed sliding-window rate-limiter guarding against mass channel/role deletion & creation, mass kicks/bans, unauthorized bot additions, and privilege escalation. Features 3 operating modes (`LOW`, `MEDIUM`, `HIGH`), immediate emergency lockdown (`/antinuke lockdown`), and automatic recovery.
4. **Intelligent Anti-Spam & Phishing Defense**: Real-time content inspection guarding against mass mention storms, message flooding bursts, Discord invite link spam, phishing/scam domains, and excessive emoji floods. Automatic progressive timeout punishments with granular exemptions.
5. **Least-Privilege Whitelist & Bot Gatekeeper**: Server-wide whitelist with strict least-privilege enforcement. Separated Bot Addition Protection prevents unauthorized bots from joining—any unapproved bot is instantly kicked and server owners are alerted.
6. **Master Security Dashboard & Dedicated Logs**: Central command suite (`/security dashboard`, `/security status`, `/security mode`, `/security lockdown`) and automatic 1-click provisioning of the dedicated `NOVEXA SECURITY LOGS` channel (`/security setup-logs`).
7. **Disaster Recovery & Non-Destructive Backups**: Complete server architecture snapshot system (`/backup create`, `/backup restore`, `/backup list`, `/backup delete`) capturing roles, channel hierarchy, permissions, and configurations for instant recovery.
8. **Connected Official Website & Web Dashboard**: Production-grade web interface powered by FastAPI running directly inside the bot's event loop (`http://localhost:8080`). Includes 10 responsive public pages (Home, Features, Commands, Premium, Status, Docs, Support, FAQ, Privacy, Terms), Discord OAuth2 login, User Dashboard, Server Dashboard with an interactive 20-template visual live previewer, and bi-directional REST API synchronization.
9. **Music Streaming**: High-fidelity audio player powered by `yt-dlp` and `FFmpeg` with interactive player controls and 24/7 VC mode.
10. **Custom Profiles & XP**: Dynamic 850x480 graphic profile cards rendering level, rank, customizable bio, custom accent colors, custom banners, custom avatars, and virtual coin balances.
11. **Payment QR & Staff Verification**: Built-in UPI/QR display (`/pay`), buyer submission with transaction reference and screenshot proof (`/payment submit`), and interactive staff review buttons (`Approve`/`Reject`).
12. **Role Hierarchy & Self-Roles**: Safe role management enforcing Discord hierarchy rules, dynamic self-role button panels, and automatic join roles (autoroles).
13. **Verification Gatekeeper**: Anti-bot distorted CAPTCHA generator (`/verify panel`), unverified isolation, 1-click or CAPTCHA verification, and automated role swapping.
14. **Moderation Suite**: Full disciplinary commands (`/ban`, `/unban`, `/kick`, `/timeout`, `/untimeout`, `/warn`, `/warnings`, `/clear`, `/slowmode`, `/lock`, `/unlock`, `/hide`, `/unhide`, `/nickname`) with confirmation dialogs and audit logging.
15. **OwO-Style Virtual Economy & RPG**: Complete economy featuring Gulamali / Novexa Coins, banking, daily streaks, gambling mini-games (`/coinflip`, `/dice`, `/slots`, `/gamble`, `/work`, `/crime`, `/slut`), hunting 49 animal species, PvP arena battles, equipment shop, pet companions, and mystery crates.
16. **Server Utilities & Server Templates**: Starboard, interactive giveaways, polls, sticky notes, and 50 complete Discord server architecture templates (`/server-setup`).
17. **Advanced AI Coding & Public AI**: Zero-command dual AI engines for automatic developer support and public Q&A with vision and OCR analysis.

---

## 📁 Project File Structure

```
NOVEXA/
│
├── main.py                     # Bot core entrypoint & lifecycle manager
├── config.py                   # Central settings, colors, directories & env loader
├── requirements.txt            # Production Python dependencies
├── .env.example                # Template for sensitive environment variables
├── README.md                   # Complete installation, setup & deployment guide
│
├── cogs/                       # Modular Slash Command extensions
│   ├── welcome.py              # Welcome & Leave announcements + banner renderer
│   ├── tickets.py              # Persistent Ticket panels & HTML transcripts
│   ├── antinuke.py             # Server security, raid limits & emergency lockdown
│   ├── music.py                # yt-dlp / FFmpeg music player with button controls
│   ├── profile.py              # Profile customization & visual card generator
│   ├── payments.py             # UPI / QR payment gateway with staff review
│   ├── roles.py                # Role manager, hierarchy checks & self-role panels
│   ├── verification.py         # Anti-bot CAPTCHA gate & role assignment
│   ├── moderation.py           # Moderation enforcement & warning logs
│   ├── leveling.py             # XP progression, leaderboards & economy
│   ├── utility.py              # Starboard, giveaways, polls & stickies
│   ├── logging.py              # Granular audit event logging
│   ├── admin.py                # Admin dashboard & database backup utility
│   ├── server_templates.py     # 50 Enterprise server template generator suite
│   ├── ai_agent.py             # Automatic AI Coding Agent & compiler debugger
│   ├── economy.py              # OwO-style Virtual Economy, banking, gambling & streaks
│   ├── hunt.py                 # Wild Animal Hunting & Zoo collection system
│   ├── battle.py               # PvP turn-based combat & duel system with betting
│   ├── inventory.py            # Weapons, equipment, armory shop & consumables
│   ├── pets.py                 # Collectible Pet Companions with passive bonuses & feeding
│   ├── crates.py               # Mystery Crates & Gem Shop with server-side RNG
│   ├── social.py               # Marriage, divorce, love ship, rep & atomic P2P trading
│   ├── economy_admin.py        # /economy-setup channel provisioner & admin management
│   └── public_ai.py            # Zero-command Public AI Q&A with vision & OCR
│
├── services/                   # Service layer
│   ├── ai_engine.py            # Multi-provider AI engine (Gemini, OpenAI, DeepSeek)
│   └── economy_service.py      # Core economy, combat, hunting & trading transaction engine
│
├── database/                   # Database subsystem
│   ├── database.py             # aiosqlite manager with WAL mode & automated schemas
│   ├── models.py               # Typed dataclass schemas
│   └── migrations/             # Schema migration history (001_economy_and_public_ai.sql)
│
├── utils/                      # Helper libraries
│   ├── embeds.py               # Standardized professional Discord embed builder
│   ├── permissions.py          # Hierarchy validation & security checks
│   ├── image_generator.py      # Pillow banner, profile card & CAPTCHA generator
│   ├── helpers.py              # HTML transcript engine, time parser & paginator
│   └── economy_checks.py       # Channel restriction guards, time formatters & purple UI
│
├── assets/                     # Graphical assets
│   └── welcome/                # Custom welcome backgrounds & branding
│
└── logs/                       # Rotating application logs & SQLite snapshots
    └── backups/                # Timestamped .db backups
```

---

## 🛠️ Prerequisites & System Requirements

- **Python**: Version 3.12 or newer (Tested and verified on Python 3.12 - 3.15)
- **Git**: Installed for repository cloning
- **FFmpeg**: Required for the Music Player voice playback
- **Operating System**: Windows 10/11, Linux (Ubuntu/Debian/CentOS), macOS, or Android (via Termux)

---

## 🔑 Discord Developer Portal Setup

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application**, name it **NOVEXA**, and click **Create**.
3. Navigate to the **Bot** tab on the left sidebar:
   - Click **Add Bot** (or **Reset Token**).
   - Copy the bot token and save it safely.
4. **Privileged Gateway Intents (CRITICAL)**:
   - Scroll down to the **Privileged Gateway Intents** section.
   - Enable **PRESENCE INTENT**.
   - Enable **SERVER MEMBERS INTENT** (Required for welcome cards, verification, autoroles).
   - Enable **MESSAGE CONTENT INTENT** (Required for chat XP, autoresponders, sticky notices).
   - Click **Save Changes**.
5. **Generate Invite Link**:
   - Go to **OAuth2** -> **URL Generator**.
   - Under **Scopes**, select:
     - `bot`
     - `applications.commands`
   - Under **Bot Permissions**, select:
     - `Administrator` (or select `Manage Server`, `Manage Roles`, `Manage Channels`, `Kick Members`, `Ban Members`, `Send Messages`, `Embed Links`, `Attach Files`, `Connect`, `Speak`, `Moderate Members`).
   - Copy the generated URL and paste it into your browser to invite the bot to your server.
   - **Important Role Hierarchy Tip**: In your Discord Server Settings -> Roles, drag the **NOVEXA** role above the roles you want it to manage or assign!

---

## 📦 Step-by-Step Installation Guides

### 1. Windows Installation

1. **Install Python**:
   - Download Python 3.12+ from [python.org](https://www.python.org/downloads/).
   - ⚠️ Check the box **"Add Python to PATH"** during installation.

2. **Install FFmpeg on Windows**:
   - Download the latest `ffmpeg-release-essentials.zip` from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).
   - Extract the zip folder to `C:\ffmpeg`.
   - Open Windows Search -> Search for **"Edit the system environment variables"**.
   - Click **Environment Variables** -> Select `Path` under User/System variables -> Click **Edit** -> Click **New** -> Add `C:\ffmpeg\bin`.
   - Open a new terminal and test: `ffmpeg -version`.

3. **Configure the Project**:
   ```powershell
   cd C:\Users\ALI\Documents\GULAMALI-ULTIMATE-BOT
   
   # Create virtual environment (recommended)
   python -m venv venv
   .\venv\Scripts\activate

   # Install dependencies
   python -m pip install -r requirements.txt
   ```

4. **Set Environment Variables**:
   - Copy `.env.example` to `.env`:
     ```powershell
     Copy-Item .env.example .env
     ```
   - Open `.env` in Notepad and replace `your_bot_token_here` with your Discord Bot Token:
     ```env
     DISCORD_TOKEN=MTA4OTI...
     OWNER_IDS=123456789012345678
     BOT_PREFIX=/
     ```

5. **Start the Bot**:
   ```powershell
   python main.py
   ```

---

### 2. Linux / VPS Installation (Ubuntu / Debian)

1. **Install System Dependencies & FFmpeg**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3 python3-pip python3-venv ffmpeg libnacl-dev
   ```

2. **Clone and Configure**:
   ```bash
   cd /opt
   sudo git clone https://github.com/your-repo/NOVEXA.git
   cd NOVEXA
   
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   
   cp .env.example .env
   nano .env   # Enter your token and owner IDs
   ```

3. **Setup 24/7 Background Service (Systemd)**:
   Create a systemd unit file:
   ```bash
   sudo nano /etc/systemd/system/novexa-bot.service
   ```
   Paste the following:
   ```ini
   [Unit]
   Description=Novexa Discord Bot
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/opt/NOVEXA
   ExecStart=/opt/NOVEXA/venv/bin/python main.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
   Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable novexa-bot
   sudo systemctl start novexa-bot
   sudo systemctl status novexa-bot
   ```

---

### 3. Android / Termux Setup

1. **Update Termux Packages**:
   ```bash
   pkg update && pkg upgrade -y
   pkg install -y python git ffmpeg clang libjpeg-turbo libpng freetype
   ```

2. **Setup Project**:
   ```bash
   git clone <repo-url>
   cd NOVEXA
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   cp .env.example .env
   nano .env
   ```

3. **Run Bot**:
   ```bash
   python main.py
   ```

---

## ⚡ Master Slash Command Reference

### 🎨 Advanced Welcome & Goodbye Studio (`/welcome` & `/goodbye`)
| Command | Description |
|---|---|
| `/welcome setup` | One-click guided setup for welcome channel, auto-role, and 20 visual templates |
| `/welcome channel <channel>` | Set or update the designated announcement channel for member welcomes |
| `/welcome template` | Select from **20 professionally designed visual themes** via interactive dropdown menu |
| `/welcome preview [template]` | Live real-time visual preview rendering the chosen template and member card |
| `/welcome customize` | Configure custom title, description, color, image toggle, embed toggle, and DM welcome |
| `/welcome autorole <role>` | Configure automatic role assignment upon member join |
| `/welcome test` | Trigger a test welcome event in the designated channel simulating a real member join |
| `/welcome disable` | Deactivate the welcome announcement system |
| `/goodbye setup <channel>` | Configure designated departure channel and leave announcement options |
| `/goodbye template <template>` | Select one of the 20 custom visual themes for departing members |
| `/goodbye customize` | Configure custom departure message, embed toggle, and footer |
| `/goodbye test` | Trigger a test departure event simulating a leaving member |
| `/goodbye disable` | Deactivate goodbye departure notifications |

### 🛡️ Advanced Anti-Nuke Protection Suite (`/antinuke`)
| Command | Description |
|---|---|
| `/antinuke settings` | View real-time sliding-window thresholds, active security mode, and configured punishments |
| `/antinuke toggle` | Enable or disable the Anti-Nuke protection engine |
| `/antinuke mode <mode>` | Set operating protection mode: `LOW` (Log only), `MEDIUM` (Automated response), `HIGH` (Aggressive strict lockdown) |
| `/antinuke punishment <action>` | Set automated punishment on threshold breach: `Quarantine (Strip Roles)`, `Kick`, `Ban` |
| `/antinuke lockdown [action]` | Emergency server lockdown: revoke permissions across all text channels (`lock` or `unlock`) |

### 🚫 Intelligent Anti-Spam & Phishing Defense (`/antispam`)
| Command | Description |
|---|---|
| `/antispam settings` | View active anti-spam thresholds, phishing heuristics, and active punishment duration |
| `/antispam toggle` | Enable or disable the real-time Anti-Spam filter |
| `/antispam mentions <max_mentions>` | Configure maximum allowed user/role mentions per message (default: 5) |
| `/antispam duplicates <max_messages>` | Set duplicate message burst limit within 5-second sliding window |
| `/antispam invites <enabled>` | Block unauthorized Discord server invite links in chat |
| `/antispam links <enabled>` | Block suspicious web URLs and heuristic phishing patterns |
| `/antispam emojis <max_emojis>` | Set emoji flood limit per message (default: 8) |
| `/antispam punishment <duration_minutes>` | Set automatic member timeout duration on violation (1 to 10,080 minutes) |
| `/antispam exempt-add <target>` | Exempt a trusted role or channel from anti-spam scanning |
| `/antispam exempt-remove <target>` | Remove an exemption for a role or channel |
| `/antispam exempt-list` | View all active exempt roles and channels |

### 📋 Granular Whitelist & Bot Gatekeeper (`/whitelist`)
| Command | Description |
|---|---|
| `/whitelist add <user_or_role>` | Add a trusted administrator or moderator to the server-wide whitelist |
| `/whitelist remove <user_or_role>` | Remove an entity from the whitelist |
| `/whitelist list` | View all currently whitelisted users, roles, and their grant details |
| `/whitelist check <user_or_role>` | Check whether a specific member or role is currently protected by whitelist |
| `/whitelist clear` | Clear all custom whitelist entries (server owner remains safe) |
| `/whitelist settings` | View whitelist security settings and bot addition protection policy |
| `/whitelist bot-approve <bot_id> <name>` | Pre-approve an external bot application ID to join the server safely |
| `/whitelist bot-remove <bot_id>` | Revoke approval for an external bot |
| `/whitelist bot-list` | View all registered and approved bot application IDs |

### 🔒 Master Security Operations & Disaster Recovery (`/security` & `/backup`)
| Command | Description |
|---|---|
| `/security dashboard` | Interactive visual security command center with live status and action buttons |
| `/security status` | Comprehensive report of Anti-Nuke, Anti-Spam, Whitelist, and audit log health |
| `/security enable` | Instantly activate all security modules with enterprise defaults |
| `/security disable` | Deactivate all automated security modules |
| `/security mode <mode>` | Set global security posture across all security sub-systems (`LOW`, `MEDIUM`, `HIGH`) |
| `/security lockdown` | Immediate emergency lockdown: revoke send permissions for regular members |
| `/security unlock` | Restore standard channel permissions after an emergency lockdown |
| `/security logs [limit]` | Inspect recent security incidents, executor IDs, actions taken, and audit timestamps |
| `/security setup-logs` | Automatically create the dedicated `NOVEXA SECURITY LOGS` channel and bind security dispatchers |
| `/backup create [name]` | Generate an immediate non-destructive snapshot of roles, channels, overwrites, and settings |
| `/backup list` | List all historical server architecture backups with snapshot IDs and dates |
| `/backup restore <backup_id>` | Safely restore missing channels, roles, and settings from a backup snapshot |
| `/backup delete <backup_id>` | Permanently remove a backup snapshot |

### High-Fidelity Music Player & 24/7 Voice
| Command | Description |
|---|---|
| `/join [channel]` | Connect bot to your voice channel (or specific voice channel) |
| `/leave` | Disconnect bot from voice channel and clear queue |
| `/247 <enabled: True/False>` | Toggle 24/7 Voice Channel Mode (stays in VC permanently across restarts) |
| `/play <query>` | Stream any song name, YouTube URL, playlist, Spotify link, or SoundCloud |
| `/pause` | Pause currently playing track |
| `/resume` | Resume playback |
| `/skip` | Skip track |
| `/stop` | Disconnect bot and purge the queue |
| `/queue` | View upcoming songs in queue |
| `/nowplaying` | Display detailed embed with song duration and playback buttons |
| `/loop <mode>` | Loop track, loop queue, or turn off |
| `/shuffle` | Shuffle upcoming songs in the queue |
| `/clearqueue` | Clear all queued songs without stopping active song |
| `/volume <1-100>` | Adjust player volume |

### Profile & Cards
| Command | Description |
|---|---|
| `/profile [user]` | Render custom graphic profile card with rank, level, bio, and coins |
| `/setbio <bio>` | Update personal bio displayed on card |
| `/setcolor <hex>` | Set custom accent color for card |
| `/setavatar` | Attach or link custom avatar image for card |
| `/setbanner` | Attach or link custom banner image for card |

### Payment Gateway (`/payment` & `/pay`)
| Command | Description |
|---|---|
| `/payment setup` | Configure UPI ID, QR code image, instructions, and review channel |
| `/pay` | Display payment instructions, QR code, and copyable UPI ID |
| `/payment submit` | Submit transaction amount, reference ID, and screenshot proof |
| `/payment history` | View recent payment status history |

### Channel Message Dispatcher & Send Message Suite
| Command | Description |
|---|---|
| `/send-message [channel] [message] [attachment] [reply_to]` | **Send Message**: Send any message or announcement to any channel through the bot. If message is omitted, pops open the multi-line "Send Message" modal. Supports full Nitro animated emojis and file attachments |
| `/send_message [channel] [message] [attachment] [reply_to]` | Alias for `/send-message` |
| `send message #channel <text>` | Direct plain typing: type in any chat to make the bot dispatch the message to `#channel` and auto-delete your trigger message |
| `/say <message> [channel] [attachment] [reply_to]` | Send any message to any channel via the bot with Nitro emoji support |
| `/say_modal [channel]` | Pop open the multi-line paragraph "Send Message" modal to format and send long announcements |
| `/embed_say <description> [title] [channel] [color] [image] [footer]` | Broadcast an embed message with custom colors and images |
| `/ping` | Check WebSocket latency |
| `/serverinfo` | View comprehensive server stats |
| `/userinfo` | Inspect member info |
| `/avatar` / `/banner` | View user avatar or banner in high resolution |
| `/poll` | Create interactive polls with reactions |
| `/suggest` | Post server suggestions for voting |
| `/giveaway_start` | Launch automated giveaways with timers and winners |
| `/starboard_setup` | Configure ⭐ Starboard showcase channel |
| `/sticky_set` / `/sticky_remove` | Manage sticky notices pinned to the bottom of channels |
| `/autoresponder` | Set up automatic text reply triggers |

### Roles & Verification
| Command | Description |
|---|---|
| `/role add / remove` | Assign or remove roles with strict role hierarchy checks |
| `/role create / delete` | Create or delete roles |
| `/role panel_create` | Create an interactive button role panel for self-assignment |
| `/role autorole` | Set automatic roles given to new members on join |
| `/verify setup` | Configure verified role, unverified role, channel, and CAPTCHA toggle |
| `/verify panel` | Deploy the persistent "Verify Here" button panel |

### Moderation & Administration
| Command | Description |
|---|---|
| `/ban`, `/unban`, `/kick` | Member disciplinary actions with reason and confirmation |
| `/timeout`, `/untimeout` | Time out members for custom durations (`10m`, `2h`, `1d`) |
| `/warn`, `/warnings` | Issue warnings and inspect warning logs |
| `/clear <amount>` | Bulk purge messages with optional user filter |
| `/lock`, `/unlock`, `/slowmode` | Channel lockouts and slowmode delay |
| `/admin dashboard` | Interactive visual dashboard to toggle any module with a select menu |
| `/admin backup` | Create immediate snapshot backup of SQLite database |
| `/admin sync` | Force synchronization of slash commands globally or to current guild |

### 🤖 Advanced AI Coding Agent (`/ai-setup`, `/ai-settings`, etc.)
| Command | Description |
|---|---|
| *(Automatic in AI Channel)* | **Zero-Command Automatic AI**: Users do not need slash commands, prefixes, or mentions. Simply post code, compiler errors, or screenshots. The AI agent analyzes and responds automatically |
| `/ai-setup` | Interactive channel selector and specialization mode menu to activate automatic AI coding support in channels |
| `/ai-disable <channel>` | Turn off automatic AI responses in a specific channel and restore normal chatting |
| `/ai-settings` | Master interactive dashboard to configure AI model, response language, user limits, and auto-threading |
| `/ai-status` | View active AI channels, configured API providers (Gemini, OpenAI, DeepSeek), active model, and daily usage |
| `/ai-model <model>` | Quick command to switch active completion model (`gemini-1.5-flash`, `gemini-1.5-pro`, `gpt-4o`, `deepseek-chat`, etc.) |
| `/ai-usage` | View token consumption, request analytics, screenshots analyzed, and top users |
| `/ai-user-limit <limit> <cooldown>` | Configure per-user hourly request limit (1-200) and anti-spam cooldown (1-60s) |
| `/ai-clear-memory [user]` | Purge conversation context memory for a specific user or for the entire channel |

### 🏗️ Server Template Generator & Reset Suite (`/server-setup` & `/server-reset`)
| Command | Description |
|---|---|
| `/server-setup` | Interactive 2-tier Category & Template Select Menu showing 50 server templates across 10 categories, Discord modal for server naming, live progress report, and automatic setup of categories, channels, 11-tier roles, Welcome, Verification, Tickets, Anti-Nuke, dedicated `🤖・ai-chat` assistant & 10 Enterprise Logging channels. Offers both `Build (Keep Existing)` and `Wipe & Build Fresh` one-click actions |
| `/server-reset [scope]` | Completely wipe all server channels, categories and custom roles to start fresh. Choose scope: `All` (channels + roles), `Channels Only`, or `Roles Only`. Includes confirmation protection and automatically creates a fresh landing channel `🚀・getting-started` |
| `/server-setup-status` | View generation metrics, active template, resources created, linked channels, and module integration status |
| `/server-setup-rollback` | Safely delete only the channels, categories, and roles created during the template setup session without touching pre-existing resources |

### 💰 Economy, RPG & Mini-Games
| Command | Description |
|---|---|
| `/balance` | Check your wallet, bank balance, net worth, and gems |
| `/wallet` | View your pocket coins available for immediate spending or gambling |
| `/bank` | View secure bank savings, deposit capacity, and interest rates |
| `/deposit <amount>` | Safely deposit wallet coins into your bank account (`all` supported) |
| `/withdraw <amount>` | Withdraw coins from your bank account to wallet (`all` supported) |
| `/pay <user> <amount>` | Transfer coins from your wallet to another server member atomically |
| `/daily` | Claim your daily coin and gem reward with consecutive streak bonuses |
| `/weekly` | Claim weekly bonus reward (5,000-8,000 coins + 15 gems + rare crate) |
| `/monthly` | Claim monthly grand prize (25,000-40,000 coins + 50 gems + epic crate) |
| `/work` | Work an honest job to earn coins and leveling XP (5-min cooldown) |
| `/crime` | High-risk criminal heist: 65% success rate for huge loot or police fine |
| `/slut` | Classic OwO-style flirtatious encounters with hilarious scenarios |
| `/coinflip <choice> <bet>` | Flip a virtual gold coin for a 2x payout (heads or tails) |
| `/dice <bet> [guess]` | Roll a 6-sided die against the bot or guess exact number for 6x payout |
| `/slots <bet>` | Spin the classic 3-reel slot machine with jackpot multipliers up to 50x |
| `/gamble <bet>` | Roll 1-100 against the house with 2x and 3x win tiers |
| `/leaderboard [type]` | Server rankings for wealth, level, zoo collection, battles, and reputation |
| `/rep <user>` | Award a reputation point to a helpful server member (24h cooldown) |
| `/achievements` | View your unlocked achievements and claim gem/coin rewards |

### 🐾 Hunt System & Zoo Collection
| Command | Description |
|---|---|
| `/hunt` | Hunt for wild animals in the forest with interactive buttons (Hunt Again, Zoo, Details, Sell) |
| `/zoo` | Showcase your collected animals organized by rarity tiers |
| `/animals` | Interactive directory and drop rate transparent statistics for all 49 wild species |
| `/animal-info <animal>` | Detailed lore, catch weight, base value, and abilities for a specific animal |
| `/sell-animal <animal> [count]` | Sell duplicate or unwanted animals to the market (`all`, `duplicates`, or exact count) |
| `/favorite-animal <animal>` | Toggle favorite star on your prized animals to protect from selling |
| `/hunt-stats` | View lifetime hunts, capture success rate, zoo net worth, and rarest catch |

### ⚔️ PvP Battle Arena
| Command | Description |
|---|---|
| `/battle <user> [bet]` | Challenge another member to a turn-based combat duel with optional coin pot |
| `/duel <user> [bet]` | Shorthand alias for `/battle` |
| `/accept-battle` | Accept an active battle challenge from a challenger |
| `/decline-battle` | Decline or forfeit an active battle challenge |
| `/battle-stats [user]` | Inspect combat record: Level, HP, ATK, DEF, equipped gear, and win/loss ratio |
| `/battle-history` | View recent duel outcomes, combat round logs, and prize distribution |

### 🛒 Weapons, Equipment & Inventory
| Command | Description |
|---|---|
| `/shop [category]` | Browse the interactive armory catalog: Swords, Guns, Bows, Shields, Armor, Boosters, Crates |
| `/buy <item> [quantity]` | Purchase weapons, defense gear, hunting nets, or consumables |
| `/sell <item> [quantity]` | Sell unequipped gear back to the marketplace for 50% refund |
| `/inventory [category]` | View your gear, equipment slots, consumables, and collectible crates |
| `/equip <item>` | Equip a weapon, shield, armor, or hunting gear to boost battle and hunt stats |
| `/unequip <slot_or_item>` | Unequip active combat gear and return it to your general bag |
| `/weapon` | Quick inspection of your currently equipped weapon and active damage bonus |
| `/weapon-info <item>` | View combat stats, rarity, critical strike chance, and abilities of any weapon |
| `/item-info <item>` | Detailed item lore, resale price, category, and active passive buffs |
| `/use-item <item>` | Consume potions, open crates, or activate timed luck boosters |

### 🐶 Pet Companions
| Command | Description |
|---|---|
| `/pets` | View all available pet companion species, adoption fees, and passive bonuses |
| `/adopt <pet_type> [name]` | Adopt a loyal companion (Dog, Cat, Wolf, Owl, Bear, Fox, Griffin, Phoenix, Dragon) |
| `/pet` | Inspect your currently equipped pet companion, happiness meter, level, and stats |
| `/pet-equip <pet_type>` | Switch your active companion pet to activate their specific passive buff |
| `/pet-feed [pet_type]` | Feed your pet with Gourmet Pet Feast or coins to boost happiness and grant XP |
| `/pet-level [pet_type]` | View pet leveling progression and upgraded stat multipliers |
| `/pet-rename <pet_type> <name>`| Give your pet a custom personalized nickname |
| `/pet-info <pet_type>` | View lore, rarity, and scaling perk rates for a pet companion |

### 🎁 Crates, Gems & Special Rewards
| Command | Description |
|---|---|
| `/crate` | View your mystery crate inventory and drop rate tables |
| `/open-crate <crate> [amount]` | Open Common, Rare, Epic, or Legendary mystery crates with server-side RNG |
| `/gems` | Check your rare Gem balance used for exclusive Mythical items |
| `/gem-shop` | Exclusive luxury bazaar offering mythical gear, special artifacts, and rings |
| `/claim-reward <type>` | Quick-claim daily streak, weekly, or monthly milestone rewards |

### 💍 Social & Community Features
| Command | Description |
|---|---|
| `/marry <user>` | Propose marriage to another member using a Diamond Engagement Ring |
| `/divorce` | Dissolve your current marriage with mutual record update |
| `/ship <user1> [user2]` | Calculate love compatibility percentage between two users with custom meter |
| `/friends` | View your server relationship status, married partner, and friends |
| `/gift <user> <item> [qty]` | Send items or mystery crates directly to a friend's inventory |
| `/trade <user>` | Launch an atomic two-party interactive trade session with double confirmation |

### 🤖 Public AI Question & Answer System
| Command | Description |
|---|---|
| *(Automatic in Channel)* | **Zero-Command Automatic AI**: Members ask questions naturally without commands, prefixes, or bot mentions. Answers programming (Python, C++, C#, JS, HTML/CSS, Android), science, math, bug diagnosis, and analyzes attached code or screenshots |
| `/ai-public setup <channel>` | Designate a channel for automatic public AI Q&A |
| `/ai-public disable <channel>` | Deactivate automatic public AI Q&A in a channel |
| `/ai-public settings` | Configure AI provider (Gemini, OpenAI, DeepSeek), model, system prompt, and cooldowns |

### ⚙️ Channel Setup & Economy Administration
| Command | Description |
|---|---|
| `/economy-setup` | Interactive channel provisioner: automatic 1-click creation of 5 suggested categories (💰 ECONOMY, 🐾 HUNTING, 🛒 MARKETPLACE, 🎮 GAMES, 🤖 AI SUPPORT) or bind existing channels |
| `/economy-admin overview` | Master admin dashboard: inspect total currency in circulation, active players, and system status |
| `/economy-admin add-coins` | Credit coins to a member's wallet or bank account with audit logging |
| `/economy-admin remove-coins`| Deduct coins from a member's wallet or bank account |
| `/economy-admin set-coins` | Set a member's exact wallet or bank balance |
| `/economy-admin give-item` | Spawn any item, crate, or weapon directly into a user's inventory |
| `/economy-admin remove-item` | Remove items from a user's inventory |
| `/economy-admin set-level` | Adjust a member's economy level and XP |
| `/economy-admin reset-economy` | Server wipe with confirmation dialog to reset user balances (leaves catalog intact) |
| `/economy-admin stats` | View macroeconomic metrics: richest users, total money supply, active hunts |
| `/economy-admin config` | Toggle economy enabled/disabled, enforce channel restrictions, and adjust reward limits |
| `/economy-admin bind-channel` | Whitelist specific text channels for specific economy categories |

#### 📋 Available Server Templates (50 Unique Architecture Presets across 10 Categories):

1. **🎮 Gaming & Esports (8 Templates)**
   - `gaming`: **Gaming Community** — Valorant, GTA V, Minecraft, PUBG, Apex, Clips & Squad VCs.
   - `esports_clan`: **Competitive Esports Team** — Scrims, roster, tournaments, strats, alpha/bravo comms.
   - `minecraft_network`: **Minecraft Server Network** — Survival, SkyBlock, Factions, Bedwars, staff queue.
   - `gta_fivem`: **GTA V & FiveM Roleplay** — Police (LSPD), EMS, mechanics, underworld, radio frequency VCs.
   - `fps_tactical`: **Tactical FPS Arena** — CS2, R6 Siege, Valorant, aim-training, line-ups, team comms.
   - `battle_royale`: **Battle Royale Hub** — Warzone, Apex, Fortnite, leaderboards, custom match scrims.
   - `roblox_studio`: **Roblox Dev & Studio** — Lua scripting, model showcases, game testing, asset commissions.
   - `free_fire`: **Free Fire Esports & Community** — Custom rooms, CS ranked scrims, tournaments, guild tryouts, points table & lineups.

2. **🛍️ Store & Commerce (6 Templates)**
   - `digital_store`: **Digital Store & Cheats Hub** — Silent aim, UID bypass, payment methods, proofs, VIP lounge.
   - `crypto_nft`: **Crypto & Web3 Alpha** — Bitcoin, Ethereum, Solana, DeFi calls, trading signals, VIP whale lounge.
   - `clothing_brand`: **Streetwear & Apparel Brand** — Lookbooks, drops, size guides, customer support tickets.
   - `service_freelance`: **Freelancer Agency Hub** — Client onboarding, design, dev, marketing, quote tickets.
   - `game_reseller`: **Account & Game Reselling** — Steam, Valorant, Epic games, warranty info, vouches.
   - `subscription_vip`: **Premium Membership Tier** — Tier perks, secret drops, masterclasses, executive VCs.

3. **💻 Tech, Coding & AI (6 Templates)**
   - `developer`: **Software Engineering HQ** — Python, Rust, Go, TypeScript, code reviews, pair programming.
   - `ai_ml_hub`: **Artificial Intelligence & LLMs** — Prompt engineering, local LLMs, PyTorch, research papers.
   - `cyber_security`: **Cyber Security & Red Team** — Ethical hacking, CTF, exploit dev, reverse engineering.
   - `ui_ux_design`: **UI/UX & Product Design** — Figma resources, design critique, portfolio reviews.
   - `bot_developer`: **Discord Bot Developers** — discord.py, discord.js, API help, bot showcases.
   - `game_dev`: **Game Engine & Indie Dev** — Unity, Unreal Engine, Godot, pixel art, 3D blender modeling.

4. **🎥 Content Creators & Media (5 Templates)**
   - `creator`: **YouTuber & Streamer HQ** — Stream alerts, video uploads, fan art, VIP sub lounge, live stage.
   - `twitch_streamer`: **Twitch Partner Streamer** — Clips, emotes, sub badges, on-stream guest VCs.
   - `podcast_network`: **Podcast & Audio Talkshow** — Episode archives, live recording stage, guest green rooms.
   - `vlogger_lifestyle`: **Lifestyle & Travel Vlogger** — Travel stories, behind the scenes, meetups, sponsor inquiries.
   - `tiktok_reels`: **Short-Form Content Creators** — TikTok, YouTube Shorts, viral trends, editing tips.

5. **⛩️ Anime, Manga & Fandoms (5 Templates)**
   - `anime_lounge`: **Anime & Manga Haven** — Seasonal anime, manga chapters, recommendations, cosplay.
   - `genshin_honkai`: **HoYoverse Sanctuary** — Genshin Impact, Honkai Star Rail, Zenless Zone Zero, builds.
   - `cosplay_hub`: **Cosplay & Costume Makers** — Crafting, foam work, 3D printing, convention meetups.
   - `lofi_cafe`: **Lofi Chill & Study Lounge** — 24/7 lofi music, aesthetic quotes, cozy mood chats.
   - `pokemon_club`: **Pokémon Trainers Club** — VGC battles, TCG cards, shiny hunting, trades, raids.

6. **💬 Social, Hangout & Lifestyle (5 Templates)**
   - `social`: **Friendly Hangout Community** — Casual chat, pet pics, food photography, game nights.
   - `study_cafe`: **Virtual Campus & Study Cafe** — Pomodoro timers, homework help, silent focus study rooms.
   - `fitness_gym`: **Fitness & Gym Motivation** — Workouts, nutrition & meal plans, transformation proofs.
   - `book_club`: **Literary & Book Lovers** — Book of the month, reading goals, fiction, non-fiction.
   - `cinema_club`: **Movie & TV Series Enthusiasts** — Movie watch parties, spoilers discussion, cinematic critique.

7. **🎵 Music & Audio Production (4 Templates)**
   - `music`: **Musicians & Songwriters Guild** — FL Studio, Ableton, feedback, stems exchange, jam rooms.
   - `dj_electronic`: **Electronic Dance Music & DJ Hub** — Synth presets, beat drops, live DJ sets, festival talks.
   - `acoustic_indie`: **Acoustic, Indie & Singer/Songwriter** — Guitar chords, vocal covers, open mic night stage.
   - `voice_acting`: **Voice Acting & Dubbing Studio** — Auditions, reel critiques, voice warmups, script reading.

8. **📚 Education, Campus & Stocks (4 Templates)**
   - `education`: **Academic University Campus** — STEM, Humanities, faculty office hours, research projects.
   - `language_learning`: **Polyglot & Language Exchange** — English, Spanish, Japanese, German, native speaker practice.
   - `medical_health`: **Medical & Healthcare Students** — Anatomy, pharmacology, USMLE/NEET study focus.
   - `finance_stocks`: **Stock Market & Trading Desk** — Technical analysis, options trading, dividends, market news.

9. **🏢 Business, Startups & Enterprise (4 Templates)**
   - `business`: **Enterprise Business HQ** — Sales, operations, HR, boardrooms, client lounges.
   - `startup_incubator`: **Startup Incubator & Pitch Lab** — Pitch decks, angel funding, MVP feedback, founder chats.
   - `real_estate`: **Real Estate & Property Investors** — Commercial, residential, mortgage financing, deal analysis.
   - `charity_ngo`: **Charity Foundation & Non-Profit** — Fundraising, volunteer coordination, field impact reports.

10. **⚡ Special Ops, Events & Minimal (3 Templates)**
    - `staff_management`: **Private Operations HQ** — Shift clock-in/out, activity tracking, executive councils.
    - `giveaway_events`: **Mega Giveaway & Events Hub** — Flash drops, daily prizes, winner proofs, interactive stage.
    - `minimal_professional`: **Minimalist Dark Executive** — Clean, uncluttered, high-speed Discord server structure.

---

## 🌐 Official Connected Website & Web Dashboard

NOVEXA features a high-performance web dashboard built with **FastAPI** running directly inside the bot's asynchronous event loop. Both the bot and website share the same memory space, Discord gateway client cache, and SQLite connection pool with zero inter-process overhead.

### 🌟 Features & Pages

| Route | Page | Description |
|---|---|---|
| `/` | **Home Landing Page** | Dark futuristic hero presentation, live server stats, and quick-add button |
| `/features` | **Features Directory** | In-depth breakdown of Security, Welcome Studio, Economy, and AI |
| `/commands` | **Interactive Command Catalog** | Categorized list of all 99 slash commands with syntax and permissions |
| `/premium` | **VIP & Premium Plans** | Tiered feature matrix, perk comparisons, and subscription benefits |
| `/status` | **System Status & Uptime** | Live gateway latency, shard status, database health, and uptime counter |
| `/docs` | **Developer & Admin Docs** | Comprehensive guides on anti-nuke thresholds, template variables, and setup |
| `/support` | **Support & Community** | Direct invite links to the official Discord support guild |
| `/faq` | **Frequently Asked Questions** | Answers to common setup, permission, and audio questions |
| `/privacy` | **Privacy Policy** | Transparent data retention policy and GDPR compliance details |
| `/terms` | **Terms of Service** | End-user agreement and server safety guidelines |
| `/login` | **Discord OAuth2 Login** | Seamless Discord login redirect (with local development fallback) |
| `/dashboard` | **User Server Hub** | Displays all Discord servers where the logged-in user has `Manage Server` permissions |
| `/dashboard/{guild_id}` | **Live Guild Control Center** | Tabbed management suite with interactive 20-template visual previewer, anti-nuke rate-limits, anti-spam filters, whitelist, and backups |
| `/admin/dashboard` | **Master Owner Console** | Restricted to configured bot owners; displays system RAM, CPU, database file size, and global guild metrics |

### 🛠️ Web Dashboard Configuration

Configure the web server in your `.env` file:
```env
# Connected Web Dashboard Configuration
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8080
SESSION_SECRET_KEY=novexa_super_secret_hmac_key_2026_change_in_production

# Discord OAuth2 (Required for production login)
DISCORD_CLIENT_ID=1089200000000000000
DISCORD_CLIENT_SECRET=your_discord_client_secret_here
DISCORD_REDIRECT_URI=http://localhost:8080/callback
```

Once the bot starts with `python main.py`, the web interface is automatically available at:
👉 **`http://localhost:8080`**

---

## 🔒 Security & Best Practices

1. **Keep Bot Token Secret**: Never commit your `.env` file or share your token publicly.
2. **Discord Role Hierarchy**: In your server's role list, position the bot's highest role above any role it needs to manage or assign.
3. **Audit Log Access**: The Anti-Nuke and Logging systems require the `View Audit Log` permission.
4. **Legitimate Audio Compliance**: The music player uses `yt-dlp` stream extraction without bypassing logins or paywalled DRM.

---

## 📄 License & Credits
- **Brand**: NOVEXA
- **Architecture**: Enterprise Asynchronous Python / discord.py 2.x
- **Author**: Novexa Software Suite

