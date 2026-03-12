from __future__ import annotations

import json
from pathlib import Path

from grace.models import BeliefState, ModuleContract


def load_contract(path: str | Path) -> ModuleContract:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return ModuleContract(**payload)


def load_belief_state(path: str | Path) -> BeliefState:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return BeliefState(**payload)
