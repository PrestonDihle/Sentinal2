"""
SENTINEL2 — Multi-Provider LLM Wrapper
Handles calls to both Gemini (bulk ops) and Claude (analysis/reasoning)
with rate limiting, retries, and model routing.
"""

import os
import time
import json
import logging
from typing import Optional

from src.utils.config import get_config, get_model_for_component

logger = logging.getLogger("sentinel2.llm")

# ── Rate limiting state ──────────────────────────────────────────────
import threading as _threading
_rate_lock = _threading.Lock()
_last_call_time = {"gemini_flash": 0.0, "claude_sonnet": 0.0, "claude_opus": 0.0}
_daily_call_count = {"gemini_flash": 0, "claude_sonnet": 0, "claude_opus": 0}
_daily_reset_date = ""

# ── Lazy-initialized clients ────────────────────────────────────────
_gemini_client = None
_anthropic_client = None


def _get_tier(model_name: str) -> str:
    """Map model name to rate-limit tier."""
    if "flash" in model_name.lower():
        return "gemini_flash"
    if "opus" in model_name.lower():
        return "claude_opus"
    if "sonnet" in model_name.lower() or "claude" in model_name.lower():
        return "claude_sonnet"
    return "gemini_flash"


def _reset_daily_if_needed():
    """Reset daily counters at midnight."""
    global _daily_call_count, _daily_reset_date
    from datetime import date
    today = date.today().isoformat()
    if _daily_reset_date != today:
        _daily_call_count = {"gemini_flash": 0, "claude_sonnet": 0, "claude_opus": 0}
        _daily_reset_date = today


def _check_rate_limit(tier: str):
    """Enforce per-minute rate limits. Sleeps if needed. Thread-safe."""
    with _rate_lock:
        _reset_daily_if_needed()
        config = get_config()
        llm_cfg = config["llm"]["providers"]

        if tier == "gemini_flash":
            limits = llm_cfg["gemini"]["rate_limits"]["flash"]
            max_rpm = limits["requests_per_minute"]
            max_rpd = limits["requests_per_day"]
        elif tier == "claude_sonnet":
            limits = llm_cfg["anthropic"]["rate_limits"]["sonnet"]
            max_rpm = limits["requests_per_minute"]
            max_rpd = limits["requests_per_day"]
        elif tier == "claude_opus":
            limits = llm_cfg["anthropic"]["rate_limits"]["opus"]
            max_rpm = limits["requests_per_minute"]
            max_rpd = limits["requests_per_day"]
        else:
            return

        if _daily_call_count[tier] >= max_rpd:
            raise RuntimeError(f"Daily rate limit reached for {tier}: {max_rpd}")

        min_interval = 60.0 / max_rpm
        elapsed = time.time() - _last_call_time[tier]
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            logger.debug(f"Rate limiting {tier}: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)


def _record_call(tier: str):
    """Record a call for rate tracking. Thread-safe."""
    with _rate_lock:
        _last_call_time[tier] = time.time()
        _daily_call_count[tier] += 1


# ── Gemini Client ────────────────────────────────────────────────────

def _get_gemini_client():
    """Lazy-initialize the Gemini client."""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client

    from google import genai
    from google.genai import types

    config = get_config()
    api_key = os.environ.get(config["llm"]["providers"]["gemini"]["api_key_env"], "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    timeout_ms = config["llm"]["providers"]["gemini"].get("timeout_ms", 300000)
    _gemini_client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout_ms),
    )
    return _gemini_client


