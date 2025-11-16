from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
  """Backend configuration container."""

  data_dir: Path = field(default_factory=lambda: BASE_DIR / "data")
  artifacts_dir: Path = field(default_factory=lambda: BASE_DIR / "data" / "artifacts")
  allowed_extensions: set[str] = field(
      default_factory=lambda: {".png", ".jpg", ".jpeg", ".bmp"})

  def __post_init__(self) -> None:
    data_override = os.getenv("PCB_DATA_DIR")
    artifact_override = os.getenv("PCB_ARTIFACTS_DIR")
    if data_override:
      self.data_dir = Path(data_override)
    if artifact_override:
      self.artifacts_dir = Path(artifact_override)
    self.data_dir.mkdir(parents=True, exist_ok=True)
    self.artifacts_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
  return Settings()
