# XANA OS — PROMETHEUS

**Next-Generation Personal Intelligence Platform**

3D Globe · Live OSINT Feeds · AI Chat · Threat Analysis · Semantic Memory

---

## What is XANA OS?

XANA OS is a self-hosted, fully offline-capable intelligence dashboard built with Streamlit. It combines:

- **Live global feeds** — real aircraft (OpenSky), vessels (AIS), satellites (CelesTrak)
- **AI-powered chat** — memory-linked conversational AI backed by your own conversation history
- **OSINT center** — news, cyber threats, IP/domain recon, crypto markets, weather
- **Autonomous investigation** — PHANTOM Protocol multi-source entity analysis
- **3D globe** — pydeck-powered multi-layer command center

All data sources are **free and require no API keys** (except optional Windy webcams).

---

## Tech Stack

| Component | Technology |
|---|---|
| Web framework | Streamlit |
| LLM (local) | Ollama (`llama3.2` or any model) |
| Vector memory | ChromaDB + `all-MiniLM-L6-v2` embeddings |
| 3D globe | pydeck |
| Charts | Plotly |
| Graph analysis | NetworkX |
| Satellite tracking | CelesTrak TLE + Keplerian propagation |

---

## Setup Guide (Step by Step)

### Quick Start (recommended)

```bash
git clone https://github.com/sriharideveloper/xanaops.git
cd xana-os
./setup.sh        # creates venv, installs deps, checks Ollama
./start.sh        # launches the app
```

Then open `http://localhost:8501`.

> GLOBE, OSINT, and all live-feed modules work immediately with no setup. Memory-linked modules (ORACLE, ARCHIVE, NEURAL MAP, DOSSIER, CHRONOS) require building the database from your conversation history — see Step 4.

---

### Step 1 — Prerequisites

