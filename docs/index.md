# TelegramGifts Complete API Reference

Welcome to the full documentation for `TelegramGifts`, a Python SDK for fetching Telegram Gift data. This library requires no API keys and keeps a local git-backed cache of JSON, WebP, and TGS assets by default.

---

## 1. Client Initialization

The main entry point for the library is the `TelegramGifts` class.

```python
from TelegramGifts import TelegramGifts

gifts = TelegramGifts(
    repo_url="https://raw.githubusercontent.com/ssamy2/TelegramGiftsAssests/main",
    cache_dir="~/.telegramgifts_cache", # Optional: Specify a custom cache directory
    ttl_seconds=600,                    # Cache Time-To-Live in seconds (10 minutes default)
    enable_cache=True,                  # Set to False to force real-time network requests
    cache_mode="git",                   # Default: keep a local repo checkout
    asset_mode="repo",                  # Default: read assets from the local repo
    git_pull_interval=None,             # Optional override; defaults to ttl_seconds
    asset_min_interval_seconds=0.2,     # Gentle spacing between asset downloads
    asset_repo_threshold=10             # Used only by lightweight HTTP/lazy mode
)
```

---

## 2. Cache and Asset Loading

The default cache is designed to avoid many individual GitHub asset requests:

- On first run, the assets repository is cloned locally.
- The library prints `TelegramGifts: Downloading gift files for the first time...` while the first download is starting.
- JSON files, WebP images, and `.tgs` animations are read from the local repo when available.
- Repo updates use `git pull --ff-only`.
- `ttl_seconds` controls the default git pull interval and automatically refreshes
  in-memory gift data in long-running `TelegramGifts` instances.

For users who want a lighter first run:

```python
gifts = TelegramGifts(cache_mode="http", asset_mode="lazy")
```

In lightweight mode, JSON files are cached over HTTP and assets are downloaded individually on demand. If `asset_repo_threshold` is greater than `0`, the cache promotes itself to a local repo-backed cache after that many network asset downloads.

## 3. Comprehensive Gift Data

### `get_gift(identifier: str, gift_type: str = "auto") -> Union[dict, list, None]`
The most powerful method. It dynamically resolves the identifier and returns a rich dictionary containing all details.
**Arguments:**
- `identifier`: The gift's ID (e.g., `"6005797617768858105"`), short name (e.g., `"artisan_brick"`), or full name (e.g., `"Artisan Brick"`).
- `gift_type`: Optional lookup mode. Use `"auto"` (default) to preserve legacy behavior and prefer upgraded/unupgraded entries, `"upgraded"`, `"unupgraded"`, `"regular"`, `"both"`, or `"all"`.

When a visible Telegram gift name exists in both upgraded and regular forms, `get_gift(identifier)` returns the upgraded/unupgraded entry first by default. This keeps existing model, custom emoji, and attribute lookups working. To retrieve both entries together, use:

```python
matches = gifts.get_gift("Khabib's Papakha", gift_type="both")
# or
matches = gifts.get_gift_matches("Khabib's Papakha")
```

**Returns:**
```python
{
    "id": "6005797617768858105",
    "short_name": "artisan_brick",
    "full_name": "Artisan Brick",
    "type": "UPGRADED", # "UPGRADED", "UNUPGRADED", or "REGULAR"
    "supply": 10000,
    "prices": {
        "floor_price_ton": 51.75,
        "portal_price_ton": 51.75,
        "getgems_price_ton": 59.0,
        "tgmrkt_price_ton": 49.41
    },
    "links": {
        "webp": "https://.../by_id/6005797617768858105.webp",
        "tgs": "https://.../by_id/6005797617768858105.tgs"
    },
    "custom_emoji_id": "5886603410492366880"
}
```

### `get_gift_matches(identifier: str) -> List[dict]`
Returns every matching entry for an identifier as a list. Upgraded/unupgraded entries are returned first, followed by the regular gift when one exists.

---

## 4. Models and Attributes (For Upgraded Gifts)

### `get_model_details(identifier: str, model_name: Optional[str] = None) -> Union[list, dict, None]`
Fetches intricate details for upgraded models, injecting real-time market prices and WebP/TGS links.
**Arguments:**
- `identifier`: Gift identifier.
- `model_name`: Exact name of the model (case-insensitive). If omitted, returns a list of all models.
**Example Output:**
```python
{
  'name': 'pro_gamer', 
  'rarity_permille': 2.0, 
  'custom_emoji_id': '5881734231838695549', 
  'model_id': '5195366267158033241', 
  'price_ton': 110.0,
  'links': {'webp': '...', 'tgs': '...'}
}
```

