"""
╔══════════════════════════════════════════════════════════════╗
║  XANA OS v4.0 — AGENTIC INTELLIGENCE SYSTEM                   ║
╚══════════════════════════════════════════════════════════════╝

Autonomous agent capabilities:
- Command routing (app launch, search, shell, OSINT)
- PHANTOM Protocol: Multi-step autonomous investigation
- Entity extraction and correlation
- Auto-briefing from multi-source intelligence
"""

import subprocess
import shlex
import urllib.parse
import datetime
import json
import os
import re
import ollama
import streamlit as st
from config import APP_LAUNCH_MAP, AGENT_SAFE_COMMANDS, LLM_MODEL
from modules.osint import OSINTEngine
from modules.database import query_memories, build_context_string, format_uptime


# ╔══════════════════════════════════════════════════════════════╗
# ║  COMMAND ROUTER — Detects and executes direct commands        ║
# ╚══════════════════════════════════════════════════════════════╝

class AgentRouter:
    """Routes user commands to system actions."""

    @staticmethod
    def detect_action(prompt):
        """Detect if a prompt is a system action command."""
        p = prompt.lower().strip()

        if p.startswith("play ") and ("youtube" in p or "on y" in p):
            song = re.sub(r"play\s+|on\s+youtube|on\s+y", "", p).strip()
            return ("youtube", song)

        if p.startswith("search google for ") or p.startswith("google "):
            query = p.replace("search google for ", "").replace("google ", "").strip()
            return ("google", query)

        if p.startswith("search for ") or p.startswith("search "):
            query = p.replace("search for ", "").replace("search ", "").strip()
            return ("search", query)

        if p.startswith("open ") or p.startswith("launch "):
            app = p.replace("open ", "").replace("launch ", "").strip()
            return ("app", app)

        if p.startswith("log:") or p.startswith("memo:") or p.startswith("note:"):
            text = prompt.split(":", 1)[1].strip()
            return ("log", text)

        if p in ("system status", "status", "diagnostics", "sys status"):
            return ("status", None)

        if p.startswith("exec ") or p.startswith("shell "):
            cmd = p.split(" ", 1)[1].strip() if " " in p else ""
            return ("shell", cmd)

        if p.startswith("weather ") or p.startswith("weather in "):
            city = p.replace("weather in ", "").replace("weather ", "").strip()
            return ("weather", city)

        if p.startswith("whois ") or p.startswith("ip "):
            target = p.split(" ", 1)[1].strip()
            return ("ip_lookup", target)

        if p.startswith("lookup ") or p.startswith("intel "):
            target = p.split(" ", 1)[1].strip() if " " in p else ""
            return ("osint_lookup", target)

        # PHANTOM investigation trigger
        if p.startswith("phantom ") or p.startswith("investigate "):
            target = p.split(" ", 1)[1].strip() if " " in p else ""
            return ("phantom", target)

        # Recon sweep
        if p.startswith("recon ") or p.startswith("sweep "):
            target = p.split(" ", 1)[1].strip() if " " in p else ""
            return ("recon", target)

        return None

    @staticmethod
    def execute(action_type, data):
        """Execute the detected action and return a response string."""

        if action_type == "youtube":
            encoded = urllib.parse.quote(data)
            url = f"https://www.youtube.com/results?search_query={encoded}"
            try:
                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            return f"[MEDIA PROTOCOL] YouTube search initiated for **'{data}'**"

        elif action_type == "google":
            encoded = urllib.parse.quote(data)
            url = f"https://www.google.com/search?q={encoded}"
            try:
                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            return f"[NETWORK SCAN] Google search deployed for **'{data}'**"

        elif action_type == "search":
            encoded = urllib.parse.quote(data)
            url = f"https://duckduckgo.com/?q={encoded}"
            try:
                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            return f"[NETWORK SCAN] DuckDuckGo search deployed for **'{data}'**"

        elif action_type == "app":
            exe = APP_LAUNCH_MAP.get(data, data)
            try:
                subprocess.Popen(exe.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"[PROCESS INJECT] Application **'{data}'** launched successfully"
            except Exception:
                return f"[PROCESS FAIL] Could not launch **'{data}'** — binary not found"

        elif action_type == "log":
            with open("xana_secure_logs.txt", "a", encoding="utf-8") as f:
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{ts}] {data}\n")
            return f"[SECURE LOG] Entry written to `xana_secure_logs.txt`"

        elif action_type == "status":
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            uptime = format_uptime(st.session_state.get("boot_time", 0))
            return f"""**XANA SYSTEM STATUS v4.0 — PROMETHEUS**
| Parameter | Value |
|---|---|
| Host OS | Linux (Native) |
| Local Time | {now} |
| Session Uptime | {uptime} |
| Neural Engine | {LLM_MODEL} |
| Vector DB | ChromaDB (MiniLM-L6-v2) |
| OSINT Engine | Online |
| Globe Intel | Active |
| Flight Tracker | Active |
| Vessel Tracker | Active |
| Satellite Tracker | Active |
| Agentic Router | Active |
| PHANTOM Protocol | Standby |"""

        elif action_type == "shell":
            if not data:
                return "[SHELL ERROR] No command specified"
            # Strict allowlist: match first token (command name) only
            cmd_parts = shlex.split(data)
            cmd_name = cmd_parts[0] if cmd_parts else ""
            SAFE_CMD_NAMES = {
                "ls", "pwd", "whoami", "date", "uptime", "df", "free",
                "head", "tail", "wc", "echo", "hostname", "uname", "neofetch",
            }
            is_safe = cmd_name in SAFE_CMD_NAMES
            # Block path traversal and sensitive paths in arguments
            if is_safe:
                for arg in cmd_parts[1:]:
                    if ".." in arg or arg.startswith(("/etc", "/root", "/proc", "/sys")):
                        return f"[SECURITY BLOCK] Restricted path in arguments: `{arg}`"
            if not is_safe:
                return f"[SECURITY BLOCK] Command `{data}` blocked by safety filter."
            try:
                result = subprocess.run(
                    shlex.split(data), capture_output=True, text=True, timeout=10,
                )
                output = result.stdout[:2000] if result.stdout else result.stderr[:2000]
                return f"```\n$ {data}\n{output}\n```"
            except subprocess.TimeoutExpired:
                return "[TIMEOUT] Command exceeded 10s limit"
            except Exception as e:
                return f"[SHELL ERROR] {e}"

        elif action_type == "weather":
            weather = OSINTEngine.fetch_weather_intel(data)
            if weather and weather.get("weather"):
                cw = weather["weather"].get("current_weather", {})
                return f"""**Weather Intel: {weather['city']}**
| Parameter | Value |
|---|---|
| Temperature | {cw.get('temperature', 'N/A')}°C |
| Wind Speed | {cw.get('windspeed', 'N/A')} km/h |
| Wind Direction | {cw.get('winddirection', 'N/A')}° |
| Coordinates | {weather['lat']:.4f}, {weather['lon']:.4f} |"""
            return f"[WEATHER FAIL] Could not fetch weather for **{data}**"

        elif action_type == "ip_lookup":
            result = OSINTEngine.fetch_ip_intel(data)
            if result.get("status") == "success":
                return f"""**IP Intelligence: {data}**
| Parameter | Value |
|---|---|
| Country | {result.get('country', 'N/A')} |
| Region | {result.get('regionName', 'N/A')} |
| City | {result.get('city', 'N/A')} |
| ISP | {result.get('isp', 'N/A')} |
| Organization | {result.get('org', 'N/A')} |
| AS | {result.get('as', 'N/A')} |
| Coordinates | {result.get('lat', 'N/A')}, {result.get('lon', 'N/A')} |"""
            return f"[IP FAIL] Lookup failed for **{data}**"

        elif action_type == "osint_lookup":
            domain_data = OSINTEngine.fetch_domain_intel(data)
            records = domain_data.get("records", {})
            ips = records.get("A", ["N/A"])
            ptr = records.get("PTR", "N/A")
            return f"""**Domain Intel: {data}**
| Parameter | Value |
|---|---|
| Resolved IPs | {', '.join(ips)} |
| Reverse DNS | {ptr} |"""

        return "[UNKNOWN ACTION]"


