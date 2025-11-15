from __future__ import annotations
from typing import List
from .types import Step, Plan, Observation
from .policies import load_prompt_resource

class PlannerAgent:
    def __init__(self) -> None:
        self.policy_text = load_prompt_resource()

    def plan(self, objective: str, max_steps: int = 3) -> Plan:
        # Planneur déterministe simple (sans LLM): découpe heuristique
        tokens = [t for t in objective.replace('-', ' ').replace('_', ' ').split() if t]
        core = " ".join(tokens[:6]) if tokens else objective
        steps: List[Step] = []
        steps.append(Step(1, f"Analyser l'objectif: {core}"))
        if max_steps >= 2:
            steps.append(Step(2, "Élaborer un plan d'actions minimal"))
        if max_steps >= 3:
            steps.append(Step(3, "Simuler l'exécution et consigner les observations"))
        return Plan(objective=objective, steps=steps)

class ExecutorAgent:
    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run

    def execute(self, step: Step) -> str:
        # Exécution simulée (aucune action système réelle à la Phase 3)
        return f"[Executor] step {step.id}: {step.description} :: {'DRY-RUN' if self.dry_run else 'RUN'}"

class ObserverAgent:
    def observe(self, step: Step, execution_note: str) -> Observation:
        # Observation triviale
        return Observation(step_id=step.id, note=f"[Observer] step {step.id} ok ({execution_note})")

class ReviewerAgent:
    def review(self, plan: Plan, observations: List[Observation]) -> str:
        # Review minimaliste: confirme si toutes les observations sont ok
        ok = all("ok" in obs.note for obs in observations)
        return "[Reviewer] plan validé" if ok else "[Reviewer] plan à améliorer"
