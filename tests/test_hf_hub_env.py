from src.hf_hub_env import resolve_hf_endpoint, xet_available


def test_resolve_hf_endpoint_defaults_to_mirror():
    assert resolve_hf_endpoint(None) == "https://hf-mirror.com"
    assert resolve_hf_endpoint("") == "https://hf-mirror.com"
    assert resolve_hf_endpoint("  ") == "https://hf-mirror.com"


def test_resolve_hf_endpoint_keeps_custom_value():
    assert resolve_hf_endpoint(" https://huggingface.co ") == "https://huggingface.co"


def test_xet_available():
    assert xet_available() is True
