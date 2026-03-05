#!/bin/bash
# XANA OS — Start Script

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "xana_env" ]; then
    source xana_env/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Check Ollama is running
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo "⚠  Ollama is not running. Start it with: ollama serve"
    echo "   Continuing anyway — DB and live-feed modules will still work."
fi

echo "⬡ Starting XANA OS..."
streamlit run app.py "$@"
