"""Rule metadata catalogue.

Each rule has a stable id, a default severity, a human description, and a
default recommendation. Analyzers reference these rules when emitting findings
and may override the message/recommendation with specifics (e.g. actual sizes).
"""

from __future__ import annotations

from dataclasses import dataclass

from contextlint.models import Severity


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    category: str
    default_severity: Severity
    description: str
    recommendation: str
    experimental: bool = False


_RULE_LIST: list[Rule] = [
    Rule(
        id="CTX001",
        name="chunk-too-large",
        category="chunk-stats",
        default_severity=Severity.WARNING,
        description="One or more chunks exceed the recommended maximum size.",
        recommendation=(
            "Split oversized chunks. Very large chunks dilute retrieval relevance and can "
            "overflow the model's usable context window. Reduce your chunk size or add "
            "semantic split points (headings, paragraphs)."
        ),
    ),
    Rule(
        id="CTX002",
        name="chunk-too-small",
        category="chunk-stats",
        default_severity=Severity.WARNING,
        description="One or more chunks are too small to carry useful standalone context.",
        recommendation=(
            "Merge tiny chunks with their neighbours. Fragments that are too small lack the "
            "context needed to answer questions and waste retrieval slots. Increase chunk "
            "size or merge short sections."
        ),
    ),
    Rule(
        id="CTX003",
        name="duplicate-content",
        category="duplicates",
        default_severity=Severity.WARNING,
        description="Exact or near-duplicate chunks were found in the corpus.",
        recommendation=(
            "Deduplicate your corpus. Duplicate chunks crowd out diverse results, bias "
            "retrieval toward repeated passages, and inflate index size. Remove or merge "
            "duplicates before indexing."
        ),
    ),
    Rule(
        id="CTX004",
        name="broken-table",
        category="tables",
        default_severity=Severity.ERROR,
        description="A markdown table appears to be split across a chunk boundary.",
        recommendation=(
            "Keep tables intact within a single chunk. A table split across chunks loses its "
            "header row and column meaning, making rows unusable at retrieval time. Use a "
            "structure-aware splitter or increase chunk size for table-heavy documents."
        ),
    ),
    Rule(
        id="CTX005",
        name="heading-fragmentation",
        category="headings",
        default_severity=Severity.WARNING,
        description="A single section (heading) spans an excessive number of chunks.",
        recommendation=(
            "Consider parent-child / hierarchical retrieval for long sections. When one "
            "heading spans many chunks, individual chunks lose the section's framing. Attach "
            "the parent heading to each child chunk, or retrieve the parent section as context."
        ),
    ),
    Rule(
        id="CTX006",
        name="high-context-fragmentation",
        category="fragmentation",
        default_severity=Severity.WARNING,
        description="The experimental Context Fragmentation Index (CFI) is high.",
        recommendation=(
            "Related information is scattered across distant chunks. Re-order or re-chunk so "
            "that discussions of the same entity stay close together, or add overlap / "
            "summaries so retrieval can reassemble the full picture. CFI is experimental — "
            "treat it as a signal to inspect, not a hard failure."
        ),
        experimental=True,
    ),
    Rule(
        id="CTX007",
        name="secret-detected",
        category="content-quality",
        default_severity=Severity.ERROR,
        description="A credential or API key appears to be embedded in the content.",
        recommendation=(
            "Never index secrets. API keys, tokens, and private keys embedded in your corpus "
            "will be stored in your vector database and can be surfaced verbatim to users at "
            "retrieval time. Remove the secret from the source, rotate it, and re-index."
        ),
    ),
    Rule(
        id="CTX008",
        name="pii-detected",
        category="content-quality",
        default_severity=Severity.WARNING,
        description="Personally identifiable information (PII) was detected in the content.",
        recommendation=(
            "Review and redact PII before indexing. Emails, phone numbers, and government or "
            "financial identifiers embedded in chunks can leak to users through retrieval and "
            "create compliance risk. Mask or remove PII, or gate the affected documents."
        ),
    ),
    Rule(
        id="CTX009",
        name="encoding-artifacts",
        category="content-quality",
        default_severity=Severity.WARNING,
        description="Mojibake or control characters suggest a broken text-extraction step.",
        recommendation=(
            "Fix the extraction/encoding upstream. Replacement characters (�), mojibake "
            "like 'Ã©' or 'â€™', and stray control characters degrade embeddings and make "
            "retrieved text unreadable. Re-extract with the correct encoding (usually UTF-8)."
        ),
    ),
    Rule(
        id="CTX010",
        name="exceeds-embedding-limit",
        category="chunk-stats",
        default_severity=Severity.WARNING,
        description="A chunk likely exceeds the embedding model's token limit.",
        recommendation=(
            "Shrink chunks to fit your embedding model. Many popular embedding models (e5, "
            "bge, MiniLM, and others) silently truncate input beyond ~512 tokens, so the tail "
            "of an oversized chunk is never embedded and becomes unsearchable. Reduce chunk "
            "size or set 'embedding_token_limit' to match your model."
        ),
    ),
]

RULES: dict[str, Rule] = {rule.id: rule for rule in _RULE_LIST}

#: Rule ids shipped by ContextLint itself (used to protect them from plugins).
BUILTIN_RULE_IDS = frozenset(RULES)


def register_rule(rule: Rule, *, override: bool = False) -> None:
    """Register a rule (e.g. from a plugin).

    Built-in rules are never silently overwritten: a plugin trying to redefine a
    ``CTX*`` id is ignored unless ``override=True`` is passed explicitly.
    """
    if rule.id in RULES and not override:
        return
    RULES[rule.id] = rule


def get_rule(rule_id: str) -> Rule:
    """Return rule metadata, synthesising a placeholder for unknown ids.

    This keeps every renderer robust even if a plugin emits a finding for a rule
    it forgot to register.
    """
    rule = RULES.get(rule_id)
    if rule is not None:
        return rule
    return Rule(
        id=rule_id,
        name=rule_id.lower().replace("_", "-"),
        category="plugin",
        default_severity=Severity.WARNING,
        description="Custom rule.",
        recommendation="See the plugin that defines this rule.",
    )
