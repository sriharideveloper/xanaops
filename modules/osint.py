"""
╔══════════════════════════════════════════════════════════════╗
║  XANA OS v4.0 — OSINT ENGINE (Expanded Intelligence)         ║
╚══════════════════════════════════════════════════════════════╝

Provides intelligence gathering from multiple open sources:
- World news (RSS multi-feed)
- Cybersecurity threat feeds (CISA KEV)
- IP geolocation & domain recon
- Cryptocurrency markets
- Weather intelligence
- GDELT geopolitical events
- Geofenced news for threat corridors
"""

import urllib.parse
import requests
import feedparser
import streamlit as st
from config import (
    HTTP_HEADERS, NEWS_FEEDS, CISA_VULNS_API, IP_API,
    GEOCODING_API, WEATHER_API, COINGECKO_API, GDELT_API,
    CACHE_TTL_NEWS, CACHE_TTL_THREATS, CACHE_TTL_IP,
    CACHE_TTL_DOMAIN, CACHE_TTL_WEATHER, CACHE_TTL_CRYPTO,
)


class OSINTEngine:
    """Open Source Intelligence gathering engine."""

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_NEWS, show_spinner=False)
    def fetch_world_news(query="world", max_results=15):
        """Fetch news from multiple RSS feeds."""
        feeds = [
            f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en",
        ] + NEWS_FEEDS

        articles = []
        for url in feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:max_results]:
                    pub_date = entry.get("published", entry.get("updated", "Unknown"))
                    articles.append({
                        "title": entry.get("title", "No Title"),
                        "link": entry.get("link", ""),
                        "summary": entry.get("summary", "")[:300],
                        "source": feed.feed.get("title", "Unknown Source"),
                        "published": pub_date,
                    })
            except Exception:
                continue

        seen_titles = set()
        unique = []
        for a in articles:
            key = a["title"][:50].lower()
            if key not in seen_titles:
                seen_titles.add(key)
                unique.append(a)
        return unique[:max_results]

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_NEWS, show_spinner=False)
    def fetch_geofenced_news(keywords, max_results=10):
        """Fetch news relevant to specific geographic keywords (for threat corridors)."""
        query = " OR ".join(keywords)
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
        articles = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_results]:
                articles.append({
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:250],
                    "source": feed.feed.get("title", "Unknown"),
                    "published": entry.get("published", "Unknown"),
                })
        except Exception:
            pass
        return articles

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_THREATS, show_spinner=False)
    def fetch_threat_feeds():
        """Fetch cybersecurity threat intelligence from CISA KEV."""
        threats = []
        try:
            resp = requests.get(CISA_VULNS_API, headers=HTTP_HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for vuln in data.get("vulnerabilities", [])[:25]:
                    threats.append({
                        "id": vuln.get("cveID", "N/A"),
                        "name": vuln.get("vulnerabilityName", "Unknown"),
                        "vendor": vuln.get("vendorProject", "Unknown"),
                        "product": vuln.get("product", "Unknown"),
                        "date_added": vuln.get("dateAdded", "Unknown"),
                        "description": vuln.get("shortDescription", "No description"),
                        "severity": "HIGH",
                    })
        except Exception:
            pass
        return threats

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_IP, show_spinner=False)
    def fetch_ip_intel(ip_address):
        """Lookup IP geolocation and threat data."""
        import ipaddress as _ipaddress
        try:
            _ipaddress.ip_address(ip_address)  # Validate IPv4/IPv6
        except ValueError:
            return {"status": "fail", "message": "Invalid IP address format"}
        try:
            resp = requests.get(IP_API.format(ip=ip_address), timeout=8)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {"status": "fail", "message": "Lookup failed"}

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_DOMAIN, show_spinner=False)
    def fetch_domain_intel(domain):
        """Domain reconnaissance via DNS."""
        intel = {"domain": domain, "records": {}}
        try:
            import socket
            ips = socket.getaddrinfo(domain, None)
            unique_ips = list(set(ip[4][0] for ip in ips))
            intel["records"]["A"] = unique_ips
            for ip in unique_ips[:3]:
                try:
                    hostname = socket.gethostbyaddr(ip)
                    intel["records"]["PTR"] = hostname[0]
                except Exception:
                    pass
        except Exception as e:
            intel["error"] = str(e)
        return intel

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_CRYPTO, show_spinner=False)
    def fetch_crypto_markets():
        """Fetch top cryptocurrency prices."""
        try:
            resp = requests.get(
                COINGECKO_API,
                params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": 15, "page": 1},
                headers=HTTP_HEADERS, timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_WEATHER, show_spinner=False)
    def fetch_weather_intel(city="New York"):
        """Fetch weather data from Open-Meteo."""
        try:
            geo_resp = requests.get(
                f"{GEOCODING_API}?name={urllib.parse.quote(city)}&count=1",
                timeout=8,
            )
            if geo_resp.status_code == 200:
                geo = geo_resp.json()
                if geo.get("results"):
                    lat = geo["results"][0]["latitude"]
                    lon = geo["results"][0]["longitude"]
                    name = geo["results"][0].get("name", city)

                    weather_resp = requests.get(
                        f"{WEATHER_API}?latitude={lat}&longitude={lon}"
                        f"&current_weather=true"
                        f"&hourly=temperature_2m,relativehumidity_2m,windspeed_10m",
                        timeout=8,
                    )
                    if weather_resp.status_code == 200:
                        data = weather_resp.json()
                        return {"city": name, "lat": lat, "lon": lon, "weather": data}
        except Exception:
            pass
        return None

    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_NEWS, show_spinner=False)
    def fetch_gdelt_events(query="conflict", max_results=20):
        """Fetch geolocated events from GDELT."""
        events = []
        try:
            params = {
                "query": query,
                "mode": "artlist",
                "maxrecords": str(max_results),
                "format": "json",
                "sort": "DateDesc",
            }
            resp = requests.get(GDELT_API, params=params, headers=HTTP_HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for article in data.get("articles", []):
                    events.append({
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "source": article.get("domain", ""),
                        "date": article.get("seendate", ""),
                        "language": article.get("language", ""),
                        "tone": article.get("tone", 0),
                    })
        except Exception:
            pass
        return events

    @staticmethod
    def geocode_location(location_name):
        """Geocode a location name to lat/lon."""
        try:
            resp = requests.get(
                f"{GEOCODING_API}?name={urllib.parse.quote(location_name)}&count=1",
                timeout=8,
            )
            if resp.status_code == 200:
                geo = resp.json()
                if geo.get("results"):
                    r = geo["results"][0]
                    return {
                        "lat": r["latitude"],
                        "lon": r["longitude"],
                        "name": r.get("name", location_name),
                        "country": r.get("country", "Unknown"),
                    }
        except Exception:
            pass
        return None