def call_gemini(
    prompt: str,
    system_prompt: str = "",
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    max_output_tokens: int = 8192,
    response_json: bool = False,
) -> str:
    """
    Call Gemini API with rate limiting and retry logic.
    Returns response text.
    """
    from google.genai import types

    if model_name is None:
        model_name = "gemini-2.5-flash"

    tier = _get_tier(model_name)
    config = get_config()
    retry_cfg = config["llm"]["providers"]["gemini"].get("retry", {})
    max_retries = retry_cfg.get("max_retries", 3)
    backoff = retry_cfg.get("backoff_seconds", 60)

    gen_config_kwargs = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    if response_json:
        gen_config_kwargs["response_mime_type"] = "application/json"

    gen_config = types.GenerateContentConfig(
        system_instruction=system_prompt if system_prompt else None,
        **gen_config_kwargs,
    )

    client = _get_gemini_client()
    use_streaming = len(prompt) + len(system_prompt) > 10000

    for attempt in range(max_retries + 1):
        try:
            _check_rate_limit(tier)

            if use_streaming:
                chunks = []
                for chunk in client.models.generate_content_stream(
                    model=model_name, contents=prompt, config=gen_config,
                ):
                    if chunk.text:
                        chunks.append(chunk.text)
                _record_call(tier)
                full_text = "".join(chunks)
            else:
                response = client.models.generate_content(
                    model=model_name, contents=prompt, config=gen_config,
                )
                _record_call(tier)
                full_text = response.text or ""

            if full_text:
                logger.info(
                    f"Gemini {model_name} OK (attempt {attempt + 1}, "
                    f"daily: {_daily_call_count[tier]})"
                )
                return full_text
            else:
                logger.warning(f"Empty response from {model_name}")
                if attempt < max_retries:
                    time.sleep(backoff)
                    continue
                return ""
        except Exception as e:
            logger.warning(f"Gemini error (attempt {attempt + 1}): {e}")
            if attempt < max_retries:
                time.sleep(backoff * (attempt + 1))
            else:
                raise


# ── Anthropic / Claude Client ────────────────────────────────────────

def _get_anthropic_client():
    """Lazy-initialize the Anthropic client."""
    global _anthropic_client
    if _anthropic_client is not None:
        return _anthropic_client

    import anthropic

    config = get_config()
    api_key = os.environ.get(
        config["llm"]["providers"]["anthropic"]["api_key_env"], ""
    )
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    timeout = config["llm"]["providers"]["anthropic"].get("timeout_seconds", 300)
    _anthropic_client = anthropic.Anthropic(
        api_key=api_key,
        timeout=timeout,
    )
    return _anthropic_client


def call_claude(
    prompt: str,
    system_prompt: str = "",
    model_name: Optional[str] = None,
    temperature: float = 0.5,
    max_tokens: int = 8192,
    _fallback_depth: int = 0,
) -> str:
    """
    Call Claude API with rate limiting and retry logic.
    Returns response text.
    """
    if model_name is None:
        model_name = "claude-sonnet-4-20250514"

    # Strip 'anthropic/' prefix if present (CrewAI-style)
    api_model = model_name.replace("anthropic/", "")

    tier = _get_tier(model_name)
    config = get_config()
    retry_cfg = config["llm"]["providers"]["anthropic"].get("retry", {})
    max_retries = retry_cfg.get("max_retries", 3)
    backoff = retry_cfg.get("backoff_seconds", 30)

    client = _get_anthropic_client()

    for attempt in range(max_retries + 1):
        try:
            _check_rate_limit(tier)

            message = client.messages.create(
                model=api_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=[{"role": "user", "content": prompt}],
            )
            _record_call(tier)

            text = message.content[0].text if message.content else ""
            if text:
                logger.info(
                    f"Claude {api_model} OK (attempt {attempt + 1}, "
                    f"daily: {_daily_call_count[tier]})"
                )
                return text
            else:
                logger.warning(f"Empty response from {api_model}")
                if attempt < max_retries:
                    time.sleep(backoff)
                    continue
                return ""
        except Exception as e:
            error_str = str(e)
            # Opus → Sonnet fallback on billing/credit errors (max 1 fallback)
            if "credit balance is too low" in error_str:
                if "opus" in api_model.lower() and _fallback_depth == 0:
                    fallback_model = "claude-sonnet-4-20250514"
                    logger.warning(
                        f"Opus credit limit hit — falling back to {fallback_model}"
                    )
                    return call_claude(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model_name=fallback_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        _fallback_depth=1,
                    )
                # Sonnet also out, or already fell back — fail immediately
                logger.error(
                    "Anthropic credit balance exhausted. "
                    "Add credits at https://console.anthropic.com/settings/plans"
                )
                raise
            logger.warning(f"Claude error (attempt {attempt + 1}): {e}")
            if attempt < max_retries:
                time.sleep(backoff * (attempt + 1))
            else:
                raise


