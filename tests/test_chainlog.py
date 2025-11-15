from pathlib import Path
from neuravia.tools.chainlog import ChainLogger

def test_chainlog_hmac_verify(tmp_path: Path):
    p = tmp_path / "chain.jsonl"
    cl = ChainLogger(p, secret="testsecret")
    cl.log("unit","info","hello",{"i":1})
    cl.log("unit","warn","world",{"i":2})
    assert ChainLogger.verify(p, secret="testsecret") is True
    # wrong secret fails
    assert ChainLogger.verify(p, secret="bad") is False
