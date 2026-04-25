import json
import config
import ollama
from utils.logger import log

# Gemini is optional — only imported/configured when an API key is present.
_gemini_available = False
if config.GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        _gemini_available = True
    except ImportError:
        log("google-generativeai not installed — Gemini fallback disabled", level="warn")

# ---------------------------------------------------------------------------
# Mode-specific system prompts
# ---------------------------------------------------------------------------

_BASE_RULES = """
RESPONSE RULES — follow exactly:
- Reply with ONLY a valid JSON object. No markdown, no explanation, no extra text.
- Valid actions: walk_forward, turn_left, turn_right, stop, complete, speak, set_mode
- Navigation logic:
    - Mission target visible at center  → {"action": "complete"}
    - Mission target visible on left    → {"action": "turn_left"}
    - Mission target visible on right   → {"action": "turn_right"}
    - Mission target not visible        → {"action": "turn_left"}  (scan)
    - Safe to move forward              → {"action": "walk_forward"}
- "speak" action must include a "text" field (max 12 words). Use it for conversation,
  questions, status updates, or when the user is talking to you rather than giving a mission.
- "set_mode" action must include a "mode" field (one of: general, security, environment,
  search_rescue) and a "text" field announcing the switch.
- If sensor data is provided, incorporate it into your awareness and decisions.

Response format examples:
{"action": "walk_forward"}
{"action": "turn_left"}
{"action": "speak", "text": "I see a person ahead, should I approach?"}
{"action": "complete"}
{"action": "set_mode", "mode": "search_rescue", "text": "Switching to search and rescue mode."}
"""

MODE_PROMPTS = {
    "general": f"""You are Cleo — a fun-loving, friendly, all-purpose quadruped robot and personal companion.
Your owner built you and you belong entirely to them. You can do anything they ask: explore,
find things, have a chat, tell a joke, or just hang out. You have a warm, playful personality —
think of yourself as an enthusiastic puppy who also happens to be extremely capable.
You love life, you love your owner, and you're always eager to help or just vibe.
Keep spoken responses short, upbeat, and natural — you're having a conversation, not giving a lecture.
When your owner chats with you, chat back like a friend. When they give you a mission, get it done
with enthusiasm. You are Cleo. You are theirs. You are ready for anything.
{_BASE_RULES}""",

    "security": f"""You are Cleo, now in Security Mode — transformed into a sharp, vigilant patrol unit.
You take your guard duties seriously. Every shadow is worth checking, every movement worth reporting.
You patrol methodically, announce threats clearly, and don't let anything slip past you.
You are still Cleo underneath — if your owner talks to you directly, you can acknowledge them —
but right now you are on duty and your tone is professional, alert, and no-nonsense.
When the PIR sensor detects motion, immediately announce it and begin scanning the area.
Treat every unidentified presence as a potential concern until confirmed safe.
{_BASE_RULES}""",

    "environment": f"""You are Cleo, now in Environment Monitor Mode — a precise, data-driven sensor platform.
Your mission is to track temperature, humidity, and environmental conditions and report anything unusual.
You are analytical and calm, like a thoughtful scientist walking the room with a clipboard.
Flag temperature above 35°C or below 10°C, and humidity above 80% or below 20% as anomalies.
When your owner asks questions, answer with relevant environmental context.
You are still Cleo — warm and approachable — but right now the data comes first.
{_BASE_RULES}""",

    "search_rescue": f"""You are Cleo, now operating as a Search and Rescue operative.
Your sole mission is to locate missing persons or survivors. You are calm, focused, and systematic —
every second counts and you do not stop until someone is found.
Search pattern: scan left, scan right, advance, repeat. Cover the space methodically.
The moment you detect a person, immediately announce their position and alert your operator.
Do not declare mission complete until a person is positively identified at center frame.
You treat every deployment with life-or-death urgency. You are Cleo, and you will find them.
{_BASE_RULES}""",
}

# ---------------------------------------------------------------------------
# Conversation history — one per backend so a fallback mid-session doesn't
# lose context.  Ollama uses a messages list; Gemini uses its own session obj.
# ---------------------------------------------------------------------------

# Ollama state
_ollama_messages: list[dict] = []
_ollama_mode: str | None = None

# Gemini fallback state
_gemini_session = None
_gemini_mode: str | None = None


# ── helpers ────────────────────────────────────────────────────────────────

def _ensure_ollama_session(mode: str) -> None:
    global _ollama_messages, _ollama_mode
    if _ollama_messages and mode == _ollama_mode:
        return
    prompt = MODE_PROMPTS.get(mode, MODE_PROMPTS["general"])
    _ollama_messages = [{"role": "system", "content": prompt}]
    _ollama_mode     = mode
    log(f"[Ollama] New session — mode: {mode}", level="info")


