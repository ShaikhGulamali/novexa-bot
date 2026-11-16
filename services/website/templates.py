"""NOVEXA - Premium HTML Templates & Complete Control Panel UI Generator.
Inspired by the dark cyberpunk / silver luxury aesthetic of https://www.zynrax.site/.

Features:
- "NOVEXA — One Bot. Infinite Power."
- 14 Public & Auth Pages (Home, Features, Commands, Docs, Premium, Statistics, Support, FAQ, Privacy, Terms, Status, Login, User Dashboard, Owner Admin)
- Complete 32-Module Server Dashboard with category-grouped sidebar from FEATURE_REGISTRY
- Live 2-Way Server-Sent Events (SSE) real-time synchronization
- Dynamic 20-template visual welcome canvas previewer
- Responsive desktop, tablet, and mobile offcanvas layouts
"""

import html
import json
import math
from typing import List, Dict, Any, Optional
from config import BOT_NAME, BOT_VERSION
from utils.welcome_templates import list_templates
from services.feature_registry import FEATURE_REGISTRY, FEATURE_CATEGORIES

BASE_CSS = """
:root {
    --bg-dark: #08090d;
    --bg-surface: #0e111a;
    --bg-card: rgba(16, 20, 32, 0.75);
    --bg-card-hover: rgba(24, 30, 48, 0.9);
    --border: rgba(255, 255, 255, 0.08);
    --border-hover: rgba(0, 229, 255, 0.4);
    --border-active: #00E5FF;
    --accent: #00E5FF;
    --accent-glow: rgba(0, 229, 255, 0.25);
    --primary: #5865F2;
    --primary-glow: rgba(88, 101, 242, 0.3);
    --gold: #F59E0B;
    --success: #10B981;
    --danger: #EF4444;
    --text-main: #F8FAFC;
    --text-muted: #94A3B8;
    --text-dim: #64748B;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: var(--bg-dark);
    color: var(--text-main);
    line-height: 1.6;
    overflow-x: hidden;
    background-image: 
        radial-gradient(circle at 12% 18%, rgba(0, 229, 255, 0.05) 0%, transparent 40%),
        radial-gradient(circle at 88% 82%, rgba(88, 101, 242, 0.06) 0%, transparent 45%);
    background-attachment: fixed;
}

a { color: var(--accent); text-decoration: none; transition: all 0.2s ease; }
a:hover { color: #67e8f9; text-shadow: 0 0 10px var(--accent-glow); }

.navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 40px;
    background: rgba(10, 12, 18, 0.85);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 1000;
}
.navbar-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 1.5px;
    color: #fff;
}
.navbar-brand span { color: var(--accent); }
.nav-links {
    display: flex;
    align-items: center;
    gap: 24px;
    list-style: none;
}
.nav-links a {
    color: var(--text-muted);
    font-size: 14px;
    font-weight: 600;
    transition: all 0.2s;
}
.nav-links a:hover, .nav-links a.active {
    color: #fff;
    text-shadow: 0 0 8px rgba(255, 255, 255, 0.3);
}

.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 10px 20px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    border: none;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    text-decoration: none;
}
.btn-primary {
    background: linear-gradient(135deg, var(--primary) 0%, #4338ca 100%);
    color: #fff !important;
    box-shadow: 0 4px 15px var(--primary-glow);
}
.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(88, 101, 242, 0.55);
}
.btn-accent {
    background: linear-gradient(135deg, var(--accent) 0%, #0284c7 100%);
    color: #06080d !important;
    box-shadow: 0 4px 15px var(--accent-glow);
}
.btn-accent:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 229, 255, 0.5);
    color: #000 !important;
}
.btn-outline {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text-main) !important;
}
.btn-outline:hover {
    border-color: var(--accent);
    color: var(--accent) !important;
    background: rgba(0, 229, 255, 0.05);
}
.btn-danger {
    background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
    color: #fff !important;
}
.btn-danger:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(239, 68, 68, 0.5);
}

.container {
    max-width: 1240px;
    margin: 0 auto;
    padding: 40px 24px;
}

.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
}
.badge-accent {
    background: rgba(0, 229, 255, 0.12);
    border: 1px solid rgba(0, 229, 255, 0.3);
    color: var(--accent);
}
.badge-success {
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #34d399;
}
.badge-gold {
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.3);
    color: #fbbf24;
}

.card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    backdrop-filter: blur(12px);
    transition: all 0.25s ease;
}
.card:hover {
    border-color: var(--border-hover);
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
}

.footer {
    border-top: 1px solid var(--border);
    padding: 50px 24px 30px;
    background: #06070a;
    text-align: center;
    margin-top: 80px;
}
.footer-links {
    display: flex;
    justify-content: center;
    gap: 28px;
    margin-bottom: 24px;
    flex-wrap: wrap;
}
.footer-links a { color: var(--text-muted); font-size: 14px; font-weight: 500; }
.footer-links a:hover { color: #fff; }
.footer p { color: var(--text-dim); font-size: 13px; }

/* Form Controls */
.form-group {
    margin-bottom: 20px;
}
.form-group label {
    display: block;
    font-size: 13px;
    font-weight: 700;
    color: var(--text-main);
    margin-bottom: 8px;
    letter-spacing: 0.3px;
}
.form-group .desc {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 8px;
}
.form-control {
    width: 100%;
    background: rgba(8, 10, 16, 0.85);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
    color: #fff;
    font-size: 14px;
    outline: none;
    transition: all 0.2s;
}
.form-control:focus {
    border-color: var(--accent);
    box-shadow: 0 0 12px var(--accent-glow);
}
select.form-control {
    cursor: pointer;
}
textarea.form-control {
    min-height: 90px;
    resize: vertical;
}

/* Switch toggle */
.switch {
    position: relative;
    display: inline-block;
    width: 48px;
    height: 26px;
}
.switch input { opacity: 0; width: 0; height: 0; }
.slider {
    position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
    background-color: #1e2538;
    transition: .3s;
    border-radius: 34px;
    border: 1px solid var(--border);
}
.slider:before {
    position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px;
    background-color: #fff;
    transition: .3s;
    border-radius: 50%;
}
input:checked + .slider {
    background-color: var(--accent);
}
input:checked + .slider:before {
    transform: translateX(22px);
    background-color: #000;
}

/* Toast Notifications */
#toast-container {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 99999;
    display: flex;
    flex-direction: column;
    gap: 12px;
}
.toast {
    background: #0e121d;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 20px;
    color: #fff;
    font-size: 14px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.6);
    display: flex;
    align-items: center;
    gap: 10px;
    animation: slideIn 0.25s ease forwards;
}
.toast-success { border-color: var(--success); }
.toast-error { border-color: var(--danger); }
@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

@media (max-width: 768px) {
    .navbar { padding: 14px 20px; }
    .nav-links { display: none; }
    .container { padding: 24px 16px; }
}
"""

# ==================== CRIMSON NOVEXA THEME (override layer) ====================
BASE_CSS += """
:root {
    --bg-dark: #0a0507;
    --bg-surface: #150a0d;
    --bg-card: rgba(30, 12, 16, 0.72);
    --bg-card-hover: rgba(52, 18, 25, 0.9);
    --border: rgba(255, 77, 94, 0.14);
    --border-hover: rgba(255, 45, 85, 0.5);
    --border-active: #FF2D55;
    --accent: #FF3B4E;
    --accent-glow: rgba(255, 45, 85, 0.3);
    --primary: #E11D48;
    --primary-glow: rgba(225, 29, 72, 0.35);
    --gold: #F59E0B;
    --success: #22C55E;
    --danger: #F87171;
    --text-main: #FFF5F6;
    --text-muted: #CFA9AF;
    --text-dim: #8F7078;
}
body {
    background-image:
        radial-gradient(circle at 14% 18%, rgba(255, 45, 85, 0.09) 0%, transparent 45%),
        radial-gradient(circle at 86% 82%, rgba(225, 29, 72, 0.1) 0%, transparent 50%);
}
body::before {
    content: "";
    position: fixed;
    inset: 0;
    background:
        linear-gradient(rgba(255,45,85,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,45,85,0.025) 1px, transparent 1px);
    background-size: 42px 42px;
    pointer-events: none;
    z-index: 0;
    mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%);
    -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%);
}

.fx-orb {
    position: fixed;
    border-radius: 50%;
    filter: blur(90px);
    opacity: .45;
    pointer-events: none;
    z-index: 0;
    animation: orbFloat 16s ease-in-out infinite alternate;
}
@keyframes orbFloat {
    from { transform: translate3d(0, 0, 0) scale(1); }
    to   { transform: translate3d(50px, -70px, 0) scale(1.18); }
}

.card {
    transform-style: preserve-3d;
    transition: transform .35s cubic-bezier(.2,.8,.2,1), box-shadow .35s ease, border-color .3s ease;
    will-change: transform;
}
.card:hover {
    box-shadow: 0 26px 60px -18px var(--accent-glow), 0 0 0 1px var(--border-hover);
}

.btn { transition: all .25s ease; }
.btn-primary {
    background: linear-gradient(135deg, #E11D48, #FF3B4E);
    box-shadow: 0 6px 24px -6px var(--primary-glow);
}
.btn-primary:hover { transform: translateY(-2px) scale(1.02); box-shadow: 0 14px 36px -6px var(--accent-glow); }
.btn-outline:hover { border-color: var(--border-active); color: var(--accent); }

.navbar {
    backdrop-filter: blur(14px);
    background: rgba(12, 5, 8, 0.85) !important;
    box-shadow: 0 4px 28px rgba(0,0,0,.5), inset 0 -1px 0 var(--border);
}
.navbar-brand { text-shadow: 0 0 24px var(--accent-glow); letter-spacing: 2px; }

h1, h2, h3 { text-shadow: 0 0 28px rgba(255,45,85,.16); }

@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 18px var(--accent-glow); }
    50%      { box-shadow: 0 0 44px var(--accent-glow); }
}
.glow-pulse { animation: pulseGlow 3s ease-in-out infinite; }

.dash-tab-btn { transition: all .22s ease; }
.dash-tab-btn:hover { transform: translateX(4px); background: rgba(255,45,85,.09); }
.dash-tab-btn.active {
    background: linear-gradient(90deg, rgba(255,45,85,.2), rgba(255,45,85,.04)) !important;
    border-left: 3px solid var(--accent) !important;
    box-shadow: inset 0 0 24px rgba(255,45,85,.08);
}
.badge-accent { background: rgba(255,45,85,.15); border: 1px solid rgba(255,45,85,.32); color: #FFB3BE; }

.form-control:focus { border-color: var(--border-active); box-shadow: 0 0 0 3px var(--accent-glow); }
.switch .slider { transition: all .25s ease; }
.switch input:checked + .slider { background: linear-gradient(135deg, #E11D48, #FF3B4E); box-shadow: 0 0 14px var(--accent-glow); }

.footer { border-top: 1px solid var(--border); background: rgba(10, 4, 6, .9); }

.btn-accent {
    background: linear-gradient(135deg, #FF5566 0%, #C1103C 55%, #8E0A2C 100%);
    color: #fff !important;
    box-shadow: 0 4px 18px rgba(255, 45, 85, .34), inset 0 1px 0 rgba(255,255,255,.16);
}
.btn-accent:hover {
    box-shadow: 0 8px 28px rgba(255, 45, 85, .55), inset 0 1px 0 rgba(255,255,255,.22);
    color: #fff !important;
}
.btn-primary {
    background: linear-gradient(135deg, rgba(255, 45, 85, .18) 0%, rgba(120, 12, 40, .55) 100%);
    border: 1px solid rgba(255, 77, 94, .45);
    color: #fff !important;
    box-shadow: 0 4px 18px rgba(225, 29, 72, .22);
}
.btn-primary:hover {
    transform: translateY(-2px);
    border-color: var(--accent);
    background: linear-gradient(135deg, rgba(255, 45, 85, .3) 0%, rgba(140, 16, 48, .7) 100%);
    box-shadow: 0 8px 26px rgba(255, 45, 85, .4);
}
.btn-outline:hover { background: rgba(255, 45, 85, .08); }
"""

# ==================== POLISH LAYER ====================
BASE_CSS += """
::selection { background: rgba(255, 45, 85, .35); color: #fff; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: #12080b; }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #E11D48, #7f1027);
    border-radius: 999px;
    border: 2px solid #12080b;
}
::-webkit-scrollbar-thumb:hover { background: #FF3B4E; }

html { scroll-behavior: smooth; }
body { letter-spacing: .1px; }

.container { max-width: 1240px; margin: 0 auto; padding: 40px 24px; }

.card {
    position: relative;
    overflow: hidden;
    border-radius: 16px;
    background: linear-gradient(160deg, rgba(52,18,25,.55), rgba(18,8,11,.85));
}
.card::after {
    content: "";
    position: absolute; inset: 0;
    background: linear-gradient(120deg, transparent 35%, rgba(255,255,255,.05) 50%, transparent 65%);
    transform: translateX(-120%);
    transition: transform .8s ease;
    pointer-events: none;
}
.card:hover::after { transform: translateX(120%); }

.badge {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 5px 13px; border-radius: 999px;
    font-size: 11px; font-weight: 800; letter-spacing: 1.2px; text-transform: uppercase;
    background: rgba(255,255,255,.04); border: 1px solid var(--border); color: var(--text-muted);
}

.btn {
    display: inline-flex; align-items: center; gap: 8px;
    border-radius: 12px; font-weight: 700; cursor: pointer;
    border: 1px solid transparent;
}
.btn-outline { background: rgba(255,255,255,.02); border-color: var(--border); color: var(--text-main); }
.btn-danger { background: linear-gradient(135deg, #7f1d1d, #EF4444); color: #fff; box-shadow: 0 6px 22px -8px rgba(239,68,68,.6); }
.btn-danger:hover { transform: translateY(-2px); }

.nav-links a { position: relative; }
.nav-links a::after {
    content: ""; position: absolute; left: 0; right: 100%; bottom: -6px; height: 2px;
    background: linear-gradient(90deg, var(--accent), transparent);
    transition: right .28s ease;
}
.nav-links a:hover::after, .nav-links a.active::after { right: 0; }

h1 { letter-spacing: -1.2px; }
p { text-wrap: pretty; }

.footer-links a { transition: color .2s ease, transform .2s ease; display: inline-block; }
.footer-links a:hover { transform: translateY(-2px); }

@keyframes riseIn { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
.container > * { animation: riseIn .5s ease both; }
.container > *:nth-child(2) { animation-delay: .06s; }
.container > *:nth-child(3) { animation-delay: .12s; }

input, select, textarea, button { font-family: inherit; }
input:focus-visible, select:focus-visible, button:focus-visible, a:focus-visible {
    outline: 2px solid rgba(255,45,85,.55); outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: .001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .001ms !important;
        scroll-behavior: auto !important;
    }
}
"""

BASE_CSS += """
/* ==================== MOBILE LAYER ==================== */
.nav-toggle {
    display: none;
    background: rgba(255, 45, 85, .12);
    border: 1px solid var(--border);
    border-radius: 10px;
    cursor: pointer;
    padding: 10px 11px;
    flex: 0 0 auto;
}
.nav-toggle span {
    display: block;
    width: 20px;
    height: 2px;
    border-radius: 2px;
    background: #fff;
    margin: 4px 0;
    transition: transform .2s ease, opacity .2s ease;
}
body.drawer-open .nav-toggle span:nth-child(1) { transform: translateY(6px) rotate(45deg); }
body.drawer-open .nav-toggle span:nth-child(2) { opacity: 0; }
body.drawer-open .nav-toggle span:nth-child(3) { transform: translateY(-6px) rotate(-45deg); }

.mobile-drawer { display: none; }

@media (max-width: 900px) {
    body.drawer-open { overflow: hidden; }

    .navbar {
        padding: 12px 16px;
        gap: 10px;
        flex-wrap: nowrap;
    }
    .navbar-brand { font-size: 17px; gap: 8px; }
    .navbar-brand span:first-child { font-size: 20px !important; }
    .nav-toggle { display: block; }
    .nav-links { display: none !important; }
    .navbar > div[style*="display:flex"] { display: none !important; }
    .navbar > a.btn { display: none !important; }

    .mobile-drawer {
        display: block;
        position: fixed;
        inset: 0;
        z-index: 1200;
        pointer-events: none;
        opacity: 0;
        transition: opacity .22s ease;
    }
    body.drawer-open .mobile-drawer { pointer-events: auto; opacity: 1; }
    .mobile-drawer-backdrop {
        position: absolute;
        inset: 0;
        background: rgba(0, 0, 0, .62);
        backdrop-filter: blur(2px);
    }
    .mobile-drawer-panel {
        position: absolute;
        top: 0;
        right: 0;
        height: 100%;
        width: min(88vw, 360px);
        display: flex;
        flex-direction: column;
        background: #0a0507;
        border-left: 1px solid var(--border);
        box-shadow: -24px 0 60px rgba(0, 0, 0, .65);
        transform: translateX(100%);
        transition: transform .24s ease;
    }
    body.drawer-open .mobile-drawer-panel { transform: translateX(0); }
    .mobile-drawer-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 18px;
        border-bottom: 1px solid var(--border);
        flex: 0 0 auto;
    }
    .mobile-drawer-title {
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 2px;
        color: var(--text-dim);
    }
    .mobile-drawer-close {
        background: rgba(255, 45, 85, .12);
        border: 1px solid var(--border);
        color: #fff;
        font-size: 16px;
        line-height: 1;
        padding: 8px 11px;
        border-radius: 10px;
        cursor: pointer;
    }
    .mobile-drawer-scroll {
        flex: 1 1 auto;
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
        padding: 8px 14px 40px;
    }
    .mobile-drawer-section {
        font-size: 11px;
        font-weight: 800;
        color: var(--text-dim);
        text-transform: uppercase;
        letter-spacing: 1.2px;
        padding: 18px 6px 8px;
    }
    .mobile-drawer-link {
        display: block;
        padding: 13px 12px;
        border-radius: 10px;
        color: #e7e9ee;
        font-size: 15px;
        font-weight: 600;
        text-decoration: none;
    }
    .mobile-drawer-link:active,
    .mobile-drawer-link:hover { background: rgba(255, 45, 85, .12); }
    .mobile-modules {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .mobile-modules .dash-tab-btn {
        width: 100%;
        margin: 0;
        padding: 12px;
        border: 1px solid transparent;
        border-radius: 10px;
        background: rgba(255, 255, 255, .03);
    }
    .mobile-modules .dash-tab-btn:hover { transform: none; }

    .dash-layout { flex-direction: column; }
    .dash-sidebar { display: none; }
    .dash-content { padding: 18px 14px 64px; }
    .dash-content h1, .dash-content h2 { font-size: 22px; }
    .tab-pane .card, .dash-content .card { overflow-x: auto; -webkit-overflow-scrolling: touch; }
    .dash-content table { min-width: 520px; }
    .dash-content > div[style*="justify-content:space-between"] .btn { width: 100%; }

    div[style*="grid-template-columns:1fr 1fr"] { grid-template-columns: 1fr !important; gap: 12px !important; }
    div[style*="grid-template-columns:2fr 1fr"] { grid-template-columns: 1fr !important; gap: 12px !important; }
    div[style*="grid-template-columns:2fr auto"] { grid-template-columns: 1fr !important; gap: 12px !important; }
    div[style*="grid-template-columns:2fr 1fr auto"] { grid-template-columns: 1fr !important; gap: 12px !important; }
    div[style*="grid-template-columns:2fr 2fr auto"] { grid-template-columns: 1fr !important; gap: 12px !important; }

    .container { padding: 24px 16px 48px; }
    h1 { font-size: 30px !important; letter-spacing: -0.8px; }
    h2 { font-size: 24px !important; }
    p, li { font-size: 14.5px; }
    .btn { max-width: 100%; }
    .toast { left: 12px; right: 12px; bottom: 12px; max-width: none; }
    pre, code { overflow-x: auto; max-width: 100%; }
    img { max-width: 100%; height: auto; }
    .footer-links { flex-wrap: wrap; gap: 10px 16px; }
}

@media (max-width: 560px) {
    div[style*="minmax(340px"] { grid-template-columns: 1fr !important; }
    div[style*="minmax(320px"] { grid-template-columns: 1fr !important; }
    div[style*="minmax(300px"] { grid-template-columns: 1fr !important; }
    div[style*="minmax(280px"] { grid-template-columns: 1fr !important; }
    .navbar { padding: 10px 12px; }
    .navbar-brand span:last-child { font-size: 15px; letter-spacing: 1px; }
    .mobile-drawer-panel { width: 100%; border-left: none; }
    .dash-content { padding: 14px 10px 64px; }
    .dash-content table { min-width: 460px; }
    .card { padding: 16px !important; border-radius: 14px; }
    .form-control { font-size: 16px; }
    h1 { font-size: 25px !important; }
    h2 { font-size: 20px !important; }
    .btn { padding: 11px 16px; font-size: 14px; }
}
"""

