from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

JsonDict = dict[str, Any]
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class BrandConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "Builder Lead Converter"
    short_name: str = "BLC"
    logo_path: Path | None = None
    primary_color: str = "#1a3a5c"
    accent_color: str = "#f5a623"
    font_heading: str = "Inter"
    font_body: str = "Inter"
    placeholder_fallback: str = "BLC"

    @field_validator("name", "short_name", "font_heading", "font_body", "placeholder_fallback")
    @classmethod
    def non_empty_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned

    @field_validator("primary_color", "accent_color")
    @classmethod
    def valid_hex_color(cls, value: str) -> str:
        cleaned = value.strip()
        if not HEX_COLOR_RE.match(cleaned):
            raise ValueError("must be a 6-digit hex color, for example #1a3a5c")
        return cleaned

    def template_context(self, *, config_path: Path | None = None) -> JsonDict:
        resolved_logo = self._resolved_logo_path(config_path)
        return {
            "name": self.name,
            "short_name": self.short_name,
            "primary_color": self.primary_color,
            "accent_color": self.accent_color,
            "font_heading": self.font_heading,
            "font_body": self.font_body,
            "placeholder_fallback": self.placeholder_fallback,
            "logo_uri": resolved_logo.as_uri() if resolved_logo else None,
            "logo_path": str(resolved_logo) if resolved_logo else None,
            "logo_exists": resolved_logo is not None,
        }

    def _resolved_logo_path(self, config_path: Path | None) -> Path | None:
        if self.logo_path is None:
            return None

        candidate = self.logo_path
        if not candidate.is_absolute():
            roots = []
            if config_path is not None:
                roots.append(config_path.parent)
            roots.append(Path.cwd())
            for root in roots:
                resolved = (root / candidate).resolve()
                if resolved.exists():
                    return resolved
            return None

        resolved = candidate.resolve()
        return resolved if resolved.exists() else None


def load_brand_config(path: Path) -> BrandConfig:
    if not path.exists():
        return BrandConfig()

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Brand config {path} must contain a YAML object.")
    return BrandConfig.model_validate(payload)
