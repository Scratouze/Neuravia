import pytest
from neuravia.llm.ollama import has_ollama

def test_has_ollama_returns_bool():
    assert isinstance(has_ollama(), bool)

@pytest.mark.skipif(not has_ollama(), reason="ollama non installé")
def test_ollama_available_smoke():
    # Simple détection; pas de génération réelle ici
    assert has_ollama() is True
