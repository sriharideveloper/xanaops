"""
╔══════════════════════════════════════════════════════════════╗
║  XANA OS v4.2 — LIVE DATA FEEDS                               ║
╚══════════════════════════════════════════════════════════════╝

Real-time data — ALL FREE, NO API KEYS:

  ✈️  Aircraft      → OpenSky Network (global ADS-B, includes military)
  🚢  Vessels       → Finnish Digitraffic AIS (real, Baltic/Nordic)
                      + global simulation on real shipping lanes
  🛰️  Satellites    → CelesTrak multi-group (Starlink, Military, GPS, ISS…)
  📷  Webcams       → Windy.com API (thousands of live cams worldwide)
                      + public DOT traffic cameras + OSINT feeds
  🌤️  Weather       → Open-Meteo (instant weather for any coordinate)
  🔍  Geocoding     → Open-Meteo Geocoding
"""

import math
import time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timezone
from config import (
    OPENSKY_API, CELESTRAK_API, HTTP_HEADERS,
    CACHE_TTL_FLIGHTS, CACHE_TTL_VESSELS, CACHE_TTL_SATELLITES,
    CACHE_TTL_WEBCAMS, CACHE_TTL_REAL_AIS, CACHE_TTL_VESSEL_REGISTRY,
    CACHE_TTL_POINT_WEATHER, DIGITRAFFIC_AIS_API, DIGITRAFFIC_VESSELS_API,
    GLOBE_DEFAULT_SAT_GROUPS,
)


# ╔══════════════════════════════════════════════════════════════╗
# ║  FLIGHT TRACKER — OpenSky Network                            ║
# ╚══════════════════════════════════════════════════════════════╝

