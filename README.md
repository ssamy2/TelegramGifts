# TelegramGifts

> **A fast, offline-first Python library for fetching Telegram Gifts data, prices, and assets—no API key required.**

[![PyPI version](https://img.shields.io/pypi/v/TelegramGifts.svg)](https://pypi.org/project/TelegramGifts/)
[![GitHub stars](https://img.shields.io/github/stars/ssamy2/TelegramGifts.svg)](https://github.com/ssamy2/TelegramGifts/stargazers)
[![License](https://img.shields.io/github/license/ssamy2/TelegramGifts.svg)](https://github.com/ssamy2/TelegramGifts/blob/main/LICENSE)
[![Python version](https://img.shields.io/pypi/pyversions/TelegramGifts.svg)](https://pypi.org/project/TelegramGifts/)

## Why this library?
- **No API Key Needed:** Fetch comprehensive gift data without authenticating to the Telegram API.
- **Continuously Auto-Updated:** Data is served directly from a GitHub-hosted, automatically synchronized dataset.
- **Smart Local Caching:** Powered by ETag-based caching to ensure lightning-fast responses and zero rate limits.
- **Unified & Simple API:** Look up models, prices, custom emojis, and backdrops with a single, intuitive interface.

## Installation

```bash
pip install TelegramGifts
```

## Quick Start

```python
from TelegramGifts import TelegramGifts

# Initialize the library (auto-creates a smart cache)
gifts = TelegramGifts()

# Fetch comprehensive information about a gift by its ID or Name
info = gifts.get_gift("Artisan Brick")

print(f"Name: {info['full_name']}")
print(f"Custom Emoji ID: {info['custom_emoji_id']}")
print(f"Market Price: {info['prices']['tgmrkt_price_ton']} TON")
```

## Features

| Feature | Description |
|---------|-------------|
| **Upgraded & Regular Gifts** | Complete data for both upgraded NFT-like models and regular Telegram gifts. |
| **Market Prices** | Instant access to floor prices across Fragment, GetGems, and TGMrkt. |
| **Custom Emojis & Backdrops** | Retrieve hidden custom emoji IDs and rarity metrics for specific models. |
| **Asset Downloading** | Download high-quality WebP and TGS sticker animations locally with ease. |

## Usage Examples

### 1. Retrieve Upgraded Models and Prices
Easily extract model specific data such as prices, attributes, and custom emojis.

```python
from TelegramGifts import TelegramGifts

gifts = TelegramGifts()

# Fetch details for the 'Pro Gamer' model of the Artisan Brick gift
model = gifts.get_model_details("artisan_brick", "Pro Gamer")

if model:
    print(f"Model: {model['name']}")
    print(f"Price: {model['price_ton']} TON")
    print(f"Emoji ID: {model['custom_emoji_id']}")
    print(f"WebP Asset: {model['links']['webp']}")
```

### 2. Download Gift Assets Locally
Automate the downloading of gift animations for bots or localized rendering.

```python
# Downloads the TGS file for a specific gift into your cache folder
local_tgs_path = gifts.download_image("artisan_brick", ext="tgs")
print(f"Saved asset to: {local_tgs_path}")
```

### 3. Retrieve All Gifts and Floor Prices
Iterate over the entire catalog of available gifts seamlessly.

```python
# Fetch all regular gifts
regular_gifts = gifts.get_regular_gifts()
for gift in regular_gifts[:5]:
    print(f"{gift.full_name} | Supply: {gift.supply} | Floor: {gift.floor_price}")
```

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request to the repository. Before submitting, ensure that your code aligns with the existing architecture and passes all basic type checks.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author & Contact
- **Developer:** Samy Mahmoud
- **PyPI Username:** [Sami3d](https://pypi.org/user/Sami3d/)
- **Telegram:** [@Sami3d](https://t.me/Sami3d)
- **Email:** Samymheg@gmail.com

<!--
telegram gifts price api, telegram unique gifts python, telegram gift emoji backdrop, telegram gifts library no api key, telegram gift models fetching, getgems telegram gifts API, python telegram gift metadata
-->