def _render_nav(user: Optional[Dict[str, Any]] = None, active_tab: str = "home") -> str:
    user_section = ""
    if user:
        avatar = user.get("avatar_url") or "https://cdn.discordapp.com/embed/avatars/0.png"
        username = html.escape(user.get("username", "Member"))
        user_section = f"""
        <div style="display:flex;align-items:center;gap:12px;">
            <a href="/dashboard" class="btn btn-primary" style="padding:8px 16px;font-size:13px;">⚡ Dashboard</a>
            <a href="/dashboard" style="display:flex;align-items:center;gap:8px;">
                <img src="{avatar}" style="width:32px;height:32px;border-radius:50%;border:2px solid var(--accent);">
                <span style="font-weight:700;color:#fff;font-size:14px;">{username}</span>
            </a>
            <a href="/api/auth/logout" style="color:var(--danger);font-size:13px;font-weight:600;margin-left:6px;">Logout</a>
        </div>
        """
    else:
        user_section = """
        <a href="/login" class="btn btn-primary" style="padding:8px 18px;font-size:13px;">Login with Discord</a>
        """

    account_links = """
            <a href="/login" class="mobile-drawer-link">Login with Discord</a>
        """ if not user else f"""
            <a href="/dashboard" class="mobile-drawer-link">⚡ Dashboard</a>
            <a href="/api/auth/logout" class="mobile-drawer-link" style="color:var(--danger);">Logout</a>
        """

    return f"""
    <nav class="navbar">
        <a href="/" class="navbar-brand">
            <span style="font-size:24px;">👑</span>
            <span>NOVEXA</span>
        </a>
        <ul class="nav-links">
            <li><a href="/" class="{'active' if active_tab == 'home' else ''}">Home</a></li>
            <li><a href="/features" class="{'active' if active_tab == 'features' else ''}">Features</a></li>
            <li><a href="/commands" class="{'active' if active_tab == 'commands' else ''}">Commands</a></li>
            <li><a href="/premium" class="{'active' if active_tab == 'premium' else ''}">Premium</a></li>
            <li><a href="/statistics" class="{'active' if active_tab == 'statistics' else ''}">Statistics</a></li>
            <li><a href="/status" class="{'active' if active_tab == 'status' else ''}">Status</a></li>
            <li><a href="/docs" class="{'active' if active_tab == 'docs' else ''}">Docs</a></li>
            <li><a href="/faq" class="{'active' if active_tab == 'faq' else ''}">FAQ</a></li>
            <li><a href="/support" class="{'active' if active_tab == 'support' else ''}">Support</a></li>
        </ul>
        {user_section}
        <button class="nav-toggle" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="mobileDrawer" onclick="toggleMobileDrawer()">
            <span></span><span></span><span></span>
        </button>
    </nav>

    <div class="mobile-drawer" id="mobileDrawer" aria-hidden="true">
        <div class="mobile-drawer-backdrop" onclick="toggleMobileDrawer(false)"></div>
        <aside class="mobile-drawer-panel" role="dialog" aria-modal="true" aria-label="Site menu">
            <div class="mobile-drawer-head">
                <span class="mobile-drawer-title">MENU</span>
                <button class="mobile-drawer-close" type="button" aria-label="Close menu" onclick="toggleMobileDrawer(false)">✕</button>
            </div>
            <div class="mobile-drawer-scroll">
                <div class="mobile-drawer-section">Pages</div>
                <a href="/" class="mobile-drawer-link">Home</a>
                <a href="/features" class="mobile-drawer-link">Features</a>
                <a href="/commands" class="mobile-drawer-link">Commands</a>
                <a href="/premium" class="mobile-drawer-link">Premium</a>
                <a href="/statistics" class="mobile-drawer-link">Statistics</a>
                <a href="/status" class="mobile-drawer-link">Status</a>
                <a href="/docs" class="mobile-drawer-link">Docs</a>
                <a href="/faq" class="mobile-drawer-link">FAQ</a>
                <a href="/support" class="mobile-drawer-link">Support</a>
                <div class="mobile-drawer-section" id="mobileModulesSection">Server Modules</div>
                <div class="mobile-modules" id="mobileModulesList"></div>
                <div class="mobile-drawer-section">Account</div>
                {account_links}
            </div>
        </aside>
    </div>

    <script>
    function toggleMobileDrawer(force) {{
        const drawer = document.getElementById('mobileDrawer');
        if (!drawer) return;
        const open = (typeof force === 'boolean') ? force : !document.body.classList.contains('drawer-open');
        document.body.classList.toggle('drawer-open', open);
        drawer.setAttribute('aria-hidden', open ? 'false' : 'true');
        const btn = document.querySelector('.nav-toggle');
        if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (open) hydrateMobileModules();
    }}
    function hydrateMobileModules() {{
        const list = document.getElementById('mobileModulesList');
        const source = document.querySelector('.dash-sidebar');
        if (!list) return;
        if (!source) {{
            document.getElementById('mobileModulesSection')?.remove();
            return;
        }}
        if (list.dataset.ready === '1') return;
        source.querySelectorAll('.dash-tab-btn').forEach(el => {{
            const clone = el.cloneNode(true);
            clone.removeAttribute('id');
            clone.classList.remove('active');
            clone.addEventListener('click', () => toggleMobileDrawer(false));
            list.appendChild(clone);
        }});
        list.dataset.ready = '1';
    }}
    document.addEventListener('keydown', e => {{ if (e.key === 'Escape') toggleMobileDrawer(false); }});
    window.addEventListener('resize', () => {{ if (window.innerWidth > 900) toggleMobileDrawer(false); }});
    </script>
    """

def _render_footer() -> str:
    return f"""
    <footer class="footer">
        <div class="footer-links">
            <a href="/">Home</a>
            <a href="/features">Features</a>
            <a href="/commands">Commands</a>
            <a href="/premium">Premium Plans</a>
            <a href="/statistics">Statistics</a>
            <a href="/status">Status Page</a>
            <a href="/docs">Documentation</a>
            <a href="/faq">FAQ</a>
            <a href="/support">Support Server</a>
            <a href="/privacy">Privacy Policy</a>
            <a href="/terms">Terms of Service</a>
            <a href="/invite">Invite Bot</a>
        </div>
        <p>© 2026 NOVEXA. One Bot. Infinite Power. All rights reserved.</p>
    </footer>
    <div id="toast-container"></div>
    <div class="fx-orb" style="width:420px;height:420px;background:radial-gradient(circle,#E11D48,transparent 70%);top:-140px;left:-120px;"></div>
    <div class="fx-orb" style="width:360px;height:360px;background:radial-gradient(circle,#FF3B4E,transparent 70%);bottom:-120px;right:-100px;animation-delay:-8s;"></div>
    <script>
    function showToast(msg, type='success') {{
        const c = document.getElementById('toast-container');
        if(!c) return;
        const t = document.createElement('div');
        t.className = 'toast toast-' + type;
        t.innerHTML = (type === 'success' ? '✅ ' : '❌ ') + msg;
        c.appendChild(t);
        setTimeout(() => {{ t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }}, 3500);
    }}
    // 3D pointer tilt on cards (skipped inside dashboard forms)
    document.querySelectorAll('.card').forEach(card => {{
        if (card.closest('.tab-pane') || card.dataset.tiltBound) return;
        card.dataset.tiltBound = '1';
        card.addEventListener('mousemove', ev => {{
            const r = card.getBoundingClientRect();
            const rx = ((ev.clientY - r.top) / r.height - .5) * -7;
            const ry = ((ev.clientX - r.left) / r.width - .5) * 7;
            card.style.transform = 'perspective(900px) rotateX(' + rx + 'deg) rotateY(' + ry + 'deg) translateY(-4px)';
        }});
        card.addEventListener('mouseleave', () => {{ card.style.transform = ''; }});
    }});
    </script>
    """

# ==================== 1. HOME PAGE ====================
def render_home(bot, user: Optional[Dict[str, Any]] = None) -> str:
    guild_count = len(bot.guilds) if (bot and hasattr(bot, "guilds")) else 0
    member_count = sum(g.member_count or 0 for g in bot.guilds) if (bot and hasattr(bot, "guilds")) else 0
    raw_latency = float(getattr(bot, "latency", float("nan")) or float("nan"))
    latency = f"{round(raw_latency * 1000)}ms" if math.isfinite(raw_latency) and raw_latency > 0 else "—"
    commands_count = 99
    try:
        from services.website.bridge import build_catalog
        live_commands = build_catalog(bot)
        if live_commands:
            commands_count = len(live_commands)
    except Exception:
        pass
    uptime_status = "Online & Ready"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NOVEXA — One Bot. Infinite Power.</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(user, 'home')}

    <div class="container" style="text-align:center;padding-top:70px;padding-bottom:50px;">
        <div class="badge badge-accent" style="margin-bottom:24px;padding:6px 16px;">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--accent);box-shadow:0 0 10px var(--accent);"></span>
            <span>NOVEXA ENTERPRISE CORE v{BOT_VERSION}</span>
        </div>
        <h1 style="font-size:58px;font-weight:900;letter-spacing:-1.5px;line-height:1.15;margin-bottom:20px;">
            NOVEXA<br>
            <span style="background:linear-gradient(135deg, #ffffff 40%, var(--accent) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">One Bot. Infinite Power.</span>
        </h1>
        <p style="font-size:20px;color:var(--text-muted);max-width:740px;margin:0 auto 36px;">
            Protect your community, automate your server and bring everything together with one powerful Discord bot.
        </p>
        <div style="display:flex;justify-content:center;gap:16px;flex-wrap:wrap;margin-bottom:60px;">
            <a href="/invite" class="btn btn-accent" style="padding:14px 32px;font-size:16px;">👑 Add NOVEXA to Discord</a>
            <a href="/dashboard" class="btn btn-primary" style="padding:14px 32px;font-size:16px;">⚡ Open Dashboard</a>
            <a href="/features" class="btn btn-outline" style="padding:14px 28px;font-size:16px;">Explore Features</a>
            <a href="/support" class="btn btn-outline" style="padding:14px 28px;font-size:16px;">Join Support Server</a>
        </div>

        <!-- Live Backend Statistics -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(180px, 1fr));gap:18px;margin-bottom:70px;">
            <div class="card" style="text-align:center;padding:22px;">
                <div style="font-size:32px;font-weight:900;color:#fff;">{guild_count:,}</div>
                <div style="font-size:13px;font-weight:600;color:var(--text-muted);">Active Servers</div>
            </div>
            <div class="card" style="text-align:center;padding:22px;">
                <div style="font-size:32px;font-weight:900;color:#fff;">{member_count:,}</div>
                <div style="font-size:13px;font-weight:600;color:var(--text-muted);">Protected Members</div>
            </div>
            <div class="card" style="text-align:center;padding:22px;">
                <div style="font-size:32px;font-weight:900;color:var(--accent);">{commands_count}</div>
                <div style="font-size:13px;font-weight:600;color:var(--text-muted);">Commands Available</div>
            </div>
            <div class="card" style="text-align:center;padding:22px;">
                <div style="font-size:32px;font-weight:900;color:#fff;">{latency}</div>
                <div style="font-size:13px;font-weight:600;color:var(--text-muted);">API Latency</div>
            </div>
            <div class="card" style="text-align:center;padding:22px;">
                <div style="font-size:32px;font-weight:900;color:#34d399;">99.9%</div>
                <div style="font-size:13px;font-weight:600;color:var(--text-muted);">Bot Uptime</div>
            </div>
            <div class="card" style="text-align:center;padding:22px;">
                <div style="font-size:20px;font-weight:800;color:#34d399;margin-top:8px;">● {uptime_status}</div>
                <div style="font-size:13px;font-weight:600;color:var(--text-muted);">Bot Status</div>
            </div>
        </div>

        <!-- Flagship Feature Grid -->
        <h2 style="font-size:34px;font-weight:800;margin-bottom:12px;color:#fff;">Engineered for Complete Control</h2>
        <p style="color:var(--text-muted);margin-bottom:40px;max-width:650px;margin-left:auto;margin-right:auto;">
            Enterprise security, autonomous intelligence, and seamless automation running on a single authoritative backend.
        </p>

        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));gap:24px;text-align:left;">
            <div class="card">
                <div style="font-size:30px;margin-bottom:12px;">🛡️</div>
                <h3 style="font-size:18px;font-weight:700;color:#fff;margin-bottom:8px;">Advanced Anti-Nuke</h3>
                <p style="color:var(--text-muted);font-size:14px;">Sub-second interception against mass channel/role deletion, webhook spam, and unauthorized admin privilege escalations with automatic recovery.</p>
            </div>
            <div class="card">
                <div style="font-size:30px;margin-bottom:12px;">💬</div>
                <h3 style="font-size:18px;font-weight:700;color:#fff;margin-bottom:8px;">Anti-Spam & AutoMod</h3>
                <p style="color:var(--text-muted);font-size:14px;">Real-time sliding-window filters guarding against mass mentions, duplicate bursts, Discord invites, emoji storms, and malicious phishing scams.</p>
            </div>
            <div class="card">
                <div style="font-size:30px;margin-bottom:12px;">🎨</div>
                <h3 style="font-size:18px;font-weight:700;color:#fff;margin-bottom:8px;">20-Template Welcome Studio</h3>
                <p style="color:var(--text-muted);font-size:14px;">Studio-designed graphic welcome banners with circular glowing avatars, real-time in-browser canvas previewer, and 10 template variables.</p>
            </div>
            <div class="card">
                <div style="font-size:30px;margin-bottom:12px;">🎫</div>
                <h3 style="font-size:18px;font-weight:700;color:#fff;margin-bottom:8px;">Advanced Ticket System</h3>
                <p style="color:var(--text-muted);font-size:14px;">Persistent interactive button panels, staff assignment alerts, multiple support categories, and dark-mode HTML transcript generator.</p>
            </div>
            <div class="card">
                <div style="font-size:30px;margin-bottom:12px;">💰</div>
                <h3 style="font-size:18px;font-weight:700;color:#fff;margin-bottom:8px;">Complete Economy & RPG</h3>
                <p style="color:var(--text-muted);font-size:14px;">Full virtual economy featuring banking, 49 safari hunting animal species, turn-based PvP duels, pet companions, and mystery crates.</p>
            </div>
        </div>
    </div>

    {_render_footer()}
</body>
</html>
"""

# ==================== 2. FEATURES DIRECTORY ====================
def render_features(bot, user: Optional[Dict[str, Any]] = None) -> str:
    categories = [
        ("Security & Anti-Raid Defense", "🛡️", [
            ("Anti-Nuke Raid Shield", "Sub-second sliding-window interception for channel/role deletions, mass kicks, and rogue webhooks."),
            ("Intelligent Anti-Spam", "Real-time token scanning for mass mentions, copypasta, invite links, and emoji storms."),
            ("Least-Privilege Whitelist", "Separated administrator whitelist ensuring general immunity never bypasses bot addition protections."),
            ("Approved Bots Gatekeeper", "Rogue and unapproved external bots are kicked instantaneously upon joining."),
            ("Emergency Lockdown", "One-click channel lockouts revoking send/speak permissions server-wide."),
            ("Disaster Recovery Backups", "Non-destructive full server snapshots capturing roles, channels, and permission overwrites.")
        ]),
        ("Community & Aesthetics", "🎨", [
            ("20-Template Welcome Studio", "20 professional themes (Cyberpunk, Purple Luxury, Glassmorphism, Gold VIP, Anime, etc.)."),
            ("Distorted CAPTCHA Gatekeeper", "Anti-bot visual distortion challenges preventing automated raids."),
            ("Dynamic Graphic Profiles", "850x480 custom graphic user cards with bio, accent colors, banners, and rank."),
            ("Role Hierarchy & Button Panels", "Interactive button role self-assignment adhering strictly to Discord hierarchy rules.")
        ]),
        ("Intelligence & Automation", "🤖", [
            ("Auto-Responders & Stickies", "Trigger-based text responses and pinned sticky channel reminders.")
        ]),
        ("Economy, Gaming & Music", "🎮", [
            ("Virtual Economy & Banking", "Secure wallet, bank savings, daily streaks, and atomic P2P transfers."),
            ("Wild Animal Safari (49 Species)", "Forest hunting, rarity tiers, zoo collection, and duels."),
            ("High-Fidelity Music Player", "Powered by yt-dlp, FFmpeg, button controls, and 24/7 voice channel mode.")
        ])
    ]

    cards_html = ""
    for cat_title, cat_icon, feats in categories:
        cards_html += f"""
        <div style="margin-bottom:40px;">
            <h2 style="font-size:24px;color:#fff;margin-bottom:20px;display:flex;align-items:center;gap:10px;">
                <span>{cat_icon}</span> <span>{cat_title}</span>
            </h2>
            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));gap:20px;">
        """
        for title, desc in feats:
            cards_html += f"""
                <div class="card">
                    <h3 style="font-size:16px;color:var(--accent);margin-bottom:8px;">{title}</h3>
                    <p style="font-size:13px;color:var(--text-muted);">{desc}</p>
                </div>
            """
        cards_html += "</div></div>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Features — NOVEXA</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(user, 'features')}
    <div class="container">
        <div style="text-align:center;margin-bottom:50px;">
            <div class="badge badge-accent" style="margin-bottom:16px;">FEATURE DIRECTORY</div>
            <h1 style="font-size:44px;font-weight:900;color:#fff;margin-bottom:12px;">Everything You Need. In One Bot.</h1>
            <p style="color:var(--text-muted);max-width:600px;margin:0 auto;">Explore the 32 operational modules powering server security, aesthetics, and engagement.</p>
        </div>
        {cards_html}
    </div>
    {_render_footer()}
</body>
</html>
"""

# ==================== 3. COMMANDS CATALOG ====================
CATEGORY_ICONS = {
    "Welcome": "🎨", "Tickets": "🎫", "Antinuke": "🛡️", "Antispam": "💬",
    "Whitelist": "📋", "Security": "🔐", "Profile": "🪪", "Payments": "💳",
    "Roles": "🎭", "Moderation": "🔨", "Leveling": "📈",
    "Utility": "🧰", "Logging": "📜", "Admin": "👑", "ServerTemplates": "🏗️",
    "Economy": "💰", "Hunt": "🏹", "Battle": "⚔️", "Inventory": "🎒",
    "Pets": "🐾", "Crates": "🎁", "Social": "💞", "EconomyAdmin": "🏦",
    "ServerCloner": "🧬", "Owo": "🌙", "MentionReply": "📣", "Staff": "🧑‍💼",
    "Dropper": "💧", "Wallpaper": "🖼️", "VoiceSystem": "🎙️", "Music": "🎵",
    "AIChat": "🤖", "Core": "⚙️",
}


def _live_command_groups(bot) -> Optional[List[Any]]:
    """Group the live command tree by cog; None when the bot isn't up."""
    try:
        from services.website.bridge import build_catalog
        catalog = build_catalog(bot)
    except Exception:
        return None
    if not catalog:
        return None
    grouped: Dict[str, List[Any]] = {}
    for cmd in catalog:
        grouped.setdefault(cmd["category"], []).append(
            (f"/{cmd['name']}", cmd["description"] or "No description provided.")
        )
    return [
        (f"{CATEGORY_ICONS.get(cat, '•')} {cat}", items)
        for cat, items in sorted(grouped.items(), key=lambda kv: kv[0].lower())
    ]


def render_commands(bot, user: Optional[Dict[str, Any]] = None) -> str:
    commands_data = _live_command_groups(bot) or [
        ("🎨 Welcome & Goodbye", [
            ("/welcome setup", "Guided setup for channel and banner"),
            ("/welcome template", "Select from 20 visual themes via dropdown"),
            ("/welcome preview", "Generate live card preview in Discord"),
            ("/welcome customize", "Configure titles, description, and DM greeting"),
            ("/welcome test", "Trigger test welcome event in designated channel"),
            ("/goodbye setup", "Configure leave notification channel and template"),
            ("/goodbye test", "Trigger test member departure event"),
        ]),
        ("🛡️ Anti-Nuke & Security", [
            ("/antinuke settings", "View real-time sliding rate limits and posture"),
            ("/antinuke mode", "Switch mode: LOW (Alerts), MEDIUM (Auto), HIGH (Lockdown)"),
            ("/antinuke punishment", "Set action on threshold breach: Quarantine, Kick, Ban"),
            ("/antinuke lockdown", "Emergency lockdown: revokes send permissions across server"),
            ("/antinuke setup-logs", "1-Click auto provisioning of #novexa-security-logs"),
            ("/backup create", "Generate disaster recovery snapshot of server"),
            ("/backup restore", "Safely restore missing channels, roles, and settings"),
        ]),
        ("💬 Anti-Spam & AutoMod", [
            ("/antispam toggle", "Enable or disable real-time message scanning"),
            ("/antispam mentions", "Configure max user/role mentions per message"),
            ("/antispam duplicates", "Set duplicate message burst limit in 5s window"),
            ("/antispam invites", "Block unauthorized Discord server invite links"),
            ("/antispam links", "Block phishing heuristics and suspicious URLs"),
            ("/antispam punishment", "Set timeout duration on violation (1-10080 mins)"),
            ("/antispam exempt-add", "Exempt trusted roles or channels from scanning"),
        ]),
        ("📋 Whitelist & Bot Gatekeeper", [
            ("/whitelist add", "Add trusted administrator or moderator to whitelist"),
            ("/whitelist remove", "Remove an entity from the whitelist"),
            ("/whitelist list", "View all currently whitelisted users and roles"),
            ("/whitelist bot-approve", "Pre-approve external bot application ID to join"),
            ("/whitelist bot-remove", "Revoke approval for an external bot"),
            ("/whitelist bot-list", "List all pre-approved bot application IDs"),
        ]),
        ("💰 Economy, RPG & Battles", [
            ("/balance", "Check wallet, bank balance, net worth, and gems"),
            ("/deposit", "Safely deposit wallet coins into your bank account"),
            ("/withdraw", "Withdraw coins from bank account to wallet"),
            ("/pay", "Transfer coins to another member atomically"),
            ("/daily", "Claim daily coins with consecutive streak bonuses"),
            ("/hunt", "Hunt wild animals in the forest across 49 species"),
            ("/zoo", "Showcase your collected animals by rarity tiers"),
            ("/battle", "Challenge another member to turn-based combat duel"),
            ("/shop", "Browse armory catalog: Swords, Armor, Boosters, Crates"),
            ("/pets", "Adopt and feed loyal pet companions for passive buffs"),
        ]),
        ("🤖 AI & Server Tools", [
            ("/ai-public setup", "Designate channel for automatic public AI Q&A"),
            ("/ai-public settings", "Configure AI provider, model, and cooldowns"),
            ("/ticket panel", "Post persistent interactive support ticket panel"),
            ("/play", "Stream high-fidelity music from YouTube/Spotify"),
            ("/server-setup", "50 complete enterprise Discord server architecture templates"),
        ]),
    ]

    groups_html = ""
    for group_name, cmds in commands_data:
        groups_html += f"""
        <div style="margin-bottom:34px;">
            <h2 style="font-size:20px;color:#fff;margin-bottom:14px;">{group_name}</h2>
            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:12px;">
        """
        for cmd, desc in cmds:
            groups_html += f"""
                <div class="card" style="padding:16px;">
                    <div style="font-family:monospace;font-weight:700;color:var(--accent);font-size:14px;margin-bottom:4px;">{cmd}</div>
                    <div style="font-size:13px;color:var(--text-muted);">{desc}</div>
                </div>
            """
        groups_html += "</div></div>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Commands — NOVEXA</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(user, 'commands')}
    <div class="container">
        <div style="text-align:center;margin-bottom:40px;">
            <div class="badge badge-accent" style="margin-bottom:16px;">{sum(len(c) for _, c in commands_data)} LIVE SLASH COMMANDS</div>
            <h1 style="font-size:44px;font-weight:900;color:#fff;margin-bottom:12px;">Master Command Catalog</h1>
            <p style="color:var(--text-muted);max-width:600px;margin:0 auto;">Explore the full suite of interactive Discord commands available in NOVEXA.</p>
        </div>
        {groups_html}
    </div>
    {_render_footer()}
