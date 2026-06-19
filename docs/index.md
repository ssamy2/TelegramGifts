# TelegramGifts API Reference

Welcome to the full documentation for `TelegramGifts`, your offline-first solution for fetching Telegram Gift data.

## `TelegramGifts` Client

The main class you interact with.

### Initialization

```python
from TelegramGifts import TelegramGifts

gifts = TelegramGifts(
    repo_url="https://raw.githubusercontent.com/ssamy2/TelegramGiftsAssests/main",
    cache_dir=None, # Automatically resolved to ~/.telegramgifts_cache
    ttl_seconds=600, 
    enable_cache=True
)
```

### Methods

#### `get_gift(identifier: str) -> Optional[dict]`
The most powerful method. Fetches all known data about a gift.
**Arguments:**
- `identifier`: The gift's ID, short name, or full name.
**Returns:** A dictionary containing the ID, type, prices, links, and custom emoji ID.

#### `get_model_details(identifier: str, model_name: Optional[str] = None) -> Union[list, dict, None]`
Fetches intricate details for upgraded models.
**Arguments:**
- `identifier`: Gift identifier.
- `model_name`: Exact name of the model (case-insensitive). If omitted, returns all models.

#### `get_attribute_price(identifier: str, attribute_type: Optional[str] = None, item_name: Optional[str] = None) -> Union[dict, float, None]`
Query specific prices for attributes.
**Arguments:**
- `attribute_type`: 'models', 'backdrops', or 'symbols'.

#### `download_image(identifier: str, ext: str = "webp") -> str`
Downloads a gift asset locally.
**Arguments:**
- `identifier`: Gift identifier.
- `ext`: Format, either 'webp' or 'tgs'.
**Returns:** Absolute path to the locally cached file.

### Custom Exceptions
All exceptions inherit from `TelegramGiftsError`.
- `CacheError`: Raised when disk writes fail.
- `GitHubFetchError`: Raised on network errors.
- `InvalidExtensionError`: Raised when providing formats other than `webp` or `tgs`.
