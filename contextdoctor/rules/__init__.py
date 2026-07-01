"""The ContextDoctor rule catalogue (CTX001–CTX010) and plugin registration."""

from contextdoctor.rules.registry import (
    BUILTIN_RULE_IDS,
    RULES,
    Rule,
    get_rule,
    register_rule,
)

__all__ = ["BUILTIN_RULE_IDS", "RULES", "Rule", "get_rule", "register_rule"]
