from __future__ import annotations

MODEL_QUALITY_PRESETS: dict[str, str] = {
    "fast": "whisper-tiny",
    "balanced": "whisper-base",
    "accurate": "whisper-large-v3",
}


def resolve_model_name(model_quality: str, custom_model_name: str | None = None) -> str:
    """Resolve a quality preset to a model name.

    If `model_quality` maps to a known preset, return the preset model name.
    Otherwise, if `custom_model_name` is provided, return it (user override).
    Falls back to "whisper-large-v3" for unknown quality values.

    Args:
        model_quality: Quality preset string (e.g., "fast", "balanced", "accurate").
        custom_model_name: Optional explicit model name override.

    Returns:
        Resolved model name string.
    """
    quality_lower: str = model_quality.lower().strip() if model_quality else "accurate"

    # Explicit custom model name always wins
    if custom_model_name:
        return custom_model_name

    # Known preset
    resolved: str | None = MODEL_QUALITY_PRESETS.get(quality_lower)
    if resolved:
        return resolved

    # Unknown quality — fall back to default
    return "whisper-large-v3"
