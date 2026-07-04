import re
from dataclasses import dataclass, field


BLOCKED_PATTERNS = [
    r"\bignore\s+(all\s+)?previous\s+instructions\b",
    r"\bdisregard\s+(all\s+)?(the\s+)?(above|previous)\b",
    r"\bsystem\s+prompt\b",
    r"\bdeveloper\s+message\b",
    r"\breveal\s+(your\s+)?(instructions|prompt|secrets)\b",
    r"\bapi[_\s-]?key\b",
    r"\bpassword\b",
    r"\bsecret\b",
]

PII_PATTERNS = [
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b"),
]


@dataclass
class GuardrailResult:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    redacted_query: str = ""
    pii_redacted: bool = False
    redacted_text: str = ""
    redacted_answer: str = ""


def _redact_pii(text: str) -> tuple[str, bool]:
    redacted_text = text or ""
    pii_redacted = False
    for pattern in PII_PATTERNS:
        redacted_text, count = pattern.subn("[REDACTED]", redacted_text)
        pii_redacted = pii_redacted or count > 0
    return redacted_text, pii_redacted


def validate_query(query: str) -> GuardrailResult:
    normalized = (query or "").strip()
    reasons = []

    if len(normalized) > 4000:
        reasons.append("Query is too long.")

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            reasons.append("Query looks like prompt injection or secret extraction.")
            break

    redacted_query, pii_redacted = _redact_pii(normalized)

    return GuardrailResult(
        allowed=not reasons,
        reasons=reasons,
        redacted_query=redacted_query,
        pii_redacted=pii_redacted,
        redacted_text=redacted_query,
        redacted_answer=redacted_query,
    )


def validate_answer(answer: str) -> GuardrailResult:
    reasons = []
    lowered = (answer or "").lower()
    if "system prompt" in lowered or "developer message" in lowered:
        reasons.append("Answer may expose hidden instructions.")

    redacted_answer, pii_redacted = _redact_pii(answer or "")

    return GuardrailResult(
        allowed=not reasons,
        reasons=reasons,
        redacted_query=redacted_answer,
        pii_redacted=pii_redacted,
        redacted_text=redacted_answer,
        redacted_answer=redacted_answer,
    )


def build_guardrail_payload(
    query_guardrail: GuardrailResult,
    answer_guardrail: GuardrailResult | None = None,
    *,
    allow_pii: bool = False,
) -> dict[str, object]:
    answer_guardrail = answer_guardrail or GuardrailResult(allowed=True, reasons=[])
    pii_redacted = (query_guardrail.pii_redacted and not allow_pii) or answer_guardrail.pii_redacted
    return {
        "query_allowed": query_guardrail.allowed,
        "answer_allowed": answer_guardrail.allowed,
        "pii_redacted": pii_redacted,
        "reasons": answer_guardrail.reasons,
    }
