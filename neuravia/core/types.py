from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

@dataclass
class Step:
    id: int
    description: str

@dataclass
class Plan:
    objective: str
    steps: List[Step] = field(default_factory=list)

@dataclass
class Observation:
    step_id: int
    note: str

@dataclass
class RunResult:
    status: str  # "ok" | "error"
    plan: Plan
    logs: List[str] = field(default_factory=list)
