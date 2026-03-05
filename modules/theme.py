"""
╔══════════════════════════════════════════════════════════════╗
║  XANA OS v4.2 — SCI-FI HOLOGRAPHIC THEME                     ║
╚══════════════════════════════════════════════════════════════╝
"""

XANA_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&family=Rajdhani:wght@300;400;500;600;700&display=swap');

:root {
    --xana-cyan: #00f0ff;
    --xana-magenta: #ff00ff;
    --xana-green: #00ff88;
    --xana-amber: #ffaa00;
    --xana-red: #ff003c;
    --xana-dark: #0a0a0f;
    --xana-panel: rgba(10, 10, 20, 0.85);
    --xana-border: rgba(0, 240, 255, 0.15);
    --xana-glow: 0 0 20px rgba(0, 240, 255, 0.3);
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* ═══════════════════════════════════════════════════════════
   SIDEBAR — FULLY HIDDEN, FULL WIDTH MAIN CONTENT
   ═══════════════════════════════════════════════════════════ */

section[data-testid="stSidebar"],
[data-testid="stSidebar"],
div[data-testid="stSidebar"],
aside[data-testid="stSidebar"] {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    pointer-events: none !important;
}

/* Hide the sidebar collapse/expand toggle button */
[data-testid="collapsedControl"],
button[kind="header"],
.st-emotion-cache-zq5wmm {
    display: none !important;
}

/* Full-width main content */
.main .block-container {
    max-width: 100% !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    padding-top: 0 !important;
    margin-left: 0 !important;
}

section.main {
    margin-left: 0 !important;
}

.stApp {
    background: var(--xana-dark);
    background-image:
        radial-gradient(ellipse at 20% 50%, rgba(0, 240, 255, 0.03) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 20%, rgba(255, 0, 255, 0.02) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 80%, rgba(0, 255, 136, 0.02) 0%, transparent 50%);
    color: #c0d0e0;
}

/* ═══════════════════════════════════════════════════════════
   XANA COMMAND BRIDGE — TOP NAVIGATION BAR
   ═══════════════════════════════════════════════════════════ */

.xana-bridge {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 24px;
    background: linear-gradient(90deg, rgba(3,3,12,0.98), rgba(8,8,22,0.96));
    border-bottom: 1px solid rgba(0, 240, 255, 0.25);
    margin-bottom: 0;
    position: relative;
    overflow: hidden;
}

.xana-bridge::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--xana-cyan), var(--xana-magenta), transparent);
    opacity: 0.6;
}

.xana-bridge-left {
    display: flex;
    align-items: center;
    gap: 14px;
}

.xana-bridge-hex {
    font-size: 2.2rem;
    color: var(--xana-cyan);
    filter: drop-shadow(0 0 10px var(--xana-cyan)) drop-shadow(0 0 20px rgba(0,240,255,0.4));
    line-height: 1;
    animation: hex-pulse 3s ease-in-out infinite;
}

@keyframes hex-pulse {
    0%, 100% { filter: drop-shadow(0 0 8px var(--xana-cyan)); }
    50% { filter: drop-shadow(0 0 18px var(--xana-cyan)) drop-shadow(0 0 30px rgba(0,240,255,0.5)); }
}

.xana-bridge-name {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.5rem;
    font-weight: 900;
    background: linear-gradient(90deg, #00f0ff, #ff00ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 7px;
    display: block;
    line-height: 1.1;
}

.xana-bridge-ver {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.58rem;
    color: rgba(0, 240, 255, 0.45);
    letter-spacing: 3px;
    display: block;
    margin-top: 1px;
    text-transform: uppercase;
}

.xana-bridge-metrics {
    display: flex;
    gap: 4px;
    align-items: center;
}

.xana-sys-metric {
    text-align: center;
    padding: 5px 16px;
    border-left: 1px solid rgba(0, 240, 255, 0.12);
}

.xana-sys-val {
    display: block;
    font-family: 'Orbitron', sans-serif;
    font-size: 0.78rem;
    color: var(--xana-cyan);
    letter-spacing: 1px;
    text-shadow: 0 0 8px rgba(0,240,255,0.5);
}

.xana-sys-lbl {
    display: block;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.52rem;
    color: rgba(0, 240, 255, 0.38);
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 1px;
}

/* ═══════════════════════════════════════════════════════════
   MODULE NAV DOCK — BUTTON STRIP
   ═══════════════════════════════════════════════════════════ */

.xana-nav-dock-wrapper {
    background: rgba(4, 4, 14, 0.95);
    border-bottom: 1px solid rgba(0, 240, 255, 0.1);
    padding: 6px 24px 0 24px;
    display: flex;
    align-items: flex-end;
    gap: 2px;
    position: relative;
}

.xana-nav-dock-wrapper::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,240,255,0.08), rgba(255,0,255,0.06), transparent);
}

