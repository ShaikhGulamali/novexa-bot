"""
NOVEXA Central Animated & Custom Emoji Registry
All emojis sourced directly from the bot's application emojis on Discord.
"""

import discord


class Emojis:
    # ==================== ANIMATED VERIFICATION & TICKS ====================
    TICK = "<a:452028tick:1568627969428295700>"
    TICK_SPIN = "<a:938761tick:1568628273519394847>"
    CHECK_BW = "<a:8632chechbw:1568627285064679534>"
    VERIFIED_BADGE = "<:1906robloxverified:1568627167657726105>"

    # ==================== ANIMATED TICKETS & SUPPORT ====================
    TICKET = "<a:560905maketicket:1568628045466570782>"
    GEAR = "<a:957955purplegear:1568628294864207933>"
    PAPER = "<a:22489pepepaper:1568627380807925760>"
    BRIEFCASE = "<a:613644purplebriefcase:1568628086172422255>"

    # ==================== ANIMATED ARROWS & BULLET POINTS ====================
    ARROW = "<a:5341arrowfexx:1568627222607175760>"
    ARROW_PINK = "<a:5274pinkarrow:1568627218152952009>"
    ARROW_YELLOW = "<a:15770animatedarrowyellow:1568627339225735289>"
    ARROW_GREEN = "<a:68523animatedarrowgreen:1568627590250500177>"
    ARROW_PURPLE = "<a:73288animatedarrowpurple:1568627614367879279>"
    ARROW_WHITE = "<a:51047animatedarrowwhite:1568627514354569367>"

    # ==================== ANIMATED STARS, CROWNS & GEMS ====================
    STAR_BLUE = "<a:27603hotblueblackstar:1568627409585045545>"
    STAR_PURPLE = "<a:202014purpleblackstar:1568627806295040110>"
    STAR_YELLOW = "<a:121835yellowblackstar:1568627751542456361>"
    STAR_BLACK = "<a:363239blackgraystar:1568627904433094676>"
    CROWN = "<a:293484crown:1568627865333923850>"
    DIAMOND = "<a:422891purplediamond:1568627946485317632>"
    SPARKLES = "<a:4720sparklesrainbow:1568627207637569848>"

    # ==================== ANIMATED FIRE & LIGHTNING ====================
    FIRE_PURPLE = "<a:5997purplefire:1568627235924086868>"
    FIRE_WHITE = "<a:6096whitefire:1568627238952509460>"
    FIRE_GREEN = "<a:9922greenfire:1568627316593004614>"
    FIRE_YELLOW = "<a:9922yellowfire:1568627318870777886>"
    FIRE_PINK = "<a:1289lightpinkfire:1568627161555013712>"
    FIRE_BLACK = "<a:9928blackfire:1568627321215393804>"
    LIGHTNING = "<a:653548lightning:1568628117667319848>"

    # ==================== ANIMATED ECONOMY & CURRENCY ====================
    COIN_PIXEL = "<a:1643pixelcoin:1568627165640269894>"
    COIN_SPIN = "<a:933416goldenspincoin:1568628266774831195>"
    FLYING_MONEY = "<a:808643flyingmoney:1568628196792860722>"
    PEPE_RICH = "<a:828203peperich:1568628204434882681>"
    CARD = "<a:761219pepecreditcard:1568628189431865464>"

    # ==================== ANIMATED WELCOME & CELEBRATION ====================
    WELCOME_SIGN = "<a:235591peeposignwelcome:1568627827950096424>"
    WELCOME_SERVER = "<a:239456welcometotheserver:1568627834350600206>"
    DANCE = "<a:8461celebrationdance:1568627280945610812>"
    PARTY = "<a:904791meowparty:1568628256889110680>"
    HEART = "<a:196509pinkheart:1568627796660723732>"

    # ==================== ANIMATED ALERTS & MODERATION ====================
    BANNED = "<a:anibanned:1568630820925874226>"
    BOMB = "<a:622606purplebomb:1568628102492594256>"
    QUESTION = "<a:550231purplequestionmark:1568628040781668362>"
    SKULL = "<a:631562skull:1568628105625608353>"
    SWORD = "<a:925149netheritesword:1568628260458205404>"

    # ==================== PARTIAL EMOJIS (For Buttons & Select Menus) ====================
    PARTIAL_TICKET = discord.PartialEmoji(name="560905maketicket", id=1568628045466570782, animated=True)
    PARTIAL_TICK = discord.PartialEmoji(name="452028tick", id=1568627969428295700, animated=True)
    PARTIAL_CROWN = discord.PartialEmoji(name="293484crown", id=1568627865333923850, animated=True)
    PARTIAL_DIAMOND = discord.PartialEmoji(name="422891purplediamond", id=1568627946485317632, animated=True)
    PARTIAL_BANNED = discord.PartialEmoji(name="anibanned", id=1568630820925874226, animated=True)
    PARTIAL_GEAR = discord.PartialEmoji(name="957955purplegear", id=1568628294864207933, animated=True)
    PARTIAL_COIN = discord.PartialEmoji(name="933416goldenspincoin", id=1568628266774831195, animated=True)
    PARTIAL_SPARKLES = discord.PartialEmoji(name="4720sparklesrainbow", id=1568627207637569848, animated=True)
    PARTIAL_FIRE = discord.PartialEmoji(name="5997purplefire", id=1568627235924086868, animated=True)
    PARTIAL_SWORD = discord.PartialEmoji(name="925149netheritesword", id=1568628260458205404, animated=True)

    # ==================== ADVANCED ANTI-NUKE EMOJIS ====================
    AN_ENABLED = "<a:452028tick:1568627969428295700>"
    AN_DISABLED = "<:943538cross:1568628281903685703>"
    AN_ACTIVE = "🛡️"
    AN_ATTACK = "<a:622606purplebomb:1568628102492594256>"
    AN_EXECUTOR = "<a:631562skull:1568628105625608353>"
    AN_BANNED = "<:339990banhammer:1568627896078307358>"
    AN_CHANNEL = "🔒"
    AN_WEBHOOK = "🗑️"
    AN_ROLE = "⚖️"
    AN_BOT = "<:32478bots:1568627431995342958>"
    AN_LOCKDOWN = "<a:22247redcard:1568627378199073000>"
    AN_LOGS = "<a:22489pepepaper:1568627380807925760>"
    AN_ALERT = "<a:622606purplebomb:1568628102492594256>"

    # Anti-Nuke Partials for Buttons & Select Menus
    PARTIAL_AN_ENABLED = discord.PartialEmoji(name="452028tick", id=1568627969428295700, animated=True)
    PARTIAL_AN_DISABLED = discord.PartialEmoji(name="943538cross", id=1568628281903685703, animated=False)
    PARTIAL_AN_BANNED = discord.PartialEmoji(name="339990banhammer", id=1568627896078307358, animated=False)
    PARTIAL_AN_BOMB = discord.PartialEmoji(name="622606purplebomb", id=1568628102492594256, animated=True)
    PARTIAL_AN_BOT = discord.PartialEmoji(name="32478bots", id=1568627431995342958, animated=False)
    PARTIAL_AN_PAPER = discord.PartialEmoji(name="22489pepepaper", id=1568627380807925760, animated=True)

