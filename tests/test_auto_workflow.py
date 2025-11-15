from pathlib import Path
from neuravia.config import Settings, General, Security, Network, Modules, LLM, Memory
from neuravia.autoimprove.workflow import self_improve_from_text

def _settings(tmp_path: Path) -> Settings:
    return Settings(
        general=General(profile="safe", os_mode="auto", dry_run=False, no_confirm=True, sandbox_path=str(tmp_path/"sb"), log_dir=str(tmp_path/"logs"), kill_switch_path=str(tmp_path/"kill")),
        security=Security(),
        network=Network(),
        modules=Modules(),
        llm=LLM(),
        memory=Memory(db_path=str(tmp_path/"mem.db"), index_enabled=False),
    )

def test_workflow_need_approval_safe(tmp_path: Path):
    s = _settings(tmp_path)
    base = tmp_path
    (base / "neuravia").mkdir(parents=True)
    (base / "neuravia" / "m.py").write_text("X=1\n", encoding="utf-8")
    patch = """--- a/neuravia/m.py
+++ b/neuravia/m.py
@@ -1 +1 @@
-X=1
+X=2
"""
    out = self_improve_from_text(s, patch, base_dir=base, approve=False)
    assert out.status == "need_approval"

def test_workflow_apply_and_revert_on_fail(tmp_path: Path):
    # profile balanced to bypass approval
    s = _settings(tmp_path)
    s.general.profile = "balanced"
    base = tmp_path
    pkg = base / "neuravia"
    tests = base / "tests"
    pkg.mkdir(parents=True)
    tests.mkdir(parents=True)

    # A function with a test expecting 1+1==3 (will fail)
    (pkg / "calc.py").write_text("def add(a,b):\n    return a+b\n", encoding="utf-8")
    (tests / "test_calc.py").write_text("from neuravia.calc import add\n\ndef test_fail():\n    assert add(1,1)==3\n", encoding="utf-8")

    # Patch that does nothing substantial
    patch = """--- a/neuravia/calc.py
+++ b/neuravia/calc.py
@@ -1 +1 @@
-def add(a,b):
+def add(a,b):
     return a+b
"""
    out = self_improve_from_text(s, patch, base_dir=base, approve=True)
    # tests should fail -> reverted
    assert out.status == "reverted_failed_tests"