/* ── NAV BUTTONS — base style for all module buttons ─────── */
.xana-nav-dock-wrapper .stButton > button {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    color: rgba(0, 240, 255, 0.45) !important;
    font-family: 'Orbitron', sans-serif !important;
    font-size: 0.62rem !important;
    font-weight: 700 !important;
    letter-spacing: 2.5px !important;
    text-transform: uppercase !important;
    padding: 8px 14px 10px 14px !important;
    transition: all 0.25s ease !important;
    white-space: nowrap !important;
    box-shadow: none !important;
}

.xana-nav-dock-wrapper .stButton > button:hover {
    background: rgba(0, 240, 255, 0.06) !important;
    color: rgba(0, 240, 255, 0.85) !important;
    border-bottom: 2px solid rgba(0, 240, 255, 0.4) !important;
    box-shadow: none !important;
    transform: none !important;
}

/* ── ACTIVE MODULE BUTTON — injected dynamically per render  */
/* (see app.py active button CSS injection)                   */

/* ── NAV ACTION BUTTONS — PURGE & EXPORT ─────────────────── */
.xana-nav-action .stButton > button {
    background: transparent !important;
    border: 1px solid rgba(0, 240, 255, 0.18) !important;
    border-radius: 2px !important;
    color: rgba(0, 240, 255, 0.5) !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.6rem !important;
    letter-spacing: 1.5px !important;
    padding: 4px 10px !important;
    transition: all 0.2s ease !important;
    box-shadow: none !important;
}

.xana-nav-action .stButton > button:hover {
    border-color: rgba(0, 240, 255, 0.5) !important;
    color: var(--xana-cyan) !important;
    background: rgba(0, 240, 255, 0.06) !important;
    box-shadow: 0 0 8px rgba(0,240,255,0.2) !important;
    transform: none !important;
}

/* ═══════════════════════════════════════════════════════════
   TYPOGRAPHY
   ═══════════════════════════════════════════════════════════ */

h1, h2, h3 {
    font-family: 'Orbitron', sans-serif !important;
    background: linear-gradient(90deg, var(--xana-cyan), var(--xana-magenta));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-shadow: none;
}

/* ═══════════════════════════════════════════════════════════
   COMPONENT STYLES
   ═══════════════════════════════════════════════════════════ */

.stChatMessage {
    background: var(--xana-panel) !important;
    border: 1px solid var(--xana-border) !important;
    border-radius: 4px !important;
    backdrop-filter: blur(10px);
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(0, 240, 255, 0.05) !important;
    border: 1px solid rgba(0, 240, 255, 0.2) !important;
    color: #e0f0ff !important;
    font-family: 'Share Tech Mono', monospace !important;
    border-radius: 2px !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--xana-cyan) !important;
    box-shadow: var(--xana-glow) !important;
}

.stButton > button {
    background: linear-gradient(135deg, rgba(0,240,255,0.1), rgba(255,0,255,0.1)) !important;
    border: 1px solid var(--xana-cyan) !important;
    color: var(--xana-cyan) !important;
    font-family: 'Orbitron', sans-serif !important;
    font-size: 0.75rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    border-radius: 2px !important;
    transition: all 0.3s ease !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, rgba(0,240,255,0.25), rgba(255,0,255,0.25)) !important;
    box-shadow: var(--xana-glow) !important;
    transform: translateY(-1px);
}

[data-testid="stMetricValue"] {
    color: var(--xana-cyan) !important;
    font-family: 'Orbitron', sans-serif !important;
}

[data-testid="stMetricLabel"] {
    color: rgba(0, 240, 255, 0.6) !important;
    font-family: 'Share Tech Mono', monospace !important;
    text-transform: uppercase !important;
    font-size: 0.7rem !important;
    letter-spacing: 2px !important;
}

.streamlit-expanderHeader {
    background: rgba(0, 240, 255, 0.05) !important;
    border: 1px solid var(--xana-border) !important;
    font-family: 'Share Tech Mono', monospace !important;
    color: var(--xana-cyan) !important;
}

