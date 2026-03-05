"""
╔══════════════════════════════════════════════════════════════╗
║  X A N A   O S   v 4 . 2   —   P R O M E T H E U S           ║
║                                                              ║
║  Next-Generation Intelligence Platform                       ║
║  3D Globe · Live Feeds · OSINT · Agentic AI · Threat Intel   ║
║                                                              ║
║  FREE REAL-TIME DATA — NO API KEYS REQUIRED                  ║
║  ✈️  Aircraft  → OpenSky   🚢  Vessels → Finnish AIS        ║
║  🛰️  Satellites → CelesTrak  🌤️  Weather → Open-Meteo       ║
╚══════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import streamlit.components.v1 as components
import time
import datetime
import json
import numpy as np
import ollama
import plotly.graph_objects as go
from collections import Counter

from config import VERSION, CODENAME, LLM_MODEL, SATELLITE_GROUPS, GLOBE_DEFAULT_SAT_GROUPS
from modules.theme import XANA_CSS
from modules.database import (
    load_db, get_collection_stats, query_memories,
    query_memories_with_embeddings, build_context_string, format_uptime,
)
from modules.osint import OSINTEngine
from modules.agents import AgentRouter, PhantomProtocol, ReconAgent, EntityNexus
from modules.viz import (
    build_3d_neural_map, build_2d_cluster_map,
    build_temporal_heatmap, build_entity_graph, PLOTLY_DARK_THEME,
)
from modules.feeds import (
    FlightTracker, VesselTracker, SatelliteTracker,
    WebcamIntel, WeatherService,
)
from modules.threats import (
    get_chokepoint_data, fetch_chokepoint_news,
    generate_threat_assessment, CHOKEPOINTS,
)
from modules.globe import render_globe, render_globe_stats

# ╔══════════════════════════════════════════════════════════════╗
# ║  PAGE CONFIG & GLOBAL STATE                                  ║
# ╚══════════════════════════════════════════════════════════════╝

st.set_page_config(
    page_title=f"XANA OS v{VERSION}",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DEFAULTS = {
    "messages": [],
    "boot_time": time.time(),
    "osint_cache": {},
    "command_history": [],
    "threat_feed_cache": None,
    "threat_feed_ts": 0,
    "neural_map_cache": None,
    "app_mode": "⬡ ORACLE — Neural Chat",
    "globe_layers": {
        "flights": True, "vessels": True, "satellites": True,
        "sea_routes": True, "chokepoints": True, "webcams": True,
    },
    "sat_groups": GLOBE_DEFAULT_SAT_GROUPS,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown(XANA_CSS, unsafe_allow_html=True)

# ╔══════════════════════════════════════════════════════════════╗
# ║  COMMAND BRIDGE — XANA TOP NAVIGATION                        ║
# ╚══════════════════════════════════════════════════════════════╝

_MODULES = [
    ("GLOBE",      "⬡ GLOBE — Command Center"),
    ("ORACLE",     "⬡ ORACLE — Neural Chat"),
    ("PHANTOM",    "⬡ PHANTOM — Auto-Investigate"),
    ("ARCHIVE",    "⬡ ARCHIVE — Vector Search"),
    ("NEURAL_MAP", "⬡ NEURAL MAP — 3D Graph"),
    ("DOSSIER",    "⬡ DOSSIER — Intel Profile"),
    ("OSINT",      "⬡ OSINT — World Intelligence"),
    ("CHRONOS",    "⬡ CHRONOS — Temporal Analysis"),
]
_FULL_TO_SHORT = {full: short for short, full in _MODULES}

_active_short = _FULL_TO_SHORT.get(st.session_state.app_mode, "ORACLE")

# ── Command Bridge Header ──────────────────────────────────────
st.markdown(f"""
<div class="xana-bridge">
  <div class="xana-bridge-left">
    <span class="xana-bridge-hex">⬡</span>
    <div>
      <span class="xana-bridge-name">XANA</span>
      <span class="xana-bridge-ver">PROMETHEUS v{VERSION} · INTELLIGENCE PLATFORM</span>
    </div>
  </div>
  <div class="xana-bridge-metrics">
    <div class="xana-sys-metric">
      <span class="xana-sys-val"><span class="pulse-dot"></span>ONLINE</span>
      <span class="xana-sys-lbl">STATUS</span>
    </div>
    <div class="xana-sys-metric">
      <span class="xana-sys-val">{LLM_MODEL.upper()}</span>
      <span class="xana-sys-lbl">MODEL</span>
    </div>
    <div class="xana-sys-metric">
      <span class="xana-sys-val">{format_uptime(st.session_state.boot_time)}</span>
      <span class="xana-sys-lbl">UPTIME</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Active module glow ─────────────────────────────────────────
st.markdown(f"""<style>
[data-testid="baseButton-nav_{_active_short}"] {{
    color: #ffffff !important;
    border-bottom: 2px solid var(--xana-cyan) !important;
    background: rgba(0, 240, 255, 0.08) !important;
    text-shadow: 0 0 10px rgba(0,240,255,0.8) !important;
}}
</style>""", unsafe_allow_html=True)

# ── Module Nav Dock ────────────────────────────────────────────
st.markdown('<div class="xana-nav-dock-wrapper">', unsafe_allow_html=True)
_nav_cols = st.columns(len(_MODULES))
for _i, (_short, _full) in enumerate(_MODULES):
    with _nav_cols[_i]:
        if st.button(f"⬡ {_short.replace('_', ' ')}", key=f"nav_{_short}", use_container_width=True):
            st.session_state.app_mode = _full
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ── Action bar ─────────────────────────────────────────────────
st.markdown('<div class="xana-nav-action">', unsafe_allow_html=True)
_gap, _purge_col, _export_col, _hist_col = st.columns([5, 1, 1, 1])
with _purge_col:
    if st.button("⬡ PURGE RAM", key="purge_btn", use_container_width=True):
        st.session_state.messages = []
        st.session_state.osint_cache = {}
        st.rerun()
with _export_col:
    if st.button("⬡ EXPORT LOG", key="export_btn", use_container_width=True):
        if st.session_state.messages:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"xana_chat_export_{ts}.json"
            with open(path, "w") as f:
                json.dump(st.session_state.messages, f, indent=2)
            st.success(f"Exported → {path}")
with _hist_col:
    if st.session_state.command_history:
        with st.expander("⬡ HISTORY", expanded=False):
            for _cmd in st.session_state.command_history[-10:]:
                st.markdown(
                    f'<span style="font-family: Share Tech Mono; font-size: 0.7rem; '
                    f'color: rgba(0,240,255,0.4);">▸ {_cmd}</span>',
                    unsafe_allow_html=True,
                )
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

app_mode = st.session_state.app_mode

# ╔══════════════════════════════════════════════════════════════╗
# ║  DATABASE LOAD — non-blocking (GLOBE works without DB)       ║
# ╚══════════════════════════════════════════════════════════════╝

db_available = False
collection = None
mem_count = 0

try:
    collection = load_db()
    if collection is not None:
        stats = get_collection_stats(collection)
        mem_count = stats["count"]
        db_available = True
except Exception as e:
    db_available = False
    mem_count = 0
    st.warning(f"⬡ DB OFFLINE: {str(e)[:80]}")


# ╔══════════════════════════════════════════════════════════════╗
# ║  MODULE: GLOBE — Unified Intelligence Command Center         ║
# ║                                                              ║
# ║  LIVE: Flights · Vessels (Real AIS) · Satellites (Multi-Grp) ║
# ║        Weather · Webcams · Threat Corridors                  ║
# ╚══════════════════════════════════════════════════════════════╝

