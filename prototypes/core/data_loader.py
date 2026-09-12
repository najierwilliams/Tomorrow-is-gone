import json
from pathlib import Path

from .enums import ItemCategory
from .items import ItemDefinition
from .loot import LootEntry, LootTable


def load_item_definitions(path: Path) -> dict[str, ItemDefinition]:
    payload = json.loads(path.read_text())
    definitions: dict[str, ItemDefinition] = {}
    for item in payload["items"]:
        definition = ItemDefinition(
            item_id=item["item_id"],
            name=item["name"],
            category=ItemCategory(item["category"]),
            max_stack=item.get("max_stack", 1),
            weight=item.get("weight", 0.0),
        )
        definitions[definition.item_id] = definition
    return definitions


def load_loot_tables(path: Path) -> dict[str, LootTable]:
    payload = json.loads(path.read_text())
    tables: dict[str, LootTable] = {}
    for table in payload["tables"]:
        entries = [
            LootEntry(
                item_id=entry["item_id"],
                chance=entry["chance"],
                min_qty=entry.get("min_qty", 1),
                max_qty=entry.get("max_qty", 1),
            )
            for entry in table["entries"]
        ]
        tables[table["table_id"]] = LootTable(table_id=table["table_id"], entries=entries)
    return tables
