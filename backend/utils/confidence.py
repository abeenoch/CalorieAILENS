from typing import List


def calculate_overall_confidence(confidences: List[str]) -> str:
    """
    Calculate overall confidence from a list of individual confidence levels.
    
    Logic:
    - If ANY item is "low", return "low" (one bad item ruins it)
    - If MOST items are "high", return "high"
    - Otherwise return "medium"
    
    Args:
        confidences: List of confidence levels ("high", "medium", "low")
        
    Returns:
        Overall confidence level
    """
    if not confidences:
        return "medium"
    
    # If any item is low, overall is low
    if any(c == "low" for c in confidences):
        return "low"
    
    # If most items are high, overall is high
    high_count = sum(1 for c in confidences if c == "high")
    if high_count >= len(confidences) / 2:
        return "high"
    
    return "medium"
