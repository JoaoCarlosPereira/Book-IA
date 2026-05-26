"""Helpers for HTMX HTML partial responses."""

from fastapi import Request
from starlette.responses import Response


def is_htmx(request: Request) -> bool:
    """Return True when the request comes from HTMX."""
    return request.headers.get("HX-Request") == "true"


def wants_html_partial(request: Request) -> bool:
    """Return True when the client expects an HTML fragment (HTMX or Accept)."""
    if is_htmx(request):
        return True
    accept = request.headers.get("accept", "")
    return "text/html" in accept and "application/json" not in accept
