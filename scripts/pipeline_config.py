#!/usr/bin/env python3
"""Tiny config loader shared by the kit's Python scripts.

Reads pipeline.config (KEY=VALUE, # comments, ~ expansion) and exposes get().
Search order: $PIPELINE_CONFIG, ../config/pipeline.config, ../pipeline.config,
~/.cross-border-selection/pipeline.config. Missing config is not fatal — get()
falls back to the provided default so scripts still run with CLI args only.
"""
from __future__ import annotations
import os
from pathlib import Path

_CACHE = None


def _find() -> Path | None:
    env = os.environ.get("PIPELINE_CONFIG")
    if env and Path(env).is_file():
        return Path(env)
    here = Path(__file__).resolve().parent
    for cand in [here / "../config/pipeline.config",
                 here / "../pipeline.config",
                 Path.home() / ".cross-border-selection/pipeline.config"]:
        if cand.is_file():
            return cand.resolve()
    return None


def _load() -> dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    cfg = {}
    p = _find()
    if p:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.split("#", 1)[0].strip()
            if v.startswith("~"):
                v = str(Path(v).expanduser())
            cfg[k] = v
    _CACHE = cfg
    return cfg


def get(key: str, default=None):
    return _load().get(key, default)
