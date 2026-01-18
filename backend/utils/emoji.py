from constants import BALANCE_STATUS_EMOJI


def get_balance_emoji(status: str) -> str:
    """
    Get emoji indicator for balance status.
    
    Args:
        status: Balance status (under_fueled, roughly_aligned, slightly_over)
        
    Returns:
        Emoji string
    """
    return BALANCE_STATUS_EMOJI.get(status, "🟢")