# ╔══════════════════════════════════════════════════════════════╗
# ║  PHANTOM PROTOCOL — Multi-Step Autonomous Investigation       ║
# ╚══════════════════════════════════════════════════════════════╝

class PhantomProtocol:
    """Multi-step autonomous intelligence investigation agent.

    Given a target (person, org, domain, location), it:
    1. Searches memory for any related information
    2. Performs OSINT lookups (domain, IP, news)
    3. Cross-references findings
    4. Generates a comprehensive intelligence brief
    """

    @staticmethod
    def investigate(target, collection, progress_callback=None):
        """Run a full PHANTOM investigation on a target."""
        findings = {
            "target": target,
            "memory_hits": [],
            "news_intel": [],
            "domain_intel": None,
            "ip_intel": None,
            "geo_intel": None,
            "gdelt_events": [],
            "weather": None,
        }

        steps = [
            ("Querying neural memory bank", "memory"),
            ("Scanning global news feeds", "news"),
            ("Running domain reconnaissance", "domain"),
            ("Geolocating target", "geo"),
            ("Pulling GDELT event data", "gdelt"),
        ]

        for i, (desc, step_type) in enumerate(steps):
            if progress_callback:
                progress_callback(desc, i / len(steps))

            try:
                if step_type == "memory":
                    docs, metas, dists = query_memories(
                        collection, target, n=8, include_distances=True
                    )
                    for doc, meta, dist in zip(docs, metas, dists):
                        findings["memory_hits"].append({
                            "text": doc[:500],
                            "title": meta.get("title", "Unknown"),
                            "date": meta.get("date", "Unknown"),
                            "similarity": max(0, 100 - dist * 50),
                        })

                elif step_type == "news":
                    articles = OSINTEngine.fetch_world_news(target, max_results=8)
                    findings["news_intel"] = articles

                elif step_type == "domain":
                    # Try treating target as a domain
                    if "." in target and " " not in target:
                        findings["domain_intel"] = OSINTEngine.fetch_domain_intel(target)
                        ips = findings["domain_intel"].get("records", {}).get("A", [])
                        if ips:
                            findings["ip_intel"] = OSINTEngine.fetch_ip_intel(ips[0])

                elif step_type == "geo":
                    findings["geo_intel"] = OSINTEngine.geocode_location(target)

                elif step_type == "gdelt":
                    findings["gdelt_events"] = OSINTEngine.fetch_gdelt_events(target, max_results=10)

            except Exception:
                continue

        if progress_callback:
            progress_callback("Compiling intelligence brief", 0.9)

        # Generate AI analysis
        brief = PhantomProtocol._generate_brief(findings)
        findings["analysis"] = brief

        if progress_callback:
            progress_callback("PHANTOM Protocol complete", 1.0)

        return findings

    @staticmethod
    def _generate_brief(findings):
        """Use LLM to analyze all gathered intelligence."""
        context_parts = [f"TARGET: {findings['target']}\n"]

        if findings["memory_hits"]:
            context_parts.append("MEMORY DATABASE HITS:")
            for hit in findings["memory_hits"][:5]:
                context_parts.append(
                    f"  [{hit['date']}] (Match: {hit['similarity']:.1f}%) {hit['text'][:200]}"
                )

        if findings["news_intel"]:
            context_parts.append("\nNEWS INTELLIGENCE:")
            for article in findings["news_intel"][:5]:
                context_parts.append(f"  - {article['title']} ({article['source']})")

        if findings["domain_intel"]:
            records = findings["domain_intel"].get("records", {})
            context_parts.append(f"\nDOMAIN INTEL: IPs={records.get('A', [])}")

        if findings["ip_intel"] and findings["ip_intel"].get("status") == "success":
            ip = findings["ip_intel"]
            context_parts.append(
                f"\nIP INTEL: {ip.get('city')}, {ip.get('country')} — ISP: {ip.get('isp')}"
            )

        if findings["geo_intel"]:
            g = findings["geo_intel"]
            context_parts.append(
                f"\nGEOLOCATION: {g['name']}, {g['country']} ({g['lat']:.4f}, {g['lon']:.4f})"
            )

        if findings["gdelt_events"]:
            context_parts.append("\nGDELT EVENTS:")
            for evt in findings["gdelt_events"][:5]:
                context_parts.append(f"  - {evt['title'][:100]} (tone: {evt.get('tone', 'N/A')})")

        context = "\n".join(context_parts)

        prompt = f"""You are XANA PHANTOM — an elite intelligence analysis system.
You have completed a multi-source investigation. Analyze the gathered intelligence below and produce
a classified brief in this exact format:

**[CLASSIFICATION: TOP SECRET // PHANTOM EYES ONLY]**
**[TARGET: {findings['target']}]**
**[DATE: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]**

**1. EXECUTIVE SUMMARY** — One-paragraph overview of all findings.

**2. MEMORY CORRELATION** — What our internal database knows about this target.

**3. OPEN SOURCE INTELLIGENCE** — News, events, public information gathered.

**4. NETWORK INTELLIGENCE** — Domain/IP/infrastructure findings (if any).

**5. GEOSPATIAL INTELLIGENCE** — Location data and geographic context.

**6. THREAT ASSESSMENT** — Risk level and potential concerns.

**7. RECOMMENDED ACTIONS** — Next steps for deeper investigation.

RAW INTELLIGENCE DATA:
{context}"""

        try:
            response = ollama.chat(
                model=LLM_MODEL,
                messages=[{"role": "system", "content": prompt}],
            )
            return response["message"]["content"]
        except Exception as e:
            return f"[ANALYSIS ENGINE OFFLINE] Could not generate brief: {e}"


