import re
from typing import Any
from app.config import load_injection_rules
from app.models import Chunk, Finding


class RuleEngine:

    def __init__(self):
        self.rules = load_injection_rules()

    def evaluate_chunk(self, chunk: Chunk) -> tuple[float, list[Finding]]:
        max_score = 0.0
        findings = []

        for rule in self.rules:
            rule_id = rule.get("id", "unknown_rule")
            weight = float(rule.get("weight", 0.5))
            owasp = rule.get("owasp")
            patterns = rule.get("patterns", [])

            for pattern_str in patterns:
                try:
                    if re.search(pattern_str, chunk.text):
                        if weight > max_score:
                            max_score = weight
                        findings.append(
                            Finding(
                                rule_id=f"rule.{rule_id}",
                                score=weight,
                                reason=f"Matched pattern: {pattern_str}",
                                owasp=owasp,
                            )
                        )
                        # One match per rule is sufficient
                        break
                except Exception:
                    pass

        return max_score, findings


rule_engine = RuleEngine()
