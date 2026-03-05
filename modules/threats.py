"""
╔══════════════════════════════════════════════════════════════╗
║  XANA OS v4.0 — THREAT CORRIDOR ANALYSIS                      ║
╚══════════════════════════════════════════════════════════════╝

Monitors strategic maritime chokepoints and correlates with
real-time news intelligence for threat assessment.
"""

import streamlit as st
from modules.osint import OSINTEngine
from config import CACHE_TTL_NEWS

# ── Strategic Maritime Chokepoints ──────────────────────────

CHOKEPOINTS = [
    {
        "name": "Strait of Hormuz",
        "lat": 26.567, "lon": 56.250,
        "description": "Controls ~21% of global oil trade. Between Iran and Oman.",
        "threat_level": "HIGH",
        "daily_traffic": "~17 million barrels of oil per day",
        "keywords": ["Hormuz", "Iran", "Persian Gulf", "IRGC", "oil tanker Iran"],
        "radius_km": 120,
        "color": [255, 0, 60, 180],
    },
    {
        "name": "Strait of Malacca",
        "lat": 2.500, "lon": 101.000,
        "description": "Busiest shipping lane in the world. Between Malaysia and Indonesia.",
        "threat_level": "MEDIUM",
        "daily_traffic": "~25% of world trade passes through",
        "keywords": ["Malacca", "piracy Southeast Asia", "Singapore strait", "maritime security"],
        "radius_km": 150,
        "color": [255, 170, 0, 180],
    },
    {
        "name": "Suez Canal",
        "lat": 30.457, "lon": 32.349,
        "description": "Connects Mediterranean to Red Sea. ~12% of global trade.",
        "threat_level": "HIGH",
        "daily_traffic": "~50 ships/day, $10B+ in goods",
        "keywords": ["Suez Canal", "Egypt canal", "Red Sea shipping", "Suez blockage"],
        "radius_km": 80,
        "color": [255, 0, 60, 180],
    },
    {
        "name": "Bab el-Mandeb",
        "lat": 12.583, "lon": 43.333,
        "description": "Gate to the Red Sea. Between Yemen and Djibouti. Houthi attacks zone.",
        "threat_level": "CRITICAL",
        "daily_traffic": "~6.2 million barrels of oil per day",
        "keywords": ["Bab el-Mandeb", "Houthi", "Red Sea attack", "Yemen shipping", "Red Sea crisis"],
        "radius_km": 100,
        "color": [255, 0, 0, 220],
    },
    {
        "name": "Panama Canal",
        "lat": 9.080, "lon": -79.680,
        "description": "Connects Atlantic and Pacific. ~5% of world trade.",
        "threat_level": "LOW",
        "daily_traffic": "~35-40 ships/day",
        "keywords": ["Panama Canal", "Panama drought", "canal delays", "Panama shipping"],
        "radius_km": 60,
        "color": [0, 255, 136, 180],
    },
    {
        "name": "Taiwan Strait",
        "lat": 24.500, "lon": 119.500,
        "description": "Geopolitical flashpoint. ~88% of largest container ships transit here.",
        "threat_level": "HIGH",
        "daily_traffic": "Major semiconductor supply chain route",
        "keywords": ["Taiwan Strait", "China Taiwan", "PLA Navy", "Taiwan military", "cross-strait"],
        "radius_km": 150,
        "color": [255, 0, 60, 180],
    },
    {
        "name": "South China Sea",
        "lat": 14.000, "lon": 114.000,
        "description": "Disputed waters. $3.4 trillion in trade passes annually.",
        "threat_level": "HIGH",
        "daily_traffic": "~$3.4 trillion in trade annually",
        "keywords": ["South China Sea", "Spratly", "Paracel", "China maritime dispute", "SCS military"],
        "radius_km": 300,
        "color": [255, 0, 60, 150],
    },
    {
        "name": "Strait of Gibraltar",
        "lat": 35.960, "lon": -5.600,
        "description": "Gateway to Mediterranean. Between Spain and Morocco.",
        "threat_level": "LOW",
        "daily_traffic": "~300 ships/day",
        "keywords": ["Gibraltar", "Mediterranean shipping", "Gibraltar strait migration"],
        "radius_km": 80,
        "color": [0, 255, 136, 180],
    },
    {
        "name": "Bosphorus Strait",
        "lat": 41.120, "lon": 29.050,
        "description": "Controls Black Sea access. Turkey controls transit.",
        "threat_level": "MEDIUM",
        "daily_traffic": "~48,000 ships/year",
        "keywords": ["Bosphorus", "Turkey strait", "Black Sea shipping", "Montreux Convention"],
        "radius_km": 50,
        "color": [255, 170, 0, 180],
    },
    {
        "name": "GIUK Gap",
        "lat": 63.000, "lon": -15.000,
        "description": "Greenland-Iceland-UK gap. Strategic NATO submarine chokepoint.",
        "threat_level": "MEDIUM",
        "daily_traffic": "Key naval / submarine monitoring zone",
        "keywords": ["GIUK gap", "NATO submarine", "North Atlantic naval", "Russian submarine"],
        "radius_km": 200,
        "color": [255, 170, 0, 150],
    },
    {
        "name": "Cape of Good Hope",
        "lat": -34.357, "lon": 18.474,
        "description": "Alternative to Suez. Traffic surged due to Red Sea attacks.",
        "threat_level": "LOW",
        "daily_traffic": "Increasing as ships divert from Red Sea",
        "keywords": ["Cape of Good Hope", "Good Hope shipping", "Africa cape route", "Suez diversion"],
        "radius_km": 100,
        "color": [0, 255, 136, 180],
    },
    {
        "name": "Danish Straits",
        "lat": 55.600, "lon": 12.650,
        "description": "Baltic Sea access. Critical for European energy imports.",
        "threat_level": "MEDIUM",
        "daily_traffic": "~70,000 ships/year",
        "keywords": ["Danish Straits", "Baltic Sea", "Nord Stream", "Baltic pipeline", "Oresund"],
        "radius_km": 80,
        "color": [255, 170, 0, 180],
    },
]


