"""HTTP against the public surface, and nothing else."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

TIMEOUT_SECONDS = float(os.environ.get("HARNESS_TIMEOUT", "300"))


class Unauthenticated(RuntimeError):
    """The server does not know who this is (CLI-3's exit 4)."""


class HttpTransport:
    """Talks to the agent over HTTP on the CLI's behalf."""

    def __init__(self, base_url: str, *, token: str | None = None) -> None:
        """Bind to `base_url`, with a bearer token if there is one."""
        self._base = base_url.rstrip("/")
        self._token = token or os.environ.get("HARNESS_TOKEN")

    def get(self, path: str) -> tuple[int, Any]:
        """GET `path` and return the status and decoded body."""
        return self._call("GET", path)

    def delete(self, path: str) -> tuple[int, Any]:
        """DELETE `path` and return the status and decoded body."""
        return self._call("DELETE", path)

    def post(self, path: str, body: dict | None = None) -> tuple[int, Any]:
        """POST `body` to `path` and return the status and decoded body."""
        return self._call("POST", path, body)

    def put(self, path: str, body: dict | None = None) -> tuple[int, Any]:
        """PUT `body` to `path` and return the status and decoded body."""
        return self._call("PUT", path, body)

    def stream(
        self, path: str, body: dict | None = None, method: str = "POST"
    ) -> Iterator[str]:
        """Lines from a server-sent-event response, as they arrive."""
        import httpx

        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        with httpx.stream(
            method,
            f"{self._base}{path}",
            json=body,
            headers=headers,
            timeout=TIMEOUT_SECONDS,
        ) as response:
            if response.status_code == 401:
                response.read()
                raise Unauthenticated(
                    f"{self._base} does not know who you are. "
                    "Set HARNESS_TOKEN, or log in again."
                )
            if response.status_code >= 400:
                response.read()
                raise RuntimeError(
                    f"The agent answered {response.status_code} to a stream"
                )
            yield from response.iter_lines()

    def _call(
        self, method: str, path: str, body: dict | None = None
    ) -> tuple[int, Any]:
        """Make one request and return the status and decoded body."""
        import httpx

        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        try:
            response = httpx.request(
                method,
                f"{self._base}{path}",
                json=body if method in ("POST", "PUT") else None,
                headers=headers,
                timeout=TIMEOUT_SECONDS,
            )
        except Exception as unreachable:
            return 0, {"detail": f"Could not reach {self._base}: {unreachable}"}
        if response.status_code == 401:
            raise Unauthenticated(
                f"{self._base} does not know who you are. "
                "Set HARNESS_TOKEN, or log in again."
            )
        return response.status_code, _body(response)


def _body(response: Any) -> Any:
    """Whatever came back, or a readable stand-in."""
    if not response.content:
        return {}
    try:
        return response.json()
    except Exception:
        return {"detail": response.text[:500]}
