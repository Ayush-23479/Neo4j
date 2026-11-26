import logging

from app.logging_utils import MaskingFilter, mask


def test_masks_email_and_16_digit_number():
    text = mask("user ayush@example.com paid with 4111 1111 1111 1111 and 4111111111111111")
    assert "ayush@example.com" not in text
    assert "4111" not in text
    assert "***" in text


def test_masks_secret_keys_and_bearer():
    text = mask('token=abc123 password: "hunter2" Authorization: Bearer xyz.789 name=ok')
    for leaked in ("abc123", "hunter2", "xyz.789"):
        assert leaked not in text
    assert "name=ok" in text


def test_masks_phone_and_iban_digits():
    text = mask("call +99-1234567 or XX00SYNTH1234567890 or GB82WEST12345698765432")
    assert "1234567" not in text
    assert "12345698765432" not in text


def test_keeps_normal_text_and_timestamps():
    text = mask("payment 2026-11-20T12:00:00Z uetr ecb4678c-1612-4aa6-be96-39ba0ed2ec9d ok")
    assert text == "payment 2026-11-20T12:00:00Z uetr ecb4678c-1612-4aa6-be96-39ba0ed2ec9d ok"


def test_filter_masks_log_records(caplog):
    logger = logging.getLogger("app.test_filter")
    logger.addFilter(MaskingFilter())
    with caplog.at_level(logging.INFO, logger="app.test_filter"):
        logger.info("contact %s", "me@example.org")
    assert "me@example.org" not in caplog.text