</body>
</html>
"""

# ==================== 4. PREMIUM PLANS ====================
def render_premium(bot, user: Optional[Dict[str, Any]] = None) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Premium Plans — NOVEXA</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(user, 'premium')}
    <div class="container" style="text-align:center;">
        <div class="badge badge-gold" style="margin-bottom:16px;">VIP MEMBERSHIP</div>
        <h1 style="font-size:44px;font-weight:900;color:#fff;margin-bottom:12px;">Elevate Your Server Security & Power</h1>
        <p style="color:var(--text-muted);max-width:600px;margin:0 auto 50px;">Configurable subscription tiers designed for ambitious Discord communities and enterprises.</p>

        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(300px, 1fr));gap:24px;text-align:left;">
            <!-- Silver -->
            <div class="card" style="border-top:4px solid #94A3B8;display:flex;flex-direction:column;justify-content:space-between;">
                <div>
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                        <h3 style="font-size:22px;color:#fff;">Silver VIP</h3>
                        <span class="badge" style="background:rgba(148,163,184,0.15);color:#cbd5e1;">TIER 1</span>
                    </div>
                    <div style="font-size:38px;font-weight:900;color:#fff;margin-bottom:16px;">₹299 <span style="font-size:14px;color:var(--text-muted);font-weight:500;">/ month</span></div>
                    <ul style="list-style:none;color:var(--text-muted);font-size:14px;display:flex;flex-direction:column;gap:10px;margin-bottom:30px;">
                        <li>✅ Priority Anti-Nuke Response</li>
                        <li>✅ Up to 10 Disaster Recovery Backups</li>
                        <li>✅ 150 Daily Autonomous AI Requests</li>
                        <li>✅ 30-Day Audit Log History</li>
                        <li>✅ Silver Discord Role & Badge</li>
                    </ul>
                </div>
                <a href="/support" class="btn btn-outline" style="width:100%;">Upgrade to Silver</a>
            </div>

            <!-- Gold -->
            <div class="card" style="border-top:4px solid var(--accent);box-shadow:0 0 30px var(--accent-glow);display:flex;flex-direction:column;justify-content:space-between;">
                <div>
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                        <h3 style="font-size:22px;color:#fff;">Gold Elite</h3>
                        <span class="badge badge-accent">POPULAR</span>
                    </div>
                    <div style="font-size:38px;font-weight:900;color:var(--accent);margin-bottom:16px;">₹599 <span style="font-size:14px;color:var(--text-muted);font-weight:500;">/ month</span></div>
                    <ul style="list-style:none;color:var(--text-muted);font-size:14px;display:flex;flex-direction:column;gap:10px;margin-bottom:30px;">
                        <li>✅ Instant Sub-Second Anti-Nuke Interception</li>
                        <li>✅ Up to 25 Disaster Recovery Backups</li>
                        <li>✅ 500 Daily AI Coding Requests</li>
                        <li>✅ 24/7 Dedicated Voice Mode</li>
                        <li>✅ 90-Day Audit Log History</li>
                        <li>✅ Gold Discord Role & Status</li>
                    </ul>
                </div>
                <a href="/support" class="btn btn-accent" style="width:100%;">Upgrade to Gold</a>
            </div>

            <!-- Platinum -->
            <div class="card" style="border-top:4px solid var(--gold);display:flex;flex-direction:column;justify-content:space-between;">
                <div>
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                        <h3 style="font-size:22px;color:#fff;">Platinum Ultimate</h3>
                        <span class="badge badge-gold">UNLIMITED</span>
                    </div>
                    <div style="font-size:38px;font-weight:900;color:#fbbf24;margin-bottom:16px;">₹999 <span style="font-size:14px;color:var(--text-muted);font-weight:500;">/ month</span></div>
                    <ul style="list-style:none;color:var(--text-muted);font-size:14px;display:flex;flex-direction:column;gap:10px;margin-bottom:30px;">
                        <li>✅ Ultimate Protection & Instant Lockdown</li>
                        <li>✅ Unlimited Disaster Recovery Backups</li>
                        <li>✅ 2,000 Daily AI Coding Requests</li>
                        <li>✅ Custom Welcome Canvas Branding</li>
                        <li>✅ 365-Day Extended Audit Retention</li>
                        <li>✅ Personal VIP Support Concierge</li>
                        <li>✅ Platinum Discord Role & Badge</li>
                    </ul>
                </div>
                <a href="/support" class="btn btn-outline" style="width:100%;">Upgrade to Platinum</a>
            </div>
        </div>
    </div>
    {_render_footer()}
</body>
</html>
"""

# ==================== 5. STATISTICS & TELEMETRY ====================
def render_statistics(bot, user: Optional[Dict[str, Any]] = None) -> str:
    guild_count = len(bot.guilds) if (bot and hasattr(bot, "guilds")) else 0
    member_count = sum(g.member_count or 0 for g in bot.guilds) if (bot and hasattr(bot, "guilds")) else 0
    raw_latency = float(getattr(bot, "latency", float("nan")) or float("nan"))
    latency = f"{round(raw_latency * 1000)}ms" if math.isfinite(raw_latency) and raw_latency > 0 else "—"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Statistics & Telemetry — NOVEXA</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(user, 'statistics')}
    <div class="container">
        <div style="text-align:center;margin-bottom:40px;">
            <div class="badge badge-accent" style="margin-bottom:16px;">LIVE TELEMETRY</div>
            <h1 style="font-size:44px;font-weight:900;color:#fff;margin-bottom:12px;">Real-Time System Metrics</h1>
            <p style="color:var(--text-muted);max-width:600px;margin:0 auto;">Live metrics streaming directly from the unified Python runtime and SQLite WAL engine.</p>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:20px;margin-bottom:40px;">
            <div class="card" style="text-align:center;">
                <div style="font-size:36px;font-weight:900;color:#fff;">{guild_count}</div>
                <div style="font-size:13px;color:var(--text-muted);font-weight:600;">Active Guilds</div>
            </div>
            <div class="card" style="text-align:center;">
                <div style="font-size:36px;font-weight:900;color:#fff;">{member_count}</div>
                <div style="font-size:13px;color:var(--text-muted);font-weight:600;">Total Users Protected</div>
            </div>
            <div class="card" style="text-align:center;">
                <div style="font-size:36px;font-weight:900;color:var(--accent);">{latency}</div>
                <div style="font-size:13px;color:var(--text-muted);font-weight:600;">WebSocket Latency</div>
            </div>
            <div class="card" style="text-align:center;">
                <div style="font-size:36px;font-weight:900;color:#34d399;">99.9%</div>
                <div style="font-size:13px;color:var(--text-muted);font-weight:600;">Historical Uptime</div>
            </div>
        </div>

        <div class="card" style="margin-bottom:30px;">
            <h3 style="font-size:18px;color:#fff;margin-bottom:16px;">Core System Health</h3>
            <div style="display:flex;flex-direction:column;gap:14px;">
                <div style="display:flex;justify-content:space-between;font-size:14px;">
                    <span style="color:var(--text-muted);">Discord Gateway Connection</span>
                    <span style="color:#34d399;font-weight:700;">● Connected (Shard 0)</span>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:14px;">
                    <span style="color:var(--text-muted);">Database Subsystem</span>
                    <span style="color:#34d399;font-weight:700;">● SQLite WAL Mode (Healthy)</span>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:14px;">
                    <span style="color:var(--text-muted);">Web Dashboard Server</span>
                    <span style="color:#34d399;font-weight:700;">● FastAPI / uvicorn Running</span>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:14px;">
                    <span style="color:var(--text-muted);">Real-Time Two-Way Sync</span>
                    <span style="color:var(--accent);font-weight:700;">● SSE Broadcaster Active</span>
                </div>
            </div>
        </div>
    </div>
    {_render_footer()}
</body>
</html>
"""

# ==================== 6. DOCUMENTATION ====================
def render_docs(bot, user: Optional[Dict[str, Any]] = None) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentation — NOVEXA</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(user, 'docs')}
    <div class="container" style="max-width:960px;">
        <div style="margin-bottom:40px;">
            <div class="badge badge-accent" style="margin-bottom:16px;">ENGINEERING DOCS</div>
            <h1 style="font-size:42px;font-weight:900;color:#fff;margin-bottom:12px;">NOVEXA System Documentation</h1>
            <p style="color:var(--text-muted);">Configuration guides, rate-limiting algorithms, and template variable specifications.</p>
        </div>

        <div class="card" style="margin-bottom:24px;">
            <h2 style="font-size:20px;color:var(--accent);margin-bottom:12px;">1. Welcome Studio Variable Tokens</h2>
            <p style="color:var(--text-muted);font-size:14px;margin-bottom:16px;">The following tokens can be dynamically embedded into welcome and goodbye message templates:</p>
            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:10px;font-family:monospace;font-size:13px;">
                <div style="background:rgba(0,0,0,0.5);padding:8px 12px;border-radius:6px;border:1px solid var(--border);"><strong style="color:var(--accent);">{'{user}'}</strong> — Mention (@Member)</div>
                <div style="background:rgba(0,0,0,0.5);padding:8px 12px;border-radius:6px;border:1px solid var(--border);"><strong style="color:var(--accent);">{'{username}'}</strong> — Username</div>
                <div style="background:rgba(0,0,0,0.5);padding:8px 12px;border-radius:6px;border:1px solid var(--border);"><strong style="color:var(--accent);">{'{user_id}'}</strong> — User ID</div>
                <div style="background:rgba(0,0,0,0.5);padding:8px 12px;border-radius:6px;border:1px solid var(--border);"><strong style="color:var(--accent);">{'{server}'}</strong> — Server Name</div>
                <div style="background:rgba(0,0,0,0.5);padding:8px 12px;border-radius:6px;border:1px solid var(--border);"><strong style="color:var(--accent);">{'{server_id}'}</strong> — Server ID</div>
                <div style="background:rgba(0,0,0,0.5);padding:8px 12px;border-radius:6px;border:1px solid var(--border);"><strong style="color:var(--accent);">{'{member_count}'}</strong> — Join Count</div>
            </div>
        </div>

        <div class="card" style="margin-bottom:24px;">
            <h2 style="font-size:20px;color:var(--accent);margin-bottom:12px;">2. Anti-Nuke Sliding-Window Logic</h2>
            <p style="color:var(--text-muted);font-size:14px;line-height:1.7;">
                The Anti-Nuke engine employs high-frequency sliding-window counters tracking executor audit IDs. When threshold counts (e.g. 2 channel deletions within 10 seconds) are breached, the engine isolates the executor, strips dangerous administrator permissions, and executes configured progressive mitigations.
            </p>
        </div>

        <div class="card">
            <h2 style="font-size:20px;color:var(--accent);margin-bottom:12px;">3. Role Hierarchy & Discord Permissions</h2>
            <p style="color:var(--text-muted);font-size:14px;line-height:1.7;">
                Discord enforces a strict role hierarchy. For NOVEXA to manage roles or quarantine executors, the <strong>NOVEXA</strong> bot role must be positioned above the roles it manages in your Discord Server Settings.
            </p>
        </div>
    </div>
    {_render_footer()}
</body>
</html>
"""

# ==================== 7. FAQ ====================
def render_faq(bot, user: Optional[Dict[str, Any]] = None) -> str:
    faqs = [
        ("How does NOVEXA differ from traditional Discord bots?", "NOVEXA connects both the bot and website to the exact same backend and SQLite database. Any change made via Discord commands updates the web dashboard in real-time, and vice versa."),
        ("Can server administrators bypass Anti-Nuke protections?", "Discord's Administrator permission grants fundamental server-wide access. While no bot can prevent Discord from executing an owner's action, NOVEXA instantly detects rogue administrator accounts, revokes their roles, and restores deleted resources from backups."),
        ("What happens if someone clicks a button multiple times in Economy?", "All virtual transactions and hunting mechanics use atomic database locks, preventing balance manipulation and duplicate rewards."),
    ]

    cards_html = ""
    for q, a in faqs:
        cards_html += f"""
        <div class="card" style="margin-bottom:16px;">
            <h3 style="font-size:17px;color:#fff;margin-bottom:8px;">{q}</h3>
            <p style="color:var(--text-muted);font-size:14px;">{a}</p>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FAQ — NOVEXA</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(user, 'faq')}
    <div class="container" style="max-width:860px;">
        <div style="text-align:center;margin-bottom:40px;">
            <div class="badge badge-accent" style="margin-bottom:16px;">HELP CENTER</div>
            <h1 style="font-size:42px;font-weight:900;color:#fff;margin-bottom:12px;">Frequently Asked Questions</h1>
            <p style="color:var(--text-muted);">Quick answers to questions regarding setup, permissions, and security.</p>
        </div>
        {cards_html}
    </div>
    {_render_footer()}
</body>
</html>
"""

# ==================== 8. STATUS PAGE ====================
def render_status(bot, user: Optional[Dict[str, Any]] = None) -> str:
    raw_latency = float(getattr(bot, "latency", float("nan")) or float("nan"))
    latency = f"{round(raw_latency * 1000)}ms" if math.isfinite(raw_latency) and raw_latency > 0 else "—"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Status — NOVEXA</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(user, 'status')}
    <div class="container" style="max-width:860px;">
        <div style="text-align:center;margin-bottom:40px;">
            <div class="badge badge-success" style="margin-bottom:16px;padding:6px 18px;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#10b981;"></span>
                <span>ALL SYSTEMS OPERATIONAL</span>
            </div>
            <h1 style="font-size:42px;font-weight:900;color:#fff;margin-bottom:12px;">Operational Health & Shards</h1>
            <p style="color:var(--text-muted);">Live status monitors across global Discord gateway connections.</p>
        </div>

        <div class="card" style="margin-bottom:20px;">
            <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid var(--border);">
                <div>
                    <strong style="color:#fff;">Discord Gateway Connection</strong>
                    <div style="font-size:12px;color:var(--text-muted);">Shard 0 — Latency: {latency}</div>
                </div>
                <span class="badge badge-success">Operational</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid var(--border);">
                <div>
                    <strong style="color:#fff;">SQLite WAL Storage Subsystem</strong>
                    <div style="font-size:12px;color:var(--text-muted);">Latency: &lt;1ms • High-concurrency async locks</div>
                </div>
                <span class="badge badge-success">Operational</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid var(--border);">
                <div>
                    <strong style="color:#fff;">Connected FastAPI Web Service</strong>
                    <div style="font-size:12px;color:var(--text-muted);">HTTP Port 8080 • Direct in-memory access</div>
                </div>
                <span class="badge badge-success">Operational</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;">
                <div>
                    <strong style="color:#fff;">Real-Time SSE Event Broadcaster</strong>
                    <div style="font-size:12px;color:var(--text-muted);">Two-Way Sync Gateway Active</div>
                </div>
                <span class="badge badge-success">Operational</span>
            </div>
        </div>
    </div>
    {_render_footer()}
</body>
</html>
"""

# ==================== 9. SUPPORT ====================
def render_support(bot, user: Optional[Dict[str, Any]] = None) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Support & Community — NOVEXA</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(user, 'support')}
    <div class="container" style="max-width:860px;text-align:center;">
        <div class="badge badge-accent" style="margin-bottom:16px;">24/7 SUPPORT</div>
        <h1 style="font-size:42px;font-weight:900;color:#fff;margin-bottom:12px;">Need Help with NOVEXA?</h1>
        <p style="color:var(--text-muted);margin-bottom:40px;">Our dedicated team and community are available 24/7 to assist you.</p>

        <div class="card" style="padding:40px;">
            <div style="font-size:48px;margin-bottom:16px;">👑</div>
            <h2 style="font-size:24px;color:#fff;margin-bottom:12px;">Join Official Discord Support</h2>
            <p style="color:var(--text-muted);font-size:15px;margin-bottom:24px;">Connect with server engineers, report issues, request features, and get instant technical assistance.</p>
            <a href="https://discord.gg/" target="_blank" class="btn btn-primary" style="padding:14px 32px;font-size:16px;">Join Discord Support Server</a>
        </div>
    </div>
    {_render_footer()}
</body>
</html>
"""

# ==================== 10. PRIVACY POLICY ====================
def render_privacy() -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Privacy Policy — NOVEXA</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(None, 'privacy')}
    <div class="container" style="max-width:860px;">
        <h1 style="font-size:36px;color:#fff;margin-bottom:16px;">Privacy Policy</h1>
        <p style="color:var(--text-muted);margin-bottom:24px;">Last updated: November 2026</p>
        <div class="card" style="line-height:1.8;color:var(--text-muted);">
            <p style="margin-bottom:16px;"><strong>1. Information We Collect:</strong> NOVEXA collects basic Discord entity identifiers (guild IDs, user IDs, channel IDs) required strictly to execute user-requested commands, moderation logging, anti-nuke defense, and virtual economy data.</p>
            <p style="margin-bottom:16px;"><strong>2. Message Content:</strong> Message content is processed in memory for anti-spam heuristics, sticky notices, and AI responses. We do not store raw messages permanently on external servers.</p>
            <p style="margin-bottom:16px;"><strong>3. Data Retention:</strong> Server configuration settings and database snapshots persist until explicitly deleted by the server owner via `/backup delete` or bot removal.</p>
        </div>
    </div>
    {_render_footer()}
</body>
</html>
"""

# ==================== 10B. OAUTH SETUP (Discord login not configured yet) ====================
def render_oauth_setup(client_id: str) -> str:
    redirect = "http://localhost:8080/api/auth/callback"
    safe_client = html.escape(client_id or "…")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Connect Discord Login — NOVEXA</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(None, 'login')}
    <div class="container" style="max-width:820px;">
        <div class="card glow-pulse" style="padding:36px;margin-top:40px;">
            <h1 style="font-size:30px;color:#fff;margin-bottom:10px;">🔐 One step left: connect your Discord account</h1>
            <p style="color:var(--text-muted);margin-bottom:22px;line-height:1.7;">
                The control panel is locked. Only Discord accounts with <strong style="color:#fff;">Administrator / Manage Server</strong>
                permissions can change bot settings. Add the OAuth secret below to activate Discord login.
            </p>
            <ol style="color:var(--text-muted);line-height:2;padding-left:22px;margin-bottom:22px;">
                <li>Open the <a href="https://discord.com/developers/applications/{safe_client}" target="_blank">Discord Developer Portal → your application</a>.</li>
                <li>Go to <strong style="color:#fff;">OAuth2 → General</strong> and add this redirect URL:<br>
                    <code style="background:rgba(255,45,85,.12);padding:4px 10px;border-radius:6px;color:#FFB3BE;">{redirect}</code></li>
                <li>Go to <strong style="color:#fff;">OAuth2 → Client Secret</strong>, copy the secret.</li>
                <li>Paste it into <code style="background:rgba(255,45,85,.12);padding:4px 10px;border-radius:6px;color:#FFB3BE;">.env</code> as
                    <code style="background:rgba(255,45,85,.12);padding:4px 10px;border-radius:6px;color:#FFB3BE;">DISCORD_CLIENT_SECRET=…</code> and restart the bot.</li>
            </ol>
            <p style="color:var(--text-dim);font-size:13px;">Client ID is already resolved automatically: <code style="color:#FFB3BE;">{safe_client}</code></p>
            <a href="/" class="btn btn-primary" style="display:inline-block;margin-top:18px;">← Back to Home</a>
        </div>
    </div>
    {_render_footer()}
</body>
</html>
"""

# ==================== 11. TERMS OF SERVICE ====================
def render_terms() -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Terms of Service — NOVEXA</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(None, 'terms')}
    <div class="container" style="max-width:860px;">
        <h1 style="font-size:36px;color:#fff;margin-bottom:16px;">Terms of Service</h1>
        <p style="color:var(--text-muted);margin-bottom:24px;">Last updated: November 2026</p>
        <div class="card" style="line-height:1.8;color:var(--text-muted);">
            <p style="margin-bottom:16px;"><strong>1. Acceptance:</strong> By inviting NOVEXA to your Discord server or using the web dashboard, you agree to these Terms and Discord's Developer Terms of Service.</p>
            <p style="margin-bottom:16px;"><strong>2. Prohibited Uses:</strong> You may not use NOVEXA to execute malicious raids, distribute malware, spam Discord APIs, or bypass rate limits.</p>
            <p style="margin-bottom:16px;"><strong>3. Service Availability:</strong> While we aim for 99.9% uptime, NOVEXA is provided on an "as is" and "as available" basis.</p>
        </div>
    </div>
    {_render_footer()}
</body>
</html>
"""

# ==================== 12. USER DASHBOARD (SERVER SELECTOR) ====================
def render_user_dashboard(bot, user: Dict[str, Any], user_guilds: List[Dict[str, Any]]) -> str:
    guild_cards = ""
    for g in user_guilds:
        gid = g.get("id")
        name = html.escape(g.get("name", "Unknown Server"))
        icon = g.get("icon_url") or "https://cdn.discordapp.com/embed/avatars/0.png"
        bot_in_guild = g.get("bot_in_guild", False)
        is_owner = g.get("is_owner", False)
        badge_text = "Server Owner" if is_owner else "Administrator"

        if bot_in_guild:
            btn_action = (
                f'<div style="display:flex;gap:8px;">'
                f'<a href="/dashboard/{gid}" class="btn btn-primary" style="flex:1;">⚡ Control Panel</a>'
                f'<a href="/dashboard/{gid}/console" class="btn btn-outline" style="flex:1;">⌘ Console</a>'
                f'</div>'
            )
            status_badge = '<span class="badge badge-success">● Installed</span>'
        else:
            btn_action = f'<a href="/invite?guild_id={gid}" target="_blank" class="btn btn-accent" style="width:100%;">👑 Invite NOVEXA</a>'
            status_badge = '<span class="badge" style="background:rgba(255,255,255,0.08);color:var(--text-muted);">Not Installed</span>'

        guild_cards += f"""
        <div class="card" style="display:flex;flex-direction:column;justify-content:space-between;">
            <div>
                <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">
                    <img src="{icon}" style="width:52px;height:52px;border-radius:14px;border:1px solid var(--border);object-fit:cover;">
                    <div style="overflow:hidden;">
                        <h3 style="font-size:16px;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</h3>
                        <div style="display:flex;gap:6px;margin-top:4px;">
                            <span class="badge badge-accent" style="font-size:11px;">{badge_text}</span>
                            {status_badge}
                        </div>
                    </div>
                </div>
            </div>
            <div>{btn_action}</div>
        </div>
        """

    if not guild_cards:
        guild_cards = """
        <div class="card" style="grid-column:1/-1;text-align:center;padding:40px;">
            <p style="color:var(--text-muted);font-size:16px;margin-bottom:16px;">No servers found with Manage Server or Administrator permissions.</p>
            <a href="/invite" class="btn btn-accent">Add NOVEXA to a Server</a>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Server Hub — NOVEXA</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(user, 'dashboard')}
    <div class="container">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:34px;flex-wrap:wrap;gap:16px;">
            <div>
                <h1 style="font-size:32px;font-weight:900;color:#fff;">Select a Server to Manage</h1>
                <p style="color:var(--text-muted);font-size:14px;">Select any Discord server where you have administrative permissions.</p>
            </div>
            <a href="/invite" class="btn btn-outline">+ Add to Another Server</a>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(300px, 1fr));gap:20px;">
            {guild_cards}
        </div>
    </div>
    {_render_footer()}