- **Python 3.10+**
- **Ollama** — local LLM runtime ([ollama.com](https://ollama.com))

```bash
# Install a model (default is llama3.2)
ollama pull llama3.2

# You can also use mistral, qwen2.5, gemma3, etc.
# Change LLM_MODEL in config.py to match.
```

---

### Step 2 — Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/xana-os.git
cd xana-os
```

---

### Step 3 — Install & Run

```bash
./setup.sh        # one-time setup: creates venv + installs all dependencies
./start.sh        # start XANA OS
```

**Manual setup (Windows or if you prefer):**

```bash
python -m venv xana_env
source xana_env/bin/activate   # Linux/macOS
# xana_env\Scripts\activate    # Windows
pip install -r requirements.txt
streamlit run app.py
```

> The first run downloads the `all-MiniLM-L6-v2` embedding model (~90 MB) automatically when a memory DB is loaded.

Open your browser at `http://localhost:8501`.

---

### Step 4 — Build Your Memory Database (Optional)

The AI memory system uses your own conversation history. It works best with **ChatGPT conversation exports**, but any structured chat data works.

#### 4a — Export Your Conversations

**From ChatGPT:**
1. Go to Settings → Data Controls → Export Data
2. Download and extract the ZIP
3. Copy all `conversations-*.json` files into the project root

#### 4b — Extract to CSV

```bash
python legacy/parse_chats.py
```

This reads `conversations-1.json`, `conversations-2.json`, etc. and produces `master_chats.csv`.

> Adjust the number of files in the last line of `parse_chats.py` if you have more or fewer files.

#### 4c — Pair Messages

```bash
python legacy/1_prep_data.py
```

This pairs each user message with its AI response into semantic blocks, producing `paired_chats.csv`.

#### 4d — Build the Vector Database

```bash
python legacy/build-brain.py
```

This embeds all messages using `all-MiniLM-L6-v2` and stores them in `xana_memory_db/`.

> This may take a few minutes depending on the size of your conversation history. CPU-only is fine.

#### 4e — Restart the App

```bash
./start.sh        # or: streamlit run app.py
```

All memory-linked modules (ORACLE, ARCHIVE, NEURAL MAP, DOSSIER, CHRONOS) are now fully operational.

---

### Step 5 — Optional: Windy Webcams API

For live webcam feeds from around the world, get a free API key at [api.windy.com](https://api.windy.com/) and set it:

```bash
export WINDY_API_KEY=your_key_here
./start.sh        # or: streamlit run app.py
```

Or add it to a `.streamlit/secrets.toml` file:

```toml
WINDY_API_KEY = "your_key_here"
```

---

## Configuration

Edit `config.py` to customize:

| Setting | Default | Description |
|---|---|---|
| `LLM_MODEL` | `llama3.2` | Ollama model name |
| `DB_PATH` | `./xana_memory_db` | ChromaDB directory |
| `COLLECTION_NAME` | `xana_memories` | ChromaDB collection name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `GLOBE_DEFAULT_SAT_GROUPS` | stations, starlink, gps, military, weather | Default satellite layers |
| `AGENT_SAFE_COMMANDS` | see config.py | Allowed shell commands for exec agent |

To use a different LLM (e.g. `mistral`, `qwen2.5`, `gemma3`):

```python
LLM_MODEL = "mistral"
```

---

## How It Works — The Core Idea

XANA needs **zero fine-tuning or model training**. Instead of teaching the model your data, it retrieves the most relevant chunks from your conversation history at query time and injects them directly into the prompt as context. The LLM reasons over your data without ever having been trained on it.

```
Your question
     │
     ▼
ChromaDB Vector Search  ──►  top N most relevant memory chunks
     │
     ▼
[System prompt] + [Memory chunks] + [Chat history] + [Your question]
     │
     ▼
Local LLM (Ollama)  ──►  Grounded, specific answer
```

**Why this matters:**
- Works with any Ollama model, any size
- Your data never leaves your machine
- No GPU required for training — inference only
- Swap the model in `config.py` without rebuilding the database
- Feed it from any ChatGPT export — no reformatting needed

---

## Performance Tuning

XANA works on any machine. Tune these three variables to match your hardware.

### The Knobs

| What to change | Where | Default | Effect |
|---|---|---|---|
| LLM model | `config.py` → `LLM_MODEL` | `llama3.2` | Speed vs. quality of responses |
| Embedding model | `config.py` → `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Quality vs. speed of vector search |
| Memory depth | `app.py` line ~907 → `n=5` | `5` | How many memory chunks are retrieved per query |
| Context window | `modules/database.py` line ~80 → `max_chars=4000` | `4000` | Max characters of memory fed to the LLM |
| Chat history | `app.py` line ~929 → `messages[-4:]` | `4` | How many previous turns stay in the LLM's context |

---

### Potato (old laptop, CPU-only, < 8 GB RAM)

Goal: stay responsive, avoid OOM.

**`config.py`:**
```python
LLM_MODEL      = "llama3.2:1b"   # or "qwen2.5:0.5b" — tiny, fast
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # keep this, it's already lightweight
```

**`app.py` (~line 907) — reduce memory retrieval:**
```python
docs, metas, _ = query_memories(collection, prompt, n=3)
```

**`app.py` (~line 929) — fewer chat turns in context:**
```python
for msg in st.session_state.messages[-2:]:
```

**`modules/database.py` (~line 80) — smaller context block:**
```python
def build_context_string(docs, metas, max_chars=1500):
```

---

### Mid-Range (modern CPU, 8–16 GB RAM) — Default

No changes needed. The defaults are tuned for this tier.

```python
LLM_MODEL       = "llama3.2"        # ~4 GB RAM
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
# app.py:      n=5,  messages[-4:]
# database.py: max_chars=4000
```

---

### Beast (GPU / 16 GB+ VRAM, fast machine)

Goal: maximum context richness — longer memory, deeper retrieval.

**`config.py`:**
```python
LLM_MODEL       = "llama3.1:8b"    # or "mistral", "qwen2.5:14b", "deepseek-r1:8b"
EMBEDDING_MODEL = "all-mpnet-base-v2"  # higher quality embeddings (slower to build DB)
```

**`app.py` (~line 907) — pull more memories:**
```python
docs, metas, _ = query_memories(collection, prompt, n=10)
```

**`app.py` (~line 929) — keep more chat history:**
```python
for msg in st.session_state.messages[-8:]:
```

**`modules/database.py` (~line 80) — larger context block:**
```python
def build_context_string(docs, metas, max_chars=8000):
```

---

### Quick Reference

| Tier | Model | `n=` | `messages[-N:]` | `max_chars` |
|---|---|---|---|---|
| Potato | `llama3.2:1b` | 3 | 2 | 1500 |
| Mid-range (default) | `llama3.2` | 5 | 4 | 4000 |
| Beast | `llama3.1:8b`+ | 10 | 8 | 8000 |

> **Tip:** The embedding model only affects DB build time and search quality — not LLM speed. You can rebuild the DB with a better embedding model anytime by deleting `xana_memory_db/` and re-running `legacy/build-brain.py`.

---

## Modules

| Module | Description | Requires DB |
|---|---|---|
| GLOBE | 3D live globe — aircraft, vessels, satellites, threats, webcams | No |
| ORACLE | Memory-linked AI chat with agentic commands | Yes |
| PHANTOM | Autonomous multi-source investigation protocol | Yes |
| ARCHIVE | Raw semantic vector search | Yes |
| NEURAL MAP | 3D semantic topology visualization | Yes |
| DOSSIER | AI-generated intelligence profile from memory | Yes |
| OSINT | News, cyber threats, IP/domain recon, crypto, weather | No |
| CHRONOS | Temporal pattern analysis of conversation history | Yes |

---

## ORACLE Commands

In the chat interface, you can use these direct commands:

| Command | Action |
|---|---|
| `play [song] on youtube` | Open YouTube search |
| `google [query]` | Open Google search |
| `open [app]` | Launch application |
| `weather [city]` | Fetch weather |
| `ip [address]` | IP geolocation |
| `lookup [domain]` | Domain recon |
| `phantom [target]` | Full PHANTOM investigation |
| `recon [target]` | Quick recon sweep |
| `exec [command]` | Safe shell execution |
| `status` | System diagnostics |

---

## Data Sources

All free, no API keys required:

| Source | Data |
|---|---|
| OpenSky Network | Live aircraft transponder data |
| Finnish Digitraffic AIS | Real vessel positions (Baltic Sea + global) |
| CelesTrak | Satellite TLE orbital elements |
| CARTO | Dark map tiles |
| Google News RSS | World news headlines |
| CISA KEV | Known exploited vulnerabilities |
| ip-api.com | IP geolocation |
| CoinGecko | Cryptocurrency markets |
| Open-Meteo | Weather forecasts |
| GDELT | Geopolitical event database |

---

## Scripts

| Script | Purpose |
|---|---|
| `setup.sh` | One-time setup — creates venv, installs deps, checks Ollama |
| `start.sh` | Launch XANA OS (activates venv + starts Streamlit) |

## Data Pipeline (legacy/)

The `legacy/` directory contains the memory database pipeline:

| Script | Purpose |
|---|---|
| `parse_chats.py` | Extracts messages + timestamps from ChatGPT JSON exports |
| `1_prep_data.py` | Pairs user/AI messages into semantic blocks |
| `build-brain.py` | Embeds paired messages into ChromaDB |

---

## Privacy Note

XANA OS runs entirely on your local machine. No data is sent to external servers except:
- Public API requests to the data sources listed above (read-only, no personal data sent)
- LLM inference via Ollama (runs locally, no data leaves your machine)

Your conversation history and memory database stay on your device.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*XANA OS · PROMETHEUS · ALL SYSTEMS NOMINAL*
