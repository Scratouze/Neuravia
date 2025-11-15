import importlib
import pytest
from pathlib import Path
from neuravia.config import load_settings
from neuravia.tools.ocr import has_tesseract, ocr_image_to_text, FileSecurityError

def _has_pillow():
    try:
        import PIL  # noqa: F401
        return True
    except Exception:
        return False

@pytest.mark.skipif(not has_tesseract() or not _has_pillow(), reason="tesseract ou Pillow manquant")
def test_ocr_on_generated_image(tmp_path: Path):
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
    s = load_settings(config="config", profile="safe", overrides={"dry_run": True})
    # génère une image simple avec 'HELLO'
    img = Image.new("RGB", (300, 120), "white")
    d = ImageDraw.Draw(img)
    d.text((10, 40), "HELLO", fill="black")  # font par défaut
    target = Path(s.general.sandbox_path) / "ocr/hello.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    img.save(target)

    out = ocr_image_to_text(s, "ocr/hello.png", lang="eng")
    assert "HELLO" in out.upper()

def test_ocr_ext_blocked(tmp_path: Path):
    s = load_settings(config="config", profile="safe")
    # crée un fichier avec mauvaise extension
    p = Path(s.general.sandbox_path) / "ocr/bad.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("dummy", encoding="utf-8")
    with pytest.raises(FileSecurityError):
        ocr_image_to_text(s, "ocr/bad.txt")
