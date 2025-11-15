from __future__ import annotations
from dataclasses import dataclass

@dataclass
class LLMRequest:
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.2

class LLM:
    def generate(self, req: LLMRequest) -> str:  # pragma: no cover - interface
        raise NotImplementedError
