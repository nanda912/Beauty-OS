"""
Beauty OS — LLM Service

Unified interface for Gemini (Google), Claude (Anthropic), or GPT (OpenAI).
"""

import json
from config.settings import (
    LLM_PROVIDER,
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
    GEMINI_API_KEY,
    LLM_MODEL,
)


def call_llm(system_prompt: str, user_message: str) -> str:
    """
    Send a message to the configured LLM and return the text response.
    Raises RuntimeError if the provider is misconfigured.
    """
    if LLM_PROVIDER == "gemini":
        return _call_gemini(system_prompt, user_message)
    elif LLM_PROVIDER == "anthropic":
        return _call_anthropic(system_prompt, user_message)
    elif LLM_PROVIDER == "openai":
        return _call_openai(system_prompt, user_message)
    else:
        raise RuntimeError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")


def call_llm_json(system_prompt: str, user_message: str) -> dict:
    """
    Call the LLM and parse the response as JSON.
    The system prompt should instruct the model to reply with valid JSON only.
    """
    raw = call_llm(system_prompt, user_message)
    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)


# ── Provider implementations ─────────────────────────────────────────

def _call_gemini(system_prompt: str, user_message: str) -> str:
    from google import genai

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=LLM_MODEL,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=1024,
        ),
        contents=user_message,
    )
    return response.text


def _call_anthropic(system_prompt: str, user_message: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=LLM_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text


def _call_openai(system_prompt: str, user_message: str) -> str:
    import openai

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=1024,
    )
    return response.choices[0].message.content
