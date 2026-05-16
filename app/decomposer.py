"""
app/decomposer.py
-----------------
Step 1 of the RAG pipeline: Query Decomposition.

Takes the user's raw natural language query and asks the LLM to extract
structured intent (category, keywords, price range, etc.) as a JSON dict.

This structured output is then passed to app/retriever.py to build precise
SQL queries — instead of doing fuzzy keyword search on the raw query.
"""

import json
from app.llm import call_llm

# System prompt instructs the LLM to act as a structured extraction engine.
# The output MUST be valid JSON only — no markdown, no explanation.
DECOMPOSER_SYSTEM_PROMPT = """You are a query decomposition engine for an e-commerce search system.

Given a user's natural language product query, extract a structured JSON object with these fields:
- category (string): product category e.g. "bluetooth speaker", "laptop", "headphones"
- keywords (string): space-separated key feature words for full-text search
- price_min (number or null): minimum price in INR if mentioned
- price_max (number or null): maximum price in INR if mentioned
- min_rating (number or null): minimum rating (1-5) if mentioned
- in_stock_only (boolean): true if user wants only available items
- attributes (list of strings): specific features like ["waterproof", "wireless", "foldable"]

Respond ONLY with valid JSON. No explanation, no markdown, no backticks."""

# Safe default returned when LLM response cannot be parsed as JSON
_DEFAULT_RESULT = {
    "category": None,
    "keywords": "",
    "price_min": None,
    "price_max": None,
    "min_rating": None,
    "in_stock_only": False,
    "attributes": [],
}


def decompose_query(user_query: str) -> dict:
    """
    Sends the user query to the LLM and returns a structured dict of filters.

    Args:
        user_query: The raw natural language query from the user.

    Returns:
        A dict with keys: category, keywords, price_min, price_max,
        min_rating, in_stock_only, attributes.
        Returns a safe default dict if the LLM response can't be parsed.

    Example output:
        {
            "category": "bluetooth speaker",
            "keywords": "waterproof bass portable",
            "price_min": null,
            "price_max": 2000,
            "min_rating": null,
            "in_stock_only": false,
            "attributes": ["waterproof", "bass"]
        }
    """
    try:
        # Ask the LLM to extract structured intent from the raw query
        raw_response = call_llm(DECOMPOSER_SYSTEM_PROMPT, user_query)

        # Strip any accidental leading/trailing whitespace before parsing
        cleaned = raw_response.strip()

        # Parse the JSON string into a Python dict
        return json.loads(cleaned)

    except (json.JSONDecodeError, Exception):
        # If JSON parsing fails (LLM hallucinated non-JSON), return a safe
        # fallback so the rest of the pipeline can still run without crashing
        print(f"[decomposer] Warning: failed to parse LLM response as JSON. Using defaults.")
        return dict(_DEFAULT_RESULT)
