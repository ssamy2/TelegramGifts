import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional
import requests.exceptions
from .exceptions import GitHubFetchError, CacheError

class CacheManager:
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        ttl_seconds: int = 600,
        enable_cache: bool = True
    ):
        self.enable_cache = enable_cache
        self.ttl_seconds = ttl_seconds
        
        if cache_dir is None:
            self.cache_dir = Path.home() / ".telegramgifts_cache"
        else:
            self.cache_dir = Path(cache_dir)
            
        self.meta_file = self.cache_dir / "meta.json"
        
        if self.enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._init_meta()

    def _init_meta(self):
        if not self.meta_file.exists():
            self._save_meta({})

    def _load_meta(self) -> Dict[str, Any]:
        try:
            with open(self.meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_meta(self, meta: Dict[str, Any]):
        with open(self.meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta, f)

    def fetch_github_file(self, url: str, filename: str) -> Optional[dict]:
        """
        Fetches a JSON file from GitHub using ETag to avoid rate limits and unnecessary downloads.
        Returns the parsed JSON dictionary.
        """
        if not self.enable_cache:
            try:
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as e:
                raise GitHubFetchError(f"Failed to fetch data from GitHub: {str(e)}")

        meta = self._load_meta()
        file_meta = meta.get(filename, {})
        last_check = file_meta.get("last_check", 0)
        etag = file_meta.get("etag", "")
        
        file_path = self.cache_dir / filename
        current_time = time.time()

        # Use cache if within TTL and file exists
        if (current_time - last_check) < self.ttl_seconds and file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass # Fallback to re-download if file is corrupted

        headers = {}
        if etag and file_path.exists():
            headers['If-None-Match'] = etag

        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 304: # Not Modified
                file_meta["last_check"] = current_time
                meta[filename] = file_meta
                self._save_meta(meta)
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
                    
            response.raise_for_status()
            
            # Save new file and ETag
            data = response.json()
            tmp_file_path = str(file_path) + ".tmp"
            with open(tmp_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            os.rename(tmp_file_path, file_path)
                
            new_etag = response.headers.get('ETag')
            if new_etag:
                file_meta["etag"] = new_etag
            file_meta["last_check"] = current_time
            meta[filename] = file_meta
            self._save_meta(meta)
            
            return data
            
        except requests.exceptions.RequestException as e:
            # On failure (like no internet), fallback to cache if available
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            raise GitHubFetchError(f"Network error while fetching {filename}: {str(e)}")

    def save_image(self, url: str, filename: str, subfolder: str = "images") -> str:
        """
        Downloads an image/tgs file if not cached, and returns the absolute local path.
        """
        if not self.enable_cache:
            raise CacheError("Image saving requires caching to be enabled.")
            
        target_dir = self.cache_dir / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = target_dir / filename
        
        if file_path.exists():
            return str(file_path)
            
        try:
            response = requests.get(url, stream=True, timeout=15)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise GitHubFetchError(f"Network error while downloading image: {str(e)}")
        
        tmp_file_path = str(file_path) + ".tmp"
        try:
            with open(tmp_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            os.rename(tmp_file_path, file_path)
        except Exception as e:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
            raise e
                
        return str(file_path)
