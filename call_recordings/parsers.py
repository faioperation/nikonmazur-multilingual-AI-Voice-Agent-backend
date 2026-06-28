"""Map a VAPI 'end-of-call-report' webhook payload to CallRecording fields.

Every lookup is defensive: a missing or malformed field yields ``None`` rather
than raising, so the webhook can never crash on an unexpected payload shape.
"""

import re

from django.utils.dateparse import parse_datetime

# A real phone number must contain at least this many digits. This filters out
# placeholder values such as "yes" that VAPI sometimes returns for web calls.
_MIN_PHONE_DIGITS = 5


def _get(data, *keys):
    """Safely walk nested dicts; return None if any key is missing."""
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def _structured_results(message):
    """Yield each structured-output ``result`` keyed by its ``name``.

    ``artifact.structuredOutputs`` is a dict keyed by UUID, where each value
    looks like ``{"name": "lead_data", "result": {...}}``.
    """
    outputs = _get(message, "artifact", "structuredOutputs")
    results = {}
    if isinstance(outputs, dict):
        for entry in outputs.values():
            if isinstance(entry, dict) and entry.get("name"):
                results[entry["name"]] = entry.get("result")
    return results


def _clean_phone(value):
    """Return the value only if it looks like a real phone number, else None."""
    if not value or not isinstance(value, str):
        return None
    if len(re.sub(r"\D", "", value)) >= _MIN_PHONE_DIGITS:
        return value.strip()
    return None


def _extract_phone(message, lead_data):
    """Probe every known location a phone number could appear.

    Web calls currently carry no real number, so this returns None for them.
    Phone calls (future) populate one of the customer fields.
    """
    candidates = [
        _get(message, "customer", "number"),
        _get(message, "call", "customer", "number"),
        _get(message, "phoneNumber", "number"),
        _get(message, "artifact", "variables", "call", "customer", "number"),
        lead_data.get("caller_phone") if isinstance(lead_data, dict) else None,
    ]
    for candidate in candidates:
        phone = _clean_phone(candidate)
        if phone:
            return phone
    return None


def _to_int_seconds(value):
    """Convert durationSeconds (often a float) to whole seconds."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _sentiment_from_consent(structured):
    """Map the boolean 'consent' structured output to a sentiment label."""
    result = structured.get("consent")
    if result is True:
        return "Positive"
    if result is False:
        return "Negative"
    return None


def parse_end_of_call_report(payload):
    """Build a dict of CallRecording field values from a webhook payload.

    ``payload`` is the raw webhook body, ``{"message": {...}}``.
    """
    message = payload.get("message", {}) if isinstance(payload, dict) else {}

    structured = _structured_results(message)
    lead_data = structured.get("lead_data") or {}
    if not isinstance(lead_data, dict):
        lead_data = {}

    assistant_name = None
    activations = _get(message, "artifact", "assistantActivations")
    if isinstance(activations, list) and activations:
        assistant_name = _get(activations[0], "assistantName")

    audio_url = _get(message, "artifact", "recordingUrl") or message.get("recordingUrl")

    call_date = message.get("startedAt") or _get(
        message, "artifact", "variables", "call", "createdAt"
    )
    call_date = parse_datetime(call_date) if isinstance(call_date, str) else None

    return {
        "caller_name": lead_data.get("caller_name") or None,
        "caller_number": _extract_phone(message, lead_data),
        "assistant_name": assistant_name,
        "audio_url": audio_url,
        "call_date": call_date,
        "duration_seconds": _to_int_seconds(message.get("durationSeconds")),
        "outcome": lead_data.get("call_intent") or None,
        "sentiment": _sentiment_from_consent(structured),
        "ai_summary": _get(message, "analysis", "summary"),
        "transcript": _get(message, "artifact", "transcript"),
        "lead_score": lead_data.get("lead_status") or None,
    }
