from __future__ import annotations


class GPMRuntimeUnavailableError(Exception):
    """Raised when no callable GPM LLM runtime is available.

    Never includes tokens or credentials in any field.
    Callers decide whether to skip or hard-fail based on context.
    """

    def __init__(
        self,
        reason: str,
        attempted_runtime: str,
        provider: str = "qwen",
        safe_message: str = "",
        operator_action_required: bool = True,
    ) -> None:
        self.reason = reason
        self.attempted_runtime = attempted_runtime
        self.provider = provider
        self.safe_message = safe_message
        self.operator_action_required = operator_action_required
        super().__init__(safe_message or reason)

    def to_status(self) -> dict:
        """Return a loggable status dict. Never includes tokens or credentials."""
        return {
            "runtime_status": "unavailable",
            "attempted_runtime": self.attempted_runtime,
            "provider": self.provider,
            "reason": self.reason,
            "operator_action_required": self.operator_action_required,
            "safe_message": self.safe_message,
        }
