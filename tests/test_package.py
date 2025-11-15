import importlib

def test_import_version():
    m = importlib.import_module("neuravia")
    assert hasattr(m, "__version__")
    assert isinstance(m.__version__, str)
    assert len(m.__version__) >= 5  # ex: 0.1.0
