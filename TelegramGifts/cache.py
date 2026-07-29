import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import requests.exceptions

from .exceptions import CacheError, GitHubFetchError


DEFAULT_ASSETS_REPO_URL = "https://github.com/ssamy2/TelegramGiftsAssests.git"
DEFAULT_RAW_URL = "https://raw.githubusercontent.com/ssamy2/TelegramGiftsAssests/main"
DEFAULT_ALIAS_MANIFEST = "Gift_Aliases.json"


class CacheManager:
    """
    Local cache for TelegramGifts data.

    The default mode keeps a full local checkout of the assets repository so
    repeated JSON/image/TGS reads come from disk after the first run.
    """

    VALID_CACHE_MODES = {"http", "git", "auto"}
    VALID_ASSET_MODES = {"lazy", "repo"}

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        ttl_seconds: int = 600,
        enable_cache: bool = True,
        repo_url: str = DEFAULT_RAW_URL,
        cache_mode: str = "git",
        asset_mode: str = "repo",
        git_pull_interval: Optional[int] = None,
        asset_min_interval_seconds: float = 0.2,
        asset_repo_threshold: int = 10,
    ):
        self.enable_cache = enable_cache
        self.ttl_seconds = max(0, int(ttl_seconds))
        self.repo_url = repo_url.rstrip("/")
        self.cache_mode = cache_mode
        self.asset_mode = asset_mode
        self.git_pull_interval = (
            max(0, int(git_pull_interval))
            if git_pull_interval is not None
            else self.ttl_seconds
        )
        self.asset_min_interval_seconds = max(0.0, float(asset_min_interval_seconds))
        self.asset_repo_threshold = max(0, int(asset_repo_threshold))

        if self.cache_mode not in self.VALID_CACHE_MODES:
            raise CacheError(
                f"cache_mode must be one of {sorted(self.VALID_CACHE_MODES)}"
            )
        if self.asset_mode not in self.VALID_ASSET_MODES:
            raise CacheError(
                f"asset_mode must be one of {sorted(self.VALID_ASSET_MODES)}"
            )

        if cache_dir is None:
            self.cache_dir = Path.home() / ".telegramgifts_cache"
        else:
            self.cache_dir = Path(cache_dir).expanduser()

        self.meta_file = self.cache_dir / "meta.json"
        self.json_dir = self.cache_dir / "json"
        self.assets_dir = self.cache_dir / "assets"
        self.repo_dir = self.cache_dir / "TelegramGiftsAssests"
        self._asset_lock = threading.Lock()
        self._last_asset_download = 0.0

        if self.enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.json_dir.mkdir(parents=True, exist_ok=True)
            self.assets_dir.mkdir(parents=True, exist_ok=True)
            self._init_meta()
            if self.cache_mode == "git":
                self._ensure_repo(include_assets=self.asset_mode == "repo", strict=True)

    def _init_meta(self):
        if not self.meta_file.exists():
            self._save_meta({})

    def _load_meta(self) -> Dict[str, Any]:
        try:
            with self.meta_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_meta(self, meta: Dict[str, Any]):
        tmp_path = self.meta_file.with_suffix(".json.tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2, sort_keys=True)
            os.replace(tmp_path, self.meta_file)
        except OSError as exc:
            raise CacheError(f"Failed to write cache metadata: {exc}")

    def _cache_key(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _json_cache_path(self, url: str, filename: str) -> Path:
        suffix = Path(filename).suffix or ".json"
        return self.json_dir / f"{self._cache_key(url)}{suffix}"

    def _asset_cache_path(self, url: str, filename: str, subfolder: str) -> Path:
        suffix = Path(filename).suffix
        stem = Path(filename).stem or self._cache_key(url)
        return self.cache_dir / subfolder / f"{stem}{suffix}"

    def _repo_clone_url(self) -> str:
        if "raw.githubusercontent.com" in self.repo_url:
            parts = self.repo_url.split("/")
            if len(parts) >= 5:
                owner = parts[3]
                repo = parts[4]
                return f"https://github.com/{owner}/{repo}.git"
        return DEFAULT_ASSETS_REPO_URL

    def _ensure_repo(self, include_assets: bool = False, strict: bool = False) -> bool:
        if not self.enable_cache:
            return False

        meta = self._load_meta()
        last_pull = meta.get("last_repo_pull", 0)
        current_time = time.time()

        if not self.repo_dir.exists():
            print("TelegramGifts: Downloading gift files for the first time...")
            clone_cmd = [
                "git",
                "clone",
                "--depth",
                "1",
                self._repo_clone_url(),
                str(self.repo_dir),
            ]
            if not include_assets:
                clone_cmd[2:2] = ["--filter=blob:none", "--sparse"]

            try:
                subprocess.run(
                    clone_cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if not include_assets:
                    subprocess.run(
                        [
                            "git",
                            "-C",
                            str(self.repo_dir),
                            "sparse-checkout",
                            "set",
                            "Gifts_Details.json",
                            "ss.json",
                            DEFAULT_ALIAS_MANIFEST,
                        ],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                meta["last_repo_pull"] = current_time
                meta["repo_has_assets"] = include_assets
                self._save_meta(meta)
                return True
            except Exception as exc:
                meta["last_repo_error"] = str(exc)
                self._save_meta(meta)
                if strict:
                    raise CacheError(f"Failed to clone asset repository: {exc}")
                return False
        else:
            if include_assets and not meta.get("repo_has_assets", False):
                try:
                    subprocess.run(
                        [
                            "git",
                            "-C",
                            str(self.repo_dir),
                            "sparse-checkout",
                            "disable",
                        ],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    meta["repo_has_assets"] = True
                    self._save_meta(meta)
                except Exception as exc:
                    meta["last_repo_error"] = str(exc)
                    self._save_meta(meta)
                    if strict:
                        raise CacheError(f"Failed to expand asset repository: {exc}")
                    return False

        if (current_time - last_pull) >= self.git_pull_interval:
            try:
                subprocess.run(
                    ["git", "-C", str(self.repo_dir), "pull", "--ff-only"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                meta["last_repo_pull"] = current_time
                meta.pop("last_repo_error", None)
                if include_assets:
                    meta["repo_has_assets"] = True
                self._save_meta(meta)
                return True
            except Exception as exc:
                meta["last_repo_error"] = str(exc)
                self._save_meta(meta)
                if strict:
                    raise CacheError(f"Failed to update asset repository: {exc}")
                return False

        return True

    def _get_local_repo_path(self, url: str) -> Optional[Path]:
        repo_prefix = f"{self.repo_url}/"
        if url.startswith(repo_prefix):
            rel_path = url[len(repo_prefix) :]
            return self.repo_dir / rel_path
        return None

    def _read_json_file(self, path: Path) -> Optional[dict]:
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, (dict, list)) else None
        except (OSError, json.JSONDecodeError):
            return None

    def _fetch_json_http(self, url: str, filename: str) -> Optional[dict]:
        cache_path = self._json_cache_path(url, filename)
        meta = self._load_meta() if self.enable_cache else {}
        json_meta = meta.setdefault("json", {})
        entry = json_meta.get(url, {})
        current_time = time.time()

        if self.enable_cache and cache_path.exists():
            fetched_at = entry.get("fetched_at", 0)
            if (current_time - fetched_at) <= self.ttl_seconds:
                cached = self._read_json_file(cache_path)
                if cached is not None:
                    return cached

        headers = {}
        if self.enable_cache:
            if entry.get("etag"):
                headers["If-None-Match"] = entry["etag"]
            if entry.get("last_modified"):
                headers["If-Modified-Since"] = entry["last_modified"]

        try:
            resp = requests.get(url, timeout=15, headers=headers)
            if resp.status_code == 304 and self.enable_cache and cache_path.exists():
                entry["fetched_at"] = current_time
                json_meta[url] = entry
                self._save_meta(meta)
                cached = self._read_json_file(cache_path)
                if cached is not None:
                    return cached

            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            if self.enable_cache and cache_path.exists():
                cached = self._read_json_file(cache_path)
                if cached is not None:
                    return cached
            raise GitHubFetchError(f"Failed to fetch data from GitHub: {e}")
        except ValueError as e:
            raise GitHubFetchError(f"GitHub response is not valid JSON: {e}")

        if self.enable_cache:
            tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
            try:
                with tmp_path.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
                os.replace(tmp_path, cache_path)
            except OSError as exc:
                raise CacheError(f"Failed to write JSON cache: {exc}")

            json_meta[url] = {
                "path": cache_path.name,
                "etag": resp.headers.get("ETag"),
                "last_modified": resp.headers.get("Last-Modified"),
                "fetched_at": current_time,
            }
            self._save_meta(meta)

        return data

    def fetch_github_file(self, url: str, filename: str) -> Optional[dict]:
        """
        Fetch a JSON file using the configured cache.

        In the default HTTP mode this downloads only the requested JSON file.
        In git mode it first tries the local repository, then falls back to HTTP.
        In auto mode it uses an existing local repository if present.
        """
        if self.enable_cache and self.cache_mode in {"git", "auto"}:
            if self.cache_mode == "git":
                self._ensure_repo()
            local_file = self._get_local_repo_path(url)
            if local_file and local_file.exists():
                cached = self._read_json_file(local_file)
                if cached is not None:
                    return cached

        return self._fetch_json_http(url, filename)

    def _wait_for_asset_slot(self):
        if self.asset_min_interval_seconds <= 0:
            return

        with self._asset_lock:
            now = time.time()
            wait_for = self.asset_min_interval_seconds - (
                now - self._last_asset_download
            )
            if wait_for > 0:
                time.sleep(wait_for)
            self._last_asset_download = time.time()

    def _asset_repo_should_promote(self) -> bool:
        if not self.enable_cache:
            return False
        if self.asset_repo_threshold <= 0:
            return False
        meta = self._load_meta()
        if self.repo_dir.exists() and meta.get("repo_has_assets", False):
            return True

        return meta.get("asset_download_count", 0) >= self.asset_repo_threshold

    def _record_asset_download(self) -> int:
        if not self.enable_cache or self.asset_repo_threshold <= 0:
            return 0

        meta = self._load_meta()
        meta["asset_download_count"] = int(meta.get("asset_download_count", 0)) + 1
        self._save_meta(meta)
        return meta["asset_download_count"]

    def save_image(self, url: str, filename: str, subfolder: str = "images") -> str:
        """
        Lazily download and cache an image/tgs file, returning its local path.

        Assets are never downloaded during client initialization in the default
        configuration. Each asset is fetched once and then reused from disk.
        """
        if self._asset_repo_should_promote():
            self._ensure_repo(include_assets=True, strict=False)

        if (self.enable_cache and self.cache_mode in {"git", "auto"}) or self.repo_dir.exists():
            local_file = self._get_local_repo_path(url)
            if local_file and local_file.exists():
                return str(local_file)

        file_path = self._asset_cache_path(url, filename, subfolder)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if self.enable_cache and file_path.exists() and file_path.stat().st_size > 0:
            return str(file_path)

        tmp_file_path = str(file_path) + ".tmp"
        try:
            self._wait_for_asset_slot()
            response = requests.get(url, stream=True, timeout=15)
            response.raise_for_status()
            with open(tmp_file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            os.replace(tmp_file_path, file_path)
            download_count = self._record_asset_download()
            if download_count >= self.asset_repo_threshold > 0:
                self._ensure_repo(include_assets=True, strict=False)
            return str(file_path)
        except requests.exceptions.RequestException as e:
            raise GitHubFetchError(f"Network error while downloading asset: {e}")
        except OSError as e:
            raise CacheError(f"Failed to write downloaded asset: {e}")
        finally:
            try:
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
            except OSError:
                pass
