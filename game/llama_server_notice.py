from __future__ import annotations

from collections.abc import Iterable


UNREACHABLE_LLAMA_SERVER_MARKER = "Unable to reach llama-server at "


def is_llama_server_unreachable(error: str | None) -> bool:
    return bool(error) and UNREACHABLE_LLAMA_SERVER_MARKER in error


def build_llama_server_not_running_text(endpoints: Iterable[str]) -> str:
    unique_endpoints: list[str] = []
    for endpoint in endpoints:
        if endpoint and endpoint not in unique_endpoints:
            unique_endpoints.append(endpoint)

    label = "URL" if len(unique_endpoints) == 1 else "URLs"
    configured_urls = ", ".join(unique_endpoints)
    return (
        f"llama-server is not running at the configured {label}: {configured_urls}. "
        "Start llama-server or update the VW_*_ENDPOINT settings."
    )


def append_llama_server_not_running_text(base_text: str, endpoints: Iterable[str], error: str | None) -> str:
    if not is_llama_server_unreachable(error):
        return base_text

    notice = build_llama_server_not_running_text(endpoints)
    if not base_text:
        return notice
    return f"{base_text}\n\n{notice}"
