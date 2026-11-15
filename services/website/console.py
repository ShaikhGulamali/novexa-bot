"""NOVEXA - Command Console, Server Explorer and Leaderboards UI."""

from __future__ import annotations

import html
import json
from typing import Any, Dict, List, Optional

from services.website.templates import BASE_CSS, _render_nav

CONSOLE_CSS = """
.deck { max-width: 1380px; margin: 0 auto; padding: 26px 22px 60px; }
.deck-hero {
  display:flex; align-items:center; gap:18px; flex-wrap:wrap;
  padding:22px 24px; border-radius:20px; margin-bottom:22px;
  background:linear-gradient(120deg, rgba(255,45,85,.08), rgba(225,29,72,.10) 55%, rgba(0,0,0,0));
  border:1px solid var(--border); position:relative; overflow:hidden;
}
.deck-hero:before {
  content:""; position:absolute; inset:-40% -10% auto; height:220px;
  background:radial-gradient(closest-side, rgba(255,45,85,.16), transparent);
  animation:deckPulse 7s ease-in-out infinite;
}
@keyframes deckPulse { 0%,100%{opacity:.55} 50%{opacity:.95} }
.deck-hero img { width:58px;height:58px;border-radius:16px;border:2px solid rgba(255,45,85,.5); }
.deck-hero h1 { font-size:24px; font-weight:900; color:#fff; letter-spacing:-.4px; }
.deck-hero p { font-size:13px; color:var(--text-muted); }
.deck-tabs { display:flex; gap:8px; margin-left:auto; flex-wrap:wrap; }
.deck-tab {
  padding:9px 16px;border-radius:999px;font-size:13px;font-weight:700;cursor:pointer;
  border:1px solid var(--border); color:var(--text-muted); background:rgba(255,255,255,.02);
  transition:all .2s ease;
}
.deck-tab:hover { color:#fff; border-color:rgba(255,45,85,.45); transform:translateY(-1px); }
.deck-tab.active { color:#04121a; background:linear-gradient(135deg,var(--primary),var(--accent)); border-color:transparent; box-shadow:0 6px 22px rgba(255,45,85,.25); }
.deck-grid { display:grid; grid-template-columns:340px 1fr; gap:20px; align-items:start; }
.deck-panel { background:var(--bg-card); border:1px solid var(--border); border-radius:18px; padding:18px; backdrop-filter:blur(10px); }
.deck-panel h3 { font-size:13px; text-transform:uppercase; letter-spacing:1px; color:var(--text-dim); margin-bottom:12px; }
.cmd-search {
  width:100%; padding:11px 14px; border-radius:12px; border:1px solid var(--border);
  background:rgba(0,0,0,.35); color:#fff; font-size:13px; outline:none;
}
.cmd-search:focus { border-color:rgba(255,45,85,.6); box-shadow:0 0 0 3px rgba(255,45,85,.12); }
.cmd-list { max-height:62vh; overflow:auto; margin-top:12px; padding-right:4px; }
.cmd-cat { font-size:10px; font-weight:800; letter-spacing:1.2px; text-transform:uppercase; color:var(--text-dim); padding:12px 6px 4px; }
.cmd-item {
  display:flex; flex-direction:column; gap:2px; width:100%; text-align:left; cursor:pointer;
  padding:9px 11px; border-radius:10px; border:1px solid transparent; background:transparent;
  color:var(--text-main); font-size:13px; transition:all .16s ease;
}
.cmd-item:hover { background:rgba(255,45,85,.07); border-color:rgba(255,45,85,.2); }
.cmd-item.active { background:rgba(255,45,85,.12); border-color:rgba(255,45,85,.5); }
.cmd-item b { font-weight:800; color:#fff; }
.cmd-item span { font-size:11px; color:var(--text-dim); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.runner-head { display:flex; align-items:center; gap:12px; margin-bottom:14px; flex-wrap:wrap; }
.runner-slash { font-family:ui-monospace,monospace; font-size:12px; color:var(--accent); background:rgba(255,45,85,.1); padding:3px 9px; border-radius:7px; }
.field { margin-bottom:14px; }
.field label { display:block; font-size:12px; font-weight:700; color:var(--text-muted); margin-bottom:6px; }
.field label em { color:var(--danger); font-style:normal; }
.field small { display:block; color:var(--text-dim); font-size:11px; margin-top:4px; }
.field input, .field select, .field textarea {
  width:100%; padding:11px 12px; border-radius:11px; border:1px solid var(--border);
  background:rgba(0,0,0,.35); color:#fff; font-size:13px; outline:none; font-family:inherit;
}
.field input:focus, .field select:focus, .field textarea:focus { border-color:rgba(255,45,85,.6); }
.field textarea { min-height:84px; resize:vertical; }
.run-btn {
  padding:12px 24px; border-radius:12px; border:none; cursor:pointer; font-weight:800; font-size:14px;
  color:#03121a; background:linear-gradient(135deg,var(--primary),var(--accent)); box-shadow:0 8px 24px rgba(255,45,85,.28);
  transition:transform .16s ease, box-shadow .16s ease;
}
.run-btn:hover { transform:translateY(-2px); box-shadow:0 12px 30px rgba(255,45,85,.4); }
.run-btn:disabled { opacity:.55; cursor:wait; }
.out { margin-top:18px; display:flex; flex-direction:column; gap:10px; }
.out-msg { border:1px solid var(--border); border-left:3px solid var(--accent); border-radius:12px; padding:12px 14px; background:rgba(255,45,85,.04); font-size:13px; color:var(--text-main); white-space:pre-wrap; }
.out-msg.bad { border-left-color:var(--danger); background:rgba(239,68,68,.07); }
.out-title { font-size:12px; font-weight:800; color:#fff; margin-bottom:6px; }
.out-field { font-size:12px; color:var(--text-muted); margin-top:6px; }
.out-field b { color:#cbd5e1; }
.deck-empty { color:var(--text-dim); font-size:13px; padding:18px; text-align:center; }
.stat-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; margin-bottom:20px; }
.stat { background:var(--bg-card); border:1px solid var(--border); border-radius:16px; padding:16px; transition:transform .2s ease, border-color .2s ease; }
.stat:hover { transform:translateY(-3px); border-color:rgba(255,45,85,.35); }
.stat b { display:block; font-size:26px; font-weight:900; color:#fff; }
.stat span { font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:.8px; }
.data-table { width:100%; border-collapse:collapse; font-size:13px; }
.data-table th { text-align:left; font-size:10px; letter-spacing:1px; text-transform:uppercase; color:var(--text-dim); padding:10px 8px; border-bottom:1px solid var(--border); }
.data-table td { padding:10px 8px; border-bottom:1px solid rgba(255,255,255,.04); color:var(--text-main); vertical-align:middle; }
.data-table tr:hover td { background:rgba(255,45,85,.04); }
.pill { display:inline-block; padding:2px 9px; border-radius:999px; font-size:11px; font-weight:700; background:rgba(255,255,255,.06); color:var(--text-muted); }
.pill.ok { background:rgba(16,185,129,.15); color:#34d399; }
.pill.bot { background:rgba(225,29,72,.18); color:#a5b4fc; }
.ava { width:26px;height:26px;border-radius:50%;vertical-align:middle;margin-right:8px; }
.role-dot { display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px;vertical-align:middle; }
.muted { color:var(--text-dim); font-size:12px; }
.deck-body { display:none; }
.deck-body.active { display:block; animation:deckIn .28s ease; }
@keyframes deckIn { from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:none;} }
@media (max-width:980px) { .deck-grid { grid-template-columns:1fr; } .cmd-list{max-height:280px;} }
"""