# ── Unified Router ───────────────────────────────────────────────────

def call_llm(
    prompt: str,
    system_prompt: str = "",
    component: Optional[str] = None,
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Unified LLM router. Calls the right provider based on component config
    or explicit provider/model override.

    Args:
        prompt: The main prompt content.
        system_prompt: System instruction.
        component: Pipeline component key (e.g., 'cma', 'processor').
                   Looks up model/provider/temp from models.yaml.
        model_name: Override model name.
        provider: Override provider ('gemini' or 'anthropic').
        temperature: Override temperature.
        max_tokens: Override max tokens.

    Returns:
        Response text from the LLM.
    """
    # Resolve from component config if provided
    if component and not model_name:
        comp_cfg = get_model_for_component(component)
        model_name = comp_cfg["model"]
        provider = provider or comp_cfg["provider"]
        temperature = temperature if temperature is not None else comp_cfg.get("temperature", 0.5)
        max_tokens = max_tokens or comp_cfg.get("max_tokens", 8192)

    # Default fallback
    if not model_name:
        model_name = "gemini-2.5-flash"
    if not provider:
        provider = "anthropic" if "claude" in model_name.lower() or "anthropic" in model_name.lower() else "gemini"
    if temperature is None:
        temperature = 0.5
    if max_tokens is None:
        max_tokens = 8192

    # Pre-flight token estimate (~4 chars per token for English)
    est_tokens = (len(prompt) + len(system_prompt)) // 4
    if provider == "anthropic":
        limit = 200_000  # Sonnet/Opus input limit
        if est_tokens > limit:
            logger.warning(
                f"Prompt too large for Claude: ~{est_tokens:,} tokens "
                f"(limit {limit:,}). Truncating prompt."
            )
            # Truncate prompt to fit, keeping system_prompt intact
            max_prompt_chars = (limit - len(system_prompt) // 4) * 4
            prompt = prompt[:max_prompt_chars]
    elif provider == "gemini":
        limit = 1_000_000  # Gemini Flash input limit
        if est_tokens > limit:
            logger.warning(
                f"Prompt too large for Gemini: ~{est_tokens:,} tokens "
                f"(limit {limit:,}). Truncating prompt."
            )
            max_prompt_chars = (limit - len(system_prompt) // 4) * 4
            prompt = prompt[:max_prompt_chars]

    if provider == "gemini":
        return call_gemini(
            prompt=prompt,
            system_prompt=system_prompt,
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
    else:
        return call_claude(
            prompt=prompt,
            system_prompt=system_prompt,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )


def call_llm_json(
    prompt: str,
    system_prompt: str = "",
    component: Optional[str] = None,
    **kwargs,
) -> dict:
    """Call LLM and parse response as JSON."""
    raw = call_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        component=component,
        **kwargs,
    )

    # Clean markdown wrappers
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Attempt repair of truncated JSON
        for start, end in [("[", "]"), ("{", "}")]:
            if cleaned.startswith(start):
                last = cleaned.rfind("}" if start == "[" else "}")
                if last > 0:
                    repaired = cleaned[:last + 1] + ("]" if start == "[" else "")
                    try:
                        return json.loads(repaired)
                    except json.JSONDecodeError:
                        pass
        logger.error(f"JSON parse failed: {cleaned[:200]}...")
        return {"error": "JSON parse failed", "raw_response": raw}


def get_daily_usage() -> dict:
    """Return current daily API usage stats."""
    return {
        "gemini_flash": _daily_call_count.get("gemini_flash", 0),
        "claude_sonnet": _daily_call_count.get("claude_sonnet", 0),
        "claude_opus": _daily_call_count.get("claude_opus", 0),
        "date": _daily_reset_date,
    }