class FlightTracker:
    """Live aircraft tracking via OpenSky Network (anonymous, free).

    Includes military/cargo/private aircraft classification from callsigns.
    """

    # Known military callsign prefixes (partial list — covers NATO + major militaries)
    MILITARY_PREFIXES = [
        "RCH", "REACH", "EVAC", "DARK", "TOPCAT", "GORDO", "NCHO", "DUKE",
        "MOOSE", "KNIFE", "KING", "HAVOC", "ROGUE", "VADER",
        "NATO", "AWACS", "MAGIC", "MYSTIC",
        "RRR",          # US Army
        "CNV", "NAVY",  # US/generic Navy
        "BAF",          # Belgian Air Force
        "GAF",          # German Air Force
        "FAF",          # French Air Force
        "RFR",          # French Air Force (alt)
        "IAM",          # Italian Air Force
        "AME",          # Spanish Air Force (Ejército del Aire)
        "SUI",          # Swiss Air Force
        "SHF",          # Swedish Air Force
        "HVK",          # Netherlands Air Force
        "PLF",          # Polish Air Force
        "CFC",          # Canadian Forces
        "ASY",          # Royal Australian Air Force
        "IAF",          # Indian Air Force
        "JAF",          # Japan Air Self-Defense Force
        "BOLT", "VIPER", "SKULL", "FURY", "REAPER", "PROWL", "GHOST",
    ]

    # Commercial airline ICAO prefixes (mapping to category)
    CARGO_AIRLINES = [
        "FDX", "UPS", "GTI", "CLX", "ABW", "CKS", "BOX", "MPH",
        "CAO", "SQC", "KAL", "NCA", "ANA", "HVN",
    ]

    @staticmethod
    def classify_aircraft(callsign, country):
        """Classify aircraft by callsign and country of origin."""
        if not callsign:
            return "Unknown"
        cs = callsign.strip().upper()

        # Military detection
        for prefix in FlightTracker.MILITARY_PREFIXES:
            if cs.startswith(prefix):
                return "Military"

        # Cargo detection
        for prefix in FlightTracker.CARGO_AIRLINES:
            if cs.startswith(prefix):
                return "Cargo"

        # Government (typically short numeric-only callsigns from certain countries)
        if cs.isdigit() and len(cs) <= 5:
            return "Government"

        # General aviation (short alphanumeric callsigns like N-registered)
        if len(cs) <= 6 and (cs.startswith("N") or cs.startswith("G-") or
                              cs.startswith("D-") or cs.startswith("F-")):
            return "Private"

        # Default: commercial/unknown
        if cs[:3].isalpha() and len(cs) >= 4:
            return "Commercial"
        return "Unknown"

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_FLIGHTS, show_spinner=False)
    def fetch_all(bounds=None, _cache_key=None):
        """Fetch all aircraft currently in the air.

        Args:
            bounds: Optional dict with lat1, lon1, lat2, lon2 for bounding box.
        """
        try:
            params = {}
            if bounds:
                params = {
                    "lamin": bounds["lat1"], "lomin": bounds["lon1"],
                    "lamax": bounds["lat2"], "lomax": bounds["lon2"],
                }
            resp = requests.get(OPENSKY_API, params=params,
                                headers=HTTP_HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                states = data.get("states", [])
                if not states:
                    return pd.DataFrame()

                records = []
                for s in states:
                    if s[6] is None or s[5] is None:
                        continue
                    if s[8]:
                        continue  # skip ground

                    callsign = (s[1] or "").strip()
                    country = s[2] or ""
                    alt = float(s[7] or 0)
                    vel = float(s[9] or 0)
                    heading = float(s[10] or 0)

                    records.append({
                        "icao24": s[0] or "",
                        "callsign": callsign,
                        "country": country,
                        "longitude": float(s[5]),
                        "latitude": float(s[6]),
                        "altitude": alt,
                        "velocity": vel,
                        "heading": heading,
                        "vertical_rate": float(s[11] or 0),
                        "geo_altitude": float(s[13] or 0),
                        "aircraft_type": FlightTracker.classify_aircraft(callsign, country),
                        "speed_kmh": round(vel * 3.6, 0),
                        # Tooltip fields
                        "entity_type": "✈️ AIRCRAFT",
                        "name": callsign or s[0] or "Unknown",
                        "info": (
                            f"Country: {country} | Alt: {alt:,.0f}m | "
                            f"Speed: {vel * 3.6:,.0f} km/h | Hdg: {heading:.0f}°"
                        ),
                    })
                return pd.DataFrame(records)
        except Exception:
            pass
        return pd.DataFrame()

    @staticmethod
    def get_flight_summary(df):
        """Get summary statistics from flight data."""
        if df.empty:
            return {}
        return {
            "total_aircraft": len(df),
            "countries": df["country"].nunique(),
            "avg_altitude": df["altitude"].mean(),
            "max_altitude": df["altitude"].max(),
            "avg_speed": df["velocity"].mean() * 3.6,
            "top_countries": df["country"].value_counts().head(10).to_dict(),
            "military_count": len(df[df["aircraft_type"] == "Military"]),
            "cargo_count": len(df[df["aircraft_type"] == "Cargo"]),
            "commercial_count": len(df[df["aircraft_type"] == "Commercial"]),
            "type_breakdown": df["aircraft_type"].value_counts().to_dict(),
        }


# ╔══════════════════════════════════════════════════════════════╗
# ║  VESSEL TRACKER — Finnish AIS + Global Simulation             ║
# ╚══════════════════════════════════════════════════════════════╝

class VesselTracker:
    """Maritime vessel tracking — real AIS data + global simulation.

    Real AIS: Finnish Digitraffic Marine API (free, no key)
              Covers: Gulf of Finland, Baltic Sea, North Sea approaches
    Simulation: Realistic traffic on 10 major global shipping lanes
    """

    # AIS Ship Type codes → human-readable
    SHIP_TYPE_MAP = {
        range(20, 30): "WIG Craft",
        range(30, 36): "Fishing/Tug/Diving",
        range(36, 37): "Sailing",
        range(37, 38): "Pleasure Craft",
        range(40, 50): "High Speed Craft",
        range(50, 60): "Pilot/SAR/Port",
        range(60, 70): "Passenger Ship",
        range(70, 80): "Cargo Ship",
        range(80, 90): "Tanker",
        range(90, 100): "Other",
    }

    NAV_STATUS_MAP = {
        0: "Under way (engine)",
        1: "At anchor",
        2: "Not under command",
        3: "Restricted manoeuvrability",
        4: "Constrained by draught",
        5: "Moored",
        6: "Aground",
        7: "Fishing",
        8: "Under way (sailing)",
        11: "Power-driven towing astern",
        12: "Power-driven pushing ahead",
        14: "AIS-SART active",
        15: "Undefined",
    }

    SHIPPING_LANES = [
        {"name": "Suez-Mediterranean", "waypoints": [
            (31.28, 32.34), (33.0, 32.0), (35.0, 34.0), (30.0, 35.0),
            (20.0, 37.0), (10.0, 38.0), (5.0, 37.0), (-5.0, 36.0),
        ]},
        {"name": "Malacca Strait Route", "waypoints": [
            (103.8, 1.3), (100.5, 3.0), (98.0, 5.5), (95.0, 7.0),
            (85.0, 10.0), (78.0, 10.0), (73.0, 12.0),
        ]},
        {"name": "Persian Gulf Export", "waypoints": [
            (50.3, 26.5), (54.0, 25.5), (56.5, 25.0), (60.0, 23.0),
            (65.0, 20.0), (70.0, 15.0), (73.0, 12.0),
        ]},
        {"name": "Panama-Pacific Route", "waypoints": [
            (-79.5, 9.0), (-85.0, 10.0), (-100.0, 15.0),
            (-120.0, 20.0), (-140.0, 25.0), (-160.0, 30.0),
        ]},
        {"name": "North Atlantic Corridor", "waypoints": [
            (-74.0, 40.7), (-60.0, 42.0), (-40.0, 47.0),
            (-20.0, 50.0), (-5.0, 50.0), (0.0, 51.5),
        ]},
        {"name": "Cape of Good Hope Route", "waypoints": [
            (55.0, -5.0), (45.0, -12.0), (35.0, -25.0),
            (18.4, -34.0), (10.0, -30.0), (0.0, -5.0),
            (-10.0, 5.0), (-20.0, 10.0),
        ]},
        {"name": "East Asia-Pacific", "waypoints": [
            (121.5, 31.2), (125.0, 33.0), (130.0, 33.0),
            (140.0, 35.0), (150.0, 35.0), (160.0, 30.0), (180.0, 25.0),
        ]},
        {"name": "South China Sea Route", "waypoints": [
            (114.2, 22.3), (113.0, 18.0), (110.0, 12.0),
            (108.0, 8.0), (106.0, 5.0), (104.0, 1.3),
        ]},
        {"name": "Bab el-Mandeb Route", "waypoints": [
            (43.1, 12.6), (44.0, 13.0), (45.0, 14.5),
            (42.0, 15.0), (39.0, 20.0), (35.0, 28.0), (32.5, 30.0),
        ]},
        {"name": "Baltic Sea Trade", "waypoints": [
            (12.0, 54.5), (14.0, 55.0), (18.0, 56.0),
            (20.0, 58.0), (24.0, 59.5), (28.0, 60.0),
        ]},
    ]

    VESSEL_TYPES = [
        "Container Ship", "Bulk Carrier", "Oil Tanker", "LNG Carrier",
        "Cruise Ship", "Cargo Ship", "Chemical Tanker", "RORO Vessel",
        "Naval Vessel", "Fishing Vessel", "Submarine Support", "Deep-Sea Trawler",
    ]

    VESSEL_FLAGS = [
        "Panama", "Liberia", "Marshall Islands", "Hong Kong", "Singapore",
        "Malta", "Bahamas", "Greece", "China", "Japan", "Norway",
        "United Kingdom", "USA", "Germany", "Denmark", "Russia",
    ]

    @staticmethod
    def _classify_ship_type(type_code):
        """Convert AIS ship type code to human-readable string."""
        if type_code is None:
            return "Unknown"
        try:
            code = int(type_code)
        except (ValueError, TypeError):
            return "Unknown"
        for code_range, name in VesselTracker.SHIP_TYPE_MAP.items():
            if code in code_range:
                return name
        return "Unknown"

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_REAL_AIS, show_spinner=False)
    def fetch_real_ais():
        """Fetch REAL vessel positions from Finnish Digitraffic AIS API.

        Returns real AIS data covering Baltic Sea, Gulf of Finland, and
        Nordic waters. Completely free, no API key required.
        """
        try:
            resp = requests.get(
                DIGITRAFFIC_AIS_API,
                headers={**HTTP_HEADERS, "Accept-Encoding": "gzip"},
                timeout=20,
            )
            if resp.status_code != 200:
                return pd.DataFrame()

            data = resp.json()
            features = data.get("features", [])
            if not features:
                return pd.DataFrame()

            records = []
            for feat in features[:2000]:  # cap to prevent slowness
                geom = feat.get("geometry", {})
                props = feat.get("properties", {})
                coords = geom.get("coordinates", [None, None])

                if coords[0] is None or coords[1] is None:
                    continue

                lon, lat = float(coords[0]), float(coords[1])
                if lon == 0 and lat == 0:
                    continue

                mmsi = props.get("mmsi") or feat.get("mmsi", "")
                sog = props.get("sog", 0) or 0
                cog = props.get("cog", 0) or 0
                heading = props.get("heading", 0) or 0
                nav_stat = props.get("navStat", 15)

                # Skip moored/anchored for cleaner globe display
                if nav_stat in (1, 5) and sog < 0.5:
                    continue

                nav_desc = VesselTracker.NAV_STATUS_MAP.get(nav_stat, "Unknown")

                records.append({
                    "mmsi": str(mmsi),
                    "name": f"AIS-{mmsi}",
                    "longitude": round(lon, 5),
                    "latitude": round(lat, 5),
                    "speed_knots": round(sog / 10.0, 1),  # Digitraffic SOG is in 1/10 knot
                    "heading": round(heading / 10.0 if heading > 360 else heading, 1),
                    "course": round(cog / 10.0, 1),
                    "nav_status": nav_desc,
                    "type": "Real AIS",
                    "flag": "Detected",
                    "lane": "Baltic Sea (Live AIS)",
                    "source": "real",
                    "entity_type": "🚢 VESSEL (LIVE AIS)",
                    "info": (
                        f"MMSI: {mmsi} | SOG: {sog/10:.1f} kn | "
                        f"COG: {cog/10:.0f}° | Status: {nav_desc}"
                    ),
                })

            return pd.DataFrame(records)
        except Exception:
            return pd.DataFrame()

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_VESSEL_REGISTRY, show_spinner=False)
    def fetch_vessel_registry():
        """Fetch vessel metadata (names, types) from Digitraffic.

        Returns dict mapping MMSI → {name, shipType, destination, callSign}.
        """
        try:
            resp = requests.get(
                DIGITRAFFIC_VESSELS_API,
                headers={**HTTP_HEADERS, "Accept-Encoding": "gzip"},
                timeout=30,
            )
            if resp.status_code != 200:
                return {}

            vessels = resp.json()
            registry = {}
            for v in vessels:
                mmsi = str(v.get("mmsi", ""))
                if mmsi:
                    registry[mmsi] = {
                        "name": v.get("name", "").strip() or f"MMSI-{mmsi}",
                        "shipType": VesselTracker._classify_ship_type(v.get("shipType")),
                        "destination": v.get("destination", "").strip(),
                        "callSign": v.get("callSign", "").strip(),
                    }
            return registry
        except Exception:
            return {}

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_VESSELS, show_spinner=False)
    def generate_global_traffic(_timestamp_key=None):
        """Generate simulated vessel positions on real global shipping lanes."""
        import random
        seed = int(time.time() // 60)
        rng = random.Random(seed)
        vessels = []
        vid = 0

        for lane in VesselTracker.SHIPPING_LANES:
            n = rng.randint(8, 15)
            wps = lane["waypoints"]
            for _ in range(n):
                seg = rng.randint(0, len(wps) - 2)
                t = rng.random()
                lon1, lat1 = wps[seg]
                lon2, lat2 = wps[seg + 1]
                lon = lon1 + t * (lon2 - lon1) + rng.gauss(0, 0.3)
                lat = lat1 + t * (lat2 - lat1) + rng.gauss(0, 0.2)
                speed = rng.uniform(8, 22)
                hd = math.degrees(math.atan2(lon2 - lon1, lat2 - lat1)) % 360
                v_type = rng.choice(VesselTracker.VESSEL_TYPES)
                v_flag = rng.choice(VesselTracker.VESSEL_FLAGS)
                v_name = (
                    f"{rng.choice(['MV', 'MT', 'MSC', 'CMA', 'HMS', 'USNS'])} "
                    f"{rng.choice(['PACIFIC', 'ATLANTIC', 'ORIENT', 'NORDIC', 'LIBERTY', 'STAR', 'FORTUNE', 'DRAGON', 'EAGLE', 'PEARL', 'ENDURANCE', 'RESOLVE'])} "
                    f"{rng.choice(['I', 'II', 'III', 'EXPRESS', 'SPIRIT', 'VOYAGER'])}"
                )
                vessels.append({
                    "mmsi": f"SIM{vid:05d}",
                    "name": v_name,
                    "longitude": round(lon, 4),
                    "latitude": round(lat, 4),
                    "speed_knots": round(speed, 1),
                    "heading": round(hd, 1),
                    "course": round(hd, 1),
                    "nav_status": "Under way (engine)",
                    "type": v_type,
                    "flag": v_flag,
                    "lane": lane["name"],
                    "source": "simulation",
                    "entity_type": "🚢 VESSEL",
                    "info": (
                        f"{v_type} | {v_flag} | {speed:.1f} kn | "
                        f"Lane: {lane['name']}"
                    ),
                })
                vid += 1
        return pd.DataFrame(vessels)

    @staticmethod
    def get_combined_vessels():
        """Merge real AIS + global simulation → unified vessel DataFrame."""
        real = VesselTracker.fetch_real_ais()

        # Enrich real AIS with vessel registry (names, types)
        if not real.empty:
            registry = VesselTracker.fetch_vessel_registry()
            if registry:
                for idx, row in real.iterrows():
                    meta = registry.get(row["mmsi"])
                    if meta:
                        real.at[idx, "name"] = meta["name"]
                        real.at[idx, "type"] = meta["shipType"]
                        real.at[idx, "info"] = (
                            f"{meta['name']} | {meta['shipType']} | "
                            f"{row['speed_knots']} kn | {row['nav_status']}"
                        )

        simulated = VesselTracker.generate_global_traffic(
            _timestamp_key=int(time.time() // 120)
        )

        parts = []
        if not real.empty:
            parts.append(real)
        if not simulated.empty:
            parts.append(simulated)

        if parts:
            combined = pd.concat(parts, ignore_index=True)
            return combined
        return pd.DataFrame()

    @staticmethod
    def get_sea_routes():
        """Get shipping lane paths for visualization."""
        routes = []
        for lane in VesselTracker.SHIPPING_LANES:
            path = [[wp[0], wp[1]] for wp in lane["waypoints"]]
            routes.append({"name": lane["name"], "path": path})
        return routes


# ╔══════════════════════════════════════════════════════════════╗
# ║  SATELLITE TRACKER — CelesTrak Multi-Group                   ║
# ╚══════════════════════════════════════════════════════════════╝

class SatelliteTracker:
    """Live satellite tracking from CelesTrak — Starlink, Military, GPS, ISS…

    Computes real-time lat/lon from Two-Line Element (TLE) orbital data
    using Keplerian approximation. No sgp4 dependency needed.
    """

    @staticmethod
    def _compute_gmst(utc_now):
        """Greenwich Mean Sidereal Time in degrees."""
        j2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        du = (utc_now - j2000).total_seconds() / 86400.0
        return (280.46061837 + 360.98564736629 * du) % 360.0

    @staticmethod
    def _omm_to_position(omm, utc_now):
        """Compute approximate satellite lat/lon from OMM orbital elements."""
        try:
            epoch_str = omm.get("EPOCH", "")
            if not epoch_str:
                return None

            epoch_str = epoch_str.replace("Z", "+00:00")
            if "+" not in epoch_str and "-" not in epoch_str[10:]:
                epoch_str += "+00:00"
            try:
                epoch = datetime.fromisoformat(epoch_str)
            except ValueError:
                return None
            if epoch.tzinfo is None:
                epoch = epoch.replace(tzinfo=timezone.utc)

            dt = (utc_now - epoch).total_seconds()
            mean_motion = float(omm.get("MEAN_MOTION", 0))
            if mean_motion <= 0:
                return None

            period = 86400.0 / mean_motion
            inc = math.radians(float(omm.get("INCLINATION", 0)))
            raan = math.radians(float(omm.get("RA_OF_ASC_NODE", 0)))
            ma0 = math.radians(float(omm.get("MEAN_ANOMALY", 0)))
            omega = math.radians(float(omm.get("ARG_OF_PERICENTER", 0)))

            n = 2.0 * math.pi / period
            ma = (ma0 + n * dt) % (2.0 * math.pi)
            u = ma + omega

            sin_lat = math.sin(inc) * math.sin(u)
            sin_lat = max(-1.0, min(1.0, sin_lat))
            lat = math.degrees(math.asin(sin_lat))

            gmst = SatelliteTracker._compute_gmst(utc_now)
            cos_u = math.cos(u)
            sin_u = math.sin(u)
            cos_inc = math.cos(inc)

            lon_orbital = math.degrees(math.atan2(
                cos_inc * sin_u * math.cos(raan) + cos_u * math.sin(raan),
                cos_u * math.cos(raan) - cos_inc * sin_u * math.sin(raan),
            ))
            lon = (lon_orbital - gmst + 180) % 360 - 180

            mu = 398600.4418
            a = (mu * (period / (2 * math.pi)) ** 2) ** (1.0 / 3.0)
            alt = a - 6371.0

            return {"lat": lat, "lon": lon, "alt": max(0, alt)}
        except Exception:
            return None

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_SATELLITES, show_spinner=False)
    def fetch_satellites(group="stations", limit=100):
        """Fetch satellite data for a single group."""
        try:
            resp = requests.get(
                CELESTRAK_API,
                params={"GROUP": group, "FORMAT": "json"},
                headers=HTTP_HEADERS, timeout=15,
            )
            if resp.status_code != 200:
                return pd.DataFrame()

            satellites = resp.json()
            if not isinstance(satellites, list):
                return pd.DataFrame()

            utc_now = datetime.now(timezone.utc)
            records = []
            for sat in satellites[:limit]:
                pos = SatelliteTracker._omm_to_position(sat, utc_now)
                if pos is None:
                    continue
                sat_name = sat.get("OBJECT_NAME", "Unknown")
                norad = sat.get("NORAD_CAT_ID", "")
                alt_km = round(pos["alt"], 1)
                period = round(1440.0 / float(sat.get("MEAN_MOTION", 15)), 1)
                records.append({
                    "name": sat_name,
                    "norad_id": norad,
                    "longitude": round(pos["lon"], 4),
                    "latitude": round(pos["lat"], 4),
                    "altitude_km": alt_km,
                    "inclination": float(sat.get("INCLINATION", 0)),
                    "period_min": period,
                    "group": group,
                    "entity_type": "🛰️ SATELLITE",
                    "info": (
                        f"NORAD: {norad} | Alt: {alt_km:,.0f} km | "
                        f"Group: {group} | Period: {period} min"
                    ),
                })
            return pd.DataFrame(records)
        except Exception:
            return pd.DataFrame()

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_SATELLITES, show_spinner=False)
    def fetch_multi_group(groups=None, limit_per_group=60):
        """Fetch satellites from MULTIPLE groups in one call.

        Default groups: ISS/stations, Starlink, Military, GPS, Weather.
        Returns combined DataFrame with 'group' column.
        """
        if groups is None:
            groups = GLOBE_DEFAULT_SAT_GROUPS

        all_frames = []
        for group in groups:
            df = SatelliteTracker.fetch_satellites(group=group, limit=limit_per_group)
            if not df.empty:
                all_frames.append(df)

        if all_frames:
            return pd.concat(all_frames, ignore_index=True)
        return pd.DataFrame()

    @staticmethod
    def get_satellite_summary(df):
        """Get summary statistics from satellite data."""
        if df.empty:
            return {}
        return {
            "total_tracked": len(df),
            "avg_altitude": df["altitude_km"].mean(),
            "leo_count": len(df[df["altitude_km"] < 2000]),
            "meo_count": len(df[(df["altitude_km"] >= 2000) & (df["altitude_km"] < 35000)]),
            "geo_count": len(df[df["altitude_km"] >= 35000]),
            "groups": df["group"].value_counts().to_dict() if "group" in df else {},
            "starlink_count": len(df[df["group"] == "starlink"]) if "group" in df else 0,
            "military_count": len(df[df["group"] == "military"]) if "group" in df else 0,
        }


