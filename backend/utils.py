"""
Utility functions for maintaining context windows.
"""
from typing import List, Dict

def truncate_messages(messages: List[Dict[str, str]], max_turns: int = 8) -> List[Dict[str, str]]:
    """
    Retains system messages (indexes 0 and 1) and retains up to the last max_turns messages.
    """
    if len(messages) <= (2 + max_turns):
        return messages
    return messages[:2] + messages[-max_turns:]