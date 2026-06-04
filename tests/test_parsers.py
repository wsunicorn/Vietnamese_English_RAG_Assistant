from app.ingestion.parsers import detect_language, repair_mojibake


def test_repair_mojibake_restores_vietnamese_text():
    repaired = repair_mojibake("TÃ i liá»u nÃ³i vá» lá» trÃ¬nh AI Engineer.")

    assert repaired == "Tài liệu nói về lộ trình AI Engineer."
    assert detect_language(repaired) == "vi"
