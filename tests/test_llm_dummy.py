from neuravia.llm.dummy import DummyLLM
from neuravia.llm.base import LLMRequest

def test_dummy_llm_generates_numbered_plan():
    llm = DummyLLM()
    out = llm.generate(LLMRequest(prompt="Construire un plan minimal"))
    lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
    assert len(lines) == 3
    assert lines[0].startswith("1.")
    assert lines[1].startswith("2.")
    assert lines[2].startswith("3.")