# ╔══════════════════════════════════════════════════════════════╗
# ║  WEBCAM INTELLIGENCE — Windy API + Public DOT Feeds           ║
# ╚══════════════════════════════════════════════════════════════╝

class WebcamIntel:
    """Real OSINT-grade webcam feeds from public APIs.

    Sources:
      1. Windy Webcams API v3 — thousands of real live cams worldwide
         (free tier: 1000 req/day, needs free API key from api.windy.com)
      2. Public DOT traffic camera feeds (direct image URLs)
      3. Global weather/port cameras

    All cameras return actual live image URLs or player embed URLs.
    """

    # Windy API key — get free at https://api.windy.com/
    # Set env var WINDY_API_KEY or it will use the fallback curated list
    WINDY_API_KEY = "oWG9Lbjhvq7P4YYGrBSZJc8YbcjaV495"



    @staticmethod
    def _get_windy_key():
        """Get Windy API key from environment."""
        import os
        return os.environ.get("WINDY_API_KEY", WebcamIntel.WINDY_API_KEY)

    @staticmethod
    @st.cache_data(ttl=300, show_spinner=False)
    def fetch_windy_nearby(lat, lon, radius_km=100, limit=50):
        """Fetch real webcams from Windy API near a location."""
        key = WebcamIntel._get_windy_key()
        if not key:
            return []
        try:
            resp = requests.get(
                "https://api.windy.com/webcams/v3/webcams",
                params={
                    "nearby": f"{lat},{lon},{radius_km}",
                    "limit": limit,
                    "include": "images,player,location",
                },
                headers={"x-windy-api-key": key},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                cams = []
                for wc in data.get("webcams", []):
                    loc = wc.get("location", {})
                    images = wc.get("images", {})
                    player = wc.get("player", {})
                    cams.append({
                        "id": wc.get("webcamId", ""),
                        "name": wc.get("title", "Unknown"),
                        "lat": loc.get("latitude", 0),
                        "lon": loc.get("longitude", 0),
                        "latitude": loc.get("latitude", 0),
                        "longitude": loc.get("longitude", 0),
                        "country": loc.get("country", ""),
                        "city": loc.get("city", ""),
                        "image_url": images.get("current", {}).get("preview", ""),
                        "thumbnail": images.get("current", {}).get("thumbnail", ""),
                        "player_url": player.get("day", {}).get("embed", "")
                            or player.get("lifetime", {}).get("embed", ""),
                        "type": "Live Webcam",
                        "source": "Windy API",
                        "embeddable": bool(player.get("day", {}).get("embed")),
                        "url": f"https://www.windy.com/webcams/{wc.get('webcamId','')}",
                        "entity_type": "📷 WEBCAM",
                        "info": f"Live | {loc.get('city','')} {loc.get('country','')} | Windy",
                    })
                return cams
        except Exception:
            pass
        return []

    @staticmethod
    @st.cache_data(ttl=300, show_spinner=False)
    def fetch_windy_global(limit=200):
        """Fetch popular webcams worldwide from Windy API."""
        key = WebcamIntel._get_windy_key()
        if not key:
            return []
        try:
            resp = requests.get(
                "https://api.windy.com/webcams/v3/webcams",
                params={
                    "limit": limit,
                    "include": "images,player,location",
                    "orderby": "popularity",
                },
                headers={"x-windy-api-key": key},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                cams = []
                for wc in data.get("webcams", []):
                    loc = wc.get("location", {})
                    images = wc.get("images", {})
                    player = wc.get("player", {})
                    cams.append({
                        "id": wc.get("webcamId", ""),
                        "name": wc.get("title", "Unknown"),
                        "lat": loc.get("latitude", 0),
                        "lon": loc.get("longitude", 0),
                        "latitude": loc.get("latitude", 0),
                        "longitude": loc.get("longitude", 0),
                        "country": loc.get("country", ""),
                        "city": loc.get("city", ""),
                        "image_url": images.get("current", {}).get("preview", ""),
                        "thumbnail": images.get("current", {}).get("thumbnail", ""),
                        "player_url": player.get("day", {}).get("embed", "")
                            or player.get("lifetime", {}).get("embed", ""),
                        "type": "Live Webcam",
                        "source": "Windy API",
                        "embeddable": bool(player.get("day", {}).get("embed")),
                        "url": f"https://www.windy.com/webcams/{wc.get('webcamId','')}",
                        "entity_type": "📷 WEBCAM",
                        "info": f"Live | {loc.get('city','')} {loc.get('country','')} | Windy",
                    })
                return cams
        except Exception:
            pass
        return []

    # Public DOT + infrastructure cameras (real image URLs, updated periodically)
    DOT_CAMERAS = [
        # US DOT Traffic Cameras (direct JPEG feeds, refresh every 30-120s)
        {"name": "I-405 Los Angeles", "lat": 33.97, "lon": -118.39,
         "image_url": "https://cwwp2.dot.ca.gov/data/d7/cctv/image/i405-manning/i405-manning.jpg",
         "type": "DOT Traffic", "source": "Caltrans"},
        {"name": "I-80 San Francisco Bay Bridge", "lat": 37.82, "lon": -122.35,
         "image_url": "https://cwwp2.dot.ca.gov/data/d4/cctv/image/tvr08--80-at-bay-bridge-toll/tvr08--80-at-bay-bridge-toll.jpg",
         "type": "DOT Traffic", "source": "Caltrans"},
        {"name": "I-5 Downtown Seattle", "lat": 47.61, "lon": -122.33,
         "image_url": "https://images.wsdot.wa.gov/nw/005vc06464.jpg",
         "type": "DOT Traffic", "source": "WSDOT"},
        {"name": "I-90 Floating Bridge Seattle", "lat": 47.59, "lon": -122.28,
         "image_url": "https://images.wsdot.wa.gov/nw/090vc02498.jpg",
         "type": "DOT Traffic", "source": "WSDOT"},
        # Airport cameras
        {"name": "Zürich Airport Runway", "lat": 47.458, "lon": 8.548,
         "image_url": "https://www.airport-zurich.com/webcam/cam_dock_e.jpg",
         "type": "Airport", "source": "Zurich Airport"},
        # Port / maritime cameras
        {"name": "Port of Rotterdam Europoort", "lat": 51.955, "lon": 4.130,
         "image_url": "https://www.portofrotterdam.com/sites/default/files/webcam-europoort.jpg",
         "type": "Port", "source": "Port of Rotterdam"},
        {"name": "Port of Singapore Keppel", "lat": 1.263, "lon": 103.822,
         "image_url": "https://www.psa.com.sg/webcam/keppel.jpg",
         "type": "Port", "source": "PSA Singapore"},
        # Weather / Volcano cams
        {"name": "Mount Etna Volcano", "lat": 37.751, "lon": 14.994,
         "image_url": "https://www.ct.ingv.it/WEBCAMS/images/cam_etna01.jpg",
         "type": "Volcano", "source": "INGV"},
        {"name": "Yellowstone Old Faithful", "lat": 44.460, "lon": -110.828,
         "image_url": "https://www.nps.gov/webcams-yell/oldfaith2.jpg",
         "type": "Nature", "source": "NPS"},
        # City cams (public infrastructure)
        {"name": "London Tower Bridge", "lat": 51.505, "lon": -0.075,
         "image_url": "https://www.towerbridge.org.uk/webcam/webcam.jpg",
         "type": "Infrastructure", "source": "TowerBridge"},
        {"name": "NYC George Washington Bridge", "lat": 40.851, "lon": -73.952,
         "image_url": "https://511ny.org/map/Cctv/0600025--1",
         "type": "DOT Traffic", "source": "511NY"},
        {"name": "Hong Kong Victoria Harbour", "lat": 22.293, "lon": 114.169,
         "image_url": "https://www.hko.gov.hk/wxinfo/aws/hko_mica/cp1/latest_CP1.jpg",
         "type": "Port", "source": "HK Observatory"},
        {"name": "Tokyo Bay Rainbow Bridge", "lat": 35.637, "lon": 139.762,
         "image_url": "https://weathernews.jp/livecam/cgi/livecam_movie.cgi?id=350",
         "type": "Infrastructure", "source": "WeatherNews JP"},
    ]

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_WEBCAMS, show_spinner=False)
    def get_webcams(filter_type=None):
        """Get all available webcams — merges Windy API + public DOT feeds."""
        all_cams = []

        # Try Windy API first (real live feeds)
        windy_cams = WebcamIntel.fetch_windy_global(limit=150)
        all_cams.extend(windy_cams)

        # Add public DOT / infrastructure cameras
        for cam in WebcamIntel.DOT_CAMERAS:
            all_cams.append({
                **cam,
                "latitude": cam["lat"],
                "longitude": cam["lon"],
                "embeddable": False,
                "player_url": "",
                "thumbnail": cam.get("image_url", ""),
                "url": cam.get("image_url", ""),
                "entity_type": "📷 WEBCAM",
                "name": cam["name"],
                "info": f"{cam['type']} | {cam['source']} | Live Image Feed",
            })

        if filter_type and filter_type != "All":
            all_cams = [c for c in all_cams if c.get("type") == filter_type]

        return pd.DataFrame(all_cams) if all_cams else pd.DataFrame()

    @staticmethod
    def get_camera_types():
        """Get available camera type categories."""
        types = set()
        for cam in WebcamIntel.DOT_CAMERAS:
            types.add(cam["type"])
        types.update(["Live Webcam"])  # Windy type
        return ["All"] + sorted(types)

    @staticmethod
    def find_nearest(lat, lon, max_distance_km=500):
        """Find cameras near a location — first tries Windy API, then DOT list."""
        results = []

        # Try Windy API for nearby cams
        windy_nearby = WebcamIntel.fetch_windy_nearby(lat, lon, radius_km=min(max_distance_km, 250))
        for cam in windy_nearby[:10]:
            dlat = math.radians(cam["lat"] - lat)
            dlon = math.radians(cam["lon"] - lon)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat)) * math.cos(math.radians(cam["lat"])) *
                 math.sin(dlon / 2) ** 2)
            dist = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            results.append({**cam, "distance_km": round(dist, 1)})

        # Also check DOT cameras
        for cam in WebcamIntel.DOT_CAMERAS:
            dlat = math.radians(cam["lat"] - lat)
            dlon = math.radians(cam["lon"] - lon)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat)) * math.cos(math.radians(cam["lat"])) *
                 math.sin(dlon / 2) ** 2)
            dist = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            if dist <= max_distance_km:
                results.append({
                    **cam,
                    "latitude": cam["lat"],
                    "longitude": cam["lon"],
                    "embeddable": False,
                    "url": cam.get("image_url", ""),
                    "distance_km": round(dist, 1),
                })

        results.sort(key=lambda x: x["distance_km"])
        return results[:15]