div[data-testid="stExpander"] {
    border: 1px solid var(--xana-border) !important;
    border-radius: 2px !important;
    background: var(--xana-panel) !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 0px;
    background: rgba(0, 240, 255, 0.03);
    border-bottom: 1px solid var(--xana-border);
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Orbitron', sans-serif !important;
    font-size: 0.7rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    color: rgba(0, 240, 255, 0.5) !important;
    border: none !important;
    padding: 12px 24px !important;
}

.stTabs [aria-selected="true"] {
    color: var(--xana-cyan) !important;
    border-bottom: 2px solid var(--xana-cyan) !important;
    background: rgba(0, 240, 255, 0.08) !important;
}

.stSlider [data-baseweb="slider"] [role="slider"] {
    background: var(--xana-cyan) !important;
}

.stSelectbox > div > div {
    background: rgba(0, 240, 255, 0.05) !important;
    border: 1px solid var(--xana-border) !important;
    color: #e0f0ff !important;
    font-family: 'Share Tech Mono', monospace !important;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--xana-dark); }
::-webkit-scrollbar-thumb { background: rgba(0,240,255,0.3); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--xana-cyan); }

/* ═══════════════════════════════════════════════════════════
   XANA CUSTOM CLASSES
   ═══════════════════════════════════════════════════════════ */

.xana-header {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.8rem;
    font-weight: 900;
    background: linear-gradient(90deg, #00f0ff, #ff00ff, #00ff88);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 4px;
    text-transform: uppercase;
    margin-bottom: 0;
}

.xana-sub {
    font-family: 'Share Tech Mono', monospace;
    color: rgba(0, 240, 255, 0.5);
    font-size: 0.75rem;
    letter-spacing: 3px;
    margin-top: -10px;
}

.sys-override {
    color: var(--xana-amber);
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.85rem;
    padding: 8px 12px;
    background: rgba(255, 170, 0, 0.08);
    border-left: 3px solid var(--xana-amber);
    margin: 8px 0;
}

.threat-high { color: var(--xana-red); font-weight: bold; }
.threat-med { color: var(--xana-amber); }
.threat-low { color: var(--xana-green); }

.osint-card {
    background: rgba(0, 240, 255, 0.04);
    border: 1px solid var(--xana-border);
    border-radius: 4px;
    padding: 16px;
    margin: 8px 0;
    backdrop-filter: blur(5px);
}

.intel-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin: 16px 0;
}

.intel-card {
    background: rgba(0, 240, 255, 0.04);
    border: 1px solid var(--xana-border);
    border-radius: 4px;
    padding: 16px;
    text-align: center;
    transition: all 0.3s ease;
}

.intel-card:hover {
    border-color: var(--xana-cyan);
    box-shadow: var(--xana-glow);
}

.intel-val {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.4rem;
    color: var(--xana-cyan);
}

.intel-label {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.65rem;
    color: rgba(0,240,255,0.5);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 4px;
}

.pulse-dot {
    display: inline-block;
    width: 8px; height: 8px;
    background: var(--xana-green);
    border-radius: 50%;
    animation: pulse 2s infinite;
    margin-right: 6px;
    vertical-align: middle;
}

.pulse-red {
    display: inline-block;
    width: 8px; height: 8px;
    background: var(--xana-red);
    border-radius: 50%;
    animation: pulse 1.5s infinite;
    margin-right: 6px;
    vertical-align: middle;
}

@keyframes pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 4px var(--xana-green); }
    50% { opacity: 0.4; box-shadow: 0 0 12px var(--xana-green); }
}

@keyframes scanline {
    0% { transform: translateY(-100%); }
    100% { transform: translateY(100vh); }
}

.scanline-overlay {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 2px;
    background: linear-gradient(90deg, transparent, rgba(0,240,255,0.1), transparent);
    animation: scanline 8s linear infinite;
    pointer-events: none;
    z-index: 9999;
}

.globe-controls {
    background: rgba(0, 240, 255, 0.03);
    border: 1px solid var(--xana-border);
    border-radius: 4px;
    padding: 12px;
    margin: 8px 0;
}

.feed-live {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.75rem;
    color: var(--xana-green);
    animation: pulse 2s infinite;
}

.threat-banner {
    background: rgba(255, 0, 60, 0.1);
    border: 1px solid rgba(255, 0, 60, 0.3);
    border-radius: 4px;
    padding: 12px 16px;
    margin: 8px 0;
    font-family: 'Share Tech Mono', monospace;
}

div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {
    gap: 12px;
}
</style>
<div class="scanline-overlay"></div>
"""