### `get_attribute_price(identifier: str, attribute_type: Optional[str] = None, item_name: Optional[str] = None) -> Union[dict, float, None]`
Query specific prices for underlying NFT attributes.
**Arguments:**
- `attribute_type`: Can be `"models"`, `"backdrops"`, or `"symbols"`.
- `item_name`: The specific attribute name (e.g., `"Diamond"`, `"Amber"`).

---

## 5. Bulk Data Retrieval (Lists)

These methods return lists of Python Dataclasses (`GiftDetail` and `RegularGift`).

### `get_upgraded_gifts() -> List[GiftDetail]`
Returns a list of all **Upgraded** (NFT) gifts.

### `get_unupgraded_gifts() -> List[GiftDetail]`
Returns a list of all **Unupgraded** gifts (gifts with limited supply that haven't been minted yet).

### `get_regular_gifts() -> List[RegularGift]`
Returns a list of all **Regular** gifts (standard Telegram gifts).

### `get_all_gifts_details() -> List[GiftDetail]`
Returns a combined list of all upgraded and unupgraded gift details.

### `raw_gifts_details() -> dict`
Returns the raw parsed JSON dictionary from `Gifts_Details.json`.
**Example Output Structure:**
```python
{
  "upgraded": [
    {
      "full_name": "Artisan Brick",
      "short_name": "artisan_brick",
      "regular_id": "6005797617768858105",
      "custom_emoji_id": "5886603410492366880",
      "floor_price_ton": 51.75,
      "models": [ ... ]
    }
  ],
  "unupgraded": [ ... ]
}
```

### `raw_ss_data() -> list`
Returns the raw parsed JSON list from `ss.json`.
**Example Output Structure:**
```python
[
  {
    "id": "5956308547863052791",
    "short_name": "Trojan Horse",
    "full_name": "Trojan Horse",
    "type": "REGULAR",
    "floor_price": "0",
    "supply": 10000
  }
]
```

---

## 6. Market Prices

### `get_upgraded_price(identifier: str, source: str = "tgmrkt") -> Optional[float]`
Fetches the floor price for an upgraded gift from a specific marketplace.
**Arguments:**
- `source`: `"floor"` (overall lowest), `"portal"`, `"getgems"`, or `"tgmrkt"`.

### `get_unupgraded_price(identifier: str) -> Optional[float]`
Returns the standard floor price of an unupgraded gift.

---

## 7. Image and Asset Management

### `get_image_url(identifier: str, ext: str = "webp") -> str`
### `get_image_url_by_id(gift_id: str, ext: str = "webp") -> str`
Returns the direct GitHub URL for the image or animation. Valid extensions: `"webp"`, `"tgs"`.

### `download_image(identifier: str, ext: str = "webp") -> str`
Downloads the asset by name, caches it locally safely (using `.tmp` atomic writes to prevent corruption), and returns the **absolute local path**.
**Returns:** `/home/user/.telegramgifts_cache/webp/artisan_brick.webp`

Assets are repo-backed by default: the first run creates a local checkout, and future calls return local paths when the file is available. In lightweight `cache_mode="http", asset_mode="lazy"` mode, assets are downloaded on demand and cached individually.

### `download_image_by_id(gift_id: str, ext: str = "webp") -> str`
Downloads the asset by its numeric ID and returns the absolute local path.

### `download_model_image(short_name: str, model_short_name: str, ext: str = "webp") -> str`
Downloads the specific variant asset for a model (e.g., `pro_gamer.webp` for `artisan_brick`) and returns the local path.

---

## 8. Data Structures (Types)

The library uses Dataclasses for structured data.

### `GiftDetail` (Upgraded & Unupgraded)
- `full_name` (str)
- `short_name` (str)
- `regular_id` (str)
- `custom_emoji_id` (Optional[str])
- `prices` (`GiftPrices` object)
- `models` (List of `ModelInfo` objects)

### `RegularGift`
- `id` (str)
- `short_name` (str)
- `full_name` (str)
- `type` (str)
- `supply` (int)
- `floor_price` (str)
- `is_active` (bool)

---

## 9. Custom Exceptions

Handle errors safely by importing from `TelegramGifts.exceptions`.

```python
from TelegramGifts.exceptions import GitHubFetchError, CacheError

try:
    gifts.download_image("artisan_brick")
except GitHubFetchError as e:
    print(f"Internet connection issue: {e}")
except CacheError as e:
    print(f"Filesystem/Cache issue: {e}")
```

- **`TelegramGiftsError`**: Base class for all library errors.
- **`GitHubFetchError`**: Raised on HTTP/Network failures when pulling data.
- **`CacheError`**: Raised when disk operations fail or cache is misconfigured.
- **`GiftNotFoundError`**: Raised when searching for a gift fails.
- **`InvalidExtensionError`**: Raised if a file extension other than `webp` or `tgs` is requested.
