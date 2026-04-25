import json
import config
import google.generativeai as genai
from utils.logger import log

# ---------------------------------------------------------------------------
# Mode-specific system prompts
# Each mode gives Gemini a different personality and set of priorities.
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
# Chat session management
# A single persistent Gemini chat session is kept alive per mode so that
# Gemini has full conversation history throughout the session.
# ---------------------------------------------------------------------------

genai.configure(api_key=config.GEMINI_API_KEY)

_chat_session = None
_current_mode = None


def _get_or_create_session(mode: str):
    """Return the active chat session, creating a new one if mode changed."""
    global _chat_session, _current_mode

    if _chat_session is None or mode != _current_mode:
        prompt = MODE_PROMPTS.get(mode, MODE_PROMPTS["general"])
        model  = genai.GenerativeModel(
            model_name=config.LLM_MODEL,
            system_instruction=prompt,
        )
        _chat_session  = model.start_chat(history=[])
        _current_mode  = mode
        log(f"New chat session started — mode: {mode}", level="info")

    return _chat_session


def reset_session(mode: str):
    """Force a fresh chat session (call this when the robot switches modes)."""
    global _chat_session, _current_mode
    _chat_session = None
    _current_mode = None
    _get_or_create_session(mode)


def decide(
    user_input: str,
    detections: list,
    mode: str,
    sensor_data: dict | None = None,
) -> dict:
    """
    Send the current situation to Gemini and get back a JSON action.

    Parameters
    ----------
    user_input  : What the user just said (mission or conversational text).
    detections  : List of vision detections, each with 'label' and 'position'.
    mode        : Current robot mode (general / security / environment / search_rescue).
    sensor_data : Optional dict with live sensor readings, e.g.
                  {"motion_detected": True, "temperature": 24.5, "humidity": 55.0}
    """
    session = _get_or_create_session(mode)

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

    log(f"→ Gemini | {message.replace(chr(10), ' | ')}", level="debug")

    try:
        response = session.send_message(message)
        raw      = response.text.strip()
        log(f"← Gemini | {raw}", level="debug")
        result   = json.loads(raw)
        if result.get("action") not in config.VALID_ACTIONS:
            log(f"Invalid action '{result.get('action')}' — defaulting to stop", level="warn")
            return {"action": "stop"}
        return result
    except json.JSONDecodeError:
        log(f"JSON parse failed on: {raw!r}", level="warn")
        return {"action": "stop"}
    except Exception as e:
        log(f"Gemini error: {e}", level="error")
        return {"action": "stop"}