_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__ — NOVEXA</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>__CSS__</style>
</head>
<body>
__NAV__
<div class="deck">
  <div class="deck-hero">
    <img src="__GICON__" alt="">
    <div>
      <h1>__GNAME__</h1>
      <p>__GSUB__</p>
    </div>
    <div class="deck-tabs">__TABS__</div>
  </div>
  __BODY__
</div>
</body>
</html>
"""


def _shell(user, title: str, guild, subtitle: str, tabs: str, body: str) -> str:
    page = _SHELL
    page = page.replace("__TITLE__", html.escape(title))
    page = page.replace("__CSS__", BASE_CSS + CONSOLE_CSS)
    page = page.replace("__NAV__", _render_nav(user, "dashboard"))
    page = page.replace("__GICON__", str(guild.icon.url) if guild.icon else "https://cdn.discordapp.com/embed/avatars/0.png")
    page = page.replace("__GNAME__", html.escape(guild.name))
    page = page.replace("__GSUB__", subtitle)
    page = page.replace("__TABS__", tabs)
    page = page.replace("__BODY__", body)
    return page


def _tabs(gid: int, active: str) -> str:
    items = [("console", "⌘ Command Console"), ("explorer", "🛰️ Explorer"), ("boards", "🏆 Leaderboards")]
    out = ""
    for key, label in items:
        cls = "deck-tab active" if key == active else "deck-tab"
        out += f'<a class="{cls}" href="/dashboard/{gid}/{key}">{label}</a>'
    out += f'<a class="deck-tab" href="/dashboard/{gid}">⚙️ Config</a>'
    return out


# ==================== CONSOLE ====================

_CONSOLE_BODY = """
<div class="deck-grid">
  <div class="deck-panel">
    <h3>__COUNT__ Commands</h3>
    <input class="cmd-search" id="cmd-search" placeholder="Search commands…" autocomplete="off">
    <div class="cmd-list" id="cmd-list"></div>
  </div>
  <div class="deck-panel">
    <h3>Console</h3>
    <div id="runner">
      <div class="deck-empty">Pick a command on the left. It runs against __GNAME__ through the bot process — same code path as Discord.</div>
    </div>
    <div class="out" id="out"></div>
  </div>
