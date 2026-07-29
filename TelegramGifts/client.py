import threading
import time
from typing import List, Optional, Dict, Union, Any, Tuple
from .cache import CacheManager
from .types import GiftDetail, RegularGift
from .exceptions import InvalidExtensionError, GiftNotFoundError
from .identity import DEFAULT_ALIAS_MANIFEST, resolve_alias

class TelegramGifts:
    def __init__(
        self,
        repo_url: str = "https://raw.githubusercontent.com/ssamy2/TelegramGiftsAssests/main",
        cache_dir: Optional[str] = None,
        ttl_seconds: int = 600,
        enable_cache: bool = True,
        cache_mode: str = "git",
        asset_mode: str = "repo",
        git_pull_interval: Optional[int] = None,
        asset_min_interval_seconds: float = 0.2,
        asset_repo_threshold: int = 10,
    ):
        self.BASE_RAW_URL = repo_url.rstrip('/')
        self.cache = CacheManager(
            cache_dir,
            ttl_seconds,
            enable_cache,
            repo_url=self.BASE_RAW_URL,
            cache_mode=cache_mode,
            asset_mode=asset_mode,
            git_pull_interval=git_pull_interval,
            asset_min_interval_seconds=asset_min_interval_seconds,
            asset_repo_threshold=asset_repo_threshold,
        )
        self._gifts_details: Optional[dict] = None
        self._ss_data: Optional[list] = None
        self._aliases: Optional[dict] = None
        self._upgraded_gifts: Optional[List[GiftDetail]] = None
        self._unupgraded_gifts: Optional[List[GiftDetail]] = None
        self._regular_gifts: Optional[List[RegularGift]] = None
        self._detail_by_id: Dict[str, GiftDetail] = {}
        self._detail_by_text: Dict[str, GiftDetail] = {}
        self._details_by_id: Dict[str, List[Tuple[str, GiftDetail]]] = {}
        self._details_by_text: Dict[str, List[Tuple[str, GiftDetail]]] = {}
        self._regular_by_id: Dict[str, RegularGift] = {}
        self._regular_by_text: Dict[str, RegularGift] = {}
        self._detail_type_by_id: Dict[str, str] = {}
        self._data_loaded_at: Optional[float] = None
        self._data_lock = threading.RLock()

    def _load_data(self):
        """Loads and caches both main data files."""
        with self._data_lock:
            current_time = time.time()
            cache = getattr(self, "cache", None)
            if (
                self._data_loaded_at is not None
                and getattr(cache, "enable_cache", False)
                and (current_time - self._data_loaded_at)
                >= getattr(cache, "ttl_seconds", 0)
            ):
                self._invalidate_loaded_data()

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

            if self._aliases is None:
                try:
                    aliases = self.cache.fetch_github_file(
                        f"{self.BASE_RAW_URL}/{DEFAULT_ALIAS_MANIFEST}",
                        DEFAULT_ALIAS_MANIFEST,
                    )
                    self._aliases = aliases if isinstance(aliases, dict) else {}
                except Exception:
                    self._aliases = {}

            if self._upgraded_gifts is None:
                self._build_indexes()

            self._data_loaded_at = current_time

    def _invalidate_loaded_data(self) -> None:
        self._gifts_details = None
        self._ss_data = None
        self._aliases = None
        self._upgraded_gifts = None
        self._unupgraded_gifts = None
        self._regular_gifts = None
        self._detail_by_id = {}
        self._detail_by_text = {}
        self._details_by_id = {}
        self._details_by_text = {}
        self._regular_by_id = {}
        self._regular_by_text = {}
        self._detail_type_by_id = {}
        self._data_loaded_at = None

    def _normalize_key(self, value: Any) -> str:
        return str(value).strip().lower()

    def _detail_priority(self, gift_type: str) -> int:
        return {"UPGRADED": 0, "UNUPGRADED": 1}.get(gift_type, 99)

    def _set_preferred_detail(
        self,
        index: Dict[str, GiftDetail],
        key: str,
        gift: GiftDetail,
        gift_type: str,
    ) -> None:
        current = index.get(key)
        if current is None:
            index[key] = gift
            return

        current_type = self._detail_type_by_id.get(str(current.regular_id), "UNUPGRADED")
        if self._detail_priority(gift_type) < self._detail_priority(current_type):
            index[key] = gift

    def _build_indexes(self):
        upgraded_data = self._gifts_details.get("upgraded", []) if isinstance(self._gifts_details, dict) else []
        unupgraded_data = self._gifts_details.get("unupgraded", []) if isinstance(self._gifts_details, dict) else []
        regular_data = self._ss_data if isinstance(self._ss_data, list) else []

        self._upgraded_gifts = [GiftDetail.from_dict(g) for g in upgraded_data]
        self._unupgraded_gifts = [GiftDetail.from_dict(g) for g in unupgraded_data]
        self._regular_gifts = [RegularGift.from_dict(g) for g in regular_data]
        self._detail_by_id = {}
        self._detail_by_text = {}
        self._details_by_id = {}
        self._details_by_text = {}
        self._regular_by_id = {}
        self._regular_by_text = {}
        self._detail_type_by_id = {}

        for gift_type, gifts in (
            ("UPGRADED", self._upgraded_gifts),
            ("UNUPGRADED", self._unupgraded_gifts),
        ):
            for gift in gifts:
                if gift.regular_id:
                    id_key = str(gift.regular_id)
                    current_type = self._detail_type_by_id.get(id_key)
                    if current_type is None or self._detail_priority(gift_type) < self._detail_priority(current_type):
                        self._detail_type_by_id[id_key] = gift_type
                    self._details_by_id.setdefault(id_key, []).append((gift_type, gift))
                    self._set_preferred_detail(self._detail_by_id, id_key, gift, gift_type)
                for key in (gift.short_name, gift.full_name):
                    normalized = self._normalize_key(key)
                    if normalized:
                        self._details_by_text.setdefault(normalized, []).append((gift_type, gift))
                        self._set_preferred_detail(self._detail_by_text, normalized, gift, gift_type)

        for gift in self._regular_gifts:
            if gift.id:
                self._regular_by_id[str(gift.id)] = gift
            for key in (gift.short_name, gift.full_name):
                normalized = self._normalize_key(key)
                if normalized:
                    self._regular_by_text[normalized] = gift

    @property
    def raw_gifts_details(self) -> dict:
        self._load_data()
        return self._gifts_details or {}

    @property
    def raw_ss_data(self) -> list:
        self._load_data()
        return self._ss_data or []

    @property
    def raw_aliases(self) -> dict:
        self._load_data()
        return self._aliases or {}

    # --- Lists ---
    def get_upgraded_gifts(self) -> List[GiftDetail]:
        self._load_data()
        return list(self._upgraded_gifts or [])

    def get_unupgraded_gifts(self) -> List[GiftDetail]:
        self._load_data()
        return list(self._unupgraded_gifts or [])

    def get_regular_gifts(self) -> List[RegularGift]:
        self._load_data()
        return list(self._regular_gifts or [])
        
    def get_all_gifts_details(self) -> List[GiftDetail]:
        return self.get_upgraded_gifts() + self.get_unupgraded_gifts()

    # --- Single Gift Properties ---
    def _candidate_identifiers(self, identifier: str) -> List[str]:
        if not identifier:
            return []

        original = str(identifier)
        aliased = resolve_alias(original, self.raw_aliases)
        candidates = [aliased, original]
        return list(dict.fromkeys(candidates))

    def _find_raw_gift_data(self, identifier: str) -> Tuple[Optional[RegularGift], Optional[GiftDetail]]:
        candidates = self._candidate_identifiers(identifier)
        if not candidates:
            return None, None

        regular_gift = None
        detail_gift = None

        for candidate in candidates:
            identifier_str = self._normalize_key(candidate)
            detail_gift = self._detail_by_id.get(str(candidate)) or self._detail_by_text.get(identifier_str)
            if detail_gift:
                break

        for candidate in candidates:
            identifier_str = self._normalize_key(candidate)
            regular_gift = self._regular_by_id.get(str(candidate)) or self._regular_by_text.get(identifier_str)
            if regular_gift:
                break
                
        return regular_gift, detail_gift

    def _find_detail_matches(self, identifier: str) -> List[Tuple[str, GiftDetail]]:
        candidates = self._candidate_identifiers(identifier)
        matches: List[Tuple[str, GiftDetail]] = []
        seen = set()

        for candidate in candidates:
            identifier_str = self._normalize_key(candidate)
            candidate_matches = []
            candidate_matches.extend(self._details_by_id.get(str(candidate), []))
            candidate_matches.extend(self._details_by_text.get(identifier_str, []))

            for gift_type, gift in candidate_matches:
                seen_key = (gift_type, gift.regular_id, gift.short_name)
                if seen_key in seen:
                    continue
                seen.add(seen_key)
                matches.append((gift_type, gift))

        return sorted(matches, key=lambda item: self._detail_priority(item[0]))

    def _format_detail_gift(
        self,
        detail: GiftDetail,
        gift_type: str,
        regular: Optional[RegularGift] = None,
    ) -> dict:
        info = {
            "id": detail.regular_id,
            "short_name": detail.short_name,
            "full_name": detail.full_name,
            "type": gift_type,
        }

        if gift_type == "UPGRADED":
            info["supply"] = regular.supply if regular else None
            info["prices"] = {
                "floor_price_ton": detail.prices.floor_price_ton,
                "portal_price_ton": detail.prices.portal_price_ton,
                "getgems_price_ton": detail.prices.getgems_price_ton,
                "tgmrkt_price_ton": detail.prices.tgmrkt_price_ton,
            }
        else:
            info["prices"] = {
                "floor_price_ton": detail.prices.floor_price_ton
            }

        info["links"] = {
            "webp": self.get_image_url_by_id(detail.regular_id, "webp"),
            "tgs": self.get_image_url_by_id(detail.regular_id, "tgs")
        }
        if detail.custom_emoji_id:
            info["custom_emoji_id"] = detail.custom_emoji_id

        return info

    def _format_regular_gift(self, regular: RegularGift) -> dict:
        return {
            "id": regular.id,
            "short_name": regular.short_name,
            "full_name": regular.full_name,
            "type": "REGULAR",
            "supply": regular.supply,
            "prices": {
                "floor_price": float(regular.floor_price) if regular.floor_price else None
            },
            "links": {
                "webp": self.get_image_url_by_id(regular.id, "webp")
            }
        }

    def get_gift_matches(self, identifier: str) -> List[dict]:
        """
        Returns every matching gift for a shared identifier.
        Upgraded/unupgraded entries are returned first, followed by the regular gift.
        """
        regular, _ = self._find_raw_gift_data(identifier)
        detail_matches = self._find_detail_matches(identifier)

        matches = [
            self._format_detail_gift(gift, gift_type, regular)
            for gift_type, gift in detail_matches
        ]
        if regular:
            matches.append(self._format_regular_gift(regular))
        return matches

    def get_gift(self, identifier: str, gift_type: str = "auto") -> Union[dict, List[dict], None]:
        """
        Returns a comprehensive dictionary containing properties, prices, type, and download links for a gift.
        Accepts the gift ID, short_name, or full_name.

        gift_type:
        - "auto" (default): preserve legacy behavior and prefer upgraded/unupgraded data.
        - "upgraded": return only upgraded data.
        - "unupgraded": return only unupgraded data.
        - "regular": return only regular data.
        - "both" or "all": return every matching entry as a list.
        """
        requested_type = self._normalize_key(gift_type or "auto")
        if requested_type in {"both", "all"}:
            matches = self.get_gift_matches(identifier)
            return matches or None

        regular, detail = self._find_raw_gift_data(identifier)

        if not regular and not detail:
            return None

        if requested_type == "regular":
            return self._format_regular_gift(regular) if regular else None

        if requested_type in {"upgraded", "unupgraded"}:
            target_type = requested_type.upper()
            for detail_type, detail_match in self._find_detail_matches(identifier):
                if detail_type == target_type:
                    return self._format_detail_gift(detail_match, detail_type, regular)
            return None

        if detail:
            detail_type = self._detail_type_by_id.get(str(detail.regular_id), "UNUPGRADED")
            return self._format_detail_gift(detail, detail_type, regular)

        return self._format_regular_gift(regular) if regular else None

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
    def _get_gift_prices_data(self, short_name: str) -> Optional[dict]:
        """Fetches the prices.json for a specific gift models"""
        url = f"{self.BASE_RAW_URL}/models/{short_name}/prices.json"
        filename = f"models_{short_name}_prices.json"
        try:
            return self.cache.fetch_github_file(url, filename)
        except Exception:
            return None

    def _get_gift_config_data(self, short_name: str) -> Optional[list]:
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
            
        config_data = self._get_gift_config_data(short_name)
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
            if model.get("name", "").lower().replace(" ", "_") == model_name_lower:
                return _enrich_model(model)
                
        return None

    def _resolve_upgraded_short_name(self, identifier: str) -> Optional[str]:
        """Helper to resolve an ID or full name to a short_name for upgraded gifts"""
        for candidate in self._candidate_identifiers(identifier):
            identifier_str = self._normalize_key(candidate)
            gift = self._detail_by_id.get(str(candidate)) or self._detail_by_text.get(identifier_str)
            if gift and self._detail_type_by_id.get(str(gift.regular_id)) == "UPGRADED":
                return gift.short_name
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
            
        prices = self._get_gift_prices_data(short_name)
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
