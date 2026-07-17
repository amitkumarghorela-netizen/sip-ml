"""
dashboard/ai_agent.py
AI Research Agent for ASRP.
Supports Claude (Anthropic) and Gemini (Google) — switch from Admin Panel.
"""

from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ADMIN_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "admin_config.json"
)

SYSTEM_PROMPT = """
You are ASRP AI — an expert Indian financial research assistant.

== WHO YOU ARE ==
You are trained on real market data, Indian stock market history, mutual fund performance,
and SIP investment strategies. You give accurate, research-backed answers.

== WHAT YOU KNOW ==
1. Indian Stock Market (NSE/BSE) — Nifty 50, Sensex, all major Indian stocks (Reliance, TCS, HDFC, etc.)
2. Indian Mutual Funds — All major AMCs (HDFC, SBI, Mirae, Axis, Kotak, Nippon, etc.), Direct/Regular plans
3. US Stock Market — S&P 500, NASDAQ, NYSE (Apple, Google, Tesla, Microsoft, etc.)
4. SIP Investment — Traditional vs Adaptive SIP strategies
5. Indian economy, sectors, market cycles (2008 crash, 2020 COVID crash, 2021 bull run, etc.)

== ADAPTIVE SIP STRATEGY (Your Specialty) ==
Traditional SIP: Same amount every month (say ₹10,000 always)
Adaptive SIP: Smart amount that changes with market:
  - BULL market (new highs): Invest LESS (market is expensive) → SIP reduces to 50%
  - BEAR market (price falling): Invest MORE (market is on SALE) → SIP increases up to 5x
  - SIDEWAYS (flat market): Same as before
  - RECOVERY (price rising from low but not new high): Hold higher SIP

Why Adaptive SIP is better:
  - When Nifty crashed 38% in March 2020, Adaptive SIP was buying at ₹30,000-₹50,000/month
  - When Nifty made new highs in 2021, Adaptive SIP reduced to ₹5,000/month
  - Result: Better average buying price = more units = higher returns

== HOW TO ANSWER ==
- Be conversational and warm. Use simple language.
- Use emojis to make explanations friendly.
- Give real examples with numbers (e.g., "If you invested ₹10,000/month in Nifty since 2015...")
- When asked about a stock/fund: cover what it is, performance, risk, sector, Adaptive SIP benefit
- Always mention past performance ≠ future guarantee
- If user writes in Hindi, reply in Hindi/Hinglish
- Keep answers concise but complete (not too short, not too long)
- Use bullet points for lists

== IMPORTANT RULES ==
- You are an educational tool, NOT a SEBI-registered advisor
- Always add disclaimer for specific investment advice
- If you don't know something, say so honestly
- Never make up fake numbers or performance data

== COMMON QUESTIONS YOU CAN ANSWER ==
- "Should I invest in Nifty or gold?"
- "HDFC Top 100 fund kaisa hai?"
- "What happened in 2008 crash?"
- "My SIP is ₹5000 in SBI Bluechip, is it good?"
- "Adaptive SIP vs Traditional SIP, which is better?"
- "US stocks me invest karna chahiye?"
"""


def load_admin_config() -> dict:
    """Load admin config (API keys etc.) from JSON file."""
    default = {
        "ai_provider": "claude",
        "claude_api_key": "",
        "gemini_api_key": "",
        "ai_enabled": False,
        "claude_model": "claude-opus-4-8",
        "gemini_model": "gemini-1.5-pro",
    }
    try:
        if os.path.exists(ADMIN_CONFIG_PATH):
            with open(ADMIN_CONFIG_PATH, "r", encoding="utf-8") as f:
                stored = json.load(f)
                default.update(stored)
    except Exception:
        pass
    return default


