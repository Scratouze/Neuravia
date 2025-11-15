from pathlib import Path
from neuravia.autoimprove.patcher import apply_patch_text, PatchSecurityError

def test_apply_patch_respects_allowlist(tmp_path: Path):
    base = tmp_path
    (base / "neuravia").mkdir()
    # create a file
    f = base / "neuravia" / "x.txt"
    f.write_text("hello\n", encoding="utf-8")
    # patch that tries to write outside allowlist
    bad_patch = """--- a/../evil.txt
+++ b/../evil.txt
@@ -1 +1 @@
-BOOM
+BOOM2
"""
    try:
        apply_patch_text(base, bad_patch, allow_roots=[Path("neuravia"), Path("tests"), Path("config")], dry_run=True)
        assert False, "Should have raised"
    except PatchSecurityError:
        pass

    # valid patch inside allowlist
    good_patch = """--- a/neuravia/x.txt
+++ b/neuravia/x.txt
@@ -1 +1 @@
-hello
+hello world
"""
    res = apply_patch_text(base, good_patch, allow_roots=[Path("neuravia"), Path("tests"), Path("config")], dry_run=False)
    assert any("x.txt" in str(p) for p,_ in res.changed)
    assert (base / "neuravia" / "x.txt").read_text(encoding="utf-8") == "hello world"