</div>
<script>
const GUILD_ID = "__GID__";
const CATALOG = __CATALOG__;
const opts = __OPTS__;
let active = null;

const list = document.getElementById('cmd-list');
const out = document.getElementById('out');
const runner = document.getElementById('runner');

function pill(text){ const s=document.createElement('span'); s.className='pill'; s.textContent=text; return s; }

function renderList(filter){
  const q = (filter||'').toLowerCase();
  list.innerHTML = '';
  let cat = '';
  const items = CATALOG.filter(c => !q || c.name.includes(q) || c.description.toLowerCase().includes(q) || c.category.toLowerCase().includes(q));
  if(!items.length){ list.innerHTML = '<div class="deck-empty">No match.</div>'; return; }
  for(const c of items){
    if(c.category !== cat){ cat = c.category; const h=document.createElement('div'); h.className='cmd-cat'; h.textContent=cat; list.appendChild(h); }
    const b = document.createElement('button');
    b.className = 'cmd-item' + (active && active.name===c.name ? ' active' : '');
    b.innerHTML = '<b>/'+c.name+'</b><span>'+c.description+'</span>';
    b.onclick = () => selectCommand(c);
    list.appendChild(b);
  }
}

function selectCommand(c){
  active = c;
  renderList(document.getElementById('cmd-search').value);
  out.innerHTML = '';
  let h = '<div class="runner-head"><span class="runner-slash">/'+c.name+'</span><span class="muted">'+c.category+'</span></div>';
  h += '<p class="muted" style="margin-bottom:16px;">'+c.description+'</p>';
  if(!c.options.length){ h += '<p class="muted">No options — runs immediately.</p>'; }
  for(const o of c.options){
    h += '<div class="field"><label>'+o.name+(o.required?' <em>*</em>':'')+'</label>';
    if(o.choices.length){
      h += '<select id="f-'+o.name+'"><option value="">—</option>';
      for(const ch of o.choices){ h += '<option value="'+ch.value+'">'+ch.name+'</option>'; }
      h += '</select>';
    } else if(o.type==='role'){
      h += '<select id="f-'+o.name+'"><option value="">—</option>'+opts.roles.map(r=>'<option value="'+r.id+'">@'+r.name+'</option>').join('')+'</select>';
    } else if(o.type==='channel'){
      h += '<select id="f-'+o.name+'"><option value="">—</option>'+opts.channels.map(r=>'<option value="'+r.id+'">#'+r.name+'</option>').join('')+'</select>';
    } else if(o.type==='user' || o.type==='mentionable'){
      h += '<input id="f-'+o.name+'" placeholder="User ID">';
    } else if(o.type==='boolean'){
      h += '<select id="f-'+o.name+'"><option value="">—</option><option value="true">true</option><option value="false">false</option></select>';
    } else if(o.type==='integer' || o.type==='number'){
      h += '<input id="f-'+o.name+'" type="number" placeholder="'+o.type+'">';
    } else {
      h += '<input id="f-'+o.name+'" placeholder="'+o.type+'">';
    }
    if(o.description) h += '<small>'+o.description+'</small>';
    h += '</div>';
  }
  h += '<button class="run-btn" id="run">▶ Run command</button>';
  runner.innerHTML = h;
  document.getElementById('run').onclick = run;
}

async function run(){
  if(!active) return;
  const btn = document.getElementById('run');
  btn.disabled = true; btn.textContent = 'Running…';
  const payload = {name: active.name, options: {}};
  for(const o of active.options){
    const el = document.getElementById('f-'+o.name);
    if(el && el.value !== '') payload.options[o.name] = el.value;
  }
  out.innerHTML = '';
  try {
    const res = await fetch('/api/guilds/'+GUILD_ID+'/commands/run', {
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)
    });
    const data = await res.json();
    if(!data.ok){ showMsg(data.error || 'Command failed', true); }
    else if(!data.messages || !data.messages.length){ showMsg('Executed. No text response was produced.', false); }
    else { for(const m of data.messages) showCaptured(m); }
  } catch(e){ showMsg('Network error: '+e.message, true); }
  btn.disabled = false; btn.textContent = '▶ Run command';
}

