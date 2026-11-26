import logging
import re

MASK = "***"

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"\+\d[\d\s().-]{7,}\d")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
_CARD = re.compile(r"(?<!\d)\d{4}(?:[ -]?\d{4}){3,4}(?!\d)")
_LONG_DIGITS = re.compile(r"(?<!\d)\d{12,}(?!\d)")
_SECRET_KEYS = re.compile(
    r"""(?ix)
    (["']?(?:secret|token|password|authorization)[\w-]*["']?\s*[:=]\s*["']?)
    (?:bearer\s+)?[^\s,"'}&]+
    """
)


def mask(text: str) -> str:
    """Mask emails, phone numbers, long digit runs and values of secret-like keys."""
    text = _SECRET_KEYS.sub(lambda m: m.group(1) + MASK, text)
    text = _EMAIL.sub(MASK, text)
    text = _PHONE.sub(MASK, text)
    text = _IBAN.sub(MASK, text)
    text = _CARD.sub(MASK, text)
    return _LONG_DIGITS.sub(MASK, text)


class MaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask(record.getMessage())
        record.args = None
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Attach the masking filter to the root and uvicorn handlers. Safe to call twice."""
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    masking = MaskingFilter()
    names = ("", "uvicorn", "uvicorn.error", "uvicorn.access", "app")
    for name in names:
        logger = logging.getLogger(name)
        if not any(isinstance(f, MaskingFilter) for f in logger.filters):
            logger.addFilter(masking)
        for handler in logger.handlers:
            if not any(isinstance(f, MaskingFilter) for f in handler.filters):
                handler.addFilter(masking)