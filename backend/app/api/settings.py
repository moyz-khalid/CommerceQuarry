from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from uuid import UUID, uuid4
from typing import List

router = APIRouter()

_settings: dict[str, dict] = {}


class UserSettings(BaseModel):
    default_scan_mode: str = "category"
    max_products: int = 100
    min_profit: float = 5.0
    min_roi: float = 20.0


@router.get("/settings/{user_id}", response_model=UserSettings)
def get_settings(user_id: str):
    return _settings.get(user_id, UserSettings())


@router.put("/settings/{user_id}", response_model=UserSettings)
def update_settings(user_id: str, settings: UserSettings):
    _settings[user_id] = settings.dict()
    return settings
