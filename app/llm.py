"""
app/llm.py
----------
Unified LLM caller. Provides a single call_llm() function that routes to the
correct provider (Ollama, OpenAI, or Claude) based on config.LLM_PROVIDER.
All other modules call only this function — never the provider SDKs directly.

To add a new provider: add a new elif block in call_llm() below.
"""

import requests
import config


def call_llm(system_prompt: str, user_message: str) -> str:
    """
    Calls the configured LLM provider and returns the text response.
    
    Args:
        system_prompt: Instructions that define the LLM's role and behavior.
        user_message: The actual user input to process.
    
    Returns:
        The LLM's text response as a plain string.
    
    Raises:
        ValueError: If LLM_PROVIDER is not one of "ollama", "openai", or "claude".
    """
    provider = config.LLM_PROVIDER

    if provider == "ollama":
        # --- Ollama: local LLM server, no API key needed ---
        # POST to the Ollama chat endpoint with stream=False to get a single response
        response = requests.post(
            f"{config.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": config.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,  # get complete response, not a stream of tokens
            },
            timeout=120,  # local models can be slow; give them 2 minutes
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    elif provider == "openai":
        # --- OpenAI: uses the official openai Python SDK ---
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        # Extract the text from the first (and only) completion choice
        return response.choices[0].message.content

    elif provider == "claude":
        # --- Anthropic Claude: uses the official anthropic Python SDK ---
        # Note: Claude uses a separate 'system' param, not a system message in the list
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=1024,
            system=system_prompt,       # Claude takes system prompt separately
            messages=[
                {"role": "user", "content": user_message},
            ],
        )
        # response.content is a list of content blocks; get text from the first one
        return response.content[0].text

    # Add a new elif block here to support a new provider.
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider}'. "
            "Set LLM_PROVIDER to 'ollama', 'openai', or 'claude' in your .env file."
        )
