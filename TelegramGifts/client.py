from typing import List, Optional, Dict, Union, Any
from .cache import CacheManager
from .types import GiftDetail, RegularGift
from .exceptions import InvalidExtensionError, GiftNotFoundError

class TelegramGifts:
    def __init__(
        self,
        repo_url: str = "https://raw.githubusercontent.com/ssamy2/TelegramGiftsAssests/main",
        cache_dir: Optional[str] = None,
        ttl_seconds: int = 600,
        enable_cache: bool = True
    ):
        self.BASE_RAW_URL = repo_url.rstrip('/')
        self.cache = CacheManager(cache_dir, ttl_seconds, enable_cache)
        self._gifts_details: Optional[dict] = None
        self._ss_data: Optional[list] = None

    def _load_data(self):
        """Loads and caches both main data files."""
        if self._gifts_details is None:
            self._gifts_details = self.cache.fetch_github_file(
                f"{self.BASE_RAW_URL}/Gifts_Details.json", 
                "Gifts_Details.json"
            )
            
        if self._ss_data is None:
            self._ss_data = self.cache.fetch_github_file(
                f"{self.BASE_RAW_URL}/ss.json", 
                "ss.json"
            )

    @property
    def raw_gifts_details(self) -> dict:
        self._load_data()
        return self._gifts_details or {}

    @property
    def raw_ss_data(self) -> list:
        self._load_data()
        return self._ss_data or []

    # --- Lists ---
    def get_upgraded_gifts(self) -> List[GiftDetail]:
        data = self.raw_gifts_details.get("upgraded", [])
        return [GiftDetail.from_dict(g) for g in data]

    def get_unupgraded_gifts(self) -> List[GiftDetail]:
        data = self.raw_gifts_details.get("unupgraded", [])
        return [GiftDetail.from_dict(g) for g in data]

    def get_regular_gifts(self) -> List[RegularGift]:
        return [RegularGift.from_dict(g) for g in self.raw_ss_data]
        
    def get_all_gifts_details(self) -> List[GiftDetail]:
        return self.get_upgraded_gifts() + self.get_unupgraded_gifts()

    # --- Single Gift Properties ---
    def _find_raw_gift_data(self, identifier: str) -> tuple[Optional[RegularGift], Optional[GiftDetail]]:
        identifier_str = str(identifier).lower()
        regular_gift = None
        detail_gift = None
        
        # Search regular gifts
        for g in self.get_regular_gifts():
            if str(g.id) == str(identifier) or g.short_name.lower() == identifier_str or g.full_name.lower() == identifier_str:
                regular_gift = g
                break
                
        # Search details
        for g in self.get_all_gifts_details():
            if str(g.regular_id) == str(identifier) or g.short_name.lower() == identifier_str or g.full_name.lower() == identifier_str:
                detail_gift = g
                break
                
        return regular_gift, detail_gift

    def get_gift(self, identifier: str) -> Optional[dict]:
        """
        Returns a comprehensive dictionary containing properties, prices, type, and download links for a gift.
        Accepts the gift ID, short_name, or full_name.
        """
        regular, detail = self._find_raw_gift_data(identifier)

        if not regular and not detail:
            return None

        gift_id = detail.regular_id if detail else (regular.id if regular else "")
        
        # Determine if it's in upgraded or unupgraded list
        gift_type = "UNKNOWN"
        if detail:
            # Check if it's upgraded or unupgraded
            for g in self.get_upgraded_gifts():
                if str(g.regular_id) == str(gift_id):
                    gift_type = "UPGRADED"
                    break
            if gift_type == "UNKNOWN":
                gift_type = "UNUPGRADED"
        elif regular:
            gift_type = "REGULAR"

        info = {
            "id": gift_id,
            "short_name": detail.short_name if detail else (regular.short_name if regular else ""),
            "full_name": detail.full_name if detail else (regular.full_name if regular else ""),
            "type": gift_type,
        }

        if gift_type == "UPGRADED":
            info["supply"] = regular.supply if regular else None
            info["prices"] = {
                "floor_price_ton": detail.prices.floor_price_ton if detail else None,
                "portal_price_ton": detail.prices.portal_price_ton if detail else None,
                "getgems_price_ton": detail.prices.getgems_price_ton if detail else None,
                "tgmrkt_price_ton": detail.prices.tgmrkt_price_ton if detail else None,
            }
            info["links"] = {
                "webp": self.get_image_url_by_id(gift_id, "webp"),
                "tgs": self.get_image_url_by_id(gift_id, "tgs")
            }
            if detail and detail.custom_emoji_id:
                info["custom_emoji_id"] = detail.custom_emoji_id
        elif gift_type == "UNUPGRADED":
            info["prices"] = {
                "floor_price_ton": detail.prices.floor_price_ton if detail else None
            }
            info["links"] = {
                "webp": self.get_image_url_by_id(gift_id, "webp"),
                "tgs": self.get_image_url_by_id(gift_id, "tgs")
            }
            if detail and detail.custom_emoji_id:
                info["custom_emoji_id"] = detail.custom_emoji_id
        elif gift_type == "REGULAR":
            info["supply"] = regular.supply if regular else None
            info["prices"] = {
                "floor_price": float(regular.floor_price) if regular and regular.floor_price else None
            }
            info["links"] = {
                "webp": self.get_image_url_by_id(gift_id, "webp")
            }

        return info

    # --- Prices ---
    def get_upgraded_price(self, identifier: str, source: str = "tgmrkt") -> Optional[float]:
        """
        source can be: 'floor', 'portal', 'getgems', 'tgmrkt'
        """
        _, detail = self._find_raw_gift_data(identifier)
        if not detail:
            return None
            
        if source == "floor":
            return detail.prices.floor_price_ton
        elif source == "portal":
            return detail.prices.portal_price_ton
        elif source == "getgems":
            return detail.prices.getgems_price_ton
        elif source == "tgmrkt":
            return detail.prices.tgmrkt_price_ton
        return None

    def get_unupgraded_price(self, identifier: str) -> Optional[float]:
        """Returns the floor price of the regular/unupgraded version if available"""
        regular, _ = self._find_raw_gift_data(identifier)
        if regular and regular.floor_price:
            return float(regular.floor_price)
        return None

    # --- Images and Resources ---
    def get_image_url(self, short_name: str, ext: str = "webp") -> str:
        """
        Returns the raw GitHub URL for the image or tgs by name.
        ext: 'webp' or 'tgs'
        """
        if ext not in ['webp', 'tgs']:
            raise InvalidExtensionError("Extension must be 'webp' or 'tgs'")
        return f"{self.BASE_RAW_URL}/{ext}/by_name/{short_name}.{ext}"

    def get_image_url_by_id(self, gift_id: str, ext: str = "webp") -> str:
        """
        Returns the raw GitHub URL for the image or tgs by ID.
        ext: 'webp' or 'tgs'
        """
        if ext not in ['webp', 'tgs']:
            raise InvalidExtensionError("Extension must be 'webp' or 'tgs'")
        return f"{self.BASE_RAW_URL}/{ext}/by_id/{gift_id}.{ext}"

    def download_image(self, short_name: str, ext: str = "webp") -> str:
        """
        Downloads and caches the image/tgs file by name and returns its local absolute path.
        """
        url = self.get_image_url(short_name, ext)
        filename = f"{short_name}.{ext}"
        return self.cache.save_image(url, filename, subfolder=ext)

    def download_image_by_id(self, gift_id: str, ext: str = "webp") -> str:
        """
        Downloads and caches the image/tgs file by ID and returns its local absolute path.
        """
        url = self.get_image_url_by_id(gift_id, ext)
        filename = f"{gift_id}.{ext}"
        return self.cache.save_image(url, filename, subfolder=ext)

    # --- Models and Attributes ---
    def get_gift_prices_data(self, short_name: str) -> Optional[dict]:
        """Fetches the prices.json for a specific gift models"""
        url = f"{self.BASE_RAW_URL}/models/{short_name}/prices.json"
        filename = f"models_{short_name}_prices.json"
        try:
            return self.cache.fetch_github_file(url, filename)
        except Exception:
            return None

    def get_gift_config_data(self, short_name: str) -> Optional[list]:
        """Fetches the config.json for a specific gift models"""
        url = f"{self.BASE_RAW_URL}/models/{short_name}/config.json"
        filename = f"models_{short_name}_config.json"
        try:
            return self.cache.fetch_github_file(url, filename)
        except Exception:
            return None

    def get_model_details(self, identifier: str, model_name: Optional[str] = None) -> Union[list, dict, None]:
        """
        Returns the configuration details for models of an upgraded gift, including 'custom_emoji_id'.
        Injects real URLs for webp/tgs and the price of the model.
        If model_name is provided, returns the dict for that specific model.
        Otherwise, returns a list of all models' details.
        """
        short_name = self._resolve_upgraded_short_name(identifier)
        if not short_name:
            return None
            
        config_data = self.get_gift_config_data(short_name)
        if not config_data:
            return None
            
        prices_data = self.get_attribute_price(short_name, "models") or {}

        def _enrich_model(m_dict):
            m_copy = m_dict.copy()
            raw_name = m_copy.get("name", "")
            
            # Find the price matching the name
            price = None
            for p_name, p_val in prices_data.items():
                if p_name.lower().replace(" ", "_") == raw_name.lower().replace(" ", "_"):
                    price = p_val
                    break
                    
            m_copy["price_ton"] = price
            m_copy["links"] = {
                "webp": self.get_model_image_url(short_name, raw_name, "webp"),
                "tgs": self.get_model_image_url(short_name, raw_name, "tgs")
            }
            # Remove raw github repo paths
            m_copy.pop("webp_path", None)
            m_copy.pop("tgs_path", None)
            
            return m_copy

        if not model_name:
            return [_enrich_model(m) for m in config_data]
            
        model_name_lower = model_name.lower().replace(" ", "_")
        for model in config_data:
            if model.get("name", "").lower() == model_name_lower:
                return _enrich_model(model)
                
        return None

    def _resolve_upgraded_short_name(self, identifier: str) -> Optional[str]:
        """Helper to resolve an ID or full name to a short_name for upgraded gifts"""
        for g in self.get_upgraded_gifts():
            if str(identifier) in (g.regular_id, g.short_name, g.full_name):
                return g.short_name
        return None

    def get_attribute_price(
        self, 
        identifier: str, 
        attribute_type: Optional[str] = None, 
        item_name: Optional[str] = None
    ) -> Union[dict, float, None]:
        """
        Returns prices for attributes (models, backdrops, symbols) of an upgraded gift.
        identifier: Can be the ID, short_name, or full_name of the upgraded gift.
        attribute_type: 'models', 'backdrops', or 'symbols'. If None, returns all categories.
        item_name: The specific name of the attribute. If None, returns all items in the category.
        """
        short_name = self._resolve_upgraded_short_name(identifier)
        if not short_name:
            return None
            
        prices = self.get_gift_prices_data(short_name)
        if not prices:
            return None
            
        if not attribute_type:
            return prices
            
        if attribute_type not in prices:
            return None
            
        if not item_name:
            return prices[attribute_type]
            
        return prices[attribute_type].get(item_name)

    def get_model_image_url(self, short_name: str, model_short_name: str, ext: str = "webp") -> str:
        """Returns the URL of a specific model image/tgs"""
        if ext not in ['webp', 'tgs']:
            raise InvalidExtensionError("Extension must be 'webp' or 'tgs'")
        return f"{self.BASE_RAW_URL}/models/{short_name}/{model_short_name}.{ext}"

    def download_model_image(self, short_name: str, model_short_name: str, ext: str = "webp") -> str:
        """Downloads a specific model image/tgs and returns the local path"""
        url = self.get_model_image_url(short_name, model_short_name, ext)
        filename = f"{short_name}_{model_short_name}.{ext}"
        return self.cache.save_image(url, filename, subfolder=ext)
