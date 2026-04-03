from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
from fnmatch import fnmatch
from .config import SECURITY
from .logger import get_logger
from . import policies

logger = get_logger("MoriX.security")

class SecurityError(Exception):
    pass

@dataclass
class Decision:
    allowed: bool
    reason: str = ""
    requires_confirmation: bool = False

class SecurityManager:
    def __init__(self, policy: Dict[str, Any] | None = None) -> None:
        self.policy = policy or SECURITY

    def _match_any(self, scope: str, patterns: List[str]) -> bool:
        for p in patterns:
            if fnmatch(scope, p):
                return True
        return False

    def require(self, scope: str, *, text: str | None = None, confirmed: bool = False,
                requires_network: bool = False, **context: Any) -> None:
        pol = self.policy

        if self._match_any(scope, pol.get("denied_scopes", [])):
            self._audit("DENY", scope, "explicitly denied", context)
            raise SecurityError(f"Denied by policy: {scope}")

        allowed = pol.get("allowed_scopes")
        if allowed and not self._match_any(scope, allowed):
            self._audit("DENY", scope, "not in allowed_scopes", context)
            raise SecurityError(f"Scope not allowed: {scope}")

        if requires_network and not pol.get("network_allowed", False):
            self._audit("DENY", scope, "network not allowed (offline)", context)
            raise SecurityError("Network access is disabled by policy")

        confirm_scopes = pol.get("require_confirmation_scopes", [])
        need_confirm = self._match_any(scope, confirm_scopes)
        if not need_confirm and text:
            if policies.needs_confirmation(text):
                need_confirm = True

        if need_confirm and not confirmed:
            self._audit("HOLD", scope, "confirmation required", context)
            raise SecurityError("Confirmation required")

        self._audit("ALLOW", scope, "ok", context)

    def _audit(self, verdict: str, scope: str, reason: str, context: Dict[str, Any]) -> None:
        if not self.policy.get("audit_enabled", True):
            return
        safe_ctx = {k: v for k, v in context.items() if k in ("user", "resource", "hint", "length")}
        logger.info(f"SECURITY {verdict}|{scope}|{reason}|ctx={safe_ctx}")

security_manager = SecurityManager(SECURITY)