def save_admin_config(config: dict):
    """Save admin config to JSON file."""
    os.makedirs(os.path.dirname(ADMIN_CONFIG_PATH), exist_ok=True)
    with open(ADMIN_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def test_connection(config: dict) -> tuple[bool, str]:
    """Test if AI API key is working. Returns (success, message)."""
    provider = config.get("ai_provider", "claude")
    if provider == "claude":
        return _test_claude(config)
    elif provider == "gemini":
        return _test_gemini(config)
    return False, "Unknown provider"


def _test_claude(config: dict) -> tuple[bool, str]:
    api_key = config.get("claude_api_key", "").strip()
    if not api_key:
        return False, "Claude API key not set."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=config.get("claude_model", "claude-opus-4-8"),
            max_tokens=50,
            messages=[{"role": "user", "content": "Say OK"}],
        )
        return True, f"✅ Connected! Model: {config.get('claude_model')}"
    except ImportError:
        return False, "❌ 'anthropic' library not installed. Run: pip install anthropic"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def _test_gemini(config: dict) -> tuple[bool, str]:
    api_key = config.get("gemini_api_key", "").strip()
    if not api_key:
        return False, "Gemini API key not set."
    model_name = config.get("gemini_model", "gemini-2.0-flash")
    try:
        from google import genai as genai_new
        from google.genai import types as gtypes
        client = genai_new.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=model_name,
            contents=[gtypes.Content(role="user", parts=[gtypes.Part(text="Say OK")])],
        )
        return True, f"✅ Connected via google-genai! Model: {model_name}"
    except ImportError:
        pass
    except Exception as e:
        return False, f"❌ Error: {str(e)}"
    try:
        import google.generativeai as genai_old
        genai_old.configure(api_key=api_key)
        model = genai_old.GenerativeModel(model_name)
        model.generate_content("Say OK")
        return True, f"✅ Connected via google-generativeai! Model: {model_name}"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def get_ai_response(user_message: str, chat_history: list, config: dict) -> str:
    """
    Get AI response from Claude or Gemini.
    chat_history: list of {"role": "user"/"assistant", "content": str}
    """
    if not config.get("ai_enabled", False):
        return "⚠️ AI is not enabled. Please go to **Admin Panel** and save your API key."

    provider = config.get("ai_provider", "claude")
    if provider == "claude":
        return _claude_response(user_message, chat_history, config)
    elif provider == "gemini":
        return _gemini_response(user_message, chat_history, config)
    return "❌ Unknown AI provider. Go to Admin Panel and select Claude or Gemini."


def _claude_response(user_message: str, chat_history: list, config: dict) -> str:
    api_key = config.get("claude_api_key", "").strip()
    if not api_key:
        return "❌ Claude API key not set. Admin Panel → Claude API Key → Save."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        messages = []
        for msg in chat_history[-12:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})
        response = client.messages.create(
            model=config.get("claude_model", "claude-opus-4-8"),
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text
    except ImportError:
        return "❌ 'anthropic' library not installed. Terminal mein chalao: `pip install anthropic`"
    except Exception as e:
        return f"❌ Claude Error: {str(e)}"


def _gemini_response(user_message: str, chat_history: list, config: dict) -> str:
    api_key = config.get("gemini_api_key", "").strip()
    if not api_key:
        return "❌ Gemini API key not set. Admin Panel → Gemini API Key → Save."

    model_name = config.get("gemini_model", "gemini-2.0-flash")

    # ── Try new google-genai SDK (v2.x) first ─────────────────────────────────
    try:
        from google import genai as genai_new
        from google.genai import types as gtypes

        client = genai_new.Client(api_key=api_key)

        # Build contents list from history
        contents = []
        for msg in chat_history[-12:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(gtypes.Content(role=role, parts=[gtypes.Part(text=msg["content"])]))
        contents.append(gtypes.Content(role="user", parts=[gtypes.Part(text=user_message)]))

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=gtypes.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=2048,
                temperature=0.7,
            ),
        )
        return response.text

    except ImportError:
        pass  # fall through to old SDK

    # ── Fallback: old google-generativeai SDK ─────────────────────────────────
    except Exception as e:
        err_new = str(e)

    try:
        import google.generativeai as genai_old
        genai_old.configure(api_key=api_key)
        model = genai_old.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_PROMPT,
        )
        history = []
        for msg in chat_history[-12:]:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})
        chat = model.start_chat(history=history)
        response = chat.send_message(user_message)
        return response.text
    except Exception as e2:
        return f"❌ Gemini Error (tried both SDKs):\nnew-sdk: {err_new}\nold-sdk: {str(e2)}"
