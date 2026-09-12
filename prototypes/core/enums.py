from enum import Enum


class ItemCategory(str, Enum):
    WEAPON = "weapon"
    AMMO = "ammo"
    FOOD = "food"
    WATER = "water"
    MEDICAL = "medical"
    CRAFTING = "crafting"
    QUEST = "quest"
    CLOTHING = "clothing"
    EQUIPMENT = "equipment"
    MISC = "misc"


class ZombieState(str, Enum):
    IDLE = "idle"
    WANDER = "wander"
    INVESTIGATE = "investigate"
    DETECT_PLAYER = "detect_player"
    CHASE = "chase"
    ATTACK = "attack"
    SEARCH = "search"
    LOSE_TARGET = "lose_target"
    RETURN_TO_WANDER = "return_to_wander"