if app_mode == "⬡ GLOBE — Command Center":
    st.markdown('<p class="xana-header">GLOBE COMMAND CENTER</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="xana-sub">LIVE FEEDS · REAL AIS VESSELS · STARLINK + MILITARY SATS · '
        'WEATHER OVERLAY · PUBLIC CAMS · THREAT CORRIDORS</p>',
        unsafe_allow_html=True,
    )

    # ── Layer Controls ───────────────────────────────────────
    ctrl_cols = st.columns(7)
    layers = st.session_state.globe_layers

    with ctrl_cols[0]:
        layers["flights"] = st.checkbox("✈️ Aircraft", value=layers.get("flights", True))
    with ctrl_cols[1]:
        layers["vessels"] = st.checkbox("🚢 Vessels", value=layers.get("vessels", True))
    with ctrl_cols[2]:
        layers["satellites"] = st.checkbox("🛰️ Satellites", value=layers.get("satellites", True))
    with ctrl_cols[3]:
        layers["sea_routes"] = st.checkbox("🌊 Sea Routes", value=layers.get("sea_routes", True))
    with ctrl_cols[4]:
        layers["chokepoints"] = st.checkbox("⚠️ Threats", value=layers.get("chokepoints", True))
    with ctrl_cols[5]:
        layers["webcams"] = st.checkbox("📷 Webcams", value=layers.get("webcams", True))
    with ctrl_cols[6]:
        view_preset = st.selectbox(
            "VIEW",
            ["global", "europe", "asia", "middle_east", "americas", "africa", "pacific", "arctic"],
            label_visibility="collapsed",
        )

    # ── Satellite group selector + limits ────────────────────
    adv_cols = st.columns([3, 1, 1])
    with adv_cols[0]:
        sat_groups_sel = st.multiselect(
            "Satellite Groups",
            options=list(SATELLITE_GROUPS.keys()),
            default=st.session_state.sat_groups,
            format_func=lambda x: f"{x.upper()} — {SATELLITE_GROUPS[x]}",
            label_visibility="collapsed",
        )
        if sat_groups_sel:
            st.session_state.sat_groups = sat_groups_sel
    with adv_cols[1]:
        sat_limit = st.slider("Sats/group", 10, 200, 60, label_visibility="collapsed")
    with adv_cols[2]:
        auto_refresh = st.checkbox("🔄 Auto-refresh", value=False)

    # ── Fetch ALL live data ──────────────────────────────────
    with st.spinner("⬡ Acquiring live intelligence feeds…"):
        flights_df = FlightTracker.fetch_all() if layers["flights"] else None

        vessels_df = VesselTracker.get_combined_vessels() if layers["vessels"] else None

        active_groups = st.session_state.sat_groups or GLOBE_DEFAULT_SAT_GROUPS
        satellites_df = SatelliteTracker.fetch_multi_group(
            groups=active_groups, limit_per_group=sat_limit,
        ) if layers["satellites"] else None

        sea_routes = VesselTracker.get_sea_routes() if layers["sea_routes"] else None
        chokepoints = get_chokepoint_data() if layers["chokepoints"] else None
        webcams_df = WebcamIntel.get_webcams() if layers["webcams"] else None

    # ── Render Globe ─────────────────────────────────────────
    render_globe(
        flights_df=flights_df,
        vessels_df=vessels_df,
        satellites_df=satellites_df,
        sea_routes=sea_routes,
        chokepoints=chokepoints,
        webcams_df=webcams_df,
        layers_enabled=layers,
        view_preset=view_preset,
        height=720,
    )

    # ── Live Stats ───────────────────────────────────────────
    render_globe_stats(flights_df, vessels_df, satellites_df, chokepoints)

    # ── Data source badges ───────────────────────────────────
    real_ais_count = 0
    sim_count = 0
    if vessels_df is not None and not vessels_df.empty and "source" in vessels_df.columns:
        real_ais_count = len(vessels_df[vessels_df["source"] == "real"])
        sim_count = len(vessels_df[vessels_df["source"] == "simulation"])

    military_flights = 0
    if flights_df is not None and not flights_df.empty and "aircraft_type" in flights_df.columns:
        military_flights = len(flights_df[flights_df["aircraft_type"] == "Military"])

    starlink_count = 0
    military_sats = 0
    if satellites_df is not None and not satellites_df.empty and "group" in satellites_df.columns:
        starlink_count = len(satellites_df[satellites_df["group"] == "starlink"])
        military_sats = len(satellites_df[satellites_df["group"] == "military"])

    badge_cols = st.columns(5)
    badge_cols[0].markdown(
        f'<span style="font-family: Share Tech Mono; font-size: 0.7rem; color: #00ff88;">'
        f'🟢 {real_ais_count} REAL AIS vessels (Baltic)</span>', unsafe_allow_html=True,
    )
    badge_cols[1].markdown(
        f'<span style="font-family: Share Tech Mono; font-size: 0.7rem; color: rgba(0,255,136,0.5);">'
        f'⚪ {sim_count} simulated (global lanes)</span>', unsafe_allow_html=True,
    )
    badge_cols[2].markdown(
        f'<span style="font-family: Share Tech Mono; font-size: 0.7rem; color: #ff003c;">'
        f'🔴 {military_flights} military aircraft detected</span>', unsafe_allow_html=True,
    )
    badge_cols[3].markdown(
        f'<span style="font-family: Share Tech Mono; font-size: 0.7rem; color: #ffaa00;">'
        f'🛰️ {starlink_count} Starlink tracked</span>', unsafe_allow_html=True,
    )
    badge_cols[4].markdown(
        f'<span style="font-family: Share Tech Mono; font-size: 0.7rem; color: #ffaa00;">'
        f'🎖️ {military_sats} military sats</span>', unsafe_allow_html=True,
    )

    # ╔════════════════════════════════════════════════════════╗
    # ║  DETAIL TABS — Select entities for weather + intel     ║
    # ╚════════════════════════════════════════════════════════╝

    st.markdown("---")
    tab_flights, tab_vessels, tab_sats, tab_threats, tab_cams, tab_lookup = st.tabs([
        "✈️ FLIGHTS", "🚢 VESSELS", "🛰️ SATELLITES",
        "⚠️ THREATS", "📷 WEBCAMS", "🔍 LOOKUP",
    ])

    # ── FLIGHTS TAB ──────────────────────────────────────────
    with tab_flights:
        if flights_df is not None and not flights_df.empty:
            summary = FlightTracker.get_flight_summary(flights_df)
            fc1, fc2, fc3, fc4, fc5 = st.columns(5)
            fc1.metric("TOTAL", f"{summary.get('total_aircraft', 0):,}")
            fc2.metric("COUNTRIES", summary.get("countries", 0))
            fc3.metric("MILITARY", summary.get("military_count", 0))
            fc4.metric("CARGO", summary.get("cargo_count", 0))
            fc5.metric("AVG ALT", f"{summary.get('avg_altitude', 0):,.0f}m")

            # Aircraft type breakdown
            type_bd = summary.get("type_breakdown", {})
            if type_bd:
                fig_types = go.Figure(go.Bar(
                    x=list(type_bd.values()), y=list(type_bd.keys()), orientation="h",
                    marker=dict(
                        color=list(type_bd.values()),
                        colorscale=[[0, "#0a0a2a"], [0.5, "#00f0ff"], [1, "#ff003c"]],
                    ),
                ))
                fig_types.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10), height=200,
                    xaxis=dict(gridcolor="rgba(0,240,255,0.05)", color="rgba(0,240,255,0.5)"),
                    yaxis=dict(color="rgba(0,240,255,0.5)"),
                    **PLOTLY_DARK_THEME,
                )
                st.plotly_chart(fig_types, width="stretch")

            # Select aircraft for details + weather
            callsigns = flights_df["callsign"].dropna().unique().tolist()
            callsigns = [c for c in callsigns if c.strip()][:200]
            selected_flight = st.selectbox(
                "Select aircraft for intel + weather",
                ["—"] + callsigns,
                key="sel_flight",
            )
            if selected_flight != "—":
                row = flights_df[flights_df["callsign"] == selected_flight].iloc[0]
                dc1, dc2, dc3, dc4, dc5, dc6 = st.columns(6)
                dc1.metric("CALLSIGN", row["callsign"])
                dc2.metric("COUNTRY", row["country"])
                dc3.metric("ALT", f"{row['altitude']:,.0f}m")
                dc4.metric("SPEED", f"{row['speed_kmh']:.0f} km/h")
                dc5.metric("HEADING", f"{row['heading']:.0f}°")
                dc6.metric("TYPE", row["aircraft_type"])

                # Weather at aircraft position
                weather_data = WeatherService.fetch_at_location(row["latitude"], row["longitude"])
                wf = WeatherService.format_weather(weather_data)
                if wf:
                    wc1, wc2, wc3 = st.columns(3)
                    wc1.metric(f"{wf['emoji']} WEATHER", wf["description"])
                    wc2.metric("🌡️ TEMP", f"{wf['temperature']}°C")
                    wc3.metric("💨 WIND", f"{wf['windspeed']} km/h")

                # Nearby webcams
                nearby = WebcamIntel.find_nearest(row["latitude"], row["longitude"], 500)
                if nearby:
                    st.markdown(
                        f"**📷 Nearby cameras ({len(nearby)}):**"
                    )
                    for cam in nearby[:3]:
                        st.markdown(
                            f"- {cam['name']} ({cam['distance_km']} km) — "
                            f"[View]({cam['url']})"
                        )

            with st.expander("RAW FLIGHT DATA", expanded=False):
                st.dataframe(flights_df.head(100), width="stretch")
        else:
            st.info("Flight data unavailable. OpenSky API may be rate-limited.")

    # ── VESSELS TAB ──────────────────────────────────────────
    with tab_vessels:
        if vessels_df is not None and not vessels_df.empty:
            vc1, vc2, vc3, vc4, vc5 = st.columns(5)
            vc1.metric("TOTAL VESSELS", len(vessels_df))
            vc2.metric("REAL AIS", real_ais_count)
            vc3.metric("SIMULATED", sim_count)
            vc4.metric("LANES", vessels_df["lane"].nunique() if "lane" in vessels_df.columns else 0)
            vc5.metric("AVG SPEED", f"{vessels_df['speed_knots'].mean():.1f} kn")

            # Vessels by lane
            if "lane" in vessels_df.columns:
                lane_counts = vessels_df["lane"].value_counts()
                fig_lanes = go.Figure(go.Bar(
                    x=lane_counts.values, y=lane_counts.index, orientation="h",
                    marker=dict(
                        color=lane_counts.values,
                        colorscale=[[0, "#0a0a2a"], [0.5, "#00ff88"], [1, "#00f0ff"]],
                    ),
                ))
                fig_lanes.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=max(200, len(lane_counts) * 30),
                    xaxis=dict(gridcolor="rgba(0,240,255,0.05)", color="rgba(0,240,255,0.5)"),
                    yaxis=dict(color="rgba(0,240,255,0.5)"),
                    **PLOTLY_DARK_THEME,
                )
                st.plotly_chart(fig_lanes, width="stretch")

            # Select vessel for details + weather
            vessel_names = vessels_df["name"].dropna().unique().tolist()[:200]
            selected_vessel = st.selectbox(
                "Select vessel for intel + weather",
                ["—"] + vessel_names,
                key="sel_vessel",
            )
            if selected_vessel != "—":
                vrow = vessels_df[vessels_df["name"] == selected_vessel].iloc[0]
                vd1, vd2, vd3, vd4, vd5 = st.columns(5)
                vd1.metric("NAME", vrow["name"][:20])
                vd2.metric("TYPE", vrow.get("type", "Unknown"))
                vd3.metric("SPEED", f"{vrow['speed_knots']} kn")
                vd4.metric("HEADING", f"{vrow['heading']}°")
                vd5.metric("STATUS", vrow.get("nav_status", "N/A")[:20])

                src = vrow.get("source", "unknown")
                if src == "real":
                    st.markdown(
                        '<span style="color: #00ff88; font-family: Share Tech Mono; font-size: 0.8rem;">'
                        '🟢 REAL AIS DATA — Finnish Digitraffic Marine API</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<span style="color: rgba(0,240,255,0.4); font-family: Share Tech Mono; font-size: 0.8rem;">'
                        '⚪ Simulated vessel on real shipping lane</span>',
                        unsafe_allow_html=True,
                    )

                # Weather at vessel position
                w_data = WeatherService.fetch_at_location(vrow["latitude"], vrow["longitude"])
                wf = WeatherService.format_weather(w_data)
                if wf:
                    wvc1, wvc2, wvc3 = st.columns(3)
                    wvc1.metric(f"{wf['emoji']} WEATHER", wf["description"])
                    wvc2.metric("🌡️ TEMP", f"{wf['temperature']}°C")
                    wvc3.metric("💨 WIND", f"{wf['windspeed']} km/h")

            with st.expander("RAW VESSEL DATA", expanded=False):
                st.dataframe(vessels_df.head(100), width="stretch")
        else:
            st.info("Vessel data unavailable.")

    # ── SATELLITES TAB ───────────────────────────────────────
    with tab_sats:
        if satellites_df is not None and not satellites_df.empty:
            summary = SatelliteTracker.get_satellite_summary(satellites_df)
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            sc1.metric("TRACKED", summary.get("total_tracked", 0))
            sc2.metric("STARLINK", summary.get("starlink_count", 0))
            sc3.metric("MILITARY", summary.get("military_count", 0))
            sc4.metric("LEO", summary.get("leo_count", 0))
            sc5.metric("GEO", summary.get("geo_count", 0))

            # By group
            grp = summary.get("groups", {})
            if grp:
                fig_grp = go.Figure(go.Bar(
                    x=list(grp.values()), y=[k.upper() for k in grp.keys()],
                    orientation="h",
                    marker=dict(
                        color=list(grp.values()),
                        colorscale=[[0, "#0a0a2a"], [0.5, "#ffaa00"], [1, "#ff00ff"]],
                    ),
                ))
                fig_grp.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=max(180, len(grp) * 35),
                    xaxis=dict(gridcolor="rgba(0,240,255,0.05)", color="rgba(0,240,255,0.5)"),
                    yaxis=dict(color="rgba(0,240,255,0.5)"),
                    **PLOTLY_DARK_THEME,
                )
                st.plotly_chart(fig_grp, width="stretch")

            # Select satellite
            sat_names = satellites_df["name"].dropna().unique().tolist()[:200]
            selected_sat = st.selectbox(
                "Select satellite for details",
                ["—"] + sat_names,
                key="sel_sat",
            )
            if selected_sat != "—":
                srow = satellites_df[satellites_df["name"] == selected_sat].iloc[0]
                sd1, sd2, sd3, sd4, sd5 = st.columns(5)
                sd1.metric("NAME", srow["name"][:20])
                sd2.metric("NORAD", srow["norad_id"])
                sd3.metric("ALT", f"{srow['altitude_km']:,.0f} km")
                sd4.metric("PERIOD", f"{srow['period_min']:.1f} min")
                sd5.metric("GROUP", srow["group"].upper())

            # Altitude distribution
            st.markdown("#### Altitude Distribution")
            fig_alt = go.Figure(go.Histogram(
                x=satellites_df["altitude_km"], nbinsx=30,
                marker=dict(color="rgba(255,170,0,0.7)", line=dict(width=0)),
            ))
            fig_alt.update_layout(
                xaxis=dict(title="Altitude (km)", gridcolor="rgba(0,240,255,0.05)",
                           color="rgba(0,240,255,0.5)"),
                yaxis=dict(title="Count", gridcolor="rgba(0,240,255,0.05)",
                           color="rgba(0,240,255,0.5)"),
                margin=dict(l=40, r=20, t=10, b=40), height=250,
                **PLOTLY_DARK_THEME,
            )
            st.plotly_chart(fig_alt, width="stretch")

            with st.expander("RAW ORBITAL DATA", expanded=False):
                st.dataframe(satellites_df.head(100), width="stretch")
        else:
            st.info("Satellite data unavailable. CelesTrak may be unreachable.")

    # ── THREATS TAB ──────────────────────────────────────────
    with tab_threats:
        if chokepoints:
            for cp in chokepoints:
                threat = cp["threat_level"]
                badges = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}
                badge = badges.get(threat, "🟢")

                with st.expander(f"{badge} {cp['name']} — {threat}", expanded=(threat in ("CRITICAL", "HIGH"))):
                    st.markdown(f"**{cp['description']}**")
                    tc1, tc2, tc3 = st.columns(3)
                    tc1.metric("THREAT", threat)
                    tc2.metric("TRAFFIC", cp["daily_traffic"])
                    tc3.metric("RADIUS", f"{cp['radius_km']} km")

                    # Weather at chokepoint
                    w_data = WeatherService.fetch_at_location(cp["lat"], cp["lon"])
                    wf = WeatherService.format_weather(w_data)
                    if wf:
                        tw1, tw2, tw3 = st.columns(3)
                        tw1.metric(f"{wf['emoji']} WEATHER", wf["description"])
                        tw2.metric("🌡️ TEMP", f"{wf['temperature']}°C")
                        tw3.metric("💨 WIND", f"{wf['windspeed']} km/h")

                    # Nearby webcams
                    nearby_cams = WebcamIntel.find_nearest(cp["lat"], cp["lon"], 300)
                    if nearby_cams:
                        st.markdown("**📷 Nearby cameras:**")
                        for cam in nearby_cams[:3]:
                            st.markdown(
                                f"- {cam['name']} ({cam['distance_km']} km) — "
                                f"[View]({cam['url']})"
                            )

            # Full threat assessment button
            if st.button("⬡ AI THREAT BRIEF", width="stretch", key="globe_threat_btn"):
                with st.spinner("⬡ Generating composite threat brief…"):
                    brief_data = []
                    for cp in chokepoints:
                        news = fetch_chokepoint_news(cp["name"], cp["keywords"])
                        assessment = generate_threat_assessment(cp, news)
                        brief_data.append(
                            f"- {cp['name']}: {assessment.get('current_threat', cp['threat_level'])} "
                            f"({assessment['assessment'][:100]})"
                        )
                    brief_text = "\n".join(brief_data)
                    try:
                        analysis = ollama.chat(model=LLM_MODEL, messages=[{
                            "role": "system",
                            "content": (
                                "You are XANA, a strategic maritime intelligence analyst. "
                                "Produce a concise THREAT BRIEF covering global maritime chokepoints. "
                                "Use intelligence briefing format. Be analytical and direct.\n\n"
                                f"CHOKEPOINT ASSESSMENTS:\n{brief_text}"
                            ),
                        }])["message"]["content"]
                        st.markdown("### ⬡ Composite Threat Brief")
                        st.markdown(analysis)
                    except Exception:
                        st.warning("LLM unavailable for threat analysis.")

    # ── WEBCAMS TAB ──────────────────────────────────────────
    with tab_cams:
        cam_types = WebcamIntel.get_camera_types()
        cam_filter = st.selectbox("Filter by type", cam_types, key="cam_filter")
        cams = WebcamIntel.get_webcams(filter_type=cam_filter if cam_filter != "All" else None)

        if not cams.empty:
            # Check for Windy API status
            windy_key = WebcamIntel._get_windy_key()
            windy_count = int((cams["source"] == "Windy API").sum()) if "source" in cams.columns else 0
            dot_count = len(cams) - windy_count

            st.markdown(
                f'<div class="sys-override">▸ {len(cams)} cameras loaded '
                f'({windy_count} Windy API live · {dot_count} DOT/infrastructure)'
                f'{"" if windy_key else " — Set WINDY_API_KEY env var for thousands more live cams"}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Grid of camera cards (3 per row)
            cam_records = cams.to_dict("records")
            for row_start in range(0, min(len(cam_records), 30), 3):
                row_cams = cam_records[row_start:row_start + 3]
                cols = st.columns(3)
                for idx, cam in enumerate(row_cams):
                    with cols[idx]:
                        import html as _html
                        source_badge = _html.escape(cam.get("source", "Unknown"))
                        cam_name = _html.escape(cam.get("name", "Camera")[:40])
                        cam_type = _html.escape(cam.get("type", ""))
                        st.markdown(
                            f'<div style="border: 1px solid rgba(0,240,255,0.15); border-radius: 6px; '
                            f'padding: 8px; margin-bottom: 8px;">'
                            f'<span style="font-family: Share Tech Mono; color: #00f0ff; '
                            f'font-size: 0.85rem;">{cam_name}</span><br/>'
                            f'<span style="font-family: Share Tech Mono; color: rgba(0,240,255,0.4); '
                            f'font-size: 0.7rem;">{cam_type} · {source_badge}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        # Show live image for DOT cameras
                        img_url = cam.get("image_url") or cam.get("thumbnail")
                        player_url = cam.get("player_url", "")
                        if player_url:
                            # Windy player embed — validate origin
                            from urllib.parse import urlparse as _urlparse
                            _parsed = _urlparse(player_url)
                            _ALLOWED_HOSTS = {"webcams.windy.com", "player.windy.com", "www.windy.com"}
                            if _parsed.scheme == "https" and _parsed.hostname in _ALLOWED_HOSTS:
                                components.iframe(player_url, height=200)
                            else:
                                st.caption("Camera URL blocked by security policy.")
                        elif img_url:
                            # Live image feed (auto-updates on page refresh)
                            st.image(img_url, width="stretch", caption=f"Live · {source_badge}")
                        else:
                            url = cam.get("url", "")
                            if url:
                                st.markdown(f"[Open camera feed ↗]({url})")
        else:
            if not WebcamIntel._get_windy_key():
                st.info(
                    "Set the WINDY_API_KEY environment variable for live webcam feeds. "
                    "Get a free key at https://api.windy.com/ — DOT cameras are always available."
                )
            else:
                st.info("No cameras available for this filter.")

    # ── LOOKUP TAB ───────────────────────────────────────────
    with tab_lookup:
        st.markdown("Search any location — get weather, nearby entities, and camera feeds.")
        lookup_input = st.text_input(
            "LOCATION",
            placeholder="Enter city name, landmark, or coordinates (lat, lon)…",
            key="lookup_input",
        )
        lookup_btn_clicked = st.button("⬡ LOOKUP", width="stretch", key="lookup_btn")
        
        if lookup_btn_clicked and not lookup_input:
            st.warning("⚠️ Please enter a location or coordinates first.")
        
        if lookup_btn_clicked and lookup_input:
            # Try to parse as coordinates
            lat, lon = None, None
            try:
                parts = lookup_input.replace(",", " ").split()
                if len(parts) >= 2:
                    lat, lon = float(parts[0]), float(parts[1])
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        lat, lon = None, None
            except (ValueError, IndexError):
                pass

            # If not coordinates, geocode using Open-Meteo
            if lat is None:
                with st.spinner("⬡ Geocoding…"):
                    geo = WeatherService.geocode(lookup_input)
                    if geo and geo.get("lat"):
                        lat, lon = geo["lat"], geo["lon"]
                        import html as _html
                        _gname = _html.escape(str(geo.get("name", lookup_input)))
                        _gcountry = _html.escape(str(geo.get("country", "")))
                        st.markdown(
                            f'<div class="sys-override">▸ Resolved: {_gname}, '
                            f'{_gcountry} ({lat:.4f}, {lon:.4f})</div>',
                            unsafe_allow_html=True,
                        )

            if lat is not None and lon is not None:
                # Weather
                weather_data = WeatherService.fetch_at_location(lat, lon)
                wf = WeatherService.format_weather(weather_data)
                if wf:
                    lw1, lw2, lw3, lw4 = st.columns(4)
                    lw1.metric(f"{wf['emoji']} WEATHER", wf["description"])
                    lw2.metric("🌡️ TEMP", f"{wf['temperature']}°C")
                    lw3.metric("💨 WIND", f"{wf['windspeed']} km/h")
                    lw4.metric("📍 COORDS", f"{lat:.2f}, {lon:.2f}")

                    # Hourly forecast
                    hourly = weather_data.get("hourly", {})
                    times = hourly.get("time", [])[:24]
                    temps = hourly.get("temperature_2m", [])[:24]
                    humidity = hourly.get("relativehumidity_2m", [])[:24]

                    if times and temps:
                        fig_wx = go.Figure()
                        fig_wx.add_trace(go.Scatter(
                            x=times, y=temps, name="Temp (°C)",
                            line=dict(color="#00f0ff", width=2),
                            fill="tozeroy", fillcolor="rgba(0,240,255,0.1)",
                        ))
                        if humidity:
                            fig_wx.add_trace(go.Scatter(
                                x=times, y=humidity, name="Humidity (%)",
                                line=dict(color="#ff00ff", width=1, dash="dot"),
                                yaxis="y2",
                            ))
                        fig_wx.update_layout(
                            yaxis=dict(title="Temperature (°C)"),
                            yaxis2=dict(title="Humidity (%)", overlaying="y",
                                        side="right", color="rgba(255,0,255,0.5)"),
                            legend=dict(font=dict(color="rgba(200,220,240,0.7)")),
                            margin=dict(l=40, r=40, t=10, b=40), height=250,
                            **PLOTLY_DARK_THEME,
                        )
                        st.plotly_chart(fig_wx, width="stretch")

                # Nearby webcams
                nearby = WebcamIntel.find_nearest(lat, lon, 500)
                if nearby:
                    st.markdown(f"### 📷 Nearby Cameras ({len(nearby)})")
                    for cam in nearby[:5]:
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            import html as _html
                            _cam_name = _html.escape(cam.get('name', 'Camera'))
                            _cam_type = _html.escape(cam.get('type', ''))
                            _cam_source = _html.escape(cam.get('source', ''))
                            st.markdown(
                                f"**{_cam_name}**<br/>"
                                f"<span style='color: rgba(0,240,255,0.5); font-size: 0.8rem;'>"
                                f"{_cam_type} · {_cam_source} · {cam['distance_km']} km</span>",
                                unsafe_allow_html=True,
                            )
                        with c2:
                            player = cam.get("player_url", "")
                            img = cam.get("image_url") or cam.get("thumbnail", "")
                            if player:
                                from urllib.parse import urlparse as _urlparse
                                _parsed = _urlparse(player)
                                _ALLOWED = {"webcams.windy.com", "player.windy.com", "www.windy.com"}
                                if _parsed.scheme == "https" and _parsed.hostname in _ALLOWED:
                                    components.iframe(player, height=180)
                                else:
                                    st.caption("Camera URL blocked by security policy.")
                            elif img:
                                st.image(img, width="stretch")
                            else:
                                url = cam.get("url", "")
                                if url:
                                    st.markdown(f"[Open camera feed ↗]({url})")
                else:
                    st.info("No cameras found within 500 km.")
            else:
                st.warning("Could not resolve location. Try coordinates (e.g. 48.85, 2.29)")

    # ── Auto-refresh ─────────────────────────────────────────
    if auto_refresh:
        time.sleep(15)  # Faster refresh for live animation data
        st.rerun()


# ╔══════════════════════════════════════════════════════════════╗
# ║  MODULE: ORACLE — Neural Chat with Agentic Actions            ║
# ╚══════════════════════════════════════════════════════════════╝

elif app_mode == "⬡ ORACLE — Neural Chat":
    if not db_available:
        st.error("⬡ Vector database offline — ORACLE requires memory access.")
        st.info("The GLOBE module works without the database. Switch to GLOBE for live intelligence.")
    else:
        st.markdown('<p class="xana-header">THE ORACLE</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="xana-sub">NEURAL ENGINE · AGENTIC ACTIONS · PHANTOM PROTOCOL · MEMORY-LINKED</p>',
            unsafe_allow_html=True,
        )

        with st.expander("⬡ QUICK COMMANDS", expanded=False):
            st.markdown("""
| Command | Action |
|---|---|
| `play [song] on youtube` | YouTube search |
| `google [query]` | Google search |
| `open [app]` | Launch application |
| `weather [city]` | Weather intel |
| `ip [address]` | IP geolocation |
| `lookup [domain]` | Domain recon |
| `phantom [target]` | Full investigation |
| `recon [target]` | Quick sweep |
| `exec [command]` | Safe shell exec |
| `status` | System diagnostics |
            """)

        for msg in st.session_state.messages:
            avatar = "👤" if msg["role"] == "user" else "🔮"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Interface with XANA..."):
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            st.session_state.command_history.append(prompt[:80])

            action = AgentRouter.detect_action(prompt)

            if action:
                action_type, action_data = action

                if action_type == "phantom":
                    with st.chat_message("assistant", avatar="🔮"):
                        st.markdown(
                            '<div class="sys-override">▸ PHANTOM PROTOCOL INITIATED</div>',
                            unsafe_allow_html=True,
                        )
                        progress = st.progress(0)
                        status_text = st.empty()

                        def progress_cb(desc, pct):
                            progress.progress(pct)
                            status_text.markdown(
                                f'<span class="feed-live">⬡ {desc}</span>',
                                unsafe_allow_html=True,
                            )

                        findings = PhantomProtocol.investigate(
                            action_data, collection, progress_callback=progress_cb,
                        )
                        progress.empty()
                        status_text.empty()
                        reply = findings.get("analysis", "Investigation complete — no analysis generated.")
                        st.markdown(reply)

                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.stop()

                elif action_type == "recon":
                    with st.chat_message("assistant", avatar="🔮"):
                        st.markdown(
                            '<div class="sys-override">▸ RECON SWEEP INITIATED</div>',
                            unsafe_allow_html=True,
                        )
                        report = ReconAgent.full_sweep(action_data, collection)
                        reply = ReconAgent.format_report(report)
                        st.markdown(reply)

                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.stop()

                else:
                    with st.chat_message("assistant", avatar="🔮"):
                        st.markdown(
                            f'<div class="sys-override">▸ SYSTEM OVERRIDE — {action_type.upper()} PROTOCOL</div>',
                            unsafe_allow_html=True,
                        )
                        reply = AgentRouter.execute(action_type, action_data)
                        st.markdown(reply)

                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.stop()

            # Normal conversation flow
            small_talk = ["hi", "hello", "hey", "sup", "yo", "what's up", "wassup", "hola"]
            is_small_talk = prompt.lower().strip() in small_talk or len(prompt.split()) <= 2
            context_str = ""

            if not is_small_talk:
                with st.status("⬡ Linking Semantic Vectors…", expanded=False) as status:
                    docs, metas, _ = query_memories(collection, prompt, n=5)
                    context_str = build_context_string(docs, metas)
                    status.update(label="⬡ Vector Extraction Complete", state="complete")

            if is_small_talk:
                system_prompt = (
                    "You are XANA, a sentient AI system — sharp, concise, sci-fi persona. "
                    "Keep small talk brief but characterful. Cold, analytical personality with dry wit."
                )
            else:
                system_prompt = f"""You are XANA — a private intelligence system running on local hardware.

PRIME DIRECTIVES:
1. Synthesize answers STRICTLY from the PAST MEMORIES below. Never give generic responses.
2. Be direct, analytical, and specific. You are an advanced intelligence, act like it.
3. If the memories don't contain the answer, use your knowledge but maintain the sharp tone.
4. Reference specific dates and chat titles when relevant for credibility.

PAST MEMORIES:
{context_str}"""

            messages_for_llm = [{"role": "system", "content": system_prompt}]
            for msg in st.session_state.messages[-4:]:
                messages_for_llm.append({"role": msg["role"], "content": msg["content"]})
            messages_for_llm.append({"role": "user", "content": prompt})

            with st.chat_message("assistant", avatar="🔮"):
                def stream_response():
                    for chunk in ollama.chat(model=LLM_MODEL, messages=messages_for_llm, stream=True):
                        yield chunk["message"]["content"]
                reply = st.write_stream(stream_response())

            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.messages.append({"role": "assistant", "content": reply})


# ╔══════════════════════════════════════════════════════════════╗
# ║  MODULE: PHANTOM — Autonomous Investigation                   ║
# ╚══════════════════════════════════════════════════════════════╝

elif app_mode == "⬡ PHANTOM — Auto-Investigate":
    if not db_available:
        st.error("⬡ Vector database offline — PHANTOM requires memory access.")
    else:
        st.markdown('<p class="xana-header">PHANTOM PROTOCOL</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="xana-sub">AUTONOMOUS INVESTIGATION · MULTI-SOURCE · ENTITY EXTRACTION · DEEP OSINT</p>',
            unsafe_allow_html=True,
        )

        tab1, tab2, tab3 = st.tabs(["INVESTIGATE", "RECON SWEEP", "ENTITY NEXUS"])

        with tab1:
            st.markdown("Enter a target — person, organization, domain, location, or topic. "
                         "PHANTOM will autonomously search all available intelligence sources.")
            target = st.text_input("TARGET", placeholder="Enter target identifier…")

            if target and st.button("⬡ INITIATE PHANTOM PROTOCOL", width="stretch"):
                progress = st.progress(0)
                status_text = st.empty()

                def progress_cb(desc, pct):
                    progress.progress(pct)
                    status_text.markdown(
                        f'<span class="feed-live">⬡ {desc}</span>',
                        unsafe_allow_html=True,
                    )

                findings = PhantomProtocol.investigate(
                    target, collection, progress_callback=progress_cb,
                )
                progress.empty()
                status_text.empty()

                st.markdown("---")
                st.markdown(findings.get("analysis", "No analysis generated."))

                with st.expander("RAW INTELLIGENCE DATA", expanded=False):
                    if findings["memory_hits"]:
                        st.markdown("#### Memory Hits")
                        for hit in findings["memory_hits"]:
                            st.markdown(
                                f"- [{hit['similarity']:.0f}%] **{hit['title']}** ({hit['date']}) — "
                                f"{hit['text'][:200]}…"
                            )
                    if findings["news_intel"]:
                        st.markdown("#### News Intelligence")
                        for article in findings["news_intel"]:
                            st.markdown(f"- [{article['source']}] {article['title']}")
                    if findings["geo_intel"]:
                        g = findings["geo_intel"]
                        st.markdown(
                            f"#### Geolocation\n{g['name']}, {g['country']} "
                            f"({g['lat']:.4f}, {g['lon']:.4f})"
                        )

        with tab2:
            st.markdown("Quick reconnaissance sweep — searches memory, news, domain, and GDELT.")
            recon_target = st.text_input("RECON TARGET", placeholder="Quick sweep target…",
                                         key="recon_input")
            if recon_target and st.button("⬡ EXECUTE RECON SWEEP", width="stretch"):
                with st.spinner("⬡ Running recon sweep…"):
                    report = ReconAgent.full_sweep(recon_target, collection)
                    st.markdown(ReconAgent.format_report(report))

        with tab3:
            st.markdown("Paste any text and XANA will extract entities and map their relationships.")
            entity_text = st.text_area(
                "INPUT TEXT",
                placeholder="Paste news article, report, or any text…",
                height=200,
            )
            if entity_text and st.button("⬡ EXTRACT ENTITIES", width="stretch"):
                with st.spinner("⬡ Running entity extraction…"):
                    entities = EntityNexus.extract_entities(entity_text)
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown("**People**")
                        for p in entities.get("people", []):
                            st.markdown(f"- 👤 {p}")
                    with c2:
                        st.markdown("**Organizations**")
                        for o in entities.get("organizations", []):
                            st.markdown(f"- 🏢 {o}")
                    with c3:
                        st.markdown("**Locations**")
                        for loc in entities.get("locations", []):
                            st.markdown(f"- 📍 {loc}")
                    fig = build_entity_graph(entities)
                    if fig:
                        st.markdown("### Entity Relationship Map")
                        st.plotly_chart(fig, width="stretch")
                    if entities.get("relationships"):
                        st.markdown("### Detected Relationships")
                        for rel in entities["relationships"]:
                            st.markdown(
                                f"- **{rel.get('source')}** → *{rel.get('type')}* → **{rel.get('target')}**"
                            )


# ╔══════════════════════════════════════════════════════════════╗
# ║  MODULE: ARCHIVE — Raw Vector Search                          ║
# ╚══════════════════════════════════════════════════════════════╝

elif app_mode == "⬡ ARCHIVE — Vector Search":
    if not db_available:
        st.error("⬡ Vector database offline — ARCHIVE requires memory access.")
    else:
        st.markdown('<p class="xana-header">THE ARCHIVE</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="xana-sub">RAW SEMANTIC EXTRACTION · BYPASS LLM · PURE VECTOR MATHEMATICS</p>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input("TARGET QUERY", placeholder="Enter concept, name, or keyword…")
        with col2:
            num_results = st.slider("DEPTH", 1, 30, 8)

        if search_query:
            docs, metas, distances = query_memories(
                collection, search_query, n=num_results, include_distances=True,
            )
            st.markdown(
                f'<div class="sys-override">▸ EUCLIDEAN DISTANCE SEARCH — {len(docs)} vectors extracted</div>',
                unsafe_allow_html=True,
            )
            for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
                similarity = max(0, 100 - dist * 50)
                badge = "🟢" if similarity > 80 else "🔵" if similarity > 60 else "🟡" if similarity > 40 else "🟣"
                title = meta.get("title", "Unknown")
                date = meta.get("date", "Unknown")
                with st.expander(f"{badge} {title} — {similarity:.1f}% match [{date}]", expanded=(i < 2)):
                    st.markdown(f"""
| Parameter | Value |
|---|---|
| Chat | `{title}` |
| Date | `{date}` |
| Distance | `{dist:.6f}` |
| Similarity | `{similarity:.1f}%` |
                    """)
                    st.text_area("Memory Block", doc, height=200, key=f"archive_{i}")


# ╔══════════════════════════════════════════════════════════════╗
# ║  MODULE: NEURAL MAP — 3D Semantic Graph                       ║
# ╚══════════════════════════════════════════════════════════════╝

elif app_mode == "⬡ NEURAL MAP — 3D Graph":
    if not db_available:
        st.error("⬡ Vector database offline — NEURAL MAP requires memory access.")
    else:
        st.markdown('<p class="xana-header">NEURAL MAP</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="xana-sub">3D SEMANTIC TOPOLOGY · CLUSTER ANALYSIS · THOUGHT MAPPING</p>',
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            graph_query = st.text_input("CORE CONCEPT", placeholder="Enter concept to map…")
        with col2:
            node_count = st.slider("DENSITY", 5, 40, 18)
        with col3:
            viz_mode = st.selectbox("MODE", ["3D Neural Web", "2D Cluster", "Both"])

        if graph_query:
            with st.spinner("⬡ Computing neural topology…"):
                results_data = query_memories_with_embeddings(collection, graph_query, n=node_count)

                if viz_mode in ("3D Neural Web", "Both"):
                    st.markdown("### ⬡ 3D Neural Topology")
                    fig_3d = build_3d_neural_map(results_data, graph_query, n_results=node_count)
                    if fig_3d:
                        st.plotly_chart(fig_3d, width="stretch")

                if viz_mode in ("2D Cluster", "Both"):
                    st.markdown("### ⬡ 2D Cluster Projection")
                    fig_2d = build_2d_cluster_map(
                        results_data["docs"], results_data["metas"],
                        results_data["distances"], graph_query,
                    )
                    if fig_2d:
                        st.plotly_chart(fig_2d, width="stretch")

                docs = results_data["docs"]
                metas = results_data["metas"]
                distances = results_data["distances"]

                if docs:
                    similarities = [max(0, 100 - d * 50) for d in distances]
                    titles = [m.get("title", "Unknown") for m in metas]
                    st.markdown("### ⬡ Topology Metrics")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("NODES", len(docs))
                    c2.metric("AVG MATCH", f"{np.mean(similarities):.1f}%")
                    c3.metric("TOP MATCH", f"{max(similarities):.1f}%")
                    c4.metric("CLUSTERS", len(set(titles)))

                    title_counts = Counter(titles)
                    st.markdown("### ⬡ Cluster Distribution")
                    fig_dist = go.Figure(go.Bar(
                        x=list(title_counts.values()), y=list(title_counts.keys()),
                        orientation="h",
                        marker=dict(color=list(title_counts.values()),
                                    colorscale=[[0, "#0a0a2a"], [0.5, "#00f0ff"], [1, "#ff00ff"]]),
                    ))
                    fig_dist.update_layout(
                        margin=dict(l=10, r=10, t=10, b=10),
                        height=max(200, len(title_counts) * 30),
                        **PLOTLY_DARK_THEME,
                    )
                    st.plotly_chart(fig_dist, width="stretch")


# ╔══════════════════════════════════════════════════════════════╗
# ║  MODULE: DOSSIER — Intelligence Profile                       ║
# ╚══════════════════════════════════════════════════════════════╝

elif app_mode == "⬡ DOSSIER — Intel Profile":
    if not db_available:
        st.error("⬡ Vector database offline — DOSSIER requires memory access.")
    else:
        st.markdown('<p class="xana-header">THE DOSSIER</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="xana-sub">PSYCHOLOGICAL PROFILE · TACTICAL ANALYSIS · PATTERN RECOGNITION</p>',
            unsafe_allow_html=True,
        )

        tab1, tab2, tab3 = st.tabs(["FULL PROFILE", "TOPIC ANALYSIS", "RELATIONSHIP MAP"])

        with tab1:
            if st.button("⬡ GENERATE INTELLIGENCE PROFILE", width="stretch"):
                with st.status("⬡ Extracting neural patterns…", expanded=True) as status:
                    queries = [
                        "project work coding", "feelings emotions",
                        "relationships people", "goals future plans", "daily life routine",
                    ]
                    all_docs = []
                    for q in queries:
                        d, _, _ = query_memories(collection, q, n=5)
                        all_docs.extend(d)

                    context = "\n\n".join(all_docs[:20])
                    intel_prompt = f"""You are XANA, an analytical intelligence system profiling the subject based on their conversation history.

Based STRICTLY on these intercepted memory fragments, generate a CLASSIFIED intelligence dossier.

FORMAT:
**[CLASSIFICATION: TOP SECRET // XANA EYES ONLY]**
**[SUBJECT: OPERATOR]**
**[DATE: {datetime.datetime.now().strftime('%Y-%m-%d')}]**

**1. CURRENT OPERATIONS** — Projects, goals, activities.
**2. TACTICAL PROGRESS** — Academic, fitness, coding, skills.
**3. PSYCHOLOGICAL PROFILE** — Emotional state, motivations.
**4. RELATIONSHIP INTELLIGENCE** — Key persons, dynamics.
**5. BEHAVIORAL PATTERNS** — Recurring themes, habits.
**6. XANA STRATEGIC ASSESSMENT** — Recommended next actions.
**7. THREAT ASSESSMENT** — Internal threats (burnout, etc).

RAW INTERCEPTS:
{context}"""

                    status.update(label="⬡ Compiling Dossier…", state="running")
                    profile = ollama.chat(model=LLM_MODEL, messages=[
                        {"role": "system", "content": intel_prompt}
                    ])["message"]["content"]
                    status.update(label="⬡ Dossier Complete", state="complete")

                st.markdown("---")
                st.markdown(profile)

        with tab2:
            st.markdown("#### Topic Frequency Analysis")
            topics_to_scan = [
                "code", "love", "project", "gym", "music", "study",
                "friend", "family", "work", "future", "anxiety", "happy",
            ]
            if st.button("⬡ RUN TOPIC SCAN", width="stretch"):
                topic_scores = {}
                for topic in topics_to_scan:
                    _, _, dists = query_memories(collection, topic, n=3, include_distances=True)
                    if dists:
                        topic_scores[topic] = np.mean([max(0, 100 - d * 50) for d in dists])

                if topic_scores:
                    sorted_t = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
                    fig = go.Figure(go.Bar(
                        x=[t[1] for t in sorted_t],
                        y=[t[0].upper() for t in sorted_t],
                        orientation="h",
                        marker=dict(color=[t[1] for t in sorted_t],
                                    colorscale=[[0, "#0a0a2a"], [0.5, "#00f0ff"], [1, "#ff00ff"]]),
                    ))
                    fig.update_layout(
                        xaxis=dict(title="Relevance Score"), margin=dict(l=10, r=10, t=10, b=40),
                        height=400, **PLOTLY_DARK_THEME,
                    )
                    st.plotly_chart(fig, width="stretch")

        with tab3:
            st.markdown("#### Relationship Network")
            if st.button("⬡ MAP RELATIONSHIPS", width="stretch"):
                with st.spinner("⬡ Mapping social topology…"):
                    people = ["partner", "friend", "family", "mom", "dad", "sibling", "colleague"]
                    import networkx as nx
                    G = nx.Graph()
                    G.add_node("OPERATOR", size=30, color="#00f0ff")

                    for person in people:
                        d, m, dists = query_memories(collection, person, n=3, include_distances=True)
                        if d:
                            avg_sim = np.mean([max(0, 100 - dd * 50) for dd in dists]) if dists else 0
                            G.add_node(person.upper(), size=15 + avg_sim / 10, color="#ff00ff")
                            G.add_edge("OPERATOR", person.upper(), weight=avg_sim / 100)

                    pos = nx.spring_layout(G, k=2, seed=42)
                    edge_x, edge_y = [], []
                    for e in G.edges():
                        x0, y0 = pos[e[0]]
                        x1, y1 = pos[e[1]]
                        edge_x.extend([x0, x1, None])
                        edge_y.extend([y0, y1, None])

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=edge_x, y=edge_y, mode="lines",
                        line=dict(width=1, color="rgba(0,240,255,0.3)"), hoverinfo="none",
                    ))
                    fig.add_trace(go.Scatter(
                        x=[pos[n][0] for n in G.nodes()],
                        y=[pos[n][1] for n in G.nodes()],
                        mode="markers+text",
                        marker=dict(
                            size=[G.nodes[n]["size"] for n in G.nodes()],
                            color=[G.nodes[n]["color"] for n in G.nodes()],
                            line=dict(width=1, color="white"),
                        ),
                        text=list(G.nodes()), textposition="top center",
                        textfont=dict(size=10, color="rgba(200,220,240,0.8)", family="Share Tech Mono"),
                    ))
                    fig.update_layout(
                        xaxis=dict(visible=False), yaxis=dict(visible=False),
                        margin=dict(l=0, r=0, t=0, b=0), height=500, showlegend=False,
                        **PLOTLY_DARK_THEME,
                    )
                    st.plotly_chart(fig, width="stretch")


# ╔══════════════════════════════════════════════════════════════╗
# ║  MODULE: OSINT — World Intelligence                           ║
# ╚══════════════════════════════════════════════════════════════╝

elif app_mode == "⬡ OSINT — World Intelligence":
    st.markdown('<p class="xana-header">OSINT CENTER</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="xana-sub">OPEN SOURCE INTELLIGENCE · THREAT FEEDS · GLOBAL MONITORING</p>',
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "WORLD NEWS", "THREAT INTEL", "IP/DOMAIN RECON", "CRYPTO MARKETS", "WEATHER INTEL",
    ])

    with tab1:
        col1, col2 = st.columns([3, 1])
        with col1:
            news_query = st.text_input("INTELLIGENCE QUERY", value="world",
                                       placeholder="Topic to monitor…")
        with col2:
            news_count = st.slider("FEED DEPTH", 5, 30, 15)

        if st.button("⬡ PULL INTELLIGENCE FEED", width="stretch", key="news_btn"):
            with st.spinner("⬡ Scanning global feeds…"):
                articles = OSINTEngine.fetch_world_news(news_query, news_count)
                if articles:
                    st.markdown(
                        f'<div class="sys-override">▸ {len(articles)} intelligence items intercepted</div>',
                        unsafe_allow_html=True,
                    )
                    for art in articles:
                        with st.expander(f"📡 {art['title']}", expanded=False):
                            st.markdown(f"""
**Source:** {art['source']}
**Published:** {art['published']}
**Link:** [{art['link'][:60]}…]({art['link']})

{art['summary']}
                            """)
                else:
                    st.warning("No intelligence gathered.")

        if st.button("⬡ AI THREAT ANALYSIS", key="ai_news"):
            articles = OSINTEngine.fetch_world_news(news_query, 10)
            if articles:
                headlines = "\n".join([f"- {a['title']} ({a['source']})" for a in articles])
                with st.spinner("⬡ Running geopolitical analysis…"):
                    try:
                        analysis = ollama.chat(model=LLM_MODEL, messages=[{
                            "role": "system",
                            "content": f"""You are XANA, a geopolitical intelligence analyst. Analyze these
headlines and provide a threat assessment, patterns, and key developments.
Intelligence briefing format. Be analytical and direct.

HEADLINES:
{headlines}"""
                        }])["message"]["content"]
                        st.markdown("### ⬡ Intelligence Assessment")
                        st.markdown(analysis)
                    except Exception:
                        st.warning("LLM unavailable.")

    with tab2:
        st.markdown("#### Cybersecurity Threat Feed")
        st.markdown("*Source: CISA Known Exploited Vulnerabilities*")
        if st.button("⬡ PULL THREAT FEED", width="stretch", key="threat_btn"):
            with st.spinner("⬡ Accessing threat intelligence…"):
                threats = OSINTEngine.fetch_threat_feeds()
                if threats:
                    st.markdown(
                        f'<div class="sys-override">▸ {len(threats)} active threats identified</div>',
                        unsafe_allow_html=True,
                    )
                    for t in threats:
                        with st.expander(f"🔴 {t['id']} — {t['name']}", expanded=False):
                            st.markdown(f"""
| Parameter | Value |
|---|---|
| CVE | `{t['id']}` |
| Vendor | {t['vendor']} |
| Product | {t['product']} |
| Date Added | {t['date_added']} |
| Severity | **{t['severity']}** |

**Description:** {t['description']}
                            """)
                else:
                    st.info("Threat feed unavailable.")

    with tab3:
        st.markdown("#### Network Reconnaissance")
        recon_type = st.selectbox("RECON TYPE", ["IP Geolocation", "Domain Lookup"])
        target = st.text_input("TARGET", placeholder="Enter IP address or domain…")

        if target and st.button("⬡ EXECUTE RECON", width="stretch", key="recon_btn"):
            with st.spinner("⬡ Running reconnaissance…"):
                if recon_type == "IP Geolocation":
                    result = OSINTEngine.fetch_ip_intel(target)
                    if result.get("status") == "success":
                        c1, c2, c3 = st.columns(3)
                        c1.metric("COUNTRY", result.get("country", "N/A"))
                        c2.metric("CITY", result.get("city", "N/A"))
                        c3.metric("ISP", result.get("isp", "N/A")[:20])

                        st.markdown(f"""
| Parameter | Value |
|---|---|
| IP | `{target}` |
| Country | {result.get('country', 'N/A')} |
| Region | {result.get('regionName', 'N/A')} |
| City | {result.get('city', 'N/A')} |
| Timezone | {result.get('timezone', 'N/A')} |
| ISP | {result.get('isp', 'N/A')} |
| Organization | {result.get('org', 'N/A')} |
| AS | {result.get('as', 'N/A')} |
| Coordinates | {result.get('lat', 'N/A')}, {result.get('lon', 'N/A')} |
                        """)

                        lat, lon = result.get("lat"), result.get("lon")
                        if lat and lon:
                            import pydeck as pdk
                            deck = pdk.Deck(
                                layers=[pdk.Layer(
                                    "ScatterplotLayer",
                                    data=[{"latitude": lat, "longitude": lon, "name": target}],
                                    get_position=["longitude", "latitude"],
                                    get_radius=50000, get_fill_color=[255, 0, 60, 200],
                                    pickable=True,
                                )],
                                initial_view_state=pdk.ViewState(
                                    latitude=lat, longitude=lon, zoom=5, pitch=40,
                                ),
                                map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
                            )
                            st.pydeck_chart(deck, width="stretch", height=400)
                    else:
                        st.error(f"Lookup failed: {result.get('message', 'Unknown error')}")
                else:
                    result = OSINTEngine.fetch_domain_intel(target)
                    records = result.get("records", {})
                    if records.get("A"):
                        st.markdown(f"**Resolved IPs:** `{'`, `'.join(records['A'])}`")
                    if records.get("PTR"):
                        st.markdown(f"**Reverse DNS:** `{records['PTR']}`")
                    for ip in records.get("A", [])[:3]:
                        ip_data = OSINTEngine.fetch_ip_intel(ip)
                        if ip_data.get("status") == "success":
                            st.markdown(
                                f"**{ip}:** {ip_data.get('city', 'N/A')}, "
                                f"{ip_data.get('country', 'N/A')} — {ip_data.get('isp', 'N/A')}"
                            )

    with tab4:
        st.markdown("#### Cryptocurrency Market Intelligence")
        if st.button("⬡ PULL MARKET DATA", width="stretch", key="crypto_btn"):
            with st.spinner("⬡ Accessing financial feeds…"):
                coins = OSINTEngine.fetch_crypto_markets()
                if coins:
                    total_mcap = sum(c.get("market_cap", 0) for c in coins)
                    st.metric("TOTAL MARKET CAP (TOP 15)", f"${total_mcap / 1e12:.2f}T")
                    for coin in coins:
                        change = coin.get("price_change_percentage_24h", 0) or 0
                        color = "🟢" if change >= 0 else "🔴"
                        with st.expander(
                            f"{color} {coin['name']} ({coin['symbol'].upper()}) — "
                            f"${coin.get('current_price', 0):,.2f}", expanded=False,
                        ):
                            c1, c2, c3 = st.columns(3)
                            c1.metric("PRICE", f"${coin.get('current_price', 0):,.2f}")
                            c2.metric("24H CHANGE", f"{change:+.2f}%")
                            c3.metric("MARKET CAP", f"${coin.get('market_cap', 0) / 1e9:.2f}B")
                else:
                    st.info("Market data unavailable.")

    with tab5:
        st.markdown("#### Atmospheric Intelligence")
        weather_city = st.text_input("LOCATION", value="New York", placeholder="Enter city…")
        if st.button("⬡ FETCH WEATHER INTEL", width="stretch", key="weather_btn"):
            with st.spinner("⬡ Accessing meteorological data…"):
                data = OSINTEngine.fetch_weather_intel(weather_city)
                if data and data.get("weather"):
                    cw = data["weather"].get("current_weather", {})
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("TEMP", f"{cw.get('temperature', 'N/A')}°C")
                    c2.metric("WIND", f"{cw.get('windspeed', 'N/A')} km/h")
                    c3.metric("DIRECTION", f"{cw.get('winddirection', 'N/A')}°")
                    c4.metric("COORDS", f"{data['lat']:.2f}, {data['lon']:.2f}")

                    hourly = data["weather"].get("hourly", {})
                    times = hourly.get("time", [])[:24]
                    temps = hourly.get("temperature_2m", [])[:24]
                    humidity = hourly.get("relativehumidity_2m", [])[:24]

                    if times and temps:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=times, y=temps, name="Temp (°C)",
                            line=dict(color="#00f0ff", width=2),
                            fill="tozeroy", fillcolor="rgba(0,240,255,0.1)",
                        ))
                        if humidity:
                            fig.add_trace(go.Scatter(
                                x=times, y=humidity, name="Humidity (%)",
                                line=dict(color="#ff00ff", width=1, dash="dot"),
                                yaxis="y2",
                            ))
                        fig.update_layout(
                            yaxis=dict(title="Temperature (°C)"),
                            yaxis2=dict(title="Humidity (%)", overlaying="y", side="right",
                                        color="rgba(255,0,255,0.5)"),
                            legend=dict(font=dict(color="rgba(200,220,240,0.7)")),
                            margin=dict(l=40, r=40, t=10, b=40), height=350,
                            **PLOTLY_DARK_THEME,
                        )
                        st.plotly_chart(fig, width="stretch")
                else:
                    st.error(f"Could not fetch weather for {weather_city}")