function showMsg(text, bad){
  const d = document.createElement('div');
  d.className = 'out-msg' + (bad?' bad':'');
  d.textContent = text;
  out.appendChild(d);
}

function showCaptured(m){
  const d = document.createElement('div');
  d.className = 'out-msg';
  let h = '';
  if(m.content) h += '<div>'+escapeHtml(m.content)+'</div>';
  for(const e of (m.embeds||[])){
    h += '<div class="out-title">'+(e.title?escapeHtml(e.title):'Embed')+'</div>';
    if(e.description) h += '<div>'+escapeHtml(e.description)+'</div>';
    for(const f of (e.fields||[])) h += '<div class="out-field"><b>'+escapeHtml(f.name)+':</b> '+escapeHtml(f.value)+'</div>';
    if(e.footer && e.footer.text) h += '<div class="out-field muted">'+escapeHtml(e.footer.text)+'</div>';
  }
  if(m.has_view) h += '<div class="out-field muted">Interactive components attached — open Discord to press them.</div>';
  d.innerHTML = h || '<span class="muted">(empty response)</span>';
  out.appendChild(d);
}

function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

document.getElementById('cmd-search').addEventListener('input', e => renderList(e.target.value));
renderList('');
</script>
"""


def render_console(bot, user, guild, catalog: List[Dict[str, Any]]) -> str:
    gid = guild.id
    opts = {
        "roles": [{"id": str(r.id), "name": r.name} for r in sorted(guild.roles, key=lambda r: r.position, reverse=True) if not r.is_default()],
        "channels": [{"id": str(c.id), "name": c.name} for c in sorted(guild.text_channels, key=lambda c: c.position)],
    }
    body = (_CONSOLE_BODY
            .replace("__COUNT__", str(len(catalog)))
            .replace("__GNAME__", html.escape(guild.name))
            .replace("__GID__", str(gid))
            .replace("__CATALOG__", json.dumps(catalog).replace("</", "<\\/"))
            .replace("__OPTS__", json.dumps(opts).replace("</", "<\\/")))
    return _shell(user, "Command Console", guild,
                  f"{len(catalog)} live commands · executed inside the bot process",
                  _tabs(gid, "console"), body)


# ==================== EXPLORER ====================

_EXPLORER_BODY = """
<div class="stat-grid" id="stats"></div>

<div class="deck-body active" id="view-members">
  <div class="deck-panel">
    <h3>Members <input class="cmd-search" id="member-search" placeholder="Filter members…" style="max-width:280px;display:inline-block;margin-left:12px;padding:7px 12px;"></h3>
    <div style="max-height:60vh;overflow:auto;">
      <table class="data-table"><thead><tr><th>Member</th><th>Top Role</th><th>Status</th><th>Joined</th><th>ID</th></tr></thead><tbody id="member-rows"><tr><td colspan="5" class="muted">Loading…</td></tr></tbody></table>
    </div>
  </div>
</div>

<div class="deck-body active" id="view-roles">
  <div class="deck-panel" style="margin-top:20px;">
    <h3>Roles</h3>
    <div style="max-height:52vh;overflow:auto;">
      <table class="data-table"><thead><tr><th>Role</th><th>Members</th><th>Position</th><th>Flags</th></tr></thead><tbody id="role-rows"></tbody></table>
    </div>
  </div>
</div>

<div class="deck-body active" id="view-channels">
  <div class="deck-panel" style="margin-top:20px;">
    <h3>Channels</h3>
    <div style="max-height:52vh;overflow:auto;">
      <table class="data-table"><thead><tr><th>Channel</th><th>Type</th><th>Category</th><th>Notes</th></tr></thead><tbody id="chan-rows"></tbody></table>
    </div>
  </div>
</div>

<script>
const GUILD_ID = "__GID__";

function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function stat(v, label){
  return '<div class="stat"><b>'+esc(v)+'</b><span>'+esc(label)+'</span></div>';
}