# ╔══════════════════════════════════════════════════════════════╗
# ║  AUTONOMOUS RECON AGENT — Network and Entity Sweep            ║
# ╚══════════════════════════════════════════════════════════════╝

class ReconAgent:
    """Performs autonomous reconnaissance sweeps."""

    @staticmethod
    def full_sweep(target, collection):
        """Run comprehensive recon on a target entity."""
        report = {"target": target, "sections": []}

        # 1. Memory search
        docs, metas, dists = query_memories(collection, target, n=5, include_distances=True)
        if docs:
            entries = []
            for doc, meta, dist in zip(docs, metas, dists):
                sim = max(0, 100 - dist * 50)
                entries.append(f"  [{sim:.0f}%] {meta.get('title', 'Unknown')} — {doc[:150]}…")
            report["sections"].append(("MEMORY BANK", "\n".join(entries)))

        # 2. Domain/IP recon
        if "." in target and " " not in target:
            domain = OSINTEngine.fetch_domain_intel(target)
            ips = domain.get("records", {}).get("A", [])
            ptr = domain.get("records", {}).get("PTR", "N/A")
            report["sections"].append(
                ("DOMAIN RECON", f"IPs: {', '.join(ips)}\nReverse DNS: {ptr}")
            )
            for ip in ips[:2]:
                ip_data = OSINTEngine.fetch_ip_intel(ip)
                if ip_data.get("status") == "success":
                    report["sections"].append(
                        ("IP INTEL — " + ip,
                         f"{ip_data.get('city')}, {ip_data.get('country')} — "
                         f"ISP: {ip_data.get('isp')} | Org: {ip_data.get('org')}")
                    )

        # 3. News sweep
        news = OSINTEngine.fetch_world_news(target, max_results=5)
        if news:
            lines = [f"  • {a['title']} ({a['source']})" for a in news]
            report["sections"].append(("NEWS SWEEP", "\n".join(lines)))

        # 4. GDELT events
        events = OSINTEngine.fetch_gdelt_events(target, max_results=5)
        if events:
            lines = [f"  • {e['title'][:80]} (tone: {e.get('tone', 'N/A')})" for e in events]
            report["sections"].append(("GDELT EVENTS", "\n".join(lines)))

        return report

    @staticmethod
    def format_report(report):
        """Format a recon report to markdown."""
        lines = [
            f"## RECON SWEEP — {report['target']}",
            f"*Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "---",
        ]
        for title, content in report["sections"]:
            lines.append(f"### {title}")
            lines.append(content)
            lines.append("")
        return "\n".join(lines)


# ╔══════════════════════════════════════════════════════════════╗
# ║  ENTITY NEXUS — Extract & Map Entities from Text              ║
# ╚══════════════════════════════════════════════════════════════╝

class EntityNexus:
    """Extract entities and relationships from text using LLM."""

    @staticmethod
    def extract_entities(text):
        """Use LLM to extract structured entities from text."""
        prompt = f"""Analyze the following text and extract ALL entities.
Return ONLY a valid JSON object with this exact structure:
{{
    "people": ["name1", "name2"],
    "organizations": ["org1", "org2"],
    "locations": ["loc1", "loc2"],
    "technologies": ["tech1", "tech2"],
    "events": ["event1", "event2"],
    "relationships": [
        {{"source": "entity1", "target": "entity2", "type": "relationship_type"}}
    ]
}}

TEXT:
{text[:3000]}"""

        try:
            response = ollama.chat(
                model=LLM_MODEL,
                messages=[{"role": "system", "content": prompt}],
            )
            content = response["message"]["content"]
            # Try to parse JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        return {"people": [], "organizations": [], "locations": [],
                "technologies": [], "events": [], "relationships": []}
