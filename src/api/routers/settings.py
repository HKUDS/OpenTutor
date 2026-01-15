"""
Settings API Router (Simplified)
================================

Manages basic UI settings: theme, language, sidebar customization.
Configuration for LLM/Embedding/TTS/Search is handled by the unified config service.
"""

import json
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# Settings file path for UI preferences (stored in settings folder with other configs)
SETTINGS_FILE = (
    Path(__file__).parent.parent.parent.parent / "data" / "user" / "settings" / "interface.json"
)

# Default sidebar navigation order
DEFAULT_SIDEBAR_NAV_ORDER = {
    "start": ["/", "/history", "/knowledge", "/notebook"],
    "learnResearch": ["/question", "/solver", "/guide", "/ideagen", "/research", "/co_writer"],
}

# Default UI settings
DEFAULT_UI_SETTINGS = {
    "theme": "light",
    "language": "en",
    "sidebar_description": "✨ Data Intelligence Lab @ HKU",
    "sidebar_nav_order": DEFAULT_SIDEBAR_NAV_ORDER,
}


class SidebarNavOrder(BaseModel):
    start: List[str]
    learnResearch: List[str]


class UISettings(BaseModel):
    theme: Literal["light", "dark"] = "light"
    language: Literal["zh", "en"] = "en"
    sidebar_description: Optional[str] = None
    sidebar_nav_order: Optional[SidebarNavOrder] = None


class ThemeUpdate(BaseModel):
    theme: Literal["light", "dark"]


class LanguageUpdate(BaseModel):
    language: Literal["zh", "en"]


class SidebarDescriptionUpdate(BaseModel):
    description: str


class SidebarNavOrderUpdate(BaseModel):
    nav_order: SidebarNavOrder


def load_ui_settings() -> dict:
    """Load UI-specific settings from json file"""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                saved = json.load(f)
                return {**DEFAULT_UI_SETTINGS, **saved}
        except Exception:
            pass
    return DEFAULT_UI_SETTINGS.copy()


def save_ui_settings(settings: dict):
    """Save UI settings"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


@router.get("")
async def get_settings():
    """Get UI settings."""
    return {"ui": load_ui_settings()}


@router.put("/theme")
async def update_theme(update: ThemeUpdate):
    """Update UI theme"""
    current_ui = load_ui_settings()
    current_ui["theme"] = update.theme
    save_ui_settings(current_ui)
    return {"theme": update.theme}


@router.put("/language")
async def update_language(update: LanguageUpdate):
    """Update UI language"""
    current_ui = load_ui_settings()
    current_ui["language"] = update.language
    save_ui_settings(current_ui)
    return {"language": update.language}


@router.put("/ui")
async def update_ui_settings(update: UISettings):
    """Update all UI settings"""
    current_ui = load_ui_settings()
    update_dict = update.model_dump(exclude_none=True)
    current_ui.update(update_dict)
    save_ui_settings(current_ui)
    return current_ui


@router.post("/reset")
async def reset_settings():
    """Reset UI settings to default"""
    save_ui_settings(DEFAULT_UI_SETTINGS)
    return DEFAULT_UI_SETTINGS


@router.get("/themes")
async def get_themes():
    """Get available theme list"""
    return {
        "themes": [
            {"id": "light", "name": "Light"},
            {"id": "dark", "name": "Dark"},
        ]
    }


@router.get("/sidebar")
async def get_sidebar_settings():
    """Get sidebar customization settings"""
    current_ui = load_ui_settings()
    return {
        "description": current_ui.get(
            "sidebar_description", DEFAULT_UI_SETTINGS["sidebar_description"]
        ),
        "nav_order": current_ui.get("sidebar_nav_order", DEFAULT_UI_SETTINGS["sidebar_nav_order"]),
    }


@router.put("/sidebar/description")
async def update_sidebar_description(update: SidebarDescriptionUpdate):
    """Update sidebar description"""
    current_ui = load_ui_settings()
    current_ui["sidebar_description"] = update.description
    save_ui_settings(current_ui)
    return {"description": update.description}


@router.put("/sidebar/nav-order")
async def update_sidebar_nav_order(update: SidebarNavOrderUpdate):
    """Update sidebar navigation order"""
    current_ui = load_ui_settings()
    current_ui["sidebar_nav_order"] = update.nav_order.model_dump()
    save_ui_settings(current_ui)
    return {"nav_order": update.nav_order.model_dump()}
