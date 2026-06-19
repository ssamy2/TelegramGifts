from TelegramGifts import TelegramGifts

def test_gifts():
    print("Initializing TelegramGifts...")
    # ttl_seconds=0 forces it to check HTTP headers immediately
    gifts = TelegramGifts(ttl_seconds=0)

    print("\n--- Upgraded Gifts ---")
    upgraded = gifts.get_upgraded_gifts()
    print(f"Total upgraded gifts: {len(upgraded)}")
    if upgraded:
        print(f"First upgraded gift: {upgraded[0].full_name} | TGMrkt Price: {upgraded[0].prices.tgmrkt_price_ton} TON")

    print("\n--- Regular Gifts ---")
    regular = gifts.get_regular_gifts()
    print(f"Total regular gifts: {len(regular)}")
    if regular:
        print(f"First regular gift: {regular[0].full_name} | Supply: {regular[0].supply}")

    print("\n--- Specific Price ---")
    price = gifts.get_upgraded_price("artisan_brick", "tgmrkt")
    print(f"Artisan Brick TGMrkt Price: {price} TON")

    print("\n--- Full Info By Identifier ---")
    info = gifts.get_gift("Artisan Brick")
    if info:
        print(f"ID: {info['id']}")
        print(f"Name: {info['full_name']} (Type: {info['type']})")
        if "custom_emoji_id" in info:
            print(f"Emoji ID: {info['custom_emoji_id']}")
        print(f"Prices: {info['prices']}")
        print(f"Links: {info['links']}")
    
    local_path_tgs = gifts.download_image("artisan_brick", "tgs")
    print(f"Artisan Brick TGS Path: {local_path_tgs}")

    print("\n--- Model & Backdrop Prices ---")
    model_price = gifts.get_attribute_price("Artisan Brick", "models", "Diamond")
    print(f"Artisan Brick (by name) - Diamond Model Price: {model_price}")
    
    backdrop_price = gifts.get_attribute_price("6005797617768858105", "backdrops", "Amber")
    print(f"Artisan Brick (by ID) - Amber Backdrop Price: {backdrop_price}")

    all_models = gifts.get_attribute_price("artisan_brick", "models")
    if all_models:
        print(f"Artisan Brick has {len(all_models)} models available.")

    print("\n--- Model Images ---")
    model_img_url = gifts.get_model_image_url("artisan_brick", "diamond", "tgs")
    print(f"Diamond Model TGS URL: {model_img_url}")
    
    local_model = gifts.download_model_image("artisan_brick", "diamond", "tgs")
    print(f"Diamond Model Local Path: {local_model}")

if __name__ == "__main__":
    test_gifts()
