"""
╔══════════════════════════════════════════════════════════════╗
║  XANA OS v4.1 — LIVE GLOBE RENDERER (deck.gl + MapLibre)      ║
╚══════════════════════════════════════════════════════════════╝

Custom HTML/JS globe with:
- Satellite imagery tiles (ESRI World Imagery)
- Smooth animated entity movement (flights drift by heading/speed)
- Hover tooltips + click detail panels
- Client-side weather fetch (Open-Meteo, CORS-enabled)
- GPU-accelerated rendering via deck.gl
"""

import json
import math
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from config import LAYER_COLORS

# ── View Presets ─────────────────────────────────────────────
VIEW_PRESETS = {
    "global": {"lat": 20, "lon": 30, "zoom": 1.8, "pitch": 45, "bearing": 0},
    "europe": {"lat": 48, "lon": 10, "zoom": 3.8, "pitch": 50, "bearing": 0},
    "asia": {"lat": 25, "lon": 105, "zoom": 3.2, "pitch": 45, "bearing": 0},
    "middle_east": {"lat": 26, "lon": 48, "zoom": 4.2, "pitch": 50, "bearing": 0},
    "americas": {"lat": 20, "lon": -80, "zoom": 2.8, "pitch": 40, "bearing": 0},
    "africa": {"lat": 0, "lon": 25, "zoom": 3.2, "pitch": 40, "bearing": 0},
    "pacific": {"lat": 10, "lon": 150, "zoom": 2.8, "pitch": 35, "bearing": 0},
    "arctic": {"lat": 72, "lon": 0, "zoom": 2.8, "pitch": 30, "bearing": 0},
}


def _safe_json_for_html(raw_json: str) -> str:
    """Escape sequences that could break out of a <script> block."""
    return raw_json.replace("</", r"<\/").replace("<!--", r"<\!--")


def _df_to_json(df, max_records=3000):
    """Safely convert DataFrame to JSON string for JS embedding."""
    if df is None or df.empty:
        return "[]"
    # Replace NaN/Inf with null — JSON can't handle them
    df_clean = df.head(max_records).copy()
    df_clean = df_clean.replace([np.inf, -np.inf], np.nan)
    df_clean = df_clean.where(pd.notnull(df_clean), None)
    records = df_clean.to_dict(orient="records")
    # Sanitize for JSON embedding in HTML — prevent </script> breakout
    return _safe_json_for_html(json.dumps(records, default=str))


def _routes_to_json(sea_routes):
    """Convert sea routes list to JSON."""
    if not sea_routes:
        return "[]"
    return _safe_json_for_html(json.dumps(sea_routes, default=str))


def _chokepoints_to_json(chokepoints):
    """Convert chokepoints to JSON."""
    if not chokepoints:
        return "[]"
    cp_data = []
    for cp in chokepoints:
        cp_data.append({
            "name": cp["name"],
            "lat": cp["lat"],
            "lon": cp["lon"],
            "radius_km": cp.get("radius_km", 100),
            "threat_level": cp.get("threat_level", "MEDIUM"),
            "description": cp.get("description", ""),
            "daily_traffic": cp.get("daily_traffic", "N/A"),
        })
    return _safe_json_for_html(json.dumps(cp_data, default=str))


def build_globe(
    flights_df=None,
    vessels_df=None,
    satellites_df=None,
    sea_routes=None,
    chokepoints=None,
    webcams_df=None,
    layers_enabled=None,
    view_preset="global",
    **kwargs,
):
    """Build a custom HTML/JS globe with deck.gl + MapLibre + satellite imagery.

    Returns HTML string to be rendered via streamlit.components.v1.html()
    """
    if layers_enabled is None:
        layers_enabled = {
            "flights": True, "vessels": True, "satellites": True,
            "sea_routes": True, "chokepoints": True, "webcams": True,
        }

    vp = VIEW_PRESETS.get(view_preset, VIEW_PRESETS["global"])

    # Serialize data for JS
    flights_json = _df_to_json(flights_df) if layers_enabled.get("flights") else "[]"
    vessels_json = _df_to_json(vessels_df) if layers_enabled.get("vessels") else "[]"
    sats_json = _df_to_json(satellites_df) if layers_enabled.get("satellites") else "[]"
    routes_json = _routes_to_json(sea_routes) if layers_enabled.get("sea_routes") else "[]"
    cp_json = _chokepoints_to_json(chokepoints) if layers_enabled.get("chokepoints") else "[]"
    cams_json = _df_to_json(webcams_df) if layers_enabled.get("webcams") else "[]"

    layers_json = json.dumps(layers_enabled)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<script src="https://unpkg.com/maplibre-gl@4.1.2/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@4.1.2/dist/maplibre-gl.css" rel="stylesheet"/>
