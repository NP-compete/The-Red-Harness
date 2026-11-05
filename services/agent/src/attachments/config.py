"""Attachment limits, from `config/agent/runtime/agent.yaml`."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ExtractionConfig(BaseModel):
    """Which parser reads an uploaded document."""

    engine: Literal["builtin", "docling", "tika"] = "builtin"

    url: str = ""
    api_key: str = ""

    params: dict[str, Any] = Field(default_factory=dict)

    timeout_seconds: float = Field(default=120.0, gt=0, le=600)

    max_bytes: int = Field(default=20 * 1024 * 1024, ge=1)

    suffixes: list[str] = Field(
        default_factory=lambda: [
            "pdf",
            "docx",
            "doc",
            "pptx",
            "ppt",
            "odt",
            "odp",
            "rtf",
            "epub",
            "html",
            "htm",
            "png",
            "jpg",
            "jpeg",
            "tiff",
            "tif",
            "bmp",
            "webp",
        ]
    )

    fallback: bool = True

    @field_validator("url")
    @classmethod
    def _http_only(cls, value: str) -> str:
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("extraction.url must start with http:// or https://")
        return value

    def handles(self, filename: str, size: int) -> bool:
        """True when this file should go to the remote engine."""
        if self.engine == "builtin" or not self.url:
            return False
        if size > self.max_bytes:
            return False
        suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return suffix in {s.lower().lstrip(".") for s in self.suffixes}


class AttachmentsConfig(BaseModel):
    """What a user may attach to a thread."""

    enabled: bool = True

    max_file_bytes: int = Field(default=50 * 1024 * 1024, ge=1, le=500 * 1024 * 1024)

    max_thread_bytes: int = Field(default=200 * 1024 * 1024, ge=1)

    max_files_per_request: int = Field(default=10, ge=1, le=50)

    allowed_extensions: list[str] = Field(default_factory=list)

    mount_path: str = "/uploads/"

    max_inline_chars: int = Field(default=20_000, ge=100)

    def is_allowed(self, filename: str) -> bool:
        """True unless a restrictive allowlist is configured."""
        if not self.allowed_extensions:
            return True
        suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return suffix in {e.lower().lstrip(".") for e in self.allowed_extensions}
