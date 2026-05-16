# config.py
# ---------
# Central config — reads .env and exposes all settings.
# Every other module imports from here instead of calling os.getenv() directly.

import os
from dotenv import load_dotenv

load_dotenv()  # loads .env file from project root

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/shopsense")

# Which LLM provider to use: "ollama", "openai", or "claude"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

# Ollama (local, free)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Claude (Anthropic)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
