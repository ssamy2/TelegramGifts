class TelegramGiftsError(Exception):
    """Base exception for all TelegramGifts errors."""
    pass

class GiftNotFoundError(TelegramGiftsError):
    """Raised when a gift cannot be found by its identifier."""
    pass

class GitHubFetchError(TelegramGiftsError):
    """Raised when there is a network error while fetching data from GitHub."""
    pass

class CacheError(TelegramGiftsError):
    """Raised when there is an issue writing to or reading from the local cache."""
    pass

class InvalidExtensionError(TelegramGiftsError):
    """Raised when an invalid file extension is provided (e.g. not webp or tgs)."""
    pass
