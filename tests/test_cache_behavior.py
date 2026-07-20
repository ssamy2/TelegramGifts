import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from TelegramGifts.cache import CacheManager


class DummyResponse:
    def __init__(self, data=None, content=b"", status_code=200, headers=None):
        self._data = data
        self._content = content
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._data

    def iter_content(self, chunk_size=8192):
        yield self._content


class TestCacheBehavior(unittest.TestCase):
    def test_default_cache_mode_clones_full_repo_on_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("TelegramGifts.cache.print") as printed:
                with patch("TelegramGifts.cache.subprocess.run") as git_run:
                    CacheManager(cache_dir=tmp)

            git_run.assert_called_once()
            self.assertIn("clone", git_run.call_args.args[0])
            self.assertNotIn("--sparse", git_run.call_args.args[0])
            printed.assert_called_once()

    def test_json_fetch_uses_disk_cache_within_ttl(self):
        with tempfile.TemporaryDirectory() as tmp:
            url = "https://raw.githubusercontent.com/ssamy2/TelegramGiftsAssests/main/Gifts_Details.json"
            response = DummyResponse({"upgraded": [], "unupgraded": []}, headers={"ETag": "abc"})

            with patch("TelegramGifts.cache.requests.get", return_value=response) as http_get:
                cache = CacheManager(cache_dir=tmp, ttl_seconds=3600, cache_mode="http")
                first = cache.fetch_github_file(url, "Gifts_Details.json")
                second = cache.fetch_github_file(url, "Gifts_Details.json")

            self.assertEqual(first, {"upgraded": [], "unupgraded": []})
            self.assertEqual(second, first)
            self.assertEqual(http_get.call_count, 1)
            self.assertTrue(list((Path(tmp) / "json").glob("*.json")))

    def test_asset_download_is_lazy_and_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            url = "https://raw.githubusercontent.com/ssamy2/TelegramGiftsAssests/main/webp/by_id/1.webp"
            response = DummyResponse(content=b"asset")

            with patch("TelegramGifts.cache.requests.get", return_value=response) as http_get:
                cache = CacheManager(
                    cache_dir=tmp,
                    cache_mode="http",
                    asset_min_interval_seconds=0,
                )
                first = cache.save_image(url, "1.webp", subfolder="webp")
                second = cache.save_image(url, "1.webp", subfolder="webp")

            self.assertEqual(first, second)
            self.assertEqual(http_get.call_count, 1)
            self.assertEqual(Path(first).read_bytes(), b"asset")

    def test_asset_download_threshold_promotes_to_full_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            response = DummyResponse(content=b"asset")
            urls = [
                "https://raw.githubusercontent.com/ssamy2/TelegramGiftsAssests/main/webp/by_id/1.webp",
                "https://raw.githubusercontent.com/ssamy2/TelegramGiftsAssests/main/tgs/by_id/2.tgs",
            ]

            with patch("TelegramGifts.cache.requests.get", return_value=response):
                with patch("TelegramGifts.cache.print"):
                    with patch("TelegramGifts.cache.subprocess.run") as git_run:
                        cache = CacheManager(
                            cache_dir=tmp,
                            cache_mode="http",
                            asset_min_interval_seconds=0,
                            asset_repo_threshold=2,
                        )
                        cache.save_image(urls[0], "1.webp", subfolder="webp")
                        cache.save_image(urls[1], "2.tgs", subfolder="tgs")

            clone_calls = [
                call
                for call in git_run.call_args_list
                if "clone" in call.args[0]
            ]
            self.assertEqual(len(clone_calls), 1)
            self.assertNotIn("--sparse", clone_calls[0].args[0])

    def test_sparse_repo_expands_when_asset_threshold_is_reached(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "TelegramGiftsAssests"
            repo_dir.mkdir()
            meta_file = Path(tmp) / "meta.json"
            meta_file.write_text(
                json.dumps(
                    {
                        "asset_download_count": 2,
                        "last_repo_pull": 20,
                        "repo_has_assets": False,
                    }
                ),
                encoding="utf-8",
            )
            url = "https://raw.githubusercontent.com/ssamy2/TelegramGiftsAssests/main/webp/by_id/1.webp"

            with patch("TelegramGifts.cache.time.time", return_value=20):
                with patch("TelegramGifts.cache.requests.get", return_value=DummyResponse(content=b"asset")):
                    with patch("TelegramGifts.cache.subprocess.run") as git_run:
                        cache = CacheManager(
                            cache_dir=tmp,
                            cache_mode="http",
                            asset_min_interval_seconds=0,
                            asset_repo_threshold=2,
                        )
                        cache.save_image(url, "1.webp", subfolder="webp")

            commands = [call.args[0] for call in git_run.call_args_list]
            self.assertIn(
                ["git", "-C", str(repo_dir), "sparse-checkout", "disable"],
                commands,
            )

    def test_git_mode_uses_ttl_for_pull_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "TelegramGiftsAssests"
            repo_dir.mkdir()
            meta_file = Path(tmp) / "meta.json"
            meta_file.write_text(json.dumps({"last_repo_pull": 1}), encoding="utf-8")

            with patch("TelegramGifts.cache.time.time", return_value=20):
                with patch("TelegramGifts.cache.print"):
                    with patch("TelegramGifts.cache.subprocess.run") as git_run:
                        CacheManager(cache_dir=tmp, ttl_seconds=10, cache_mode="git")

            commands = [call.args[0] for call in git_run.call_args_list]
            self.assertIn(["git", "-C", str(repo_dir), "pull", "--ff-only"], commands)


if __name__ == "__main__":
    unittest.main()
