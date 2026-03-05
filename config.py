"""
╔══════════════════════════════════════════════════════════════╗
║  XANA OS v4.0 — CONFIGURATION & CONSTANTS                    ║
╚══════════════════════════════════════════════════════════════╝
"""

import os

# ── Version ──────────────────────────────────────────────────
VERSION = "4.2.0"
CODENAME = "PROMETHEUS"

# ── LLM ─────────────────────────────────────────────────────
LLM_MODEL = "llama3.2"

# ── Database ─────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "xana_memory_db")
COLLECTION_NAME = "xana_memories"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── Map Styles (free, no API key needed) ─────────────────────
MAP_STYLE_DARK = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
MAP_STYLE_DARK_NOLABEL = "https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json"
MAP_STYLE_VOYAGER = "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"

# ── API Endpoints ────────────────────────────────────────────
OPENSKY_API = "https://opensky-network.org/api/states/all"
OPENSKY_BBOX_API = "https://opensky-network.org/api/states/all?lamin={lat1}&lomin={lon1}&lamax={lat2}&lomax={lon2}"
CELESTRAK_API = "https://celestrak.org/NORAD/elements/gp.php"
CISA_VULNS_API = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
IP_API = "http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
GEOCODING_API = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_API = "https://api.open-meteo.com/v1/forecast"
COINGECKO_API = "https://api.coingecko.com/api/v3/coins/markets"
GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"

# Real-time AIS (Finnish Digitraffic — free, no key, real vessel positions)
DIGITRAFFIC_AIS_API = "https://meri.digitraffic.fi/api/ais/v1/locations"
DIGITRAFFIC_VESSELS_API = "https://meri.digitraffic.fi/api/ais/v1/vessels"

# ── News Feeds ───────────────────────────────────────────────
NEWS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://feeds.reuters.com/reuters/topNews",
    "https://www.aljazeera.com/xml/rss/all.xml",
]

# ── Cache TTL (seconds) ─────────────────────────────────────
CACHE_TTL_FLIGHTS = 30
CACHE_TTL_VESSELS = 120
CACHE_TTL_SATELLITES = 120
CACHE_TTL_NEWS = 300
CACHE_TTL_THREATS = 1800
CACHE_TTL_WEATHER = 600
CACHE_TTL_CRYPTO = 600
CACHE_TTL_WEBCAMS = 3600
CACHE_TTL_REAL_AIS = 60
CACHE_TTL_VESSEL_REGISTRY = 3600
CACHE_TTL_POINT_WEATHER = 300
CACHE_TTL_IP = 3600
CACHE_TTL_DOMAIN = 3600

# ── Colors ───────────────────────────────────────────────────
COLORS = {
    "cyan": "#00f0ff",
    "magenta": "#ff00ff",
    "green": "#00ff88",
    "amber": "#ffaa00",
    "red": "#ff003c",
    "dark": "#0a0a0f",
    "panel": "rgba(10, 10, 20, 0.85)",
    "border": "rgba(0, 240, 255, 0.15)",
}

LAYER_COLORS = {
    "flights": [0, 200, 255, 200],
    "flights_arc": [0, 240, 255, 120],
    "vessels": [0, 255, 136, 200],
    "vessels_route": [0, 255, 136, 60],
    "satellites": [255, 170, 0, 220],
    "sat_orbit": [255, 170, 0, 40],
    "threats": [255, 0, 60, 180],
    "threat_zone": [255, 0, 60, 40],
    "webcams": [255, 0, 255, 200],
    "news": [255, 255, 255, 200],
}

# ── HTTP Headers ─────────────────────────────────────────────
HTTP_HEADERS = {
    "User-Agent": "XANA-OSINT/4.0 (Prometheus Intelligence Platform)"
}

# ── Satellite Groups to Track ────────────────────────────────
SATELLITE_GROUPS = {
    "stations": "Space Stations (ISS, Tiangong)",
    "active": "Active Satellites",
    "starlink": "Starlink Constellation",
    "gps-ops": "GPS Operational",
    "galileo": "Galileo Navigation",
    "weather": "Weather Satellites",
    "resource": "Earth Resources",
    "military": "Military Satellites",
    "geo": "Geostationary",
    "science": "Scientific",
    "noaa": "NOAA Satellites",
    "goes": "GOES Weather",
    "amateur": "Amateur Radio",
    "iridium-NEXT": "Iridium NEXT",
    "oneweb": "OneWeb",
}

# Satellite groups auto-loaded on the globe
GLOBE_DEFAULT_SAT_GROUPS = ["stations", "starlink", "gps-ops", "military", "weather"]

# ── Agent Capabilities ───────────────────────────────────────
AGENT_SAFE_COMMANDS = [
    "ls", "pwd", "whoami", "date", "uptime", "df", "free",
    "cat", "head", "tail", "wc", "echo", "hostname", "uname",
    "ip addr", "ifconfig", "ps aux", "neofetch", "ping -c 3",
    "nslookup", "dig", "traceroute", "curl -I", "nmap -sn",
]

APP_LAUNCH_MAP = {
    "code": "code", "vs code": "code", "vscode": "code",
    "notepad": "gedit", "text editor": "gedit",
    "calculator": "gnome-calculator",
    "files": "nautilus", "file manager": "nautilus",
    "terminal": "gnome-terminal",
    "browser": "xdg-open http://google.com",
    "firefox": "firefox", "chrome": "google-chrome",
    "spotify": "spotify", "discord": "discord",
    "slack": "slack", "obs": "obs",
    "blender": "blender", "gimp": "gimp",
}
