from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class Paths:
    root: Path
    inbox: Path
    processed: Path
    output: Path
    data: Path
    state: Path


@dataclass
class Config:
    anthropic_api_key: str
    model: str
    confidence_threshold: float
    match_tolerance_pct: float
    match_tolerance_abs: float
    auto_review_threshold: float
    paths: Paths


def load_config(root: Path | None = None) -> Config:
    root = root or Path.cwd()
    load_dotenv(root / ".env")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and paste your "
            "Anthropic API key into it before running."
        )

    config_path = root / "config.yaml"
    if not config_path.exists():
        config_path = root / "config.example.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    paths_raw = raw.get("paths", {})
    paths = Paths(
        root=root,
        inbox=root / paths_raw.get("inbox", "inbox"),
        processed=root / paths_raw.get("processed", "processed"),
        output=root / paths_raw.get("output", "output"),
        data=root / paths_raw.get("data", "data"),
        state=root / paths_raw.get("state", "state"),
    )
    for p in (paths.inbox, paths.processed, paths.output, paths.data, paths.state):
        p.mkdir(parents=True, exist_ok=True)

    return Config(
        anthropic_api_key=api_key,
        model=raw.get("model", "claude-sonnet-5"),
        confidence_threshold=float(raw.get("confidence_threshold", 0.75)),
        match_tolerance_pct=float(raw.get("match", {}).get("tolerance_pct", 0.02)),
        match_tolerance_abs=float(raw.get("match", {}).get("tolerance_abs", 5.00)),
        auto_review_threshold=float(raw.get("approval", {}).get("auto_review_threshold", 1000.00)),
        paths=paths,
    )
