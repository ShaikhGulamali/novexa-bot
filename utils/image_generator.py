import io
import random
import string
import aiohttp
import logging
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import discord

logger = logging.getLogger("novexa.images")


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Safely load cross-platform TrueType font with fallbacks."""
    font_candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans.ttf",
        "arial.ttf",
    ]
    for candidate in font_candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


async def fetch_image(url: str) -> Optional[Image.Image]:
    """Fetch an image asynchronously from a URL and return as PIL Image."""
    if not url:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as e:
        logger.warning(f"Failed to fetch image from {url}: {e}")
    return None


def make_circular_avatar(image: Image.Image, size: Tuple[int, int]) -> Image.Image:
    """Resize image and crop into an anti-aliased circle."""
    image = image.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    output = ImageOps.fit(image, mask.size, centering=(0.5, 0.5))
    output.putalpha(mask)
    return output


from utils.welcome_templates import get_template, WELCOME_TEMPLATES


async def generate_welcome_banner(
    member: discord.Member,
    background_url: str = "",
    template_id: str = "novexa_exclusive",
    custom_title: Optional[str] = None,
    custom_footer: Optional[str] = None,
) -> discord.File:
    """Generate a high-definition, premium welcome banner image styled by selected template."""
    tmpl = get_template(template_id)
    width, height = 900, 360
    base = Image.new("RGBA", (width, height), (24, 25, 28, 255))
    draw = ImageDraw.Draw(base)

    # Background handling
    bg_img = await fetch_image(background_url) if background_url else None
    if bg_img:
        bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)
        # Apply dark overlay for readability
        overlay = Image.new("RGBA", (width, height), (15, 16, 20, 180))
        bg_img = Image.alpha_composite(bg_img, overlay)
        base.paste(bg_img, (0, 0))
    else:
        # Dynamic template gradient
        c_start, c_end = tmpl["bg_gradient"]
        for y in range(height):
            ratio = y / height
            r = int(c_start[0] + ratio * (c_end[0] - c_start[0]))
            g = int(c_start[1] + ratio * (c_end[1] - c_start[1]))
            b = int(c_start[2] + ratio * (c_end[2] - c_start[2]))
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Inner Glass Card
    card_margin = 18
    card_shape = [(card_margin, card_margin), (width - card_margin, height - card_margin)]
    card_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_overlay)
    card_draw.rounded_rectangle(
        card_shape,
        radius=20,
        fill=tmpl["card_fill"],
        outline=tmpl["card_border"],
        width=3,
    )
    base = Image.alpha_composite(base, card_overlay)
    draw = ImageDraw.Draw(base)

    # Avatar
    avatar_size = 180
    avatar_x = 60
    avatar_y = (height - avatar_size) // 2

    # Draw Avatar Glowing Ring
    ring_box = (avatar_x - 6, avatar_y - 6, avatar_x + avatar_size + 6, avatar_y + avatar_size + 6)
    draw.ellipse(ring_box, outline=tmpl["ring_color"], width=5)

    # Fetch and paste member avatar
    avatar_url = member.display_avatar.url
    avatar_img = await fetch_image(avatar_url)
    if not avatar_img:
        avatar_img = Image.new("RGBA", (avatar_size, avatar_size), tmpl["ring_color"])
    circular_avatar = make_circular_avatar(avatar_img, (avatar_size, avatar_size))
    base.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)

    # Typography
    text_x = avatar_x + avatar_size + 45
    font_welcome = _get_font(26, bold=True)
    font_name = _get_font(40, bold=True)
    font_sub = _get_font(21, bold=False)

    # Text content
    welcome_text = (custom_title or tmpl["tagline"]).upper()
    if len(welcome_text) > 30:
        welcome_text = welcome_text[:28] + "..."

    name_text = member.display_name
    if len(name_text) > 16:
        name_text = name_text[:14] + "..."
    sub_text = f"Member #{member.guild.member_count or 1} • {member.guild.name[:24]}"

    # Drawing text
    draw.text((text_x, 82), welcome_text, fill=tmpl["welcome_color"], font=font_welcome)
    draw.text((text_x, 126), name_text, fill=tmpl["name_color"], font=font_name)
    draw.text((text_x, 198), sub_text, fill=tmpl["sub_color"], font=font_sub)

    # Accent decorative bottom badge
    footer_label = custom_footer or f"Joined: {member.joined_at.strftime('%b %d, %Y') if member.joined_at else 'Today'}"
    if len(footer_label) > 36:
        footer_label = footer_label[:34] + "..."
    badge_box = [(text_x, 246), (text_x + 290, 284)]
    draw.rounded_rectangle(
        badge_box,
        radius=8,
        fill=tmpl["badge_bg"],
        outline=tmpl["card_border"],
        width=1,
    )
    badge_font = _get_font(15, bold=True)
    draw.text((text_x + 16, 255), footer_label, fill=tmpl["badge_text"], font=badge_font)

    # Output to BytesIO
    buffer = io.BytesIO()
    base.save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(fp=buffer, filename=f"welcome_{member.id}.png")


async def generate_profile_card(
    member: discord.Member,
    level: int,
    xp: int,
    xp_next: int,
    rank: int,
    wallet: int,
    bio: str,
    custom_color: str,
    custom_avatar_url: str = "",
    custom_banner_url: str = "",
) -> discord.File:
    """Generate a sleek, comprehensive user profile card."""
    width, height = 850, 480
    base = Image.new("RGBA", (width, height), (22, 24, 29, 255))
    draw = ImageDraw.Draw(base)

    # Parse custom color hex
    accent_rgb = (88, 101, 242)
    if custom_color and custom_color.startswith("#") and len(custom_color) == 7:
        try:
            accent_rgb = tuple(int(custom_color[i:i+2], 16) for i in (1, 3, 5))
        except Exception:
            pass

    # Banner Background (Top 180px)
    banner_img = await fetch_image(custom_banner_url) if custom_banner_url else None
    banner_height = 190
    if banner_img:
        banner_img = banner_img.resize((width, banner_height), Image.Resampling.LANCZOS)
        base.paste(banner_img, (0, 0))
    else:
        # Gradient banner
        for y in range(banner_height):
            ratio = y / banner_height
            r = int(accent_rgb[0] * 0.4 + ratio * 20)
            g = int(accent_rgb[1] * 0.4 + ratio * 20)
            b = int(accent_rgb[2] * 0.4 + ratio * 40)
            draw.line([(0, y), (width, y)], fill=(min(r, 255), min(g, 255), min(b, 255), 255))

    # Dark bottom card body
    draw.rectangle([(0, banner_height), (width, height)], fill=(28, 30, 36, 255))

    # Avatar placement (overlapping banner)
    avatar_size = 140
    avatar_x = 45
    avatar_y = banner_height - (avatar_size // 2)

    # Avatar border
    draw.ellipse((avatar_x - 5, avatar_y - 5, avatar_x + avatar_size + 5, avatar_y + avatar_size + 5), fill=(28, 30, 36, 255))
    draw.ellipse((avatar_x - 2, avatar_y - 2, avatar_x + avatar_size + 2, avatar_y + avatar_size + 2), outline=accent_rgb, width=4)

    # Avatar image
    avatar_src = custom_avatar_url or member.display_avatar.url
    avatar_img = await fetch_image(avatar_src)
    if not avatar_img:
        avatar_img = Image.new("RGBA", (avatar_size, avatar_size), accent_rgb)
    circular_avatar = make_circular_avatar(avatar_img, (avatar_size, avatar_size))
    base.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)

    # User Identifiers
    name_font = _get_font(30, bold=True)
    sub_font = _get_font(18, bold=False)
    draw.text((avatar_x + avatar_size + 25, banner_height + 15), member.display_name[:20], fill=(255, 255, 255), font=name_font)
    draw.text((avatar_x + avatar_size + 25, banner_height + 55), f"@{member.name} • Rank #{rank}", fill=(160, 165, 175), font=sub_font)

    # Stats Badges (Right side)
    stats_y = banner_height + 15
    badge_font = _get_font(18, bold=True)
    value_font = _get_font(22, bold=True)

    # Level Badge
    draw.text((630, stats_y), "LEVEL", fill=(160, 165, 175), font=badge_font)
    draw.text((630, stats_y + 24), str(level), fill=accent_rgb, font=value_font)

    # Coins Badge
    draw.text((730, stats_y), "COINS", fill=(160, 165, 175), font=badge_font)
    draw.text((730, stats_y + 24), f"${wallet:,}", fill=(87, 242, 135), font=value_font)

    # XP Progress Bar
    bar_x = 45
    bar_y = 330
    bar_width = width - 90
    bar_height = 22

    # Bar background
    draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)], radius=11, fill=(45, 48, 56))

    # Calculate fill ratio
    ratio = min(max(xp / max(xp_next, 1), 0.0), 1.0)
    fill_width = int(bar_width * ratio)
    if fill_width > 12:
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height)], radius=11, fill=accent_rgb)

    # XP Label
    xp_font = _get_font(15, bold=True)
    xp_str = f"XP: {xp:,} / {xp_next:,} ({int(ratio * 100)}%)"
    draw.text((bar_x + 5, bar_y - 25), "PROGRESS TO NEXT LEVEL", fill=(140, 145, 155), font=xp_font)
    draw.text((bar_x + bar_width - 150, bar_y - 25), xp_str, fill=(210, 215, 225), font=xp_font)

    # Bio Card Section
    bio_box = [(bar_x, 375), (bar_x + bar_width, height - 25)]
    draw.rounded_rectangle(bio_box, radius=10, fill=(38, 41, 48), outline=(55, 58, 68), width=1)
    bio_title_font = _get_font(14, bold=True)
    bio_font = _get_font(16, bold=False)
    draw.text((bar_x + 16, 385), "ABOUT ME", fill=accent_rgb, font=bio_title_font)

    # Wrap bio text
    clean_bio = bio.replace("\n", " ")[:120]
    draw.text((bar_x + 16, 410), clean_bio, fill=(220, 224, 230), font=bio_font)

    # Output
    buffer = io.BytesIO()
    base.save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(fp=buffer, filename=f"profile_{member.id}.png")


def generate_captcha() -> Tuple[discord.File, str]:
    """Generate a clean, readable yet bot-proof CAPTCHA image with random code."""
    width, height = 320, 110
    image = Image.new("RGBA", (width, height), (32, 34, 38, 255))
    draw = ImageDraw.Draw(image)

    # Generate 5-character alphanumeric code avoiding ambiguous characters (0, O, 1, I)
    chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    code = "".join(random.choices(chars, k=5))

    # Background random noise lines
    for _ in range(8):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        color = (random.randint(60, 120), random.randint(60, 120), random.randint(140, 200), 160)
        draw.line([(x1, y1), (x2, y2)], fill=color, width=random.randint(1, 2))

    # Draw individual characters with slight rotation & positioning jitter
    font = _get_font(46, bold=True)
    start_x = 35
    for i, char in enumerate(code):
        char_img = Image.new("RGBA", (60, 70), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)
        char_color = random.choice([
            (88, 101, 242), (87, 242, 135), (254, 231, 92), (235, 69, 158), (255, 255, 255)
        ])
        char_draw.text((10, 5), char, fill=char_color, font=font)
        # Rotate slightly
        angle = random.randint(-18, 18)
        char_img = char_img.rotate(angle, resample=Image.Resampling.BILINEAR, expand=True)
        image.paste(char_img, (start_x + i * 50, random.randint(18, 28)), char_img)

    # Security dots
    for _ in range(25):
        px = random.randint(0, width)
        py = random.randint(0, height)
        draw.point((px, py), fill=(200, 200, 200, 180))

    # Border
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline=(88, 101, 242, 200), width=2)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(fp=buffer, filename="captcha.png"), code