<script src="https://unpkg.com/deck.gl@9.0.16/dist.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #0a0a0f; overflow: hidden; font-family: 'Share Tech Mono', monospace; }}
  #map {{ width: 100%; height: 100vh; }}
  #tooltip {{
    position: absolute; z-index: 99; pointer-events: none; display: none;
    background: rgba(5,5,15,0.95); border: 1px solid #00f0ff;
    padding: 8px 12px; border-radius: 4px; max-width: 360px;
    font-size: 12px; color: #c0d0e0; box-shadow: 0 0 20px rgba(0,240,255,0.2);
  }}
  #tooltip .tt-name {{ color: #00f0ff; font-weight: bold; font-size: 13px; }}
  #tooltip .tt-info {{ color: #c0d0e0; margin-top: 4px; line-height: 1.4; }}
  #hud {{
    position: absolute; top: 10px; left: 10px; z-index: 50;
    background: rgba(5,5,15,0.8); border: 1px solid rgba(0,240,255,0.15);
    padding: 8px 14px; border-radius: 6px; color: #00f0ff; font-size: 11px;
    letter-spacing: 1px;
  }}
  #hud .hud-val {{ color: #00ff88; font-size: 13px; }}
  #detail-panel {{
    position: absolute; bottom: 10px; right: 10px; z-index: 50;
    background: rgba(5,5,15,0.92); border: 1px solid #00f0ff;
    padding: 12px 16px; border-radius: 6px; max-width: 380px; display: none;
    color: #c0d0e0; font-size: 12px; box-shadow: 0 0 30px rgba(0,240,255,0.15);
  }}
  #detail-panel .dp-title {{ color: #00f0ff; font-size: 14px; font-weight: bold; margin-bottom: 6px; }}
  #detail-panel .dp-row {{ display: flex; justify-content: space-between; padding: 2px 0; border-bottom: 1px solid rgba(0,240,255,0.07); }}
  #detail-panel .dp-label {{ color: rgba(0,240,255,0.5); }}
  #detail-panel .dp-value {{ color: #00ff88; }}
  #detail-panel .dp-close {{
    position: absolute; top: 6px; right: 10px; cursor: pointer;
    color: rgba(255,0,60,0.7); font-size: 14px;
  }}
  #detail-panel .dp-close:hover {{ color: #ff003c; }}
  #detail-panel .dp-weather {{
    margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(0,240,255,0.12);
    color: #ffaa00;
  }}
  .legend {{
    position: absolute; bottom: 10px; left: 10px; z-index: 50;
    background: rgba(5,5,15,0.8); border: 1px solid rgba(0,240,255,0.15);
    padding: 8px 12px; border-radius: 6px; font-size: 10px;
  }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; margin: 3px 0; color: #c0d0e0; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
</style>
</head>
<body>
<div id="map"></div>
<div id="tooltip"><div class="tt-name"></div><div class="tt-info"></div></div>
<div id="hud">
  <span style="color:rgba(0,240,255,0.5);">XANA GLOBE</span> &nbsp;
  ✈️ <span class="hud-val" id="hud-flights">0</span> &nbsp;
  🚢 <span class="hud-val" id="hud-vessels">0</span> &nbsp;
  🛰️ <span class="hud-val" id="hud-sats">0</span> &nbsp;
  ⚠️ <span class="hud-val" id="hud-threats">0</span> &nbsp;
  <span style="color:rgba(0,255,136,0.5);" id="hud-fps"></span>
</div>
<div id="detail-panel">
  <span class="dp-close" onclick="document.getElementById('detail-panel').style.display='none'">✕</span>
  <div class="dp-title" id="dp-title"></div>
  <div id="dp-body"></div>
  <div class="dp-weather" id="dp-weather"></div>
</div>
<div class="legend">
  <div class="legend-item"><div class="legend-dot" style="background:#00c8ff;"></div>Aircraft</div>
  <div class="legend-item"><div class="legend-dot" style="background:#00ff88;"></div>Vessels (real AIS)</div>
  <div class="legend-item"><div class="legend-dot" style="background:#00cc66;opacity:0.5;"></div>Vessels (sim)</div>
  <div class="legend-item"><div class="legend-dot" style="background:#ffaa00;"></div>Satellites</div>
  <div class="legend-item"><div class="legend-dot" style="background:#ff003c;"></div>Chokepoints</div>
  <div class="legend-item"><div class="legend-dot" style="background:#ff00ff;"></div>Webcams</div>
</div>

<script>
// ── Data from Python ────────────────────────────────────────
let flights = {flights_json};
let vessels = {vessels_json};
let satellites = {sats_json};
const seaRoutes = {routes_json};
const chokepoints = {cp_json};
const webcams = {cams_json};
const layersEnabled = {layers_json};

// ── HUD ─────────────────────────────────────────────────────
document.getElementById('hud-flights').textContent = flights.length;
document.getElementById('hud-vessels').textContent = vessels.length;
document.getElementById('hud-sats').textContent = satellites.length;
document.getElementById('hud-threats').textContent = chokepoints.filter(c => c.threat_level === 'CRITICAL' || c.threat_level === 'HIGH').length;

// ── Map init ────────────────────────────────────────────────
const map = new maplibregl.Map({{
  container: 'map',
  style: {{
    version: 8,
    sources: {{
      'satellite': {{
        type: 'raster',
        tiles: [
          'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}'
        ],
        tileSize: 256,
        attribution: 'Esri Satellite',
      }}
    }},
    layers: [{{ id: 'satellite', type: 'raster', source: 'satellite' }}],
    glyphs: 'https://demotiles.maplibre.org/font/{{fontstack}}/{{range}}.pbf'
  }},
  center: [{vp['lon']}, {vp['lat']}],
  zoom: {vp['zoom']},
  pitch: {vp['pitch']},
  bearing: {vp['bearing']},
  maxPitch: 85,
  antialias: true,
}});

map.addControl(new maplibregl.NavigationControl(), 'top-right');

// ── Tooltip ─────────────────────────────────────────────────
const tooltipEl = document.getElementById('tooltip');
function showTooltip(info) {{
  if (info.object) {{
    tooltipEl.style.display = 'block';
    tooltipEl.style.left = (info.x + 12) + 'px';
    tooltipEl.style.top = (info.y - 12) + 'px';
    tooltipEl.querySelector('.tt-name').textContent = info.object.name || info.object.callsign || 'Unknown';
    tooltipEl.querySelector('.tt-info').textContent = info.object.info || '';
  }} else {{
    tooltipEl.style.display = 'none';
  }}
}}

// ── Detail Panel + Weather ──────────────────────────────────
async function showDetail(info) {{
  if (!info.object) return;
  const obj = info.object;
  const panel = document.getElementById('detail-panel');
  const title = document.getElementById('dp-title');
  const body = document.getElementById('dp-body');
  const weather = document.getElementById('dp-weather');

  title.textContent = obj.name || obj.callsign || 'Unknown';
  let html = '';
  const fields = [
    ['Type', obj.entity_type || obj.aircraft_type || obj.type || ''],
    ['Position', (obj.latitude||0).toFixed(4) + ', ' + (obj.longitude||0).toFixed(4)],
    ['Altitude', obj.altitude ? obj.altitude.toFixed(0) + 'm' : (obj.altitude_km ? obj.altitude_km.toFixed(0) + ' km' : '')],
    ['Speed', obj.speed_kmh ? obj.speed_kmh.toFixed(0) + ' km/h' : (obj.speed_knots ? obj.speed_knots + ' kn' : '')],
    ['Heading', obj.heading != null ? obj.heading.toFixed(0) + '°' : ''],
    ['Country', obj.country || obj.flag || ''],
    ['Source', obj.source || obj.group || ''],
    ['NORAD', obj.norad_id || ''],
    ['MMSI', obj.mmsi || ''],
  ];
  for (const [label, val] of fields) {{
    if (val) html += '<div class="dp-row"><span class="dp-label">' + label + '</span><span class="dp-value">' + val + '</span></div>';
  }}
  body.innerHTML = html;
  panel.style.display = 'block';

  // Fetch weather at position
  const lat = obj.latitude || obj.lat || 0;
  const lon = obj.longitude || obj.lon || 0;
  if (lat && lon) {{
    weather.innerHTML = '⏳ Loading weather...';
    try {{
      const resp = await fetch(
        'https://api.open-meteo.com/v1/forecast?latitude=' + lat.toFixed(4) +
        '&longitude=' + lon.toFixed(4) + '&current_weather=true'
      );
      const data = await resp.json();
      if (data.current_weather) {{
        const cw = data.current_weather;
        weather.innerHTML =
          '🌡️ ' + cw.temperature + '°C &nbsp; 💨 ' + cw.windspeed + ' km/h &nbsp; ' +
          '🧭 ' + cw.winddirection + '°';
      }} else {{
        weather.innerHTML = '';
      }}
    }} catch(e) {{
      weather.innerHTML = '⚠️ Weather unavailable';
    }}
  }}
}}

// ── Build deck.gl layers ────────────────────────────────────
function buildLayers() {{
  const layers = [];

  // Sea Routes
  if (layersEnabled.sea_routes && seaRoutes.length > 0) {{
    layers.push(new deck.PathLayer({{
      id: 'sea-routes',
      data: seaRoutes,
      getPath: d => d.path,
      getColor: [0, 255, 136, 40],
      getWidth: 20000,
      widthMinPixels: 1,
      widthMaxPixels: 3,
      pickable: true,
      onHover: showTooltip,
    }}));
  }}

  // Chokepoint threat zones
  if (layersEnabled.chokepoints && chokepoints.length > 0) {{
    layers.push(new deck.ScatterplotLayer({{
      id: 'threat-zones',
      data: chokepoints,
      getPosition: d => [d.lon, d.lat],
      getRadius: d => (d.radius_km || 100) * 1000,
      getFillColor: d => d.threat_level === 'CRITICAL' ? [255,0,60,30] : d.threat_level === 'HIGH' ? [255,100,0,25] : [255,170,0,15],
      filled: true, stroked: true,
      getLineColor: [255,0,60,80], lineWidthMinPixels: 1,
      pickable: false,
    }}));
    layers.push(new deck.ScatterplotLayer({{
      id: 'threat-markers',
      data: chokepoints,
      getPosition: d => [d.lon, d.lat],
      getRadius: 30000,
      getFillColor: d => d.threat_level === 'CRITICAL' ? [255,0,60,220] : d.threat_level === 'HIGH' ? [255,100,0,200] : [255,170,0,180],
      filled: true, stroked: true,
      getLineColor: [255,255,255,150], lineWidthMinPixels: 2,
      pickable: true, onHover: showTooltip, onClick: showDetail,
    }}));
    layers.push(new deck.TextLayer({{
      id: 'threat-labels',
      data: chokepoints,
      getPosition: d => [d.lon, d.lat],
      getText: d => d.name,
      getSize: 13,
      getColor: [255,255,255,200],
      getTextAnchor: 'middle',
      getAlignmentBaseline: 'bottom',
      fontFamily: '"Share Tech Mono", monospace',
      pickable: false,
    }}));
  }}

  // Vessels — separate real vs simulated for different styling
  if (layersEnabled.vessels && vessels.length > 0) {{
    const realVessels = vessels.filter(v => v.source === 'real');
    const simVessels = vessels.filter(v => v.source !== 'real');

    if (realVessels.length > 0) {{
      layers.push(new deck.ScatterplotLayer({{
        id: 'vessels-real',
        data: realVessels,
        getPosition: d => [d.longitude, d.latitude],
        getRadius: 12000,
        getFillColor: [0, 255, 136, 220],
        filled: true, stroked: true,
        getLineColor: [255,255,255,80], lineWidthMinPixels: 1,
        pickable: true, autoHighlight: true,
        highlightColor: [0, 255, 136, 255],
        onHover: showTooltip, onClick: showDetail,
        transitions: {{ getPosition: 2000 }},
      }}));
    }}

    if (simVessels.length > 0) {{
      layers.push(new deck.ScatterplotLayer({{
        id: 'vessels-sim',
        data: simVessels,
        getPosition: d => [d.longitude, d.latitude],
        getRadius: 10000,
        getFillColor: [0, 200, 100, 120],
        filled: true,
        pickable: true, autoHighlight: true,
        onHover: showTooltip, onClick: showDetail,
        transitions: {{ getPosition: 2000 }},
      }}));
    }}
  }}

  // Flights
  if (layersEnabled.flights && flights.length > 0) {{
    layers.push(new deck.ScatterplotLayer({{
      id: 'flights',
      data: flights,
      getPosition: d => [d.longitude, d.latitude],
      getRadius: d => d.aircraft_type === 'Military' ? 16000 : 10000,
      getFillColor: d => d.aircraft_type === 'Military' ? [255,0,60,220] : d.aircraft_type === 'Cargo' ? [255,170,0,200] : [0,200,255,200],
      filled: true, stroked: true,
      getLineColor: d => d.aircraft_type === 'Military' ? [255,100,100,180] : [255,255,255,60],
      lineWidthMinPixels: 1,
      pickable: true, autoHighlight: true,
      highlightColor: [0, 240, 255, 255],
      onHover: showTooltip, onClick: showDetail,
      transitions: {{ getPosition: 2000 }},
    }}));
  }}

  // Satellites
  if (layersEnabled.satellites && satellites.length > 0) {{
    layers.push(new deck.ScatterplotLayer({{
      id: 'satellites',
      data: satellites,
      getPosition: d => [d.longitude, d.latitude],
      getRadius: d => {{
        if (d.group === 'starlink') return 8000;
        if (d.group === 'military') return 20000;
        if (d.group === 'stations') return 40000;
        return 14000;
      }},
      getFillColor: d => {{
        if (d.group === 'starlink') return [255,200,0,120];
        if (d.group === 'military') return [255,60,60,200];
        if (d.group === 'stations') return [255,255,255,255];
        if (d.group === 'gps-ops') return [100,200,255,180];
        return [255,170,0,180];
      }},
      filled: true,
      pickable: true, autoHighlight: true,
      highlightColor: [255, 170, 0, 255],
      onHover: showTooltip, onClick: showDetail,
      transitions: {{ getPosition: 3000 }},
    }}));
  }}

  // Webcams
  if (layersEnabled.webcams && webcams.length > 0) {{
    layers.push(new deck.ScatterplotLayer({{
      id: 'webcams',
      data: webcams,
      getPosition: d => [d.longitude || d.lon, d.latitude || d.lat],
      getRadius: 18000,
      getFillColor: [255, 0, 255, 200],
      filled: true, stroked: true,
      getLineColor: [255,255,255,150], lineWidthMinPixels: 1,
      pickable: true, autoHighlight: true,
      onHover: showTooltip, onClick: showDetail,
    }}));
  }}

  return layers;
}}

// ── deck.gl overlay ─────────────────────────────────────────
const deckOverlay = new deck.MapboxOverlay({{
  layers: buildLayers(),
  getTooltip: null,
}});
map.addControl(deckOverlay);

// ── Animation Loop ──────────────────────────────────────────
// Smoothly extrapolate entity positions between data refreshes
let lastAnimTime = performance.now();
let frameCount = 0;
let lastFpsUpdate = performance.now();

function animate() {{
  const now = performance.now();
  const dt = Math.min((now - lastAnimTime) / 1000, 0.5); // cap at 0.5s
  lastAnimTime = now;

  // FPS counter
  frameCount++;
  if (now - lastFpsUpdate > 1000) {{
    document.getElementById('hud-fps').textContent = frameCount + ' fps';
    frameCount = 0;
    lastFpsUpdate = now;
  }}

  let changed = false;

  // Move flights along heading
  if (layersEnabled.flights) {{
    flights.forEach(f => {{
      if (f.heading != null && f.velocity > 0) {{
        const speedMs = f.velocity; // m/s
        const hdRad = (f.heading * Math.PI) / 180;
        const dLat = (Math.cos(hdRad) * speedMs * dt) / 111320;
        const cosLat = Math.cos((f.latitude || 0) * Math.PI / 180) || 1;
        const dLon = (Math.sin(hdRad) * speedMs * dt) / (111320 * cosLat);
        f.latitude += dLat;
        f.longitude += dLon;
        changed = true;
      }}
    }});
  }}

  // Move vessels along heading
  if (layersEnabled.vessels) {{
    vessels.forEach(v => {{
      if (v.heading != null && v.speed_knots > 0) {{
        const speedMs = v.speed_knots * 0.5144; // knots to m/s
        const hdRad = ((v.heading || v.course || 0) * Math.PI) / 180;
        const dLat = (Math.cos(hdRad) * speedMs * dt) / 111320;
        const cosLat = Math.cos((v.latitude || 0) * Math.PI / 180) || 1;
        const dLon = (Math.sin(hdRad) * speedMs * dt) / (111320 * cosLat);
        v.latitude += dLat;
        v.longitude += dLon;
        changed = true;
      }}
    }});
  }}

  // Rotate satellites along orbit
  if (layersEnabled.satellites) {{
    satellites.forEach(s => {{
      if (s.period_min > 0) {{
        const angularSpeed = 360 / (s.period_min * 60); // deg/sec
        s.longitude += angularSpeed * dt;
        if (s.longitude > 180) s.longitude -= 360;
        if (s.longitude < -180) s.longitude += 360;
        changed = true;
      }}
    }});
  }}

  if (changed) {{
    deckOverlay.setProps({{ layers: buildLayers() }});
  }}

  requestAnimationFrame(animate);
}}

map.on('load', () => {{
  requestAnimationFrame(animate);
}});
</script>
</body>
</html>
"""
    return html


def render_globe(
    flights_df=None,
    vessels_df=None,
    satellites_df=None,
    sea_routes=None,
    chokepoints=None,
    webcams_df=None,
    layers_enabled=None,
    view_preset="global",
    height=700,
):
    """Render the interactive globe as a Streamlit component."""
    html = build_globe(
        flights_df=flights_df,
        vessels_df=vessels_df,
        satellites_df=satellites_df,
        sea_routes=sea_routes,
        chokepoints=chokepoints,
        webcams_df=webcams_df,
        layers_enabled=layers_enabled,
        view_preset=view_preset,
    )
    components.html(html, height=height, scrolling=False)


def render_globe_stats(flights_df, vessels_df, satellites_df, chokepoints):
    """Render summary statistics below the globe."""
    cols = st.columns(6)

    n_flights = len(flights_df) if flights_df is not None and not flights_df.empty else 0
    n_vessels = len(vessels_df) if vessels_df is not None and not vessels_df.empty else 0
    n_sats = len(satellites_df) if satellites_df is not None and not satellites_df.empty else 0
    n_threats = sum(1 for cp in (chokepoints or []) if cp.get("threat_level") in ("HIGH", "CRITICAL"))

    cols[0].metric("AIRCRAFT", f"{n_flights:,}")
    cols[1].metric("VESSELS", f"{n_vessels:,}")
    cols[2].metric("SATELLITES", f"{n_sats:,}")
    cols[3].metric("CHOKEPOINTS", str(len(chokepoints or [])))
    cols[4].metric("THREAT ZONES", str(n_threats))
    cols[5].metric("STATUS", "LIVE")

