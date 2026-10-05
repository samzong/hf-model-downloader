import importlib.util

DEFAULT_HF_MIRROR_ENDPOINT = "https://hf-mirror.com"


def resolve_hf_endpoint(endpoint: str | None) -> str:
    return (endpoint or "").strip() or DEFAULT_HF_MIRROR_ENDPOINT


def xet_available() -> bool:
    return importlib.util.find_spec("hf_xet") is not None
