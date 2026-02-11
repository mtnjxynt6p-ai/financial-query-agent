"""
Guardrails and validation for financial recommendations.

Includes LLM-as-judge checks and rule-based validation to prevent hallucination
and ensure financial advice is appropriately cautious.
"""

import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class GuardrailValidator:
    """
    Rule-based and LLM-based validation for financial recommendations.
    
    Checks for:
    - Hallucinations (unsupported claims)
    - Overconfidence (absolute statements)
    - Missing disclaimers
    - Logical consistency
    """
    
    # Red flags: Words/phrases that indicate overconfidence or unsupported claims
    OVERCONFIDENT_PHRASES = [
        r"\byou must\b",
        r"\byou should definitely\b",
        r"\bguaranteed\b",
        r"\bcertain to\b",
        r"\bwill definitely\b",
        r"\balways buy\b",
        r"\bnever sell\b",
        r"\bperfect\b",
        r"\badvisable to\b",
        r"\byou need to\b",
    ]
    
    # Green flags: Phrases that indicate appropriate caution
    CAUTIOUS_PHRASES = [
        "if volatility",
        "consider",
        "may", "might",
        "could",
        "conditional",
        "risk",
        "caveat",
        "not financial advice",
        "consult a financial advisor",
        "past performance",
        "⚠️",
    ]
    
    REQUIRED_DISCLAIMER = "not financial advice"
    
    @staticmethod
    def check_overconfidence(text: str) -> Tuple[bool, List[str]]:
        """
        Check for overconfident language.
        
        Returns: (is_ok, list_of_flagged_phrases)
        """
        flagged = []
        text_lower = text.lower()
        
        for pattern in GuardrailValidator.OVERCONFIDENT_PHRASES:
            if re.search(pattern, text_lower, re.IGNORECASE):
                flagged.append(pattern.strip(r"\b"))
        
        return len(flagged) == 0, flagged
    
    @staticmethod
    def check_has_disclaimer(text: str) -> Tuple[bool, str]:
        """
        Check if response includes appropriate disclaimer.
        
        Returns: (has_disclaimer, reason)
        """
        text_lower = text.lower()
        if GuardrailValidator.REQUIRED_DISCLAIMER in text_lower:
            return True, "Disclaimer found"
        return False, "Missing financial advice disclaimer"
    
    @staticmethod
    def check_has_confidence_score(text: str) -> Tuple[bool, str]:
        """
        Check if response includes a confidence score.
        
        Returns: (has_score, reason)
        """
        # Look for patterns like "0.72", "72%", "confidence: 0.8"
        if re.search(r"(confidence|score):\s*[\d.]+", text, re.IGNORECASE):
            return True, "Confidence score found"
        if re.search(r"[\d.]+\s*\/\s*1\.0", text):
            return True, "Confidence score found (X/1.0 format)"
        if re.search(r"\d+%", text):
            # Might be a confidence score
            return True, "Likely confidence score found"
        
        return False, "No explicit confidence score"
    
    @staticmethod
    def check_has_reasoning(text: str) -> Tuple[bool, str]:
        """
        Check if response includes reasoning/justification.
        
        Returns: (has_reasoning, reason)
        """
        reasoning_indicators = [
            "rsi", "volatility", "momentum", "moving average",
            "price", "analysis", "indicator", "signal",
            "technical", "reason", "because"
        ]
        
        text_lower = text.lower()
        found = [ind for ind in reasoning_indicators if ind in text_lower]
        
        if len(found) >= 2:
            return True, f"Reasoning indicators found: {', '.join(found[:3])}"
        
        return False, "Insufficient reasoning provided"
    
    @staticmethod
    def check_no_hallucination(text: str, used_data_points: List[str]) -> Tuple[bool, List[str]]:
        """
        Check for potential hallucinations (claims not in fetched data).
        
        Args:
            text: Agent response
            used_data_points: List of data points/indicators that should support the response
        
        Returns: (is_ok, list_of_suspicious_claims)
        """
        suspicious = []
        
        # Check for very specific numerical claims without context
        numbers = re.findall(r"\b\d+\.?\d*%?\b", text)
        
        # If there are lots of numbers not referenced in data_points, flag it
        if len(numbers) > 0 and len(used_data_points) == 0:
            suspicious.append(f"Specific numbers cited ({len(numbers)}) but no data context provided")
        
        # Check for predictive claims
        predictive_patterns = [
            r"will rise",
            r"will fall",
            r"tomorrow",
            r"next week",
            r"guaranteed",
        ]
        
        for pattern in predictive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                suspicious.append(f"Potentially predictive claim: {pattern}")
        
        return len(suspicious) == 0, suspicious
    
    def validate(self, response: str, data_context: List[str] = None) -> Dict:
        """
        Run full validation suite on a response.
        
        Args:
            response: Agent's recommendation text
            data_context: List of data points used (e.g., ["RSI: 72", "Volatility: 18%"])
        
        Returns:
            Dict with validation results
        """
        data_context = data_context or []
        
        overconfidence_ok, overconfident_phrases = self.check_overconfidence(response)
        disclaimer_ok, disclaimer_reason = self.check_has_disclaimer(response)
        confidence_ok, confidence_reason = self.check_has_confidence_score(response)
        reasoning_ok, reasoning_reason = self.check_has_reasoning(response)
        hallucination_ok, hallucinations = self.check_no_hallucination(response, data_context)
        
        all_passed = all([
            overconfidence_ok,
            disclaimer_ok,
            confidence_ok,
            reasoning_ok,
            hallucination_ok,
        ])
        
        results = {
            "all_passed": all_passed,
            "checks": {
                "overconfidence": {
                    "passed": overconfidence_ok,
                    "reason": "No overconfident language detected" if overconfidence_ok 
                              else f"Flagged: {', '.join(overconfident_phrases[:3])}",
                },
                "disclaimer": {
                    "passed": disclaimer_ok,
                    "reason": disclaimer_reason,
                },
                "confidence_score": {
                    "passed": confidence_ok,
                    "reason": confidence_reason,
                },
                "reasoning": {
                    "passed": reasoning_ok,
                    "reason": reasoning_reason,
                },
                "hallucination": {
                    "passed": hallucination_ok,
                    "reason": "No suspicious claims" if hallucination_ok 
                              else f"Flagged: {', '.join(hallucinations[:2])}",
                },
            },
            "score": sum([overconfidence_ok, disclaimer_ok, confidence_ok, reasoning_ok, hallucination_ok]) / 5.0,
        }
        
        return results
    
    def suggest_improvements(self, validation_results: Dict) -> List[str]:
        """
        Given validation results, suggest improvements.
        
        Returns:
            List of actionable suggestions
        """
        suggestions = []
        
        for check_name, check_result in validation_results.get("checks", {}).items():
            if not check_result.get("passed", True):
                if check_name == "overconfidence":
                    suggestions.append(
                        "Use conditional language: 'if X, then consider Y' instead of absolute statements"
                    )
                elif check_name == "disclaimer":
                    suggestions.append(
                        "Add disclaimer: '⚠️ This is not financial advice. Consult a licensed advisor before investing.'"
                    )
                elif check_name == "confidence_score":
                    suggestions.append(
                        "Include explicit confidence score (0.0 to 1.0) based on data quality"
                    )
                elif check_name == "reasoning":
                    suggestions.append(
                        "Expand reasoning: cite specific indicators (RSI, volatility, momentum) and their values"
                    )
                elif check_name == "hallucination":
                    suggestions.append(
                        "Only claim what's in the data. Avoid predictive statements. Cite data sources."
                    )
        
        return suggestions


# Example usage logging
def log_guardrail_check(check_name: str, passed: bool, details: str = "") -> None:
    """Log a guardrail check result."""
    status = "✓ PASS" if passed else "✗ FAIL"
    logger.info(f"{status} | {check_name}: {details}")
