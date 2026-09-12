from dataclasses import dataclass, field

from .enums import ZombieState


@dataclass
class ZombieEntity:
    zombie_id: str
    state: ZombieState = ZombieState.IDLE
    state_history: list[ZombieState] = field(default_factory=lambda: [ZombieState.IDLE])

    def transition(self, new_state: ZombieState) -> None:
        if self.state == new_state:
            return
        self.state = new_state
        self.state_history.append(new_state)

    def tick(
        self,
        *,
        can_see_player: bool,
        in_attack_range: bool,
        heard_noise: bool,
        has_last_known_position: bool,
    ) -> ZombieState:
        if can_see_player and self.state != ZombieState.ATTACK:
            self.transition(ZombieState.DETECT_PLAYER)
            self.transition(ZombieState.CHASE)

        if self.state == ZombieState.CHASE and in_attack_range:
            self.transition(ZombieState.ATTACK)
        elif self.state == ZombieState.ATTACK and not in_attack_range:
            self.transition(ZombieState.CHASE)

        if not can_see_player and self.state in {ZombieState.CHASE, ZombieState.ATTACK}:
            self.transition(ZombieState.LOSE_TARGET)
            self.transition(ZombieState.SEARCH if has_last_known_position else ZombieState.RETURN_TO_WANDER)

        if not can_see_player and heard_noise and self.state in {ZombieState.IDLE, ZombieState.WANDER}:
            self.transition(ZombieState.INVESTIGATE)

        if self.state in {ZombieState.IDLE, ZombieState.RETURN_TO_WANDER}:
            self.transition(ZombieState.WANDER)

        if self.state == ZombieState.SEARCH and not has_last_known_position:
            self.transition(ZombieState.RETURN_TO_WANDER)
            self.transition(ZombieState.WANDER)

        return self.state
