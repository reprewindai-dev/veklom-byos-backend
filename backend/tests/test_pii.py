from backend.core.privacy.pii import find_entities, detect, mask

def test_detect_pii():
    text = "Hello Jane Doe, your email is test@example.com and phone is 123-456-7890."
    res = detect(text)
    assert res["has_pii"] is True
    assert "email" in res["pii_types"]
    assert "phone" in res["pii_types"]
    assert "name" in res["pii_types"]

def test_mask_pii():
    text = "Hello Jane Doe, your email is test@example.com and phone is 123-456-7890."
    res = mask(text)
    assert "[NAME]" in res["masked_text"]
    assert "[EMAIL]" in res["masked_text"]
    assert "[PHONE]" in res["masked_text"]
    assert "test@example.com" not in res["masked_text"]
    assert "123-456-7890" not in res["masked_text"]
