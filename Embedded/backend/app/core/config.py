from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
EMBEDDED_DIR = BACKEND_DIR.parent


def _default_path(*parts: str) -> Path:
  """Return a path rooted at Embedded/ when available, else backend/"""
  embedded_candidate = EMBEDDED_DIR.joinpath(*parts)
  if embedded_candidate.exists():
    return embedded_candidate
  return BACKEND_DIR.joinpath(*parts)


@dataclass
class Settings:
    """Backend configuration container."""

    data_dir: Path = field(default_factory=lambda: _default_path("data"))
    artifacts_dir: Path = field(
        default_factory=lambda: _default_path("data", "artifacts"))
    dataset_dir: Path = field(
        default_factory=lambda: _default_path("data", "dataset"))
    allowed_extensions: set[str] = field(
        default_factory=lambda: {".png", ".jpg", ".jpeg", ".bmp"})

    def __post_init__(self) -> None:
        if env_data := os.getenv("PCB_DATA_DIR"):
            self.data_dir = Path(env_data)
            self.artifacts_dir = self.data_dir / "artifacts"
            self.dataset_dir = self.data_dir / "dataset"

        if env_artifact := os.getenv("PCB_ARTIFACTS_DIR"):
            self.artifacts_dir = Path(env_artifact)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.dataset_dir.mkdir(parents=True, exist_ok=True) 
        
        (self.artifacts_dir / "templates").mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    return Settings()