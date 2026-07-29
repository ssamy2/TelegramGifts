import unittest

from TelegramGifts.client import TelegramGifts


def make_client():
    client = TelegramGifts.__new__(TelegramGifts)
    client.BASE_RAW_URL = "https://example.test/assets"
    client._gifts_details = {
        "upgraded": [
            {
                "regular_id": "5839094187366024301",
                "short_name": "khabibs_papakha",
                "full_name": "Khabib's Papakha",
                "floor_price_ton": 12.5,
                "portal_price_ton": 12.5,
                "getgems_price_ton": 13.0,
                "tgmrkt_price_ton": 11.0,
                "custom_emoji_id": "emoji-upgraded",
                "models": [],
            }
        ],
        "unupgraded": [],
    }
    client._ss_data = [
        {
            "id": "5839094187366024301",
            "short_name": "Khabib's Papakha",
            "full_name": "Khabib's Papakha",
            "type": "REGULAR",
            "floor_price": "1.25",
            "supply": 10000,
            "is_active": True,
            "count": 10000,
        }
    ]
    client._aliases = {}
    client._upgraded_gifts = None
    client._unupgraded_gifts = None
    client._regular_gifts = None
    client._detail_by_id = {}
    client._detail_by_text = {}
    client._details_by_id = {}
    client._details_by_text = {}
    client._regular_by_id = {}
    client._regular_by_text = {}
    client._detail_type_by_id = {}
    client._build_indexes()
    return client


class TestSharedNameResolution(unittest.TestCase):
    def test_default_lookup_prefers_upgraded_for_shared_names(self):
        gift = make_client().get_gift("Khabib's Papakha")

        self.assertEqual(gift["type"], "UPGRADED")
        self.assertEqual(gift["short_name"], "khabibs_papakha")
        self.assertEqual(gift["custom_emoji_id"], "emoji-upgraded")

    def test_regular_lookup_can_be_requested_explicitly(self):
        gift = make_client().get_gift("Khabib's Papakha", gift_type="regular")

        self.assertEqual(gift["type"], "REGULAR")
        self.assertEqual(gift["short_name"], "Khabib's Papakha")
        self.assertEqual(gift["prices"]["floor_price"], 1.25)

    def test_both_lookup_returns_upgraded_and_regular(self):
        matches = make_client().get_gift("Khabib's Papakha", gift_type="both")

        self.assertEqual([gift["type"] for gift in matches], ["UPGRADED", "REGULAR"])

    def test_get_gift_matches_returns_empty_list_for_missing_name(self):
        self.assertEqual(make_client().get_gift_matches("missing"), [])


if __name__ == "__main__":
    unittest.main()
