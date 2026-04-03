from .config import CONFIRMATION_POLICY

def needs_confirmation(text: str) -> bool:
    if not CONFIRMATION_POLICY.get("require_confirmation", True):
        return False
    words = CONFIRMATION_POLICY.get("destructive_keywords", [])
    t = text.lower()
    return any(w in t for w in words)
