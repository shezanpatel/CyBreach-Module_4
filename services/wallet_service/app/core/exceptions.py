class WalletNotFound(Exception):
    """Raised when a requested wallet cannot be found."""
    pass


class InsufficientBalance(Exception):
    """Raised when an account has insufficient funds for a transaction."""
    pass


class IdempotencyKeyReuseError(Exception):
    """
    Raised when an idempotency key is reused with a
    different request payload.
    """
    pass


class WalletPaused(Exception):
    """
    Raised when an operation is attempted on a paused wallet.
    """
    pass