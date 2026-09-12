from dataclasses import dataclass, field

from .items import ItemDefinition, ItemStack


@dataclass
class Inventory:
    capacity_slots: int
    stacks: list[ItemStack] = field(default_factory=list)

    def total_items(self) -> int:
        return sum(stack.quantity for stack in self.stacks)

    def add_item(self, definition: ItemDefinition, quantity: int) -> int:
        quantity = max(0, quantity)
        remaining = quantity

        for stack in self.stacks:
            if stack.item_id == definition.item_id and stack.quantity < definition.max_stack:
                space = definition.max_stack - stack.quantity
                to_add = min(space, remaining)
                stack.quantity += to_add
                remaining -= to_add
                if remaining == 0:
                    return 0

        while remaining > 0 and len(self.stacks) < self.capacity_slots:
            to_add = min(definition.max_stack, remaining)
            self.stacks.append(ItemStack(item_id=definition.item_id, quantity=to_add))
            remaining -= to_add

        return remaining

    def remove_item(self, item_id: str, quantity: int) -> bool:
        quantity = max(0, quantity)
        if quantity == 0:
            return True

        available = sum(stack.quantity for stack in self.stacks if stack.item_id == item_id)
        if available < quantity:
            return False

        to_remove = quantity
        for stack in list(self.stacks):
            if stack.item_id != item_id:
                continue
            removing = min(stack.quantity, to_remove)
            stack.quantity -= removing
            to_remove -= removing
            if stack.quantity == 0:
                self.stacks.remove(stack)
            if to_remove == 0:
                break

        return True