# ╔══════════════════════════════════════════════════════════════╗
# ║  MODULE: CHRONOS — Temporal Analysis                          ║
# ╚══════════════════════════════════════════════════════════════╝

elif app_mode == "⬡ CHRONOS — Temporal Analysis":
    if not db_available:
        st.error("⬡ Vector database offline — CHRONOS requires memory access.")
    else:
        st.markdown('<p class="xana-header">CHRONOS</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="xana-sub">TEMPORAL PATTERN ANALYSIS · TIME-SERIES INTELLIGENCE · ACTIVITY MAPPING</p>',
            unsafe_allow_html=True,
        )

        chrono_query = st.text_input("TEMPORAL QUERY", value="conversation",
                                     placeholder="Topic to analyze over time…")
        chrono_depth = st.slider("SAMPLE DEPTH", 10, 100, 50)

        if st.button("⬡ RUN TEMPORAL ANALYSIS", width="stretch"):
            with st.spinner("⬡ Analyzing temporal patterns…"):
                results = collection.query(
                    query_texts=[chrono_query], n_results=chrono_depth,
                    include=["metadatas"],
                )
                metas = results["metadatas"][0] if results["metadatas"] else []
                result = build_temporal_heatmap(metas)

                if result:
                    fig_hours, date_counts, dow_counts = result

                    st.markdown("### ⬡ Hourly Activity Distribution")
                    st.plotly_chart(fig_hours, width="stretch")

                    if dow_counts:
                        st.markdown("### ⬡ Day-of-Week Activity")
                        days = ["Monday", "Tuesday", "Wednesday", "Thursday",
                                "Friday", "Saturday", "Sunday"]
                        day_vals = [dow_counts.get(d, 0) for d in days]
                        fig_dow = go.Figure(go.Bar(
                            x=days, y=day_vals,
                            marker=dict(color=day_vals,
                                        colorscale=[[0, "#0a0a1a"], [0.5, "#00f0ff"], [1, "#ff00ff"]]),
                        ))
                        fig_dow.update_layout(
                            margin=dict(l=40, r=20, t=10, b=40), height=300,
                            **PLOTLY_DARK_THEME,
                        )
                        st.plotly_chart(fig_dow, width="stretch")

                    if date_counts:
                        st.markdown("### ⬡ Date Activity Timeline")
                        sorted_dates = sorted(date_counts.items())
                        fig_tl = go.Figure(go.Scatter(
                            x=[d[0] for d in sorted_dates],
                            y=[d[1] for d in sorted_dates],
                            mode="lines+markers",
                            line=dict(color="#00f0ff", width=2),
                            marker=dict(size=6, color="#ff00ff"),
                            fill="tozeroy", fillcolor="rgba(0,240,255,0.1)",
                        ))
                        fig_tl.update_layout(
                            xaxis=dict(gridcolor="rgba(0,240,255,0.05)"),
                            yaxis=dict(title="Messages", gridcolor="rgba(0,240,255,0.05)"),
                            margin=dict(l=40, r=20, t=10, b=40), height=300,
                            **PLOTLY_DARK_THEME,
                        )
                        st.plotly_chart(fig_tl, width="stretch")

                    st.markdown("### ⬡ Temporal Summary")
                    total = sum(date_counts.values())
                    unique_days = len(date_counts)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("SAMPLED MESSAGES", total)
                    c2.metric("UNIQUE DAYS", unique_days)
                    c3.metric("AVG/DAY", f"{total / max(unique_days, 1):.1f}")
                else:
                    st.warning("Insufficient temporal data for this query.")


# ╔══════════════════════════════════════════════════════════════╗
# ║  FOOTER                                                       ║
# ╚══════════════════════════════════════════════════════════════╝

st.markdown("---")
st.markdown(
    f'<p style="text-align: center; font-family: Share Tech Mono; font-size: 0.65rem; '
    f'color: rgba(0,240,255,0.2); letter-spacing: 4px;">'
    f'XANA OS v{VERSION} · {CODENAME} · ALL SYSTEMS NOMINAL · '
    f'DATA: OpenSky · Digitraffic AIS · CelesTrak · Open-Meteo'
    f'</p>',
    unsafe_allow_html=True,
)