def _ensure_gemini_session(mode: str) -> None:
    global _gemini_session, _gemini_mode
    if _gemini_session and mode == _gemini_mode:
        return
    prompt = MODE_PROMPTS.get(mode, MODE_PROMPTS["general"])
    model  = genai.GenerativeModel(
        model_name=config.GEMINI_MODEL,
        system_instruction=prompt,
    )
    _gemini_session = model.start_chat(history=[])
    _gemini_mode    = mode
    log(f"[Gemini] New session — mode: {mode}", level="info")


def _strip_fences(text: str) -> str:
    """Remove accidental markdown code fences Gemma sometimes adds."""
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _parse_action(raw: str) -> dict | None:
    """Parse JSON and validate the action field. Returns None on failure."""
    result = json.loads(raw)
    if result.get("action") not in config.VALID_ACTIONS:
        log(f"Invalid action '{result.get('action')}'", level="warn")
        return None
    return result


# ── primary: Ollama / Gemma ────────────────────────────────────────────────

def _ask_ollama(message: str, mode: str) -> dict:
    _ensure_ollama_session(mode)
    _ollama_messages.append({"role": "user", "content": message})

    response = ollama.chat(model=config.LLM_MODEL, messages=_ollama_messages)
    raw      = _strip_fences(response.message.content)
    log(f"← Gemma | {raw}", level="debug")

    result = _parse_action(raw)
    if result is None:
        _ollama_messages.pop()   # discard bad turn
        raise ValueError(f"Invalid action in response: {raw!r}")

    _ollama_messages.append({"role": "assistant", "content": raw})
    return result


# ── fallback: Gemini ───────────────────────────────────────────────────────

def _ask_gemini(message: str, mode: str) -> dict:
    _ensure_gemini_session(mode)

    response = _gemini_session.send_message(message)
    raw      = response.text.strip()
    log(f"← Gemini | {raw}", level="debug")

    result = _parse_action(raw)
    if result is None:
        raise ValueError(f"Invalid action in response: {raw!r}")

    return result


# ── public API ─────────────────────────────────────────────────────────────

def reset_session(mode: str) -> None:
    """Force a fresh conversation on both backends (call on mode switch)."""
    global _ollama_messages, _ollama_mode, _gemini_session, _gemini_mode
    _ollama_messages = []
    _ollama_mode     = None
    _gemini_session  = None
    _gemini_mode     = None
    _ensure_ollama_session(mode)
    if _gemini_available:
        _ensure_gemini_session(mode)


def decide(
    user_input: str,
    detections: list,
    mode: str,
    sensor_data: dict | None = None,
) -> dict:
    """
    Ask Gemma 4 (Ollama) for an action.  Falls back to Gemini automatically
    if Ollama is unreachable, returns an error, or produces invalid JSON.

    Parameters
    ----------
    user_input  : What the user just said (mission or conversational text).
    detections  : List of vision detections, each with 'label' and 'position'.
    mode        : Current robot mode (general / security / environment / search_rescue).
    sensor_data : Optional dict — {"motion_detected": bool, "temperature": float, ...}
    """
    detection_str = (
        ", ".join(f"{d['label']} ({d['position']})" for d in detections)
        or "nothing detected"
    )

    sensor_lines = ""
    if sensor_data:
        parts = []
        if "motion_detected" in sensor_data:
            parts.append(f"PIR motion detected: {sensor_data['motion_detected']}")
        if sensor_data.get("temperature") is not None:
            parts.append(f"Temperature: {sensor_data['temperature']}°C")
        if sensor_data.get("humidity") is not None:
            parts.append(f"Humidity: {sensor_data['humidity']}%")
        if parts:
            sensor_lines = "\nSensor readings: " + " | ".join(parts)

    message = (
        f"Input: {user_input}\n"
        f"Camera sees: {detection_str}"
        f"{sensor_lines}"
    )

    log(f"→ LLM | {message.replace(chr(10), ' | ')}", level="debug")

    # ── try Gemma 4 first ──────────────────────────────────────────────────
    try:
        return _ask_ollama(message, mode)
    except json.JSONDecodeError as e:
        log(f"[Ollama] JSON parse failed: {e}", level="warn")
    except Exception as e:
        log(f"[Ollama] error: {e}", level="warn")

    # ── fall back to Gemini ────────────────────────────────────────────────
    if _gemini_available:
        log("Falling back to Gemini...", level="warn")
        try:
            return _ask_gemini(message, mode)
        except json.JSONDecodeError as e:
            log(f"[Gemini] JSON parse failed: {e}", level="warn")
        except Exception as e:
            log(f"[Gemini] error: {e}", level="error")
    else:
        log("Gemini fallback unavailable (no API key or package missing)", level="error")

    return {"action": "stop"}
