from neuravia.tools.ocr import has_tesseract, tesseract_version

def test_tesseract_detection_runs():
    # Ne dépend pas de la présence de tesseract : doit juste exécuter sans exception
    ok = has_tesseract()
    v = tesseract_version()  # None si absent
    assert (ok and v is not None) or (not ok and v is None or isinstance(v, str))