# ╔══════════════════════════════════════════════════════════════╗
# ║  WEATHER SERVICE — Open-Meteo (free, no key)                  ║
# ╚══════════════════════════════════════════════════════════════╝

class WeatherService:
    """Instant weather for any coordinate on Earth. Uses Open-Meteo (free).

    Also includes geocoding via Open-Meteo Geocoding API.
    """

    WEATHER_CODES = {
        0: ("☀️", "Clear sky"),
        1: ("🌤️", "Mainly clear"), 2: ("⛅", "Partly cloudy"), 3: ("☁️", "Overcast"),
        45: ("🌫️", "Fog"), 48: ("🌫️", "Rime fog"),
        51: ("🌦️", "Light drizzle"), 53: ("🌦️", "Moderate drizzle"), 55: ("🌦️", "Dense drizzle"),
        61: ("🌧️", "Light rain"), 63: ("🌧️", "Moderate rain"), 65: ("🌧️", "Heavy rain"),
        71: ("🌨️", "Light snow"), 73: ("🌨️", "Moderate snow"), 75: ("❄️", "Heavy snow"),
        80: ("🌧️", "Rain showers"), 81: ("🌧️", "Moderate showers"), 82: ("⛈️", "Violent showers"),
        85: ("🌨️", "Snow showers"), 86: ("🌨️", "Heavy snow showers"),
        95: ("⛈️", "Thunderstorm"), 96: ("⛈️", "Thunderstorm + hail"), 99: ("⛈️", "Severe thunderstorm"),
    }

    @staticmethod
    @st.cache_data(ttl=300, show_spinner=False)
    def geocode(query):
        """Geocode a place name to lat/lon using Open-Meteo Geocoding API.

        Returns dict with lat, lon, name, country or None.
        """
        try:
            import urllib.parse
            resp = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": query, "count": 3, "language": "en", "format": "json"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    r = results[0]
                    return {
                        "lat": r["latitude"],
                        "lon": r["longitude"],
                        "name": r.get("name", query),
                        "country": r.get("country", "Unknown"),
                        "admin": r.get("admin1", ""),
                        "population": r.get("population", 0),
                    }
        except Exception:
            pass
        return None

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_POINT_WEATHER, show_spinner=False)
    def fetch_at_location(lat, lon):
        """Get current weather + 24h forecast at any lat/lon."""
        try:
            resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "current_weather": True,
                    "hourly": "temperature_2m,windspeed_10m,relativehumidity_2m,weathercode",
                    "forecast_days": 1,
                    "timezone": "auto",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    @staticmethod
    def format_weather(weather_data):
        """Format weather data into display dict."""
        if not weather_data or "current_weather" not in weather_data:
            return None
        cw = weather_data["current_weather"]
        code = cw.get("weathercode", 0)
        emoji, desc = WeatherService.WEATHER_CODES.get(code, ("🌡️", "Unknown"))
        return {
            "emoji": emoji,
            "description": desc,
            "temperature": cw.get("temperature", "N/A"),
            "windspeed": cw.get("windspeed", "N/A"),
            "winddirection": cw.get("winddirection", "N/A"),
            "is_day": cw.get("is_day", 1),
        }
