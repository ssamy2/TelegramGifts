from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple


DEFAULT_ALIAS_MANIFEST = "Gift_Aliases.json"


def canonical_short_name(name: str) -> str:
    """
    Convert Telegram's official gift/collection name into the local canonical
    short name.

    The rule intentionally mirrors the legacy asset convention:
    keep letters and spaces only, remove everything else, then replace spaces
    with underscores and lowercase the result.
    """
    if not name:
        return ""

    kept = []
    for char in str(name):
        if char.isalpha() or char.isspace():
            kept.append(char)

    words = "".join(kept).strip().split()
    return "_".join(words).lower()


def normalize_alias_key(value: str) -> str:
    """Normalize a user-facing alias into the manifest key form."""
    if not value:
        return ""

    value = str(value).strip().lower().replace("-", "_")
    value = "_".join(value.split())
    while "__" in value:
        value = value.replace("__", "_")
    return value.strip("_")


def resolve_alias(identifier: str, aliases: Mapping[str, str]) -> str:
    """Return the canonical alias target when one exists."""
    if not identifier:
        return identifier

    raw = str(identifier)
    candidates = [
        raw,
        raw.lower(),
        normalize_alias_key(raw),
        canonical_short_name(raw),
    ]
    for candidate in candidates:
        if candidate in aliases:
            return aliases[candidate]
    return raw


def load_aliases(root: Path, manifest_name: str = DEFAULT_ALIAS_MANIFEST) -> Dict[str, str]:
    import json

    path = Path(root) / manifest_name
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"{manifest_name} must contain a JSON object")

    aliases = {}
    for alias, target in data.items():
        alias_key = normalize_alias_key(str(alias))
        target_key = normalize_alias_key(str(target))
        if alias_key and target_key and alias_key != target_key:
            aliases[alias_key] = target_key
    return aliases


@dataclass(frozen=True)
class GiftIdentity:
    regular_id: str
    full_name: str
    short_name: str
    custom_emoji_id: Optional[str] = None
    aliases: Tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_telegram(
        cls,
        telegram_gift: Mapping[str, Any],
        aliases: Optional[Iterable[str]] = None,
    ) -> "GiftIdentity":
        """Resolve a Telegram gift payload into stable local identity."""
        full_name = (
            telegram_gift.get("upgraded_name")
            or telegram_gift.get("collection_name")
            or telegram_gift.get("full_name")
            or telegram_gift.get("name")
            or telegram_gift.get("title")
            or ""
        )
        regular_id = (
            telegram_gift.get("regular_id")
            or telegram_gift.get("id")
            or telegram_gift.get("gift_id")
            or ""
        )

        canonical = canonical_short_name(str(full_name))
        normalized_aliases = []
        for alias in aliases or ():
            alias_key = normalize_alias_key(str(alias))
            if alias_key and alias_key != canonical:
                normalized_aliases.append(alias_key)

        return cls(
            regular_id=str(regular_id),
            full_name=str(full_name),
            short_name=canonical,
            custom_emoji_id=(
                str(telegram_gift["custom_emoji_id"])
                if telegram_gift.get("custom_emoji_id") is not None
                else None
            ),
            aliases=tuple(dict.fromkeys(normalized_aliases)),
        )

    def asset_paths(self) -> Dict[str, str]:
        return {
            "tgs_by_id": f"tgs/by_id/{self.regular_id}.tgs",
            "tgs_by_name": f"tgs/by_name/{self.short_name}.tgs",
            "webp_by_id": f"webp/by_id/{self.regular_id}.webp",
            "webp_by_name": f"webp/by_name/{self.short_name}.webp",
            "models": f"models/{self.short_name}",
            "backdrops": f"backdrops/{self.short_name}",
            "patterns": f"patterns/{self.short_name}",
            "symbols": f"symbols/{self.short_name}",
        }


def alias_manifest_for(identities: Iterable[GiftIdentity]) -> Dict[str, str]:
    manifest: Dict[str, str] = {}
    for identity in identities:
        for alias in identity.aliases:
            if alias != identity.short_name:
                manifest[alias] = identity.short_name
    return dict(sorted(manifest.items()))
