from __future__ import annotations

from src.utils.model_quality import MODEL_QUALITY_PRESETS, resolve_model_name


class TestModelQualityPresets:
    """Verify preset mappings are correct."""

    def test_fast_maps_to_tiny(self):
        assert MODEL_QUALITY_PRESETS["fast"] == "whisper-tiny"

    def test_balanced_maps_to_base(self):
        assert MODEL_QUALITY_PRESETS["balanced"] == "whisper-base"

    def test_accurate_maps_to_large_v3(self):
        assert MODEL_QUALITY_PRESETS["accurate"] == "whisper-large-v3"

    def test_all_presets_resolve(self):
        for quality, model_name in MODEL_QUALITY_PRESETS.items():
            resolved = resolve_model_name(quality)
            assert resolved == model_name


class TestResolveModelName:
    """Verify resolve_model_name behavior."""

    def test_fast_resolves_tiny(self):
        assert resolve_model_name("fast") == "whisper-tiny"

    def test_balanced_resolves_base(self):
        assert resolve_model_name("balanced") == "whisper-base"

    def test_accurate_resolves_large_v3(self):
        assert resolve_model_name("accurate") == "whisper-large-v3"

    def test_case_insensitive(self):
        assert resolve_model_name("FAST") == "whisper-tiny"
        assert resolve_model_name("Balanced") == "whisper-base"

    def test_whitespace_stripped(self):
        assert resolve_model_name("  fast  ") == "whisper-tiny"

    def test_unknown_quality_falls_back(self):
        assert resolve_model_name("unknown-preset") == "whisper-large-v3"

    def test_empty_string_falls_back(self):
        assert resolve_model_name("") == "whisper-large-v3"

    def test_none_falls_back(self):
        assert resolve_model_name(None) == "whisper-large-v3"

    def test_custom_model_overrides_preset(self):
        assert resolve_model_name("fast", "my-custom-model") == "my-custom-model"

    def test_custom_model_overrides_accurate(self):
        assert resolve_model_name("accurate", "whisper-turbo") == "whisper-turbo"

    def test_custom_model_with_none_quality(self):
        assert resolve_model_name(None, "tiny-int8") == "tiny-int8"