def get_chokepoint_data():
    """Return chokepoint data as a list of dicts."""
    return CHOKEPOINTS


def get_threat_color(level):
    """Return color based on threat level."""
    colors = {
        "CRITICAL": [255, 0, 0, 220],
        "HIGH": [255, 0, 60, 180],
        "MEDIUM": [255, 170, 0, 180],
        "LOW": [0, 255, 136, 180],
    }
    return colors.get(level, [255, 255, 255, 180])


@st.cache_data(ttl=CACHE_TTL_NEWS, show_spinner=False)
def fetch_chokepoint_news(chokepoint_name, keywords):
    """Fetch news related to a specific chokepoint."""
    return OSINTEngine.fetch_geofenced_news(keywords, max_results=8)


def generate_threat_assessment(chokepoint, news_articles):
    """Generate a structured threat assessment for a chokepoint."""
    assessment = {
        "chokepoint": chokepoint["name"],
        "baseline_threat": chokepoint["threat_level"],
        "news_count": len(news_articles),
        "escalation_keywords": [],
        "assessment": "",
    }

    escalation_words = [
        "attack", "missile", "military", "conflict", "war", "explosion",
        "blockade", "closure", "threat", "navy", "deployment", "crisis",
        "sanctions", "embargo", "piracy", "hijack", "drone", "strike",
    ]

    for article in news_articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        for word in escalation_words:
            if word in text and word not in assessment["escalation_keywords"]:
                assessment["escalation_keywords"].append(word)

    n_escalation = len(assessment["escalation_keywords"])
    if n_escalation >= 5:
        assessment["current_threat"] = "CRITICAL"
        assessment["assessment"] = (
            f"CRITICAL escalation detected at {chokepoint['name']}. "
            f"{n_escalation} threat indicators found in recent news. "
            f"Keywords: {', '.join(assessment['escalation_keywords'][:8])}. "
            f"Recommend heightened monitoring and contingency activation."
        )
    elif n_escalation >= 3:
        assessment["current_threat"] = "HIGH"
        assessment["assessment"] = (
            f"Elevated threat level at {chokepoint['name']}. "
            f"{n_escalation} threat indicators detected. "
            f"Keywords: {', '.join(assessment['escalation_keywords'][:6])}. "
            f"Recommend increased SIGINT collection."
        )
    elif n_escalation >= 1:
        assessment["current_threat"] = "MEDIUM"
        assessment["assessment"] = (
            f"Moderate activity at {chokepoint['name']}. "
            f"Some threat indicators present: {', '.join(assessment['escalation_keywords'])}. "
            f"Standard monitoring recommended."
        )
    else:
        assessment["current_threat"] = chokepoint["threat_level"]
        assessment["assessment"] = (
            f"{chokepoint['name']} operating at baseline threat level ({chokepoint['threat_level']}). "
            f"No escalation indicators detected in current news cycle."
        )

    return assessment
