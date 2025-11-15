from __future__ import annotations
from typing import List
from ..config import Settings
from .types import RunResult, Plan
from .agents import PlannerAgent, ExecutorAgent, ObserverAgent, ReviewerAgent

def run_goal(settings: Settings, objective: str, max_steps: int = 3) -> RunResult:
    planner = PlannerAgent()
    executor = ExecutorAgent(dry_run=settings.general.dry_run or True)  # Phase 3: toujours dry
    observer = ObserverAgent()
    reviewer = ReviewerAgent()

    plan: Plan = planner.plan(objective, max_steps=max_steps)
    logs: List[str] = [f"[Planner] {len(plan.steps)} étape(s) générée(s) pour: {objective!r}"]

    observations = []
    for step in plan.steps:
        note = executor.execute(step)
        logs.append(note)
        obs = observer.observe(step, note)
        logs.append(obs.note)
        observations.append(obs)

    review_note = reviewer.review(plan, observations)
    logs.append(review_note)

    return RunResult(status="ok", plan=plan, logs=logs)