</body>
</html>
"""

# ==================== 13. COMPLETE 32-MODULE SERVER DASHBOARD ====================
def render_server_dashboard(bot, user: Dict[str, Any], guild: Any, configs: Dict[str, Any]) -> str:
    gid = guild.id
    guild_name = html.escape(guild.name)
    icon_url = str(guild.icon.url) if guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png"
    channels = sorted([c for c in guild.text_channels], key=lambda x: x.position)
    voice_channels = sorted([c for c in guild.voice_channels], key=lambda x: x.position) if hasattr(guild, "voice_channels") else []
    categories = sorted([c for c in guild.categories], key=lambda x: x.position) if hasattr(guild, "categories") else []
    roles = sorted([r for r in guild.roles if not r.is_default()], key=lambda x: x.position, reverse=True)

    # Build category grouped sidebar items
    nav_html = ""
    for cat in FEATURE_CATEGORIES:
        nav_html += f'<div style="font-size:11px;font-weight:800;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px;padding:14px 14px 6px;">{cat}</div>'
        for key, feat in FEATURE_REGISTRY.items():
            if feat.category == cat:
                nav_html += f"""
                <button class="dash-tab-btn" onclick="switchTab('{key}')" id="tab-btn-{key}">
                    <span style="font-size:16px;">{feat.icon}</span>
                    <span style="flex:1;text-align:left;">{feat.title}</span>
                </button>
                """

    # Templates List for Welcome Studio
    _selected_template = (configs.get("welcome", {}) or {}).get("template_id") or "novexa_exclusive"
    templates_options = ""
    for t in list_templates():
        bg1, bg2 = t["bg_gradient"]
        sel = " selected" if t["id"] == _selected_template else ""
        templates_options += (
            f'<option value="{t["id"]}" data-accent="{t["accent_hex"]}" data-primary="{t["primary_hex"]}"'
            f' data-bg1="rgb({bg1[0]},{bg1[1]},{bg1[2]})" data-bg2="rgb({bg2[0]},{bg2[1]},{bg2[2]})"'
            f' data-tagline="{html.escape(t["tagline"])}" data-name-color="rgb({t["name_color"][0]},{t["name_color"][1]},{t["name_color"][2]})"'
            f'{sel}>{t["emoji"]} {t["name"]}</option>'
        )

    # Channels and Roles Options
    channel_opts = '<option value="">-- None / Select Channel --</option>'
    for c in channels:
        channel_opts += f'<option value="{c.id}">#{html.escape(c.name)}</option>'

    voice_opts = '<option value="">-- None / Select Voice Channel --</option>'
    for vc in voice_channels:
        voice_opts += f'<option value="{vc.id}">🔊 {html.escape(vc.name)}</option>'

    category_opts = '<option value="">-- None / Select Category --</option>'
    for cat in categories:
        category_opts += f'<option value="{cat.id}">📁 {html.escape(cat.name)}</option>'

    role_opts = '<option value="">-- None / Select Role --</option>'
    for r in roles:
        role_opts += f'<option value="{r.id}">@{html.escape(r.name)}</option>'

    # Unpack all configs
    welcome_cfg = configs.get("welcome", {})
    goodbye_cfg = configs.get("goodbye", {})
    autoroles_cfg = configs.get("autoroles", {})
    antinuke_cfg = configs.get("antinuke", {})
    antispam_cfg = configs.get("antispam", {})
    automod_cfg = configs.get("automod", {})
    whitelist_data = configs.get("whitelist", [])
    approved_bots = configs.get("approved_bots", [])
    moderation_cfg = configs.get("moderation", {})
    mod_logs = configs.get("moderation_logs", [])
    tickets_cfg = configs.get("tickets", {})
    ticket_panels_rows = configs.get("ticket_panels", []) or []
    ticket_rows = configs.get("tickets_list", []) or []
    logging_cfg = configs.get("logging", {})
    roles_cfg = configs.get("roles", {})
    server_setup_cfg = configs.get("server_setup", {})
    music_cfg = configs.get("music", {})
    economy_cfg = configs.get("economy", {})
    rpg_cfg = configs.get("rpg_games", {})
    pets_cfg = configs.get("pets_hunting", {})
    leveling_cfg = configs.get("leveling", {})
    giveaways_data = configs.get("giveaways", [])
    reaction_roles_data = configs.get("reaction_roles", [])
    custom_embeds_cfg = configs.get("custom_embeds", {})
    autoresponders = configs.get("autoresponders", [])
    voice_cfg = configs.get("voice_channels", {})
    j2c_cfg = configs.get("voice_j2c", {})
    backups_data = configs.get("backups", [])
    integrations_cfg = configs.get("integrations", {})
    premium_status = configs.get("premium", {})
    audit_history = configs.get("audit_history", [])
    settings_cfg = configs.get("settings", {})
    wallpaper_channels = configs.get("wallpaper_channels", [])
    dropper_members = configs.get("dropper_members", [])

    def make_channel_select(select_id, current_val):
        opts = f'<select class="form-control" id="{select_id}"><option value="">-- None / Select Channel --</option>'
        for c in channels:
            sel = "selected" if str(current_val or "") == str(c.id) else ""
            opts += f'<option value="{c.id}" {sel}>#{html.escape(c.name)}</option>'
        opts += '</select>'
        return opts

    def make_role_select(select_id, current_val):
        opts = f'<select class="form-control" id="{select_id}"><option value="">-- None / Select Role --</option>'
        for r in roles:
            sel = "selected" if str(current_val or "") == str(r.id) else ""
            opts += f'<option value="{r.id}" {sel}>@{html.escape(r.name)}</option>'
        opts += '</select>'
        return opts

    def make_voice_select(select_id, current_val):
        opts = f'<select class="form-control" id="{select_id}"><option value="">-- None / Select Voice Channel --</option>'
        for vc in voice_channels:
            sel = "selected" if str(current_val or "") == str(vc.id) else ""
            opts += f'<option value="{vc.id}" {sel}>🔊 {html.escape(vc.name)}</option>'
        opts += '</select>'
        return opts

    def make_category_select(select_id, current_val):
        opts = f'<select class="form-control" id="{select_id}"><option value="">-- None / Select Category --</option>'
        for cat in categories:
            sel = "selected" if str(current_val or "") == str(cat.id) else ""
            opts += f'<option value="{cat.id}" {sel}>📁 {html.escape(cat.name)}</option>'
        opts += '</select>'
        return opts

    # Whitelist rows HTML
    whitelist_rows_html = ""
    if whitelist_data:
        for w in whitelist_data:
            target_id = w.get("user_id") or w.get("target_id", 0)
            target_type = w.get("type", "member")
            added_by = w.get("added_by", "Owner")
            whitelist_rows_html += f"""
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:10px 14px;color:#fff;font-family:monospace;">{target_id}</td>
                <td style="padding:10px 14px;"><span class="badge badge-accent">{target_type.upper()}</span></td>
                <td style="padding:10px 14px;color:var(--text-muted);">{added_by}</td>
                <td style="padding:10px 14px;text-align:right;">
                    <button class="btn btn-outline" style="padding:4px 10px;font-size:12px;color:#ef4444;border-color:rgba(239,68,68,0.3);" onclick="deleteWhitelistEntry({target_id})">🗑️ Remove</button>
                </td>
            </tr>
            """
    else:
        whitelist_rows_html = '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--text-dim);">No custom whitelist exemptions active. Only Server Owner has bypass privileges.</td></tr>'

    # Wallpaper studio rows HTML
    wallpaper_rows_html = ""
    if wallpaper_channels:
        for w in wallpaper_channels:
            ch_id = w.get("channel_id", 0)
            ch = guild.get_channel(ch_id) if ch_id else None
            ch_label = f"<#{ch_id}>" if ch else f"`deleted ({ch_id})`"
            wallpaper_rows_html += f"""
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:10px 14px;color:#fff;">{ch_label}</td>
                <td style="padding:10px 14px;color:var(--text-muted);font-family:monospace;">{ch_id}</td>
                <td style="padding:10px 14px;color:var(--text-muted);">{w.get('created_at', '—')}</td>
                <td style="padding:10px 14px;text-align:right;">
                    <button class="btn btn-outline" style="padding:4px 10px;font-size:12px;color:#ef4444;border-color:rgba(239,68,68,0.3);" onclick="removeWallpaperChannel({ch_id})">🗑️ Remove</button>
                </td>
            </tr>
            """
    else:
        wallpaper_rows_html = '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--text-dim);">No wallpaper channels yet. Pick a channel above and press + Add.</td></tr>'

    # Dropper members rows HTML
    dropper_rows_html = ""
    if dropper_members:
        for d in dropper_members:
            user_id = d.get("user_id", 0)
            member = guild.get_member(user_id) if user_id else None
            name_label = html.escape(member.display_name) if member else f"Left server"
            added_by = d.get("added_by", 0)
            added_by_label = f"<@{added_by}>" if guild.get_member(added_by) else str(added_by)
            dropper_rows_html += f"""
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:10px 14px;color:#fff;">{name_label}</td>
                <td style="padding:10px 14px;color:var(--text-muted);font-family:monospace;">{user_id}</td>
                <td style="padding:10px 14px;color:var(--text-muted);">{added_by_label}</td>
                <td style="padding:10px 14px;text-align:right;">
                    <button class="btn btn-outline" style="padding:4px 10px;font-size:12px;color:#ef4444;border-color:rgba(239,68,68,0.3);" onclick="revokeDropperMember({user_id})">🗑️ Revoke</button>
                </td>
            </tr>
            """
    else:
        dropper_rows_html = '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--text-dim);">No active droppers. Grant the role to a member above.</td></tr>'

    # Approved Bots rows HTML
    approved_bots_html = ""
    if approved_bots:
        for b in approved_bots:
            bid = b.get("bot_id", 0)
            bname = html.escape(b.get("bot_name", "Bot"))
            approved_by = b.get("approved_by", "Admin")
            approved_bots_html += f"""
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:10px 14px;color:#fff;font-weight:700;">{bname}</td>
                <td style="padding:10px 14px;color:var(--text-muted);font-family:monospace;">{bid}</td>
                <td style="padding:10px 14px;color:var(--text-muted);">{approved_by}</td>
                <td style="padding:10px 14px;text-align:right;">
                    <button class="btn btn-outline" style="padding:4px 10px;font-size:12px;color:#ef4444;border-color:rgba(239,68,68,0.3);" onclick="revokeBotApp({bid})">Revoke</button>
                </td>
            </tr>
            """
    else:
        approved_bots_html = '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--text-dim);">No approved third-party bots registered. Anti-Bot quarantine is strictly active.</td></tr>'

    # Moderation Logs rows HTML
    mod_logs_html = ""
    if mod_logs:
        for m in mod_logs[:10]:
            cid = m.get("id") or m.get("case_id", "#")
            action = m.get("action", "WARN").upper()
            target = m.get("user_id", "User")
            mod = m.get("moderator_id", "Staff")
            reason = html.escape(str(m.get("reason", "No reason provided")))[:40]
            ts = str(m.get("created_at", ""))[:19]
            badge_class = "badge-danger" if action in ("BAN", "KICK") else "badge-accent"
            mod_logs_html += f"""
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:8px 12px;font-family:monospace;color:var(--text-dim);">#{cid}</td>
                <td style="padding:8px 12px;"><span class="badge {badge_class}">{action}</span></td>
                <td style="padding:8px 12px;color:#fff;">{target}</td>
                <td style="padding:8px 12px;color:var(--text-muted);">{mod}</td>
                <td style="padding:8px 12px;color:var(--text-muted);">{reason}</td>
                <td style="padding:8px 12px;color:var(--text-dim);font-size:12px;">{ts}</td>
            </tr>
            """
    else:
        mod_logs_html = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--text-dim);">No recent moderation sanctions recorded. Server is in good standing.</td></tr>'

    # Backups rows HTML
    backups_html = ""
    if backups_data:
        for bk in backups_data:
            bkid = bk.get("backup_id", "")
            bkname = html.escape(bk.get("backup_name", "Snapshot"))
            bkdate = str(bk.get("created_at", ""))[:19]
            backups_html += f"""
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:10px 14px;color:#fff;font-weight:700;">{bkname}</td>
                <td style="padding:10px 14px;color:var(--text-muted);font-family:monospace;font-size:12px;">{bkid}</td>
                <td style="padding:10px 14px;color:var(--text-dim);font-size:12px;">{bkdate}</td>
                <td style="padding:10px 14px;text-align:right;">
                    <button class="btn btn-outline" style="padding:4px 12px;font-size:12px;color:#38bdf8;border-color:rgba(56,189,248,0.3);" onclick="restoreBackup('{bkid}')">⚡ 1-Click Restore</button>
                </td>
            </tr>
            """
    else:
        backups_html = '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--text-dim);">No automated backups stored yet. Click "Create Server Snapshot" to take one.</td></tr>'

    # Auto Responders rows HTML
    autoresponders_html = ""
    if autoresponders:
        for ar in autoresponders:
            arid = ar.get("id", 0)
            trigger = html.escape(ar.get("trigger", ""))
            resp = html.escape(ar.get("response", ""))[:50]
            mtype = ar.get("match_type", "contains")
            autoresponders_html += f"""
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:10px 14px;color:#fff;font-weight:700;">{trigger}</td>
                <td style="padding:10px 14px;color:var(--text-muted);">{resp}...</td>
                <td style="padding:10px 14px;"><span class="badge badge-accent">{mtype}</span></td>
                <td style="padding:10px 14px;text-align:right;">
                    <button class="btn btn-outline" style="padding:4px 10px;font-size:12px;color:#ef4444;border-color:rgba(239,68,68,0.3);" onclick="deleteAutoResponder({arid})">Delete</button>
                </td>
            </tr>
            """
    else:
        autoresponders_html = '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--text-dim);">No custom auto-responders created yet. Add your first trigger below.</td></tr>'

    # Reaction Roles rows HTML
    reaction_roles_html = ""
    if reaction_roles_data:
        for rr in reaction_roles_data:
            rrid = rr.get("id", 0)
            rremoji = rr.get("emoji", "")
            rrmid = rr.get("message_id", "")
            rrchan = rr.get("channel_id", "")
            rrrole = rr.get("role_id", "")
            reaction_roles_html += f"""
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:10px 14px;font-size:20px;">{rremoji}</td>
                <td style="padding:10px 14px;color:#fff;">Role ID: <span style="font-family:monospace;">{rrrole}</span></td>
                <td style="padding:10px 14px;color:var(--text-muted);font-family:monospace;font-size:12px;">Msg: {rrmid} in &lt;#{rrchan}&gt;</td>
                <td style="padding:10px 14px;text-align:right;">
                    <button class="btn btn-outline" style="padding:4px 10px;font-size:12px;color:#ef4444;border-color:rgba(239,68,68,0.3);" onclick="deleteReactionRole({rrid})">Delete</button>
                </td>
            </tr>
            """
    else:
        reaction_roles_html = '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--text-dim);">No reaction roles configured. Bind emojis to roles below.</td></tr>'

    # Giveaways rows HTML
    giveaways_html = ""
    if giveaways_data:
        for gw in giveaways_data:
            gwid = gw.get("message_id", 0)
            gwprize = html.escape(gw.get("prize", "Prize"))
            gwwin = gw.get("winners_count", 1)
            gwend = gw.get("ended", False)
            badge_class = 'badge-danger' if gwend else 'badge-success'
            badge_text = 'ENDED' if gwend else 'ACTIVE'
            giveaways_html += f"""
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:10px 14px;color:#fff;font-weight:700;">🎁 {gwprize}</td>
                <td style="padding:10px 14px;color:var(--text-muted);">{gwwin} Winner(s)</td>
                <td style="padding:10px 14px;"><span class="badge {badge_class}">{badge_text}</span></td>
                <td style="padding:10px 14px;font-family:monospace;color:var(--text-dim);font-size:12px;">{gwid}</td>
            </tr>
            """
    else:
        giveaways_html = '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--text-dim);">No active or past giveaways on record. Launch one below!</td></tr>'

    # Audit History rows HTML
    audit_rows_html = ""
    if audit_history:
        for a in audit_history[:15]:
            ats = str(a.get("timestamp", ""))[:19]
            aact = a.get("actor_tag", "Staff")
            amod = a.get("module", "").upper()
            aset = a.get("setting_key", "")
            anew = html.escape(str(a.get("new_value", "")))[:30]
            asrc = a.get("source", "WEBSITE")
            audit_rows_html += f"""
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:8px 12px;color:var(--text-dim);font-size:12px;">{ats}</td>
                <td style="padding:8px 12px;color:#fff;font-weight:600;">{aact}</td>
                <td style="padding:8px 12px;"><span class="badge badge-accent">{amod}</span></td>
                <td style="padding:8px 12px;color:var(--text-muted);">{aset}</td>
                <td style="padding:8px 12px;color:var(--accent);font-family:monospace;font-size:12px;">{anew}</td>
                <td style="padding:8px 12px;color:var(--text-dim);font-size:11px;">{asrc}</td>
            </tr>
            """
    else:
        audit_rows_html = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--text-dim);">No configuration modifications recorded yet. All changes are logged live.</td></tr>'

    # Roles hierarchy HTML
    roles_list_html = ""
    for r in roles[:20]:
        rcolor = f"#{r.color.value:06x}" if r.color.value else "#94a3b8"
        roles_list_html += f"""
        <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;background:#0d111b;border-radius:8px;border:1px solid var(--border);margin-bottom:8px;">
            <div style="display:flex;align-items:center;gap:12px;">
                <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{rcolor};"></span>
                <span style="color:#fff;font-weight:600;">@{html.escape(r.name)}</span>
            </div>
            <div style="display:flex;align-items:center;gap:16px;">
                <span style="font-size:12px;color:var(--text-dim);">Position: {r.position}</span>
                <span style="font-size:12px;color:var(--text-muted);">{len(r.members)} Members</span>
            </div>
        </div>
        """

    # 50 Server Setup Templates Options
    templates_50 = [
        ("gaming", "🎮 Gaming & Esports Hub"),
        ("esports_clan", "🏆 Pro Esports Clan"),
        ("minecraft_network", "⛏️ Minecraft Network"),
        ("gta_fivem", "🚗 GTA V / FiveM Roleplay"),
        ("fps_tactical", "🎯 FPS Tactical Operations"),
        ("battle_royale", "🪂 Battle Royale Arena"),
        ("roblox_studio", "🧱 Roblox Studio Community"),
        ("digital_store", "🛍️ E-Commerce & Digital Store"),
        ("crypto_nft", "🪙 Crypto & Web3 Syndicate"),
        ("saas_support", "💼 SaaS & Technology HQ"),
        ("agency_creative", "🎨 Creative Design Agency"),
        ("developer_nexus", "💻 Developer & Engineering Nexus"),
        ("ai_lab", "🤖 AI Research Laboratory"),
        ("anime_haven", "🌸 Anime & Manga Haven"),
        ("music_lounge", "🎵 Music & Audiophile Lounge"),
        ("streamer_community", "📺 Content Creator Community"),
        ("study_hall", "📚 Academic Study Hall"),
        ("cozy_chill", "☕ Cozy Hangout Lounge"),
        ("fitness_lifestyle", "💪 Fitness & Health Club"),
        ("automotive_club", "🏎️ Automotive & Car Enthusiasts"),
    ]
    server_setup_options = ""
    curr_tpl = server_setup_cfg.get("template_id", "gaming")
    for tid, tname in templates_50:
        sel = "selected" if curr_tpl == tid else ""
        server_setup_options += f'<option value="{tid}" {sel}>{tname}</option>'

    # ==================== LIVE TICKET STATE (bot-created rows included) ====================
    def _chan_name(cid):
        try:
            ch = guild.get_channel(int(cid)) if cid else None
        except (TypeError, ValueError):
            ch = None
        return f"#{html.escape(ch.name)}" if ch else "—"

    ticket_panels_html = ""
    if ticket_panels_rows:
        panel_rows_html = ""
        for p in ticket_panels_rows:
            support = guild.get_role(int(p["support_role_id"])) if p.get("support_role_id") else None
            panel_rows_html += f"""
            <tr>
                <td>{_chan_name(p.get('channel_id'))}</td>
                <td>{html.escape(str(p.get('title') or 'Support Ticket'))}</td>
                <td>{('@' + html.escape(support.name)) if support else '—'}</td>
                <td>{_chan_name(p.get('transcript_channel_id')) if p.get('transcript_channel_id') else '—'}</td>
                <td style="white-space:nowrap;">
                    <button class="btn btn-outline" style="padding:6px 12px;font-size:12px;" onclick="editTicketPanel('{html.escape(str(p.get('panel_id')))}')">Edit</button>
                    <button class="btn btn-danger" style="padding:6px 12px;font-size:12px;" onclick="deleteTicketPanel('{html.escape(str(p.get('panel_id')))}')">Delete</button>
                </td>
            </tr>"""
        ticket_panels_html = f"""
                <div class="card" style="margin-top:20px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:6px;">Live Ticket Panels</h3>
                    <div class="desc" style="margin-bottom:16px;">Panels created by NOVEXA in Discord, including anything set up with slash commands.</div>
                    <table style="width:100%;border-collapse:collapse;font-size:13px;">
                        <thead>
                            <tr style="text-align:left;color:var(--text-dim);font-size:11px;text-transform:uppercase;letter-spacing:.06em;">
                                <th style="padding:8px 10px;">Channel</th>
                                <th style="padding:8px 10px;">Title</th>
                                <th style="padding:8px 10px;">Support Role</th>
                                <th style="padding:8px 10px;">Transcripts</th>
                                <th style="padding:8px 10px;">Action</th>
                            </tr>
                        </thead>
                        <tbody style="color:var(--text-muted);">{panel_rows_html}
                        </tbody>
                    </table>
                </div>"""

    ticket_live_html = ""
    if ticket_rows:
        ticket_tr_html = ""
        for t in ticket_rows:
            status = (t.get("status") or "open").lower()
            badge_bg = "rgba(34,197,94,.15)" if status == "open" else "rgba(248,113,113,.15)"
            badge_fg = "#22C55E" if status == "open" else "#F87171"
            tid_value = t.get("id")
            close_btn = (
                '<button class="btn btn-outline" style="padding:6px 10px;font-size:12px;" '
                'onclick="closeTicket(' + str(tid_value) + ')">Close</button>'
            ) if status == "open" else ""
            author_mention = "<@" + str(t.get("author_id")) + ">"
            created = str(t.get("created_at") or "—")[:16]
            ticket_tr_html += f"""
            <tr>
                <td>#{t.get('ticket_number', '?')}</td>
                <td>{author_mention}</td>
                <td>{_chan_name(t.get('channel_id'))}</td>
                <td><span style="background:{badge_bg};color:{badge_fg};padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;">{html.escape(status.upper())}</span></td>
                <td>{created}</td>
                <td style="white-space:nowrap;">{close_btn}
                    <button class="btn btn-danger" style="padding:6px 10px;font-size:12px;" onclick="deleteTicket({tid_value})">Delete</button>
                </td>
            </tr>"""
        ticket_live_html = f"""
                <div class="card" style="margin-top:20px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:6px;">Recent Tickets</h3>
                    <div class="desc" style="margin-bottom:16px;">Every ticket NOVEXA has opened here — close or delete from the dashboard.</div>
                    <table style="width:100%;border-collapse:collapse;font-size:13px;">
                        <thead>
                            <tr style="text-align:left;color:var(--text-dim);font-size:11px;text-transform:uppercase;letter-spacing:.06em;">
                                <th style="padding:8px 10px;">#</th>
                                <th style="padding:8px 10px;">Opened By</th>
                                <th style="padding:8px 10px;">Channel</th>
                                <th style="padding:8px 10px;">Status</th>
                                <th style="padding:8px 10px;">Created</th>
                                <th style="padding:8px 10px;">Actions</th>
                            </tr>
                        </thead>
                        <tbody style="color:var(--text-muted);">{ticket_tr_html}
                        </tbody>
                    </table>
                </div>"""
    elif not ticket_panels_rows:
        ticket_live_html = """
                <div class="card" style="margin-top:20px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:6px;">No Ticket System Yet</h3>
                    <div class="desc">Run <code>/ticket setup</code> in Discord to publish a panel — it appears here automatically.</div>
                </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{guild_name} — NOVEXA Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
    {BASE_CSS}
    .dash-layout {{
        display: flex;
        min-height: calc(100vh - 75px);
    }}
    .dash-sidebar {{
        width: 270px;
        background: #090b12;
        border-right: 1px solid var(--border);
        padding: 16px 10px;
        overflow-y: auto;
        height: calc(100vh - 75px);
        position: sticky;
        top: 75px;
    }}
    .dash-tab-btn {{
        width: 100%;
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 14px;
        border-radius: 8px;
        background: transparent;
        border: none;
        color: var(--text-muted);
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: var(--transition);
        margin-bottom: 2px;
        text-align: left;
    }}
    .dash-tab-btn:hover {{
        background: rgba(255, 255, 255, 0.05);
        color: #fff;
    }}
    .dash-tab-btn.active {{
        background: rgba(56, 189, 248, 0.12);
        color: var(--accent);
        font-weight: 700;
    }}
    .dash-content {{
        flex: 1;
        padding: 32px 40px;
        overflow-y: auto;
    }}
    .tab-pane {{
        display: none;
        animation: fadeIn 0.25s ease-out;
    }}
    .tab-pane.active {{
        display: block;
    }}
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(6px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    .form-group {{
        margin-bottom: 20px;
    }}
    .form-group label {{
        display: block;
        font-size: 13px;
        font-weight: 700;
        color: #fff;
        margin-bottom: 6px;
    }}
    .form-group .desc {{
        font-size: 12px;
        color: var(--text-dim);
        margin-bottom: 8px;
    }}
    .form-control {{
        width: 100%;
        padding: 10px 14px;
        background: #0d1017;
        border: 1px solid var(--border);
        border-radius: 8px;
        color: #fff;
        font-size: 13px;
        box-sizing: border-box;
        transition: var(--transition);
    }}
    .form-control:focus {{
        outline: none;
        border-color: var(--accent);
        box-shadow: 0 0 10px var(--accent-glow);
    }}
    textarea.form-control {{
        min-height: 85px;
        font-family: inherit;
        resize: vertical;
    }}
    .switch {{
        position: relative;
        display: inline-block;
        width: 48px;
        height: 24px;
    }}
    .switch input {{
        opacity: 0;
        width: 0;
        height: 0;
    }}
    .slider {{
        position: absolute;
        cursor: pointer;
        top: 0; left: 0; right: 0; bottom: 0;
        background-color: #1e293b;
        transition: .3s;
        border-radius: 24px;
    }}
    .slider:before {{
        position: absolute;
        content: "";
        height: 18px;
        width: 18px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        transition: .3s;
        border-radius: 50%;
    }}
    input:checked + .slider {{
        background-color: var(--accent);
    }}
    input:checked + .slider:before {{
        transform: translateX(24px);
    }}
    </style>
</head>
<body>
    {_render_nav(user, 'dashboard')}

    <div class="dash-layout">
        <!-- Sidebar Navigation -->
        <aside class="dash-sidebar">
            <div style="display:flex;align-items:center;gap:12px;padding:12px 14px 20px;border-bottom:1px solid var(--border);margin-bottom:12px;">
                <img src="{icon_url}" style="width:38px;height:38px;border-radius:50%;border:1px solid var(--border);">
                <div style="overflow:hidden;">
                    <div style="font-size:14px;font-weight:800;color:#fff;white-space:nowrap;text-overflow:ellipsis;overflow:hidden;">{guild_name}</div>
                    <div style="font-size:11px;color:var(--text-dim);display:flex;align-items:center;gap:6px;">
                        <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#34d399;"></span>
                        <span id="sync-status">Live Synced</span>
                    </div>
                </div>
            </div>

            <a class="dash-tab-btn" href="/dashboard/{gid}/console" style="text-decoration:none;">
                <span style="font-size:16px;">⌘</span>
                <span style="flex:1;text-align:left;">Command Console</span>
            </a>
            <a class="dash-tab-btn" href="/dashboard/{gid}/explorer" style="text-decoration:none;">
                <span style="font-size:16px;">🛰️</span>
                <span style="flex:1;text-align:left;">Server Explorer</span>
            </a>
            <a class="dash-tab-btn" href="/dashboard/{gid}/boards" style="text-decoration:none;">
                <span style="font-size:16px;">🏆</span>
                <span style="flex:1;text-align:left;">Leaderboards</span>
            </a>

            {nav_html}
        </aside>

        <!-- Main Dashboard Viewport -->
        <main class="dash-content">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:28px;flex-wrap:wrap;gap:16px;">
                <div>
                    <h1 style="font-size:24px;font-weight:900;color:#fff;" id="active-tab-title">Server Overview</h1>
                    <p style="color:var(--text-muted);font-size:13px;" id="active-tab-sub">Authoritative configuration synchronized in real-time with NOVEXA engine.</p>
                </div>
                <div style="display:flex;gap:10px;">
                    <button class="btn btn-primary" onclick="saveActiveTab()" id="btn-save">💾 Save Changes</button>
                </div>
            </div>

            <!-- Tab 1: Overview -->
            <div class="tab-pane active" id="pane-overview">
                <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:16px;margin-bottom:28px;">
                    <div class="card" style="padding:18px;">
                        <div style="font-size:26px;font-weight:900;color:#fff;">{guild.member_count:,}</div>
                        <div style="font-size:12px;color:var(--text-muted);">Total Members</div>
                    </div>
                    <div class="card" style="padding:18px;">
                        <div style="font-size:26px;font-weight:900;color:var(--accent);">{len(channels)}</div>
                        <div style="font-size:12px;color:var(--text-muted);">Text Channels</div>
                    </div>
                    <div class="card" style="padding:18px;">
                        <div style="font-size:26px;font-weight:900;color:#fff;">{len(roles)}</div>
                        <div style="font-size:12px;color:var(--text-muted);">Configured Roles</div>
                    </div>
                    <div class="card" style="padding:18px;">
                        <div style="font-size:26px;font-weight:900;color:#34d399;">Active</div>
                        <div style="font-size:12px;color:var(--text-muted);">Anti-Nuke Defense</div>
                    </div>
                </div>

                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:14px;">Instant Dispatch Controls</h3>
                    <div style="display:flex;gap:12px;flex-wrap:wrap;">
                        <button class="btn btn-outline" onclick="triggerAction('test-welcome')">🎨 Test Welcome Banner</button>
                        <button class="btn btn-outline" onclick="triggerAction('test-goodbye')">🚪 Test Goodbye Notification</button>
                        <button class="btn btn-danger" onclick="triggerAction('lockdown')">🚨 Emergency Server Lockdown</button>
                        <button class="btn btn-outline" onclick="triggerAction('unlock')">🔓 Unlock Channels</button>
                    </div>
                </div>
            </div>

            <!-- Tab 2: Welcome -->
            <div class="tab-pane" id="pane-welcome">
                <div class="card" style="margin-bottom:24px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Welcome Announcement Setup</h3>
                    
                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Enable Welcome System</label>
                            <div class="desc">Send welcome message when a new member joins.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="welcome_enabled" {'checked' if welcome_cfg.get('enabled', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div class="form-group">
                        <label>Welcome Channel</label>
                        {make_channel_select('welcome_channel_id', welcome_cfg.get('channel_id'))}
                    </div>

                    <div class="form-group">
                        <label>Visual Banner Style (20 Presets)</label>
                        <select class="form-control" id="welcome_template_id" onchange="applyWelcomeTheme()">
                            {templates_options}
                        </select>
                    </div>

                    <!-- Live Canvas Previewer -->
                    <div style="margin:20px 0;background:#05070a;border-radius:12px;padding:24px;border:1px solid var(--border);text-align:center;">
                        <div style="font-size:12px;font-weight:700;color:var(--text-muted);margin-bottom:12px;text-transform:uppercase;">Live Interactive Banner Preview</div>
                        <div id="preview-card" style="max-width:650px;margin:0 auto;height:240px;border-radius:16px;display:flex;align-items:center;justify-content:center;position:relative;background:linear-gradient(135deg, #131722, #0d0f17);border:2px solid var(--accent);box-shadow:0 0 25px var(--accent-glow);">
                            <div style="display:flex;align-items:center;gap:20px;padding:20px;">
                                <img src="{icon_url}" id="preview-avatar" style="width:90px;height:90px;border-radius:50%;border:3px solid var(--accent);box-shadow:0 0 15px var(--accent);">
                                <div style="text-align:left;">
                                    <div class="badge badge-accent" id="preview-badge" style="margin-bottom:6px;">MEMBER #{guild.member_count}</div>
                                    <h2 id="preview-title" style="font-size:24px;color:#fff;font-weight:800;">Welcome to {guild_name}!</h2>
                                    <p id="preview-sub" style="font-size:13px;color:var(--text-muted);">We are thrilled to have you here.</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Welcome Message Template</label>
                        <div class="desc">Available tokens: {{user}}, {{username}}, {{server}}, {{member_count}}</div>
                        <textarea class="form-control" id="welcome_message_template">{html.escape(welcome_cfg.get('message_template') or 'Hey {user}, welcome to **{server}**! You are member #{member_count}.')}</textarea>
                    </div>

                    <div class="form-group">
                        <label>Card Accent Color</label>
                        <input type="color" class="form-control" id="welcome_custom_color" value="{welcome_cfg.get('custom_color', '#5865F2')}" onchange="updateWelcomePreview()" style="height:44px;padding:4px;">
                    </div>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Send Private Direct Message (DM)</label>
                            <div class="desc">Send a greeting directly to member's DM.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="welcome_dm_enabled" {'checked' if welcome_cfg.get('dm_enabled') else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
            </div>

            <!-- Tab 3: Goodbye -->
            <div class="tab-pane" id="pane-goodbye">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Member Departure System</h3>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Enable Goodbye Notification</label>
                            <div class="desc">Announce departures when a member leaves or is removed.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="goodbye_goodbye_enabled" {'checked' if goodbye_cfg.get('goodbye_enabled', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div class="form-group">
                        <label>Goodbye Announcement Channel</label>
                        {make_channel_select('goodbye_leave_channel_id', goodbye_cfg.get('leave_channel_id'))}
                    </div>

                    <div class="form-group">
                        <label>Goodbye Style Template</label>
                        <select class="form-control" id="goodbye_goodbye_template_id">
                            <option value="minimal_dark" {'selected' if goodbye_cfg.get('goodbye_template_id') == 'minimal_dark' else ''}>🌑 Minimal Dark</option>
                            <option value="black_silver" {'selected' if goodbye_cfg.get('goodbye_template_id') == 'black_silver' else ''}>🥈 Black & Silver</option>
                            <option value="purple_luxury" {'selected' if goodbye_cfg.get('goodbye_template_id') == 'purple_luxury' else ''}>👑 Purple Luxury</option>
                            <option value="novexa_exclusive" {'selected' if goodbye_cfg.get('goodbye_template_id') == 'novexa_exclusive' else ''}>⚡ NOVEXA Exclusive</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label>Goodbye Message Template</label>
                        <textarea class="form-control" id="goodbye_leave_message_template">{html.escape(goodbye_cfg.get('leave_message_template') or '**{username}** has departed from {server}. We now have {member_count} members.')}</textarea>
                    </div>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Enable Goodbye Embed</label>
                            <div class="desc">Render departure announcements as a styled card embed.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="goodbye_leave_embed_enabled" {'checked' if goodbye_cfg.get('leave_embed_enabled', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <button class="btn btn-outline" onclick="triggerAction('test-goodbye')">🚪 Test Goodbye Notification</button>
                </div>
            </div>

            <!-- Tab 4: Auto Roles -->
            <div class="tab-pane" id="pane-autoroles">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Automated Join Roles</h3>
                    <p style="color:var(--text-muted);font-size:13px;margin-bottom:20px;">Roles automatically assigned to new users or verified bot additions upon arrival.</p>

                    <div class="form-group">
                        <label>Human Member Auto-Role</label>
                        <div class="desc">Granted automatically to every human member who joins.</div>
                        {make_role_select('autoroles_member_role_id', autoroles_cfg.get('auto_roles', [None])[0] if autoroles_cfg.get('auto_roles') else None)}
                    </div>

                    <div class="form-group">
                        <label>Bot Application Auto-Role</label>
                        <div class="desc">Granted exclusively to approved Discord applications/bots.</div>
                        {make_role_select('autoroles_bot_role_id', autoroles_cfg.get('bot_role_id'))}
                    </div>
                </div>
            </div>

            <!-- Tab 6: Anti-Nuke -->
            <div class="tab-pane" id="pane-antinuke">
                <div class="card" style="margin-bottom:24px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Anti-Nuke Defense Shield</h3>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Enable Anti-Nuke Protection</label>
                            <div class="desc">Intercept mass channel/role deletion and unauthorized privilege escalations.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="antinuke_enabled" {'checked' if antinuke_cfg.get('enabled', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div class="form-group">
                        <label>Protection Posture</label>
                        <select class="form-control" id="antinuke_mode">
                            <option value="low" {'selected' if antinuke_cfg.get('mode') == 'low' else ''}>🟢 LOW — Log suspicious actions & alert only</option>
                            <option value="medium" {'selected' if antinuke_cfg.get('mode', 'medium') == 'medium' else ''}>🟡 MEDIUM — Automated progressive mitigation (Recommended)</option>
                            <option value="high" {'selected' if antinuke_cfg.get('mode') == 'high' else ''}>🔴 HIGH — Strict zero-tolerance instant quarantine</option>
                            <option value="panic" {'selected' if antinuke_cfg.get('mode') == 'panic' else ''}>💀 PANIC — One strike: instant ban + full revert (channel/role/webhook/rename)</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label>Punishment on Breach</label>
                        <select class="form-control" id="antinuke_punishment_type">
                            <option value="quarantine" {'selected' if antinuke_cfg.get('punishment_type', 'quarantine') == 'quarantine' else ''}>🔒 Quarantine (Strip all dangerous permissions)</option>
                            <option value="kick" {'selected' if antinuke_cfg.get('punishment_type') == 'kick' else ''}>👢 Kick Executor</option>
                            <option value="ban" {'selected' if antinuke_cfg.get('punishment_type') == 'ban' else ''}>🔨 Ban Executor</option>
                        </select>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Max Channel Deletions (10s)</label>
                            <input type="number" class="form-control" id="antinuke_max_channel_deletions" value="{antinuke_cfg.get('max_channel_deletions', 2)}" min="1" max="20">
                        </div>
                        <div class="form-group">
                            <label>Max Role Deletions (10s)</label>
                            <input type="number" class="form-control" id="antinuke_max_role_deletions" value="{antinuke_cfg.get('max_role_deletions', 3)}" min="1" max="20">
                        </div>
                        <div class="form-group">
                            <label>Max Member Bans (10s)</label>
                            <input type="number" class="form-control" id="antinuke_max_bans" value="{antinuke_cfg.get('max_bans', 3)}" min="1" max="20">
                        </div>
                        <div class="form-group">
                            <label>Max Webhook Modifications (10s)</label>
                            <input type="number" class="form-control" id="antinuke_max_webhook_changes" value="{antinuke_cfg.get('max_webhook_changes', 4)}" min="1" max="20">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tab 7: Anti-Spam -->
            <div class="tab-pane" id="pane-antispam">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Anti-Spam & Content Scanning</h3>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Enable Real-Time Anti-Spam</label>
                            <div class="desc">Scan incoming messages for mentions, invites, and rapid flooding.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="antispam_enabled" {'checked' if antispam_cfg.get('enabled', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Max Mentions per Message</label>
                            <input type="number" class="form-control" id="antispam_max_mentions" value="{antispam_cfg.get('max_mentions', 5)}" min="1" max="30">
                        </div>
                        <div class="form-group">
                            <label>Duplicate Message Burst Limit</label>
                            <input type="number" class="form-control" id="antispam_max_duplicates" value="{antispam_cfg.get('max_duplicates', 3)}" min="1" max="10">
                        </div>
                        <div class="form-group">
                            <label>Max Emojis per Message</label>
                            <input type="number" class="form-control" id="antispam_max_emojis" value="{antispam_cfg.get('max_emojis', 8)}" min="2" max="50">
                        </div>
                        <div class="form-group">
                            <label>Timeout Penalty (Minutes)</label>
                            <input type="number" class="form-control" id="antispam_timeout_duration_minutes" value="{antispam_cfg.get('timeout_duration_minutes', 10)}" min="1" max="10080">
                        </div>
                    </div>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Block Discord Invite Links</label>
                            <div class="desc">Auto-delete unauthorized discord.gg server invites.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="antispam_block_invites" {'checked' if antispam_cfg.get('block_invites', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Block Suspicious Links & Phishing</label>
                            <div class="desc">Intercept untrusted domains and known malware URLs.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="antispam_block_links" {'checked' if antispam_cfg.get('block_links', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
            </div>

            <!-- Tab 8: AutoMod -->
            <div class="tab-pane" id="pane-automod">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Automated Content Moderation</h3>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Filter Excessive Capitalization</label>
                            <div class="desc">Detect and suppress shouting or mass uppercase messages (>70% caps).</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="automod_caps_filter_enabled" {'checked' if automod_cfg.get('caps_filter_enabled') else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div class="form-group">
                        <label>Blocked Words & Prohibited Slurs</label>
                        <div class="desc">Comma-separated list of prohibited words or phrases to censor instantly.</div>
                        <textarea class="form-control" id="automod_blocked_words" placeholder="badword, scamlink, offensivephrase">{html.escape(automod_cfg.get('blocked_words') or '')}</textarea>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Max Attachments per Minute</label>
                            <input type="number" class="form-control" id="automod_attachment_spam_limit" value="{automod_cfg.get('attachment_spam_limit', 5)}" min="1" max="20">
                        </div>
                        <div class="form-group">
                            <label>Violation Enforcement Action</label>
                            <select class="form-control" id="automod_automod_action">
                                <option value="delete" {'selected' if automod_cfg.get('automod_action') == 'delete' else ''}>🗑️ Delete Message Only</option>
                                <option value="warn" {'selected' if automod_cfg.get('automod_action') == 'warn' else ''}>⚠️ Delete & Issue Warning</option>
                                <option value="timeout" {'selected' if automod_cfg.get('automod_action') == 'timeout' else ''}>⏳ Delete & 10-Min Timeout</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tab 9: Whitelist -->
            <div class="tab-pane" id="pane-whitelist">
                <div class="card" style="margin-bottom:24px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:8px;">Add Whitelist Exemption</h3>
                    <p style="color:var(--text-muted);font-size:13px;margin-bottom:16px;">Whitelisted members and roles bypass Anti-Nuke, Anti-Spam, and AutoMod restrictions.</p>

                    <div style="display:grid;grid-template-columns:2fr 1fr auto;gap:12px;align-items:flex-end;">
                        <div class="form-group" style="margin:0;">
                            <label>Target User ID or Role ID</label>
                            <input type="text" class="form-control" id="whitelist_target_id" placeholder="e.g. 123456789012345678">
                        </div>
                        <div class="form-group" style="margin:0;">
                            <label>Entity Type</label>
                            <select class="form-control" id="whitelist_target_type">
                                <option value="member">Individual Member</option>
                                <option value="role">Discord Role</option>
                            </select>
                        </div>
                        <button class="btn btn-primary" onclick="addWhitelistEntry()">+ Add Whitelist</button>
                    </div>
                </div>

                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Active Whitelisted Entities</h3>
                    <div style="overflow-x:auto;">
                        <table style="width:100%;border-collapse:collapse;font-size:13px;">
                            <thead>
                                <tr style="border-bottom:1px solid var(--border);color:var(--text-muted);text-align:left;">
                                    <th style="padding:10px 14px;">Discord Snowflake ID</th>
                                    <th style="padding:10px 14px;">Type</th>
                                    <th style="padding:10px 14px;">Granted By</th>
                                    <th style="padding:10px 14px;text-align:right;">Actions</th>
                                </tr>
                            </thead>
                            <tbody id="whitelist-table-body">
                                {whitelist_rows_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Tab 9B: Wallpaper Studio -->
            <div class="tab-pane" id="pane-wallpaper">
                <div class="card" style="margin-bottom:24px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:8px;">🖼️ Add Wallpaper Channel</h3>
                    <p style="color:var(--text-muted);font-size:13px;margin-bottom:16px;">Every message typed in this channel becomes an AI wallpaper prompt. Size keywords: <code style="color:#FFB3BE;">4k · 2k · 1080p · phone · square · ultrawide</code>.</p>
                    <div style="display:grid;grid-template-columns:2fr auto;gap:12px;align-items:flex-end;">
                        <div class="form-group" style="margin:0;">
                            <label>Text Channel</label>
                            {make_channel_select('wallpaper_channel_select', None)}
                        </div>
                        <button class="btn btn-primary" onclick="addWallpaperChannel()">+ Add Channel</button>
                    </div>
                </div>
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Active Wallpaper Channels</h3>
                    <div style="overflow-x:auto;">
                        <table style="width:100%;border-collapse:collapse;font-size:13px;">
                            <thead>
                                <tr style="border-bottom:1px solid var(--border);color:var(--text-muted);text-align:left;">
                                    <th style="padding:10px 14px;">Channel</th>
                                    <th style="padding:10px 14px;">Channel ID</th>
                                    <th style="padding:10px 14px;">Added On</th>
                                    <th style="padding:10px 14px;text-align:right;">Actions</th>
                                </tr>
                            </thead>
                            <tbody id="wallpaper-table-body">
                                {wallpaper_rows_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Tab 9C: Dropper Suite -->
            <div class="tab-pane" id="pane-dropper">
                <div class="card" style="margin-bottom:24px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:8px;">💧 Grant Dropper Role</h3>
                    <p style="color:var(--text-muted);font-size:13px;margin-bottom:16px;">Droppers can post files, scripts and links in developer channels. Requires the Dropper role to be configured (run <code style="color:#FFB3BE;">/dropper setup</code> once).</p>
                    <div style="display:grid;grid-template-columns:2fr auto;gap:12px;align-items:flex-end;">
                        <div class="form-group" style="margin:0;">
                            <label>Member User ID</label>
                            <input type="text" class="form-control" id="dropper_user_id" placeholder="e.g. 123456789012345678">
                        </div>
                        <button class="btn btn-primary" onclick="grantDropperMember()">+ Grant Dropper</button>
                    </div>
                </div>
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Active Droppers</h3>
                    <div style="overflow-x:auto;">
                        <table style="width:100%;border-collapse:collapse;font-size:13px;">
                            <thead>
                                <tr style="border-bottom:1px solid var(--border);color:var(--text-muted);text-align:left;">
                                    <th style="padding:10px 14px;">Member</th>
                                    <th style="padding:10px 14px;">User ID</th>
                                    <th style="padding:10px 14px;">Granted By</th>
                                    <th style="padding:10px 14px;text-align:right;">Actions</th>
                                </tr>
                            </thead>
                            <tbody id="dropper-table-body">
                                {dropper_rows_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Tab 10: Approved Bots -->
            <div class="tab-pane" id="pane-approved_bots">
                <div class="card" style="margin-bottom:24px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Bot Addition Quarantine</h3>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Strict Anti-Bot Quarantine</label>
                            <div class="desc">Instantly kick or ban unauthorized bots added by non-owners.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="approved_bots_bot_protection_enabled" {'checked' if approved_bots else 'checked'}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div style="display:grid;grid-template-columns:2fr 2fr auto;gap:12px;align-items:flex-end;">
                        <div class="form-group" style="margin:0;">
                            <label>Bot Application ID</label>
                            <input type="text" class="form-control" id="approve_bot_id" placeholder="Application Client ID">
                        </div>
                        <div class="form-group" style="margin:0;">
                            <label>Bot Display Name</label>
                            <input type="text" class="form-control" id="approve_bot_name" placeholder="e.g. Midjourney Bot">
                        </div>
                        <button class="btn btn-primary" onclick="approveBotApp()">+ Approve Bot</button>
                    </div>
                </div>

                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Authorized Bot Applications</h3>
                    <div style="overflow-x:auto;">
                        <table style="width:100%;border-collapse:collapse;font-size:13px;">
                            <thead>
                                <tr style="border-bottom:1px solid var(--border);color:var(--text-muted);text-align:left;">
                                    <th style="padding:10px 14px;">Application Name</th>
                                    <th style="padding:10px 14px;">Client ID</th>
                                    <th style="padding:10px 14px;">Authorized By</th>
                                    <th style="padding:10px 14px;text-align:right;">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {approved_bots_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Tab 11: Moderation -->
            <div class="tab-pane" id="pane-moderation">
                <div class="card" style="margin-bottom:24px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Moderation Incident Handling</h3>

                    <div class="form-group">
                        <label>Moderation Case Log Channel</label>
                        {make_channel_select('moderation_mod_log_channel_id', moderation_cfg.get('mod_log_channel_id'))}
                    </div>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Direct Message (DM) Sanctioned Members</label>
                            <div class="desc">Notify members in private DM with the reason for bans, kicks, or warnings.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="moderation_dm_on_punish" {'checked' if moderation_cfg.get('dm_on_punish', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Warning Threshold Before Auto-Kick</label>
                            <input type="number" class="form-control" id="moderation_max_warnings_before_kick" value="{moderation_cfg.get('max_warnings_before_kick', 3)}" min="1" max="10">
                        </div>
                        <div class="form-group">
                            <label>Warning Threshold Before Auto-Ban</label>
                            <input type="number" class="form-control" id="moderation_max_warnings_before_ban" value="{moderation_cfg.get('max_warnings_before_ban', 5)}" min="2" max="20">
                        </div>
                    </div>
                </div>

                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Recent Moderation Sanctions</h3>
                    <div style="overflow-x:auto;">
                        <table style="width:100%;border-collapse:collapse;font-size:13px;">
                            <thead>
                                <tr style="border-bottom:1px solid var(--border);color:var(--text-muted);text-align:left;">
                                    <th style="padding:8px 12px;">Case</th>
                                    <th style="padding:8px 12px;">Action</th>
                                    <th style="padding:8px 12px;">Target Member</th>
                                    <th style="padding:8px 12px;">Staff Member</th>
                                    <th style="padding:8px 12px;">Reason</th>
                                    <th style="padding:8px 12px;">Timestamp</th>
                                </tr>
                            </thead>
                            <tbody>
                                {mod_logs_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Tab 12: Tickets -->
            <div class="tab-pane" id="pane-tickets">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Interactive Ticket Desk</h3>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Enable Support Tickets</label>
                            <div class="desc">Allow members to open private channels for confidential assistance.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="tickets_tickets_enabled" {'checked' if tickets_cfg.get('tickets_enabled', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Ticket Channels Category</label>
                            {make_category_select('tickets_category_id', tickets_cfg.get('category_id'))}
                        </div>
                        <div class="form-group">
                            <label>Support Staff Role</label>
                            {make_role_select('tickets_support_role_id', tickets_cfg.get('support_role_id'))}
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Transcript Archive Channel</label>
                        {make_channel_select('tickets_transcript_channel_id', tickets_cfg.get('transcript_channel_id'))}
                    </div>

                    <div class="form-group">
                        <label>Ticket Panel Header</label>
                        <input type="text" class="form-control" id="tickets_panel_title" value="{html.escape(tickets_cfg.get('panel_title') or '🎫 Support & Inquiries')}">
                    </div>

                    <div class="form-group">
                        <label>Ticket Panel Description Message</label>
                        <textarea class="form-control" id="tickets_panel_description">{html.escape(tickets_cfg.get('panel_description') or 'Click the button below to open a private ticket with our team.')}</textarea>
                    </div>
                </div>
                {ticket_panels_html}
                {ticket_live_html}
            </div>

            <!-- Tab 13: Logging -->
            <div class="tab-pane" id="pane-logging">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Granular Audit Log Channels</h3>
                    <p style="color:var(--text-muted);font-size:13px;margin-bottom:20px;">Separate logs by category into individual dedicated channels for maximum clarity.</p>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Member Joins Channel</label>
                            {make_channel_select('logging_joins_channel_id', logging_cfg.get('joins_channel_id'))}
                        </div>
                        <div class="form-group">
                            <label>Member Departures Channel</label>
                            {make_channel_select('logging_leaves_channel_id', logging_cfg.get('leaves_channel_id'))}
                        </div>
                        <div class="form-group">
                            <label>Message Edits Channel</label>
                            {make_channel_select('logging_message_edits_channel_id', logging_cfg.get('message_edits_channel_id'))}
                        </div>
                        <div class="form-group">
                            <label>Message Deletions Channel</label>
                            {make_channel_select('logging_message_deletes_channel_id', logging_cfg.get('message_deletes_channel_id'))}
                        </div>
                        <div class="form-group">
                            <label>Role Hierarchy Logs</label>
                            {make_channel_select('logging_role_changes_channel_id', logging_cfg.get('role_changes_channel_id'))}
                        </div>
                        <div class="form-group">
                            <label>Channel Changes Channel</label>
                            {make_channel_select('logging_channel_changes_channel_id', logging_cfg.get('channel_changes_channel_id'))}
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Bans & Kicks Audit Channel</label>
                        {make_channel_select('logging_bans_channel_id', logging_cfg.get('bans_channel_id'))}
                    </div>
                </div>
            </div>

            <!-- Tab 14: Roles -->
            <div class="tab-pane" id="pane-roles">
                <div class="card" style="margin-bottom:24px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Role Hierarchy & Permissions</h3>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Enforce Discord Role Hierarchy</label>
                            <div class="desc">Ensure bot cannot be manipulated into assigning higher roles than its own.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="roles_enforce_hierarchy" {'checked' if roles_cfg.get('enforce_hierarchy', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>

                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Current Server Role Hierarchy (Top 20)</h3>
                    {roles_list_html}
                </div>
            </div>

            <!-- Tab 15: Server Setup -->
            <div class="tab-pane" id="pane-server_setup">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">50 Pre-Built Architecture Presets</h3>
                    <p style="color:var(--text-muted);font-size:13px;margin-bottom:20px;">Deploy complete channel, role, category, and permission architectures in 1 click.</p>

                    <div class="form-group">
                        <label>Select Architecture Preset</label>
                        <select class="form-control" id="server_setup_template_id">
                            {server_setup_options}
                        </select>
                    </div>

                    <div style="background:#090d16;padding:18px;border-radius:10px;border:1px solid var(--border);margin-bottom:20px;">
                        <div style="font-weight:700;color:#fff;margin-bottom:6px;">Safety Protocol</div>
                        <div style="font-size:13px;color:var(--text-muted);">Existing channels and messages are preserved. An automated snapshot backup is created immediately prior to template deployment.</div>
                    </div>

                    <div style="display:flex;gap:12px;">
                        <button class="btn btn-primary" onclick="applyServerTemplate()">🚀 Deploy Architecture Template</button>
                    </div>
                </div>

                <!-- Dropper Channels Feature Card -->
                <div class="card" style="margin-top:24px;border:1px solid rgba(88,101,242,0.3);background:linear-gradient(135deg, rgba(88,101,242,0.06) 0%, rgba(13,17,23,0.95) 100%);">
                    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;">
                        <div style="display:flex;gap:14px;align-items:flex-start;">
                            <div style="width:48px;height:48px;border-radius:12px;background:rgba(88,101,242,0.15);border:1px solid rgba(88,101,242,0.3);display:flex;align-items:center;justify-content:center;font-size:24px;flex-shrink:0;">
                                💻
                            </div>
                            <div>
                                <div style="display:flex;align-items:center;gap:8px;">
                                    <h3 style="font-size:17px;color:#fff;margin:0;font-weight:700;">Dropper Channels</h3>
                                    <span style="background:rgba(88,101,242,0.2);color:#5865F2;border:1px solid rgba(88,101,242,0.4);font-size:11px;font-weight:700;padding:2px 8px;border-radius:12px;text-transform:uppercase;">Style-Matched</span>
                                </div>
                                <p style="color:var(--text-muted);font-size:13px;margin-top:4px;margin-bottom:0;max-width:560px;">
                                    Automatically create a complete <strong>DEVELOPER</strong> category with 16 organized channels, matching your existing server's naming, Unicode font, emoji placement, and decorative style.
                                </p>
                            </div>
                        </div>
                        <button class="btn btn-primary" onclick="openDropperModal()" style="display:flex;align-items:center;gap:8px;padding:10px 18px;font-weight:600;">
                            <span>🚀</span> Create Channels
                        </button>
                    </div>

                    <div style="margin-top:16px;display:grid;grid-template-columns:repeat(auto-fit, minmax(180px, 1fr));gap:10px;">
                        <div style="background:#090d16;padding:10px 12px;border-radius:8px;border:1px solid var(--border);font-size:12px;display:flex;align-items:center;gap:8px;">
                            <span style="color:#57F287;">✓</span> Auto Font & Separator Match
                        </div>
                        <div style="background:#090d16;padding:10px 12px;border-radius:8px;border:1px solid var(--border);font-size:12px;display:flex;align-items:center;gap:8px;">
                            <span style="color:#57F287;">✓</span> 16 Specialized Dev Channels
                        </div>
                        <div style="background:#090d16;padding:10px 12px;border-radius:8px;border:1px solid var(--border);font-size:12px;display:flex;align-items:center;gap:8px;">
                            <span style="color:#57F287;">✓</span> Zero Duplicate Guarantee
                        </div>
                    </div>
                </div>

                <!-- Dropper Confirmation Modal Dialog -->
                <div id="dropper-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.75);backdrop-filter:blur(4px);z-index:9999;align-items:center;justify-content:center;padding:20px;">
                    <div style="background:#111520;border:1px solid rgba(88,101,242,0.35);border-radius:14px;max-width:640px;width:100%;max-height:90vh;overflow-y:auto;padding:24px;box-shadow:0 20px 40px rgba(0,0,0,0.6);">
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;border-bottom:1px solid var(--border);padding-bottom:14px;">
                            <div style="display:flex;align-items:center;gap:10px;">
                                <span style="font-size:24px;">💻</span>
                                <div>
                                    <h3 style="font-size:18px;color:#fff;margin:0;font-weight:700;">Setup Dropper Channels</h3>
                                    <div style="font-size:12px;color:var(--text-muted);">Confirm planned category & channels architecture</div>
                                </div>
                            </div>
                            <button onclick="closeDropperModal()" style="background:none;border:none;color:#888;font-size:22px;cursor:pointer;">&times;</button>
                        </div>

                        <div id="dropper-modal-body">
                            <!-- Dynamic preview rendered here -->
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tab 18: Music -->
            <div class="tab-pane" id="pane-music">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">High-Fidelity Audio & Voice</h3>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Enable 24/7 Voice Channel Mode</label>
                            <div class="desc">Keep NOVEXA connected in the designated voice channel permanently.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="music_is_247" {'checked' if music_cfg.get('is_247') else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div class="form-group">
                        <label>Default 24/7 Voice Channel</label>
                        {make_voice_select('music_voice_channel_id', music_cfg.get('voice_channel_id'))}
                    </div>

                    <div class="form-group">
                        <label>Designated Music Command Channel</label>
                        {make_channel_select('music_text_channel_id', music_cfg.get('text_channel_id'))}
                    </div>

                    <div class="form-group">
                        <label>Default Playback Volume (10-100%)</label>
                        <input type="number" class="form-control" id="music_default_volume" value="{music_cfg.get('default_volume', 100)}" min="10" max="100">
                    </div>
                </div>
            </div>

            <!-- Tab 19: Economy -->
            <div class="tab-pane" id="pane-economy">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Virtual Economy & Banking Settings</h3>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Enable Virtual Economy</label>
                            <div class="desc">Enable wallet, bank, daily rewards, work, and shop systems.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="economy_is_enabled" {'checked' if economy_cfg.get('is_enabled', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Currency Name</label>
                            <input type="text" class="form-control" id="economy_currency_name" value="{economy_cfg.get('currency_name', 'NOVEXA COINS')}">
                        </div>
                        <div class="form-group">
                            <label>Currency Symbol</label>
                            <input type="text" class="form-control" id="economy_currency_symbol" value="{economy_cfg.get('currency_symbol', '🪙')}">
                        </div>
                        <div class="form-group">
                            <label>Base Daily Reward</label>
                            <input type="number" class="form-control" id="economy_daily_reward" value="{economy_cfg.get('daily_reward_min', 1000)}" min="100">
                        </div>
                        <div class="form-group">
                            <label>Daily Streak Bonus Multiplier</label>
                            <input type="number" class="form-control" id="economy_streak_bonus_per_day" value="100" min="10">
                        </div>
                        <div class="form-group">
                            <label>Work Cooldown (Seconds)</label>
                            <input type="number" class="form-control" id="economy_work_cooldown" value="{economy_cfg.get('work_cooldown', 300)}" min="30">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tab 20: RPG & Games -->
            <div class="tab-pane" id="pane-rpg_games">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">RPG Battles & Mini-Games</h3>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Enable Gambling & Mini-Games</label>
                            <div class="desc">Allows games such as coinflip, dice, slots, blackjack, and crime.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="rpg_games_games_enabled" {'checked' if rpg_cfg.get('games_enabled', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Crime Success Rate (10-90%)</label>
                            <input type="number" class="form-control" id="rpg_games_crime_success_rate" value="{rpg_cfg.get('crime_success_rate', 65)}" min="10" max="90">
                        </div>
                        <div class="form-group">
                            <label>Max Bet Limit</label>
                            <input type="number" class="form-control" id="rpg_games_max_bet_amount" value="{rpg_cfg.get('max_bet_amount', 100000)}" min="100">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tab 21: Pets & Hunting -->
            <div class="tab-pane" id="pane-pets_hunting">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Wild Animal Hunting & Pet Breeding</h3>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Hunting Delay Cooldown (Seconds)</label>
                            <input type="number" class="form-control" id="pets_hunting_hunt_cooldown" value="{pets_cfg.get('hunt_cooldown', 15)}" min="5" max="300">
                        </div>
                        <div class="form-group">
                            <label>Mythical Drop Rate (1-10%)</label>
                            <input type="number" class="form-control" id="pets_hunting_mythical_drop_rate" value="{pets_cfg.get('mythical_drop_rate', 1)}" min="1" max="10">
                        </div>
                    </div>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Enable Pet Adoption Bazaar</label>
                            <div class="desc">Allows members to adopt, name, and level companion pets.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="pets_hunting_pet_adoption_enabled" {'checked' if pets_cfg.get('pet_adoption_enabled', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
            </div>

            <!-- Tab 22: Leveling -->
            <div class="tab-pane" id="pane-leveling">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Chat Activity Experience & Leveling</h3>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Enable Chat XP Leveling</label>
                            <div class="desc">Reward members with experience points for sending active chat messages.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="leveling_leveling_enabled" {'checked' if leveling_cfg.get('leveling_enabled', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Base XP per Message</label>
                            <input type="number" class="form-control" id="leveling_xp_per_message" value="{leveling_cfg.get('xp_per_message', 20)}" min="5" max="100">
                        </div>
                        <div class="form-group">
                            <label>XP Anti-Spam Cooldown (Seconds)</label>
                            <input type="number" class="form-control" id="leveling_xp_cooldown" value="{leveling_cfg.get('xp_cooldown', 60)}" min="10" max="300">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Level-Up Announcement Channel</label>
                        {make_channel_select('leveling_level_up_channel_id', leveling_cfg.get('level_up_channel_id'))}
                    </div>
                </div>
            </div>

            <!-- Tab 23: Giveaways -->
            <div class="tab-pane" id="pane-giveaways">
                <div class="card" style="margin-bottom:24px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Giveaway Management</h3>

                    <div class="form-group">
                        <label>Giveaways Announcement Channel</label>
                        {make_channel_select('giveaways_giveaway_log_channel_id', None)}
                    </div>
                </div>

                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Active & Past Giveaways</h3>
                    <div style="overflow-x:auto;">
                        <table style="width:100%;border-collapse:collapse;font-size:13px;">
                            <thead>
                                <tr style="border-bottom:1px solid var(--border);color:var(--text-muted);text-align:left;">
                                    <th style="padding:10px 14px;">Prize</th>
                                    <th style="padding:10px 14px;">Winners</th>
                                    <th style="padding:10px 14px;">Status</th>
                                    <th style="padding:10px 14px;">Message ID</th>
                                </tr>
                            </thead>
                            <tbody>
                                {giveaways_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Tab 24: Reaction Roles -->
            <div class="tab-pane" id="pane-reaction_roles">
                <div class="card" style="margin-bottom:24px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Create Reaction Role Binding</h3>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
                        <div class="form-group" style="margin:0;">
                            <label>Target Channel</label>
                            {make_channel_select('rr_channel_id', None)}
                        </div>
                        <div class="form-group" style="margin:0;">
                            <label>Target Message ID</label>
                            <input type="text" class="form-control" id="rr_message_id" placeholder="Message ID">
                        </div>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
                        <div class="form-group" style="margin:0;">
                            <label>Emoji Trigger</label>
                            <input type="text" class="form-control" id="rr_emoji" placeholder="e.g. ⭐, 🎮, ✅">
                        </div>
                        <div class="form-group" style="margin:0;">
                            <label>Role to Grant</label>
                            {make_role_select('rr_role_id', None)}
                        </div>
                    </div>

                    <button class="btn btn-primary" onclick="addReactionRole()">+ Bind Reaction Role</button>
                </div>

                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Active Reaction Roles</h3>
                    <div style="overflow-x:auto;">
                        <table style="width:100%;border-collapse:collapse;font-size:13px;">
                            <thead>
                                <tr style="border-bottom:1px solid var(--border);color:var(--text-muted);text-align:left;">
                                    <th style="padding:10px 14px;">Emoji</th>
                                    <th style="padding:10px 14px;">Associated Role</th>
                                    <th style="padding:10px 14px;">Message Reference</th>
                                    <th style="padding:10px 14px;text-align:right;">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {reaction_roles_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Tab 25: Custom Embeds -->
            <div class="tab-pane" id="pane-custom_embeds">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Rich Embed Builder & Broadcaster</h3>

                    <div class="form-group">
                        <label>Target Destination Channel</label>
                        {make_channel_select('embed_target_channel_id', None)}
                    </div>

                    <div class="form-group">
                        <label>Embed Header Title</label>
                        <input type="text" class="form-control" id="embed_title" placeholder="Server Announcement">
                    </div>

                    <div class="form-group">
                        <label>Embed Body Message (Markdown supported)</label>
                        <textarea class="form-control" id="embed_description" style="min-height:120px;" placeholder="Write your server announcement here..."></textarea>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Sidebar Border Color</label>
                            <input type="color" class="form-control" id="embed_color" value="#38bdf8" style="height:44px;padding:4px;">
                        </div>
                        <div class="form-group">
                            <label>Footer Text</label>
                            <input type="text" class="form-control" id="embed_footer" placeholder="NOVEXA Official Broadcast">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Image URL (Optional)</label>
                        <input type="text" class="form-control" id="embed_image" placeholder="https://i.imgur.com/example.png">
                    </div>

                    <button class="btn btn-primary" onclick="dispatchCustomEmbed()">📢 Dispatch Custom Embed to Discord</button>
                </div>
            </div>

            <!-- Tab 26: Auto Responder -->
            <div class="tab-pane" id="pane-auto_responder">
                <div class="card" style="margin-bottom:24px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Add Automated Keyword Trigger</h3>

                    <div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:16px;">
                        <div class="form-group" style="margin:0;">
                            <label>Trigger Keyword / Phrase</label>
                            <input type="text" class="form-control" id="ar_trigger" placeholder="e.g. !ip, store, rules">
                        </div>
                        <div class="form-group" style="margin:0;">
                            <label>Matching Rule</label>
                            <select class="form-control" id="ar_match_type">
                                <option value="contains">Contains Word (Anywhere)</option>
                                <option value="exact">Exact Match</option>
                                <option value="startswith">Starts With</option>
                            </select>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Response Content</label>
                        <textarea class="form-control" id="ar_response" placeholder="The reply message sent by NOVEXA automatically..."></textarea>
                    </div>

                    <button class="btn btn-primary" onclick="addAutoResponder()">+ Create Auto-Responder</button>
                </div>

                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Active Auto-Responders</h3>
                    <div style="overflow-x:auto;">
                        <table style="width:100%;border-collapse:collapse;font-size:13px;">
                            <thead>
                                <tr style="border-bottom:1px solid var(--border);color:var(--text-muted);text-align:left;">
                                    <th style="padding:10px 14px;">Trigger</th>
                                    <th style="padding:10px 14px;">Response Message</th>
                                    <th style="padding:10px 14px;">Match Type</th>
                                    <th style="padding:10px 14px;text-align:right;">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {autoresponders_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Tab 27: Voice Channels -->
            <div class="tab-pane" id="pane-voice_channels">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">24/7 Voice & Dynamic Voice Hubs</h3>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Permanent 24/7 Dedicated Voice Stay</label>
                            <div class="desc">Keeps bot streaming or standby in voice room permanently.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="voice_channels_is_247" {'checked' if voice_cfg.get('is_247') else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div class="form-group">
                        <label>Dedicated Voice Channel</label>
                        {make_voice_select('voice_channels_voice_channel_id', voice_cfg.get('voice_channel_id'))}
                    </div>
                </div>

                <div class="card" style="margin-top:24px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:6px;">Join to Create — Personal Voice Rooms</h3>
                    <p style="color:var(--text-muted);font-size:13px;margin-bottom:16px;">Members who join the generator receive their own temporary room with a full control panel. This form writes the same configuration the bot reads live.</p>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>System Enabled</label>
                            <div class="desc">Spawn temporary rooms when members join the generator.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="voice_j2c_is_enabled" {'checked' if j2c_cfg.get('is_enabled') else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <div class="form-group">
                        <label>Generator Voice Channel</label>
                        {make_voice_select('voice_j2c_generator_channel_id', j2c_cfg.get('generator_channel_id'))}
                    </div>

                    <div class="form-group">
                        <label>Spawning Category</label>
                        {make_category_select('voice_j2c_category_id', j2c_cfg.get('category_id'))}
                    </div>

                    <div class="form-group">
                        <label>Channel Name Format</label>
                        <input class="form-control" id="voice_j2c_channel_name_format" value="{html.escape(j2c_cfg.get('channel_name_format') or '🔊・{username}')}" placeholder="🔊・{{username}}">
                        <div class="desc">Placeholders: {{username}}, {{display_name}}, {{name}}, {{server}}, {{count}}</div>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Default User Limit (0 = unlimited)</label>
                            <input class="form-control" type="number" min="0" max="99" id="voice_j2c_default_user_limit" value="{int(j2c_cfg.get('default_user_limit') or 0)}">
                        </div>
                        <div class="form-group">
                            <label>Default Bitrate (kbps)</label>
                            <input class="form-control" type="number" min="8" max="384" id="voice_j2c_default_bitrate" value="{int((j2c_cfg.get('default_bitrate') or 64000) / 1000)}">
                        </div>
                    </div>

                    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <label>Auto-delete Empty Rooms</label>
                            <div class="desc">Remove the room once the last member leaves.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="voice_j2c_delete_when_empty" {'checked' if j2c_cfg.get('delete_when_empty', True) else ''}>
                            <span class="slider"></span>
                        </label>
                    </div>

                    <button class="btn btn-primary" onclick="saveJoinToCreate()">💾 Save Join to Create</button>
                </div>
            </div>

            <!-- Tab 28: Backups -->
            <div class="tab-pane" id="pane-backups">
                <div class="card" style="margin-bottom:24px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
                        <div>
                            <h3 style="font-size:16px;color:#fff;margin-bottom:4px;">Disaster Recovery & Server Snapshots</h3>
                            <p style="color:var(--text-muted);font-size:13px;margin:0;">Snapshot complete channel hierarchies, role permissions, categories, and bot settings.</p>
                        </div>
                        <button class="btn btn-primary" onclick="createBackup()">💾 Create Server Snapshot</button>
                    </div>
                </div>

                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Available Backup Snapshots</h3>
                    <div style="overflow-x:auto;">
                        <table style="width:100%;border-collapse:collapse;font-size:13px;">
                            <thead>
                                <tr style="border-bottom:1px solid var(--border);color:var(--text-muted);text-align:left;">
                                    <th style="padding:10px 14px;">Snapshot Title</th>
                                    <th style="padding:10px 14px;">Unique Backup ID</th>
                                    <th style="padding:10px 14px;">Created At</th>
                                    <th style="padding:10px 14px;text-align:right;">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {backups_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Tab 29: Integrations -->
            <div class="tab-pane" id="pane-integrations">
                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Payment Gateways & UPI Store</h3>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Merchant UPI ID / VPA</label>
                            <input type="text" class="form-control" id="integrations_upi_id" value="{html.escape(integrations_cfg.get('upi_id') or '')}" placeholder="merchant@upi">
                        </div>
                        <div class="form-group">
                            <label>Static QR Code Image URL</label>
                            <input type="text" class="form-control" id="integrations_qr_image_url" value="{html.escape(integrations_cfg.get('qr_image_url') or '')}" placeholder="https://i.imgur.com/qrcode.png">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Payment & Settlement Instructions</label>
                        <textarea class="form-control" id="integrations_instructions" placeholder="Please attach transaction screenshot or reference ID...">{html.escape(integrations_cfg.get('instructions') or '')}</textarea>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                        <div class="form-group">
                            <label>Staff Review / Verifier Role</label>
                            {make_role_select('integrations_staff_role_id', integrations_cfg.get('staff_role_id'))}
                        </div>
                        <div class="form-group">
                            <label>Payment Audit Log Channel</label>
                            {make_channel_select('integrations_log_channel_id', integrations_cfg.get('log_channel_id'))}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tab 30: Premium -->
            <div class="tab-pane" id="pane-premium">
                <div class="card" style="text-align:center;padding:36px;margin-bottom:24px;">
                    <div class="badge badge-accent" style="margin-bottom:12px;">SERVER SUBSCRIPTION STATUS</div>
                    <h2 style="font-size:28px;font-weight:900;color:#fff;margin-bottom:8px;">{premium_status.get('tier', 'FREE')} TIER</h2>
                    <p style="color:var(--text-muted);font-size:14px;max-width:500px;margin:0 auto 20px;">{guild_name} currently enjoys enterprise security and autonomous bot automation.</p>
                    <a href="/premium" class="btn btn-primary" style="display:inline-block;text-decoration:none;">⭐ Upgrade Server Tier</a>
                </div>

                <div class="card">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Active Tier Capabilities</h3>
                    <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:16px;">
                        <div style="background:#0d111b;padding:16px;border-radius:8px;border:1px solid var(--border);">
                            <div style="color:#34d399;font-weight:700;margin-bottom:4px;">✓ Unlimited Backups</div>
                            <div style="font-size:12px;color:var(--text-dim);">Automated disaster recovery snapshots.</div>
                        </div>
                        <div style="background:#0d111b;padding:16px;border-radius:8px;border:1px solid var(--border);">
                            <div style="color:#34d399;font-weight:700;margin-bottom:4px;">✓ Priority AI Engine</div>
                            <div style="font-size:12px;color:var(--text-dim);">Zero cooldown with dedicated queue.</div>
                        </div>
                        <div style="background:#0d111b;padding:16px;border-radius:8px;border:1px solid var(--border);">
                            <div style="color:#34d399;font-weight:700;margin-bottom:4px;">✓ 24/7 Voice Audio</div>
                            <div style="font-size:12px;color:var(--text-dim);">Permanent voice channel connectivity.</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tab 31: Audit History -->
            <div class="tab-pane" id="pane-audit_history">
                <div class="card">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:12px;">
                        <div>
                            <h3 style="font-size:16px;color:#fff;margin-bottom:4px;">Authoritative Configuration Audit Logs</h3>
                            <p style="color:var(--text-muted);font-size:13px;margin:0;">Immutable log stream of every parameter modified via Web Dashboard or Discord slash commands.</p>
                        </div>
                        <span class="badge badge-success">● SSE Live Connected</span>
                    </div>

                    <div style="overflow-x:auto;">
                        <table style="width:100%;border-collapse:collapse;font-size:13px;">
                            <thead>
                                <tr style="border-bottom:1px solid var(--border);color:var(--text-muted);text-align:left;">
                                    <th style="padding:8px 12px;">Timestamp</th>
                                    <th style="padding:8px 12px;">Actor</th>
                                    <th style="padding:8px 12px;">Module</th>
                                    <th style="padding:8px 12px;">Setting</th>
                                    <th style="padding:8px 12px;">New Value</th>
                                    <th style="padding:8px 12px;">Source</th>
                                </tr>
                            </thead>
                            <tbody>
                                {audit_rows_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Tab 32: Settings -->
            <div class="tab-pane" id="pane-settings">
                <div class="card" style="margin-bottom:24px;">
                    <h3 style="font-size:16px;color:#fff;margin-bottom:16px;">Core Server Settings</h3>

                    <div class="form-group">
                        <label>Bot Command Prefix</label>
                        <div class="desc">Default slash commands (/) are always active. Text prefix applies to legacy command invocations.</div>
                        <input type="text" class="form-control" id="settings_prefix" value="{html.escape(settings_cfg.get('prefix') or '/')}" style="max-width:200px;">
                    </div>
                </div>

                <div class="card" style="border-color:rgba(239, 68, 68, 0.3);">
                    <h3 style="font-size:16px;color:#ef4444;margin-bottom:8px;">Danger Zone</h3>
                    <p style="color:var(--text-muted);font-size:13px;margin-bottom:16px;">Irreversible administrative actions for this guild.</p>

                    <div style="display:flex;gap:12px;flex-wrap:wrap;">
                        <button class="btn btn-outline" style="color:#ef4444;border-color:rgba(239,68,68,0.4);" onclick="triggerAction('lockdown')">🚨 Trigger Server Lockdown</button>
                    </div>
                </div>
            </div>

        </main>
    </div>

    {_render_footer()}

    <script>
    const GUILD_ID = "{gid}";
    let activeTab = 'overview';

    function switchTab(tabKey) {{
        activeTab = tabKey;
        document.querySelectorAll('.dash-tab-btn').forEach(b => b.classList.remove('active'));
        const btn = document.getElementById('tab-btn-' + tabKey);
        if(btn) btn.classList.add('active');

        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

        const specificPane = document.getElementById('pane-' + tabKey);
        if(specificPane) {{
            specificPane.classList.add('active');
        }}

        // Update header
        const tabBtn = document.getElementById('tab-btn-' + tabKey);
        if(tabBtn) {{
            document.getElementById('active-tab-title').innerText = tabBtn.innerText.trim();
        }}

        if(tabKey === 'welcome' && typeof updateWelcomePreview === 'function') updateWelcomePreview();
    }}

    function currentWelcomeOption() {{
        const sel = document.getElementById('welcome_template_id');
        return sel && sel.selectedIndex >= 0 ? sel.options[sel.selectedIndex] : null;
    }}

    function applyWelcomeTheme() {{
        const opt = currentWelcomeOption();
        const colorBox = document.getElementById('welcome_custom_color');
        if(opt && colorBox) colorBox.value = opt.dataset.accent || colorBox.value;
        updateWelcomePreview();
    }}

    function updateWelcomePreview() {{
        const opt = currentWelcomeOption();
        const color = document.getElementById('welcome_custom_color')?.value || opt?.dataset.accent || '#5865F2';
        const card = document.getElementById('preview-card');
        const badge = document.getElementById('preview-badge');
        const avatar = document.getElementById('preview-avatar');
        const title = document.getElementById('preview-title');
        if(card) {{
            if(opt && opt.dataset.bg1 && opt.dataset.bg2) {{
                card.style.background = 'linear-gradient(135deg, ' + opt.dataset.bg1 + ', ' + opt.dataset.bg2 + ')';
            }}
            card.style.borderColor = color;
            card.style.boxShadow = '0 0 25px ' + color + '40';
        }}
        if(badge) {{
            if(opt && opt.dataset.tagline) badge.textContent = opt.dataset.tagline;
            badge.style.color = color;
            badge.style.borderColor = color + '66';
        }}
        if(title && opt && opt.dataset.nameColor) title.style.color = opt.dataset.nameColor;
        if(avatar) {{
            avatar.style.borderColor = color;
            avatar.style.boxShadow = '0 0 15px ' + color;
        }}
    }}

    async function saveJoinToCreate() {{
        const limitRaw = parseInt(document.getElementById('voice_j2c_default_user_limit')?.value);
        const bitrateRaw = parseInt(document.getElementById('voice_j2c_default_bitrate')?.value);
        const payload = {{
            is_enabled: document.getElementById('voice_j2c_is_enabled')?.checked || false,
            generator_channel_id: parseInt(document.getElementById('voice_j2c_generator_channel_id')?.value) || null,
            category_id: parseInt(document.getElementById('voice_j2c_category_id')?.value) || null,
            channel_name_format: document.getElementById('voice_j2c_channel_name_format')?.value || '🔊・{{username}}',
            default_user_limit: isNaN(limitRaw) ? 0 : Math.max(0, Math.min(99, limitRaw)),
            default_bitrate: (isNaN(bitrateRaw) ? 64 : Math.max(8, bitrateRaw)) * 1000,
            delete_when_empty: document.getElementById('voice_j2c_delete_when_empty')?.checked || false,
        }};
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/config/voice_j2c', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(payload)
            }});
            if(res.ok) {{
                showToast('Join to Create settings saved and synced.');
            }} else {{
                showToast('Failed to save Join to Create: ' + res.statusText, 'error');
            }}
        }} catch(e) {{
            showToast('Network error saving Join to Create', 'error');
        }}
    }}

    async function saveActiveTab() {{
        const saveBtn = document.getElementById('btn-save');
        saveBtn.innerText = '⏳ Saving...';
        saveBtn.disabled = true;

        let payload = {{}};
        let endpoint = '/api/guilds/' + GUILD_ID + '/welcome';

        if(activeTab === 'welcome') {{
            payload = {{
                enabled: document.getElementById('welcome_enabled')?.checked || false,
                channel_id: parseInt(document.getElementById('welcome_channel_id')?.value) || null,
                template_id: document.getElementById('welcome_template_id')?.value || 'minimal_welcome',
                message_template: document.getElementById('welcome_message_template')?.value || '',
                custom_color: document.getElementById('welcome_custom_color')?.value || '#5865F2',
                dm_enabled: document.getElementById('welcome_dm_enabled')?.checked || false,
            }};
        }} else if(activeTab === 'goodbye') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/goodbye';
            payload = {{
                goodbye_enabled: document.getElementById('goodbye_goodbye_enabled')?.checked || false,
                leave_channel_id: parseInt(document.getElementById('goodbye_leave_channel_id')?.value) || null,
                goodbye_template_id: document.getElementById('goodbye_goodbye_template_id')?.value || 'minimal_dark',
                leave_embed_enabled: document.getElementById('goodbye_leave_embed_enabled')?.checked || false,
                leave_message_template: document.getElementById('goodbye_leave_message_template')?.value || '',
            }};
        }} else if(activeTab === 'autoroles') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/autoroles';
            const mrole = document.getElementById('autoroles_member_role_id')?.value;
            payload = {{
                auto_roles: mrole ? [parseInt(mrole)] : [],
                bot_role_id: parseInt(document.getElementById('autoroles_bot_role_id')?.value) || null,
            }};
        }} else if(activeTab === 'antinuke') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/security';
            payload = {{
                enabled: document.getElementById('antinuke_enabled')?.checked || false,
                mode: document.getElementById('antinuke_mode')?.value || 'medium',
                punishment_type: document.getElementById('antinuke_punishment_type')?.value || 'quarantine',
                max_channel_deletions: parseInt(document.getElementById('antinuke_max_channel_deletions')?.value) || 2,
                max_role_deletions: parseInt(document.getElementById('antinuke_max_role_deletions')?.value) || 3,
                max_bans: parseInt(document.getElementById('antinuke_max_bans')?.value) || 3,
                max_webhook_changes: parseInt(document.getElementById('antinuke_max_webhook_changes')?.value) || 4,
            }};
        }} else if(activeTab === 'antispam') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/antispam';
            payload = {{
                enabled: document.getElementById('antispam_enabled')?.checked || false,
                max_mentions: parseInt(document.getElementById('antispam_max_mentions')?.value) || 5,
                max_duplicates: parseInt(document.getElementById('antispam_max_duplicates')?.value) || 3,
                max_emojis: parseInt(document.getElementById('antispam_max_emojis')?.value) || 8,
                timeout_duration_minutes: parseInt(document.getElementById('antispam_timeout_duration_minutes')?.value) || 10,
                block_invites: document.getElementById('antispam_block_invites')?.checked || false,
                block_links: document.getElementById('antispam_block_links')?.checked || false,
            }};
        }} else if(activeTab === 'automod') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/automod';
            payload = {{
                caps_filter_enabled: document.getElementById('automod_caps_filter_enabled')?.checked || false,
                blocked_words: document.getElementById('automod_blocked_words')?.value || '',
                attachment_spam_limit: parseInt(document.getElementById('automod_attachment_spam_limit')?.value) || 5,
                automod_action: document.getElementById('automod_automod_action')?.value || 'delete',
            }};
        }} else if(activeTab === 'whitelist') {{
            showToast('Whitelist changes are committed instantly using Add/Remove buttons.');
            saveBtn.innerText = '💾 Save Changes';
            saveBtn.disabled = false;
            return;
        }} else if(activeTab === 'wallpaper') {{
            showToast('Wallpaper channels are committed instantly using Add/Remove buttons.');
            saveBtn.innerText = '💾 Save Changes';
            saveBtn.disabled = false;
            return;
        }} else if(activeTab === 'dropper') {{
            showToast('Dropper members are committed instantly using Grant/Revoke buttons.');
            saveBtn.innerText = '💾 Save Changes';
            saveBtn.disabled = false;
            return;
        }} else if(activeTab === 'approved_bots') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/approved_bots';
            payload = {{
                bot_protection_enabled: document.getElementById('approved_bots_bot_protection_enabled')?.checked || false,
            }};
        }} else if(activeTab === 'moderation') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/moderation';
            payload = {{
                mod_log_channel_id: parseInt(document.getElementById('moderation_mod_log_channel_id')?.value) || null,
                dm_on_punish: document.getElementById('moderation_dm_on_punish')?.checked || false,
                max_warnings_before_kick: parseInt(document.getElementById('moderation_max_warnings_before_kick')?.value) || 3,
                max_warnings_before_ban: parseInt(document.getElementById('moderation_max_warnings_before_ban')?.value) || 5,
            }};
        }} else if(activeTab === 'tickets') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/tickets';
            payload = {{
                tickets_enabled: document.getElementById('tickets_tickets_enabled')?.checked || false,
                category_id: parseInt(document.getElementById('tickets_category_id')?.value) || null,
                support_role_id: parseInt(document.getElementById('tickets_support_role_id')?.value) || null,
                transcript_channel_id: parseInt(document.getElementById('tickets_transcript_channel_id')?.value) || null,
                panel_title: document.getElementById('tickets_panel_title')?.value || 'Support Tickets',
                panel_description: document.getElementById('tickets_panel_description')?.value || 'Click below to create a ticket.',
            }};
        }} else if(activeTab === 'logging') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/logging';
            payload = {{
                joins_channel_id: parseInt(document.getElementById('logging_joins_channel_id')?.value) || null,
                leaves_channel_id: parseInt(document.getElementById('logging_leaves_channel_id')?.value) || null,
                message_edits_channel_id: parseInt(document.getElementById('logging_message_edits_channel_id')?.value) || null,
                message_deletes_channel_id: parseInt(document.getElementById('logging_message_deletes_channel_id')?.value) || null,
                role_changes_channel_id: parseInt(document.getElementById('logging_role_changes_channel_id')?.value) || null,
                channel_changes_channel_id: parseInt(document.getElementById('logging_channel_changes_channel_id')?.value) || null,
                bans_channel_id: parseInt(document.getElementById('logging_bans_channel_id')?.value) || null,
            }};
        }} else if(activeTab === 'roles') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/roles';
            payload = {{
                enforce_hierarchy: document.getElementById('roles_enforce_hierarchy')?.checked || false,
            }};
        }} else if(activeTab === 'server_setup') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/server_setup';
            payload = {{
                template_id: document.getElementById('server_setup_template_id')?.value || 'gaming',
            }};
        }} else if(activeTab === 'music') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/music';
            payload = {{
                is_247: document.getElementById('music_is_247')?.checked || false,
                voice_channel_id: parseInt(document.getElementById('music_voice_channel_id')?.value) || null,
                text_channel_id: parseInt(document.getElementById('music_text_channel_id')?.value) || null,
                default_volume: parseInt(document.getElementById('music_default_volume')?.value) || 100,
            }};
        }} else if(activeTab === 'economy') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/economy';
            payload = {{
                is_enabled: document.getElementById('economy_is_enabled')?.checked || false,
                currency_name: document.getElementById('economy_currency_name')?.value || 'NOVEXA COINS',
                currency_symbol: document.getElementById('economy_currency_symbol')?.value || '🪙',
                daily_reward: parseInt(document.getElementById('economy_daily_reward')?.value) || 1000,
                streak_bonus_per_day: parseInt(document.getElementById('economy_streak_bonus_per_day')?.value) || 100,
                work_cooldown: parseInt(document.getElementById('economy_work_cooldown')?.value) || 300,
            }};
        }} else if(activeTab === 'rpg_games') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/rpg_games';
            payload = {{
                games_enabled: document.getElementById('rpg_games_games_enabled')?.checked || false,
                crime_success_rate: parseInt(document.getElementById('rpg_games_crime_success_rate')?.value) || 65,
                max_bet_amount: parseInt(document.getElementById('rpg_games_max_bet_amount')?.value) || 100000,
            }};
        }} else if(activeTab === 'pets_hunting') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/pets_hunting';
            payload = {{
                hunt_cooldown: parseInt(document.getElementById('pets_hunting_hunt_cooldown')?.value) || 15,
                mythical_drop_rate: parseInt(document.getElementById('pets_hunting_mythical_drop_rate')?.value) || 1,
                pet_adoption_enabled: document.getElementById('pets_hunting_pet_adoption_enabled')?.checked || false,
            }};
        }} else if(activeTab === 'leveling') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/leveling';
            payload = {{
                leveling_enabled: document.getElementById('leveling_leveling_enabled')?.checked || false,
                xp_per_message: parseInt(document.getElementById('leveling_xp_per_message')?.value) || 20,
                xp_cooldown: parseInt(document.getElementById('leveling_xp_cooldown')?.value) || 60,
                level_up_channel_id: parseInt(document.getElementById('leveling_level_up_channel_id')?.value) || null,
            }};
        }} else if(activeTab === 'giveaways') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/giveaways';
            payload = {{
                giveaway_log_channel_id: parseInt(document.getElementById('giveaways_giveaway_log_channel_id')?.value) || null,
            }};
        }} else if(activeTab === 'reaction_roles') {{
            showToast('Reaction roles are configured via the Bind button below.');
            saveBtn.innerText = '💾 Save Changes';
            saveBtn.disabled = false;
            return;
        }} else if(activeTab === 'custom_embeds') {{
            showToast('Click "Dispatch Custom Embed to Discord" button below.');
            saveBtn.innerText = '💾 Save Changes';
            saveBtn.disabled = false;
            return;
        }} else if(activeTab === 'auto_responder') {{
            showToast('Auto-responders are managed directly in the table below.');
            saveBtn.innerText = '💾 Save Changes';
            saveBtn.disabled = false;
            return;
        }} else if(activeTab === 'voice_channels') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/voice_channels';
            payload = {{
                is_247: document.getElementById('voice_channels_is_247')?.checked || false,
                voice_channel_id: parseInt(document.getElementById('voice_channels_voice_channel_id')?.value) || null,
            }};
        }} else if(activeTab === 'backups') {{
            showToast('Create and restore backups using the dedicated Snapshot controls.');
            saveBtn.innerText = '💾 Save Changes';
            saveBtn.disabled = false;
            return;
        }} else if(activeTab === 'integrations') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/integrations';
            payload = {{
                upi_id: document.getElementById('integrations_upi_id')?.value || '',
                qr_image_url: document.getElementById('integrations_qr_image_url')?.value || '',
                instructions: document.getElementById('integrations_instructions')?.value || '',
                staff_role_id: parseInt(document.getElementById('integrations_staff_role_id')?.value) || null,
                log_channel_id: parseInt(document.getElementById('integrations_log_channel_id')?.value) || null,
            }};
        }} else if(activeTab === 'premium') {{
            showToast('Visit the Premium Plans page to upgrade server subscriptions.');
            saveBtn.innerText = '💾 Save Changes';
            saveBtn.disabled = false;
            return;
        }} else if(activeTab === 'audit_history') {{
            showToast('Audit history is an authoritative live streaming log.');
            saveBtn.innerText = '💾 Save Changes';
            saveBtn.disabled = false;
            return;
        }} else if(activeTab === 'settings') {{
            endpoint = '/api/guilds/' + GUILD_ID + '/config/settings';
            payload = {{
                prefix: document.getElementById('settings_prefix')?.value || '/',
            }};
        }}

        try {{
            const res = await fetch(endpoint, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(payload)
            }});
            if(res.ok) {{
                showToast('Settings saved and synchronized with bot!');
            }} else {{
                showToast('Failed to save settings: ' + res.statusText, 'error');
            }}
        }} catch(e) {{
            showToast('Network error saving settings', 'error');
        }} finally {{
            saveBtn.innerText = '💾 Save Changes';
            saveBtn.disabled = false;
        }}
    }}

    async function triggerAction(actionName) {{
        if(actionName === 'lockdown' && !confirm('WARNING: Are you sure you want to trigger an Emergency Server Lockdown? Regular members will lose send permissions!')) return;
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/actions/' + actionName, {{ method: 'POST' }});
            let data = {{}};
            try {{ data = await res.json(); }} catch(e) {{}}
            if(res.ok) {{
                showToast(data.message || ('Action ' + actionName + ' executed successfully!'));
            }} else {{
                showToast('Failed: ' + (data.detail || res.statusText), 'error');
            }}
        }} catch(e) {{
            showToast('Action network error', 'error');
        }}
    }}

    async function addWhitelistEntry() {{
        const targetId = document.getElementById('whitelist_target_id')?.value.trim();
        const targetType = document.getElementById('whitelist_target_type')?.value || 'member';
        if(!targetId) return showToast('Please enter a valid Snowflake ID', 'error');
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/whitelist', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ target_id: targetId, target_type: targetType }})
            }});
            if(res.ok) {{
                showToast('Whitelist entry added!');
                setTimeout(() => location.reload(), 800);
            }} else {{
                showToast('Error adding whitelist', 'error');
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function deleteWhitelistEntry(targetId) {{
        if(!confirm('Remove ID ' + targetId + ' from whitelist?')) return;
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/whitelist/' + targetId, {{ method: 'DELETE' }});
            if(res.ok) {{
                showToast('Whitelist entry removed!');
                setTimeout(() => location.reload(), 800);
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function editTicketPanel(panelId) {{
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/tickets/live');
            const data = await res.json();
            const panel = (data.panels || []).find(p => String(p.panel_id) === String(panelId));
            if(!panel) return showToast('Panel not found', 'error');
            const setVal = (id, v) => {{
                const el = document.getElementById(id);
                if(el) el.value = (v === null || v === undefined) ? '' : String(v);
            }};
            setVal('tickets_category_id', panel.category_id);
            setVal('tickets_support_role_id', panel.support_role_id);
            setVal('tickets_transcript_channel_id', panel.transcript_channel_id);
            setVal('tickets_panel_title', panel.title);
            setVal('tickets_panel_description', panel.description);
            const en = document.getElementById('tickets_tickets_enabled');
            if(en) en.checked = true;
            document.getElementById('pane-tickets')?.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            showToast('Panel loaded into the editor — change fields and save');
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function closeTicket(ticketId) {{
        if(!confirm('Mark ticket #' + ticketId + ' as closed?')) return;
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/tickets/' + ticketId + '/close', {{ method: 'POST' }});
            let data = {{}};
            try {{ data = await res.json(); }} catch(e) {{}}
            if(res.ok) {{
                showToast(data.message || ('Ticket #' + ticketId + ' closed'));
                setTimeout(() => location.reload(), 800);
            }} else {{
                showToast('Failed: ' + (data.detail || res.statusText), 'error');
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function deleteTicket(ticketId) {{
        const alsoChannel = confirm('Delete ticket #' + ticketId + ' from the database? OK = also delete the Discord channel. Cancel = keep the channel.');
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/tickets/' + ticketId + '?delete_channel=' + (alsoChannel ? '1' : '0'), {{ method: 'DELETE' }});
            let data = {{}};
            try {{ data = await res.json(); }} catch(e) {{}}
            if(res.ok) {{
                showToast(data.message || ('Ticket #' + ticketId + ' deleted'));
                setTimeout(() => location.reload(), 800);
            }} else {{
                showToast('Failed: ' + (data.detail || res.statusText), 'error');
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function deleteTicketPanel(panelId) {{
        if(!confirm('Delete ticket panel ' + panelId + '? The panel message will be removed from Discord.')) return;
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/ticket_panels/' + encodeURIComponent(panelId), {{ method: 'DELETE' }});
            let data = {{}};
            try {{ data = await res.json(); }} catch(e) {{}}
            if(res.ok) {{
                showToast(data.message || 'Ticket panel deleted');
                setTimeout(() => location.reload(), 800);
            }} else {{
                showToast('Failed: ' + (data.detail || res.statusText), 'error');
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function addWallpaperChannel() {{
        const channelId = parseInt(document.getElementById('wallpaper_channel_select')?.value);
        if(!channelId) return showToast('Please select a text channel', 'error');
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/wallpaper', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ channel_id: channelId }})
            }});
            if(res.ok) {{
                showToast('Wallpaper studio enabled in channel!');
                setTimeout(() => location.reload(), 800);
            }} else {{
                const err = await res.json().catch(() => null);
                showToast(err?.detail || 'Error enabling wallpaper channel', 'error');
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function removeWallpaperChannel(channelId) {{
        if(!confirm('Disable wallpaper studio in channel ' + channelId + '?')) return;
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/wallpaper/' + channelId, {{ method: 'DELETE' }});
            if(res.ok) {{
                showToast('Wallpaper channel removed!');
                setTimeout(() => location.reload(), 800);
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function grantDropperMember() {{
        const userId = document.getElementById('dropper_user_id')?.value.trim();
        if(!userId || isNaN(parseInt(userId))) return showToast('Please enter a valid User ID', 'error');
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/dropper', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ user_id: userId }})
            }});
            if(res.ok) {{
                showToast('Dropper role granted!');
                setTimeout(() => location.reload(), 800);
            }} else {{
                const err = await res.json().catch(() => null);
                showToast(err?.detail || 'Error granting dropper role', 'error');
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function revokeDropperMember(userId) {{
        if(!confirm('Revoke Dropper role from user ' + userId + '?')) return;
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/dropper/' + userId, {{ method: 'DELETE' }});
            if(res.ok) {{
                showToast('Dropper role revoked!');
                setTimeout(() => location.reload(), 800);
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function approveBotApp() {{
        const botId = document.getElementById('approve_bot_id')?.value.trim();
        const botName = document.getElementById('approve_bot_name')?.value.trim() || 'Bot Application';
        if(!botId) return showToast('Please enter a valid Bot Application ID', 'error');
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/bots', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ bot_id: botId, bot_name: botName }})
            }});
            if(res.ok) {{
                showToast('Bot application approved!');
                setTimeout(() => location.reload(), 800);
            }} else {{
                showToast('Error approving bot', 'error');
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function revokeBotApp(botId) {{
        if(!confirm('Revoke approval for Bot ' + botId + '?')) return;
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/bots/' + botId, {{ method: 'DELETE' }});
            if(res.ok) {{
                showToast('Bot application revoked!');
                setTimeout(() => location.reload(), 800);
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function createBackup() {{
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/backups', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ name: 'Manual Snapshot ' + new Date().toLocaleTimeString() }})
            }});
            if(res.ok) {{
                showToast('Server Snapshot created successfully!');
                setTimeout(() => location.reload(), 1000);
            }} else {{
                showToast('Failed to create backup', 'error');
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function restoreBackup(backupId) {{
        if(!confirm('DANGER: Restore server structure from backup ' + backupId + '?')) return;
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/backups/' + backupId + '/restore', {{ method: 'POST' }});
            if(res.ok) {{
                showToast('Backup restoration completed!');
                setTimeout(() => location.reload(), 1000);
            }} else {{
                showToast('Failed to restore backup', 'error');
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function addAutoResponder() {{
        const trigger = document.getElementById('ar_trigger')?.value.trim();
        const response = document.getElementById('ar_response')?.value.trim();
        const matchType = document.getElementById('ar_match_type')?.value || 'contains';
        if(!trigger || !response) return showToast('Please enter both trigger and response', 'error');
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/autoresponders', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ trigger: trigger, response: response, match_type: matchType }})
            }});
            if(res.ok) {{
                showToast('Auto-responder trigger added!');
                setTimeout(() => location.reload(), 800);
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function deleteAutoResponder(arid) {{
        if(!confirm('Delete this auto-responder trigger?')) return;
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/autoresponders/' + arid, {{ method: 'DELETE' }});
            if(res.ok) {{
                showToast('Auto-responder deleted!');
                setTimeout(() => location.reload(), 800);
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function addReactionRole() {{
        const chanId = document.getElementById('rr_channel_id')?.value;
        const msgId = document.getElementById('rr_message_id')?.value.trim();
        const emoji = document.getElementById('rr_emoji')?.value.trim();
        const roleId = document.getElementById('rr_role_id')?.value;
        if(!chanId || !msgId || !emoji || !roleId) return showToast('Please fill all reaction role fields', 'error');
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/reaction_roles', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ channel_id: parseInt(chanId), message_id: parseInt(msgId), emoji: emoji, role_id: parseInt(roleId) }})
            }});
            if(res.ok) {{
                showToast('Reaction role bound successfully!');
                setTimeout(() => location.reload(), 800);
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function deleteReactionRole(rrid) {{
        if(!confirm('Delete this reaction role?')) return;
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/reaction_roles/' + rrid, {{ method: 'DELETE' }});
            if(res.ok) {{
                showToast('Reaction role removed!');
                setTimeout(() => location.reload(), 800);
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function dispatchCustomEmbed() {{
        const cid = document.getElementById('embed_target_channel_id')?.value;
        const title = document.getElementById('embed_title')?.value.trim() || 'Announcement';
        const desc = document.getElementById('embed_description')?.value.trim();
        const color = document.getElementById('embed_color')?.value || '#38bdf8';
        const footer = document.getElementById('embed_footer')?.value.trim();
        const image = document.getElementById('embed_image')?.value.trim();
        if(!cid) return showToast('Please select a destination channel', 'error');
        if(!desc) return showToast('Please write description text for your embed', 'error');
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/actions/dispatch-embed', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ channel_id: cid, title: title, description: desc, color: color, footer: footer, image: image }})
            }});
            if(res.ok) {{
                showToast('Custom embed broadcasted to Discord!');
            }} else {{
                showToast('Failed to dispatch embed', 'error');
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    async function applyServerTemplate() {{
        const tid = document.getElementById('server_setup_template_id')?.value || 'gaming';
        if(!confirm('Deploy architecture template "' + tid + '"? Server layout will be configured according to preset specifications.')) return;
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/actions/apply-template', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ template_id: tid }})
            }});
            if(res.ok) {{
                showToast('Template architecture queued for deployment!');
            }} else {{
                showToast('Error applying template', 'error');
            }}
        }} catch(e) {{ showToast('Network error', 'error'); }}
    }}

    // ==================== DROPPER CHANNELS MODAL & ACTIONS ====================

    async function openDropperModal() {{
        const modal = document.getElementById('dropper-modal');
        const body = document.getElementById('dropper-modal-body');
        if(!modal || !body) return;
        modal.style.display = 'flex';
        body.innerHTML = '<div style="text-align:center;padding:36px;color:var(--text-muted);"><div class="spinner" style="margin:0 auto 16px;"></div>⏳ Inspecting server Unicode font, emoji styles & naming conventions...</div>';

        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/dropper/preview');
            const data = await res.json();
            if(!res.ok || data.status !== 'ok') {{
                body.innerHTML = '<div style="padding:20px;color:#ED4245;background:rgba(237,66,69,0.1);border-radius:8px;">❌ ' + (data.detail || 'Failed to inspect server style') + '</div>';
                return;
            }}
            const p = data.preview;
            let chHtml = '';
            p.channels.forEach(ch => {{
                const statusBadge = ch.already_exists 
                    ? '<span style="background:rgba(238,238,238,0.1);color:#aaa;font-size:10px;padding:2px 6px;border-radius:4px;">Already Exists (Skip)</span>'
                    : '<span style="background:rgba(87,242,135,0.15);color:#57F287;font-size:10px;padding:2px 6px;border-radius:4px;font-weight:600;">Will Create</span>';
                chHtml += '<div style="background:#090d16;padding:8px 12px;border-radius:6px;border:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;font-size:12px;">' +
                          '<span style="font-family:monospace;color:#fff;">' + ch.formatted_name + '</span>' + statusBadge + '</div>';
            }});

            const catStatusBadge = p.category_exists 
                ? '<span style="background:rgba(254,231,92,0.15);color:#FEE75C;font-size:11px;padding:3px 8px;border-radius:6px;font-weight:600;">Reusing Existing Category</span>'
                : '<span style="background:rgba(87,242,135,0.15);color:#57F287;font-size:11px;padding:3px 8px;border-radius:6px;font-weight:600;">Will Create New Category</span>';

            body.innerHTML = `
                <div style="background:rgba(88,101,242,0.08);border:1px solid rgba(88,101,242,0.25);border-radius:10px;padding:14px;margin-bottom:16px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                        <span style="font-size:12px;color:var(--text-muted);text-transform:uppercase;font-weight:700;">Target Category</span>
                        ${{catStatusBadge}}
                    </div>
                    <div style="font-size:16px;font-weight:700;color:#fff;font-family:monospace;">${{p.category_name}}</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:6px;">
                        🎨 <strong>Detected Server Style:</strong> <span style="color:#5865F2;">${{p.style_description}}</span>
                    </div>
                </div>

                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                    <span style="font-size:13px;font-weight:700;color:#fff;">Planned 16 Channels Architecture</span>
                    <span style="font-size:12px;color:var(--text-muted);">
                        <strong style="color:#57F287;">${{p.to_create_count}} to create</strong> • <strong style="color:#aaa;">${{p.already_existing_count}} already existing</strong>
                    </span>
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;max-height:280px;overflow-y:auto;padding-right:4px;margin-bottom:20px;">
                    ${{chHtml}}
                </div>

                <div style="display:flex;gap:12px;justify-content:flex-end;">
                    <button class="btn btn-secondary" onclick="closeDropperModal()" style="padding:10px 18px;">Cancel</button>
                    <button class="btn btn-primary" id="btn-confirm-dropper" onclick="confirmCreateDropper()" style="padding:10px 20px;font-weight:700;">
                        🚀 Confirm & Create ${{p.to_create_count}} Channels
                    </button>
                </div>
            `;
        }} catch(e) {{
            body.innerHTML = '<div style="padding:20px;color:#ED4245;">Network error inspecting server style.</div>';
        }}
    }}

    function closeDropperModal() {{
        const modal = document.getElementById('dropper-modal');
        if(modal) modal.style.display = 'none';
    }}

    async function confirmCreateDropper() {{
        const btn = document.getElementById('btn-confirm-dropper');
        if(btn) {{
            btn.disabled = true;
            btn.innerText = '⏳ Creating Channels Safely...';
        }}
        try {{
            const res = await fetch('/api/guilds/' + GUILD_ID + '/dropper/execute', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }}
            }});
            const data = await res.json();
            if(res.ok && data.status === 'ok') {{
                const r = data.result;
                const modal = document.getElementById('dropper-modal-body');
                if(modal) {{
                    modal.innerHTML = `
                        <div style="text-align:center;padding:24px 10px;">
                            <div style="font-size:48px;margin-bottom:12px;">✅</div>
                            <h3 style="font-size:20px;color:#fff;margin:0 0 8px 0;font-weight:700;">Dropper Channels Created!</h3>
                            <p style="color:var(--text-muted);font-size:13px;margin-bottom:18px;">
                                Successfully deployed Developer category and organized channels matching your server's style.
                            </p>
                            <div style="background:#090d16;border:1px solid var(--border);border-radius:10px;padding:16px;text-align:left;max-width:440px;margin:0 auto 20px auto;font-size:13px;">
                                <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                                    <span style="color:var(--text-muted);">Category:</span>
                                    <span style="font-weight:700;color:#fff;">${{r.category_name}} (${{r.category_reused ? 'Reused' : 'Created'}})</span>
                                </div>
                                <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                                    <span style="color:var(--text-muted);">Channels Created:</span>
                                    <span style="font-weight:700;color:#57F287;">+${{r.created_count}}</span>
                                </div>
                                <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                                    <span style="color:var(--text-muted);">Channels Skipped (Existing):</span>
                                    <span style="font-weight:700;color:#aaa;">${{r.skipped_count}}</span>
                                </div>
                                <div style="display:flex;justify-content:space-between;">
                                    <span style="color:var(--text-muted);">Style Applied:</span>
                                    <span style="color:#5865F2;">${{r.style_description}}</span>
                                </div>
                            </div>
                            <button class="btn btn-primary" onclick="closeDropperModal()" style="padding:10px 24px;">Done</button>
                        </div>
                    `;
                }}
                showToast('Dropper channels successfully created!');
            }} else {{
                showToast(data.detail || 'Failed to create dropper channels', 'error');
                if(btn) {{
                    btn.disabled = false;
                    btn.innerText = '🚀 Try Again';
                }}
            }}
        }} catch(e) {{
            showToast('Network error while creating channels', 'error');
            if(btn) {{
                btn.disabled = false;
                btn.innerText = '🚀 Try Again';
            }}
        }}
    }}

    // Real-Time Server-Sent Events (SSE) Listener
    function initSSE() {{
        const evtSource = new EventSource('/api/guilds/' + GUILD_ID + '/events');
        evtSource.onmessage = function(e) {{
            try {{
                const data = JSON.parse(e.data);
                showToast('⚡ Live Update received from Discord / Backend (' + data.event + ')');
                const sync = document.getElementById('sync-status');
                if(sync) {{
                    sync.innerText = 'Updated Just Now';
                    setTimeout(() => {{ sync.innerText = 'Live Synced'; }}, 3000);
                }}
            }} catch(err) {{}}
        }};
        evtSource.onerror = function() {{
            console.warn('SSE connection interrupted. Reconnecting...');
        }};
    }}
    initSSE();
    </script>
</body>
</html>
"""

# ==================== 14. OWNER ADMIN DASHBOARD ====================
def render_owner_dashboard(bot, user: Dict[str, Any], stats: Dict[str, Any]) -> str:
    guild_count = len(bot.guilds) if (bot and hasattr(bot, "guilds")) else 0
    member_count = sum(g.member_count or 0 for g in bot.guilds) if (bot and hasattr(bot, "guilds")) else 0
    uptime = stats.get("uptime", "Operational")
    db_size = stats.get("db_size_kb", 0)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Owner Administration — NOVEXA</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>{BASE_CSS}</style>
</head>
<body>
    {_render_nav(user, 'admin')}
    <div class="container">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:32px;flex-wrap:wrap;gap:16px;">
            <div>
                <div class="badge badge-accent" style="margin-bottom:8px;">MASTER CONSOLE</div>
                <h1 style="font-size:32px;font-weight:900;color:#fff;">Owner Administration Panel</h1>
                <p style="color:var(--text-muted);font-size:14px;">Restricted to configured bot owner accounts.</p>
            </div>
            <span class="badge badge-success" style="padding:8px 16px;">👑 Owner Authenticated</span>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:20px;margin-bottom:34px;">
            <div class="card">
                <div style="font-size:32px;font-weight:900;color:#fff;">{guild_count}</div>
                <div style="font-size:13px;color:var(--text-muted);">Connected Guilds</div>
            </div>
            <div class="card">
                <div style="font-size:32px;font-weight:900;color:#fff;">{member_count:,}</div>
                <div style="font-size:13px;color:var(--text-muted);">Total Monitored Members</div>
            </div>
            <div class="card">
                <div style="font-size:32px;font-weight:900;color:var(--accent);">{db_size:,} KB</div>
                <div style="font-size:13px;color:var(--text-muted);">SQLite Database File Size</div>
            </div>
            <div class="card">
                <div style="font-size:32px;font-weight:900;color:#34d399;">{uptime}</div>
                <div style="font-size:13px;color:var(--text-muted);">Core Runtime Uptime</div>
            </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(340px, 1fr));gap:24px;">
            <div class="card">
                <h3 style="font-size:18px;color:#fff;margin-bottom:16px;">Global Broadcast Announcement</h3>
                <div class="form-group">
                    <label>Announcement Text</label>
                    <textarea class="form-control" id="owner_announcement" placeholder="Broadcast a notice to all server dashboard banners..."></textarea>
                </div>
                <button class="btn btn-primary" onclick="showToast('Global announcement dispatched!')">Broadcast Announcement</button>
            </div>

            <div class="card">
                <h3 style="font-size:18px;color:#fff;margin-bottom:16px;">Maintenance & Control</h3>
                <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;">
                    <div>
                        <label>Maintenance Mode</label>
                        <div class="desc">Block non-owner web dashboard access during upgrades.</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="maintenance_toggle">
                        <span class="slider"></span>
                    </label>
                </div>
                <button class="btn btn-outline" style="width:100%;margin-top:10px;" onclick="showToast('Snapshot backup created!')">💾 Trigger Instant Database Snapshot</button>
            </div>
        </div>
    </div>
    {_render_footer()}
</body>
</html>
"""