async function load(){
  const res = await fetch('/api/guilds/'+GUILD_ID+'/live');
  const d = await res.json();
  const g = d.guild;
  document.getElementById('stats').innerHTML =
    stat(g.member_count.toLocaleString(),'Members') +
    stat(g.online_count.toLocaleString(),'Online') +
    stat(g.bot_count,'Bots') +
    stat(g.in_voice,'In Voice') +
    stat(g.text_channels,'Text Channels') +
    stat(g.voice_channels,'Voice Channels') +
    stat(g.role_count,'Roles') +
    stat(g.boost_level,'Boost Level');

  renderMembers(d.members);
  document.getElementById('member-search').addEventListener('input', e => renderMembers(d.members, e.target.value));

  document.getElementById('role-rows').innerHTML = g.roles.map(r =>
    '<tr><td><span class="role-dot" style="background:'+r.color+'"></span>'+esc(r.name)+'</td><td>'+r.members+'</td><td>'+r.position+'</td><td>'+
    (r.hoist?'<span class="pill">hoist</span> ':'') + (r.managed?'<span class="pill bot">managed</span> ':'') + (r.mentionable?'<span class="pill ok">mentionable</span>':'') +
    '</td></tr>').join('');

  document.getElementById('chan-rows').innerHTML = g.channels.map(c =>
    '<tr><td>'+ (c.type==='text'?'#':c.type==='voice'?'🔊':'📁') +' '+esc(c.name)+'</td><td><span class="pill">'+c.type+'</span></td><td>'+esc(c.category||'—')+'</td><td class="muted">'+
    (c.topic?esc(c.topic):(c.slowmode?('slowmode '+c.slowmode+'s'):(c.nsfw?'nsfw':'')))+'</td></tr>').join('');
}

function renderMembers(members, filter){
  const q = (filter||'').toLowerCase();
  const rows = members.filter(m => !q || m.display.toLowerCase().includes(q) || m.id.includes(q));
  document.getElementById('member-rows').innerHTML = rows.map(m =>
    '<tr><td><img class="ava" src="'+m.avatar+'">'+esc(m.display)+' '+(m.bot?'<span class="pill bot">bot</span>':'')+'</td><td>'+esc(m.top_role)+'</td><td><span class="pill '+(m.status!=='offline'?'ok':'')+'">'+m.status+'</span></td><td class="muted">'+esc((m.joined_at||'').slice(0,10))+'</td><td class="muted">'+m.id+'</td></tr>'
  ).join('') || '<tr><td colspan="5" class="muted">No match.</td></tr>';
}

load();
</script>
"""


def render_explorer(bot, user, guild) -> str:
    gid = guild.id
    body = _EXPLORER_BODY.replace("__GID__", str(gid))
    return _shell(user, "Server Explorer", guild,
                  "Live member, role and channel state read straight from the gateway cache",
                  _tabs(gid, "explorer"), body)


# ==================== LEADERBOARDS ====================

def render_leaderboards(bot, user, guild, boards: Dict[str, List[Dict[str, Any]]]) -> str:
    gid = guild.id
    sections = ""
    titles = {"wealth": "💰 Net Worth", "levels": "📈 Levels", "hunters": "🏹 Hunts", "battles": "⚔️ Battles Won"}
    for key, rows in boards.items():
        body_rows = ""
        for r in rows:
            extra = ""
            if key == "wealth":
                extra = f'<span class="muted">wallet {int(r["extra"].get("wallet", 0)):,} · bank {int(r["extra"].get("bank", 0)):,} · 💎 {int(r["extra"].get("gems", 0)):,}</span>'
            elif key == "levels":
                extra = f'<span class="muted">{int(r["extra"].get("xp", 0)):,} XP · {int(r["extra"].get("messages_count", 0)):,} msgs</span>'
            avatar = f'<img class="ava" src="{r["avatar"]}">' if r["avatar"] else ""
            body_rows += (
                f'<tr><td class="muted">#{r["rank"]}</td><td>{avatar}{html.escape(r["name"])}</td>'
                f'<td><b>{int(r["score"]):,}</b></td><td>{extra}</td></tr>'
            )
        if not body_rows:
            body_rows = '<tr><td colspan="4" class="muted">No data yet — run a few commands in Discord.</td></tr>'
        sections += f"""
        <div class="deck-panel" style="margin-bottom:20px;">
          <h3>{titles.get(key, key)}</h3>
          <table class="data-table"><thead><tr><th>#</th><th>Member</th><th>Score</th><th>Details</th></tr></thead>
          <tbody>{body_rows}</tbody></table>
        </div>
        """
    return _shell(user, "Leaderboards", guild,
                  "Economy, leveling and RPG standings pulled from the bot database",
                  _tabs(gid, "boards"), sections)
