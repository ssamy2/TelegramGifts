from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class ModelInfo:
    model_name: str
    attributes: Dict[str, Any]

@dataclass
class GiftPrices:
    floor_price_ton: Optional[float]
    portal_price_ton: Optional[float]
    getgems_price_ton: Optional[float]
    tgmrkt_price_ton: Optional[float]

@dataclass
class GiftDetail:
    full_name: str
    short_name: str
    regular_id: str
    prices: GiftPrices
    models: List[ModelInfo]
    custom_emoji_id: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GiftDetail':
        prices = GiftPrices(
            floor_price_ton=data.get('floor_price_ton'),
            portal_price_ton=data.get('portal_price_ton'),
            getgems_price_ton=data.get('getgems_price_ton'),
            tgmrkt_price_ton=data.get('tgmrkt_price_ton')
        )
        
        models = []
        for m in data.get('models', []):
            if isinstance(m, dict):
                model_name = m.get('name', 'Unknown')
                models.append(ModelInfo(model_name=model_name, attributes=m))
            else:
                models.append(ModelInfo(model_name=str(m), attributes={}))
                
        return cls(
            full_name=data.get('full_name', ''),
            short_name=data.get('short_name', ''),
            regular_id=str(data.get('regular_id', '')),
            prices=prices,
            models=models,
            custom_emoji_id=data.get('custom_emoji_id')
        )

@dataclass
class RegularGift:
    id: str
    short_name: str
    full_name: str
    type: str
    image_url: Optional[str]
    floor_price: Optional[str]
    supply: int
    is_active: bool
    count: int

    @classmethod
    def from_dict(cls, data: dict) -> 'RegularGift':
        return cls(
            id=str(data.get('id', '')),
            short_name=data.get('short_name', ''),
            full_name=data.get('full_name', ''),
            type=data.get('type', ''),
            image_url=data.get('image_url'),
            floor_price=data.get('floor_price'),
            supply=data.get('supply', 0),
            is_active=data.get('is_active', False),
            count=data.get('count', 0)
        )
