"""Game state model — PlayerState and GameState dataclasses."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Buff:
    name: str
    effect: str        # reduce_damage, hot (heal over time)
    value: int
    duration: int      # Remaining turns

    def tick(self) -> bool:
        """Decrease duration. Returns True if expired."""
        self.duration -= 1
        return self.duration <= 0

    def to_dict(self) -> dict:
        return {"name": self.name, "effect": self.effect,
                "value": self.value, "duration": self.duration}


@dataclass
class Debuff:
    name: str
    effect: str        # dot, increase_damage_taken, increase_miss, chakra_drain
    value: int
    duration: int

    def tick(self) -> bool:
        self.duration -= 1
        return self.duration <= 0

    def to_dict(self) -> dict:
        return {"name": self.name, "effect": self.effect,
                "value": self.value, "duration": self.duration}


@dataclass
class PlayerState:
    player_id: str
    name: str
    hp: int = 100
    max_hp: int = 100
    chakra: int = 100
    max_chakra: int = 100
    buffs: list[Buff] = field(default_factory=list)
    debuffs: list[Debuff] = field(default_factory=list)
    cooldowns: dict[str, int] = field(default_factory=dict)  # jutsu_name → turns left
    shadow_clone_active: bool = False  # Clone is out
    is_alive: bool = True

    def clamp_hp(self) -> None:
        self.hp = max(0, min(self.hp, self.max_hp))
        if self.hp <= 0:
            self.is_alive = False

    def clamp_chakra(self) -> None:
        self.chakra = max(0, min(self.chakra, self.max_chakra))

    def get_miss_bonus(self) -> float:
        """Extra miss % from debuffs (increase_miss effect)."""
        return sum(d.value / 100.0 for d in self.debuffs if d.effect == "increase_miss")

    def get_damage_reduction(self) -> int:
        """Flat damage reduction from buffs (reduce_damage effect)."""
        return sum(b.value for b in self.buffs if b.effect == "reduce_damage")

    def get_extra_damage_taken(self) -> int:
        """Extra damage taken from debuffs (increase_damage_taken effect)."""
        return sum(d.value for d in self.debuffs if d.effect == "increase_damage_taken")

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "chakra": self.chakra,
            "max_chakra": self.max_chakra,
            "buffs": [b.to_dict() for b in self.buffs],
            "debuffs": [d.to_dict() for d in self.debuffs],
            "cooldowns": dict(self.cooldowns),
            "shadow_clone_active": self.shadow_clone_active,
            "is_alive": self.is_alive,
        }


@dataclass
class GameState:
    players: list[PlayerState] = field(default_factory=list)
    active_player_idx: int = 0  # 0 or 1
    turn_number: int = 1
    buffer: list[str] = field(default_factory=list)
    game_over: bool = False
    winner: str | None = None
    last_action: dict[str, Any] | None = None

    @property
    def active_player(self) -> PlayerState:
        return self.players[self.active_player_idx]

    @property
    def inactive_player(self) -> PlayerState:
        return self.players[1 - self.active_player_idx]

    def switch_turn(self) -> None:
        self.active_player_idx = 1 - self.active_player_idx
        self.turn_number += 1
        self.buffer.clear()

    def check_game_over(self) -> bool:
        for p in self.players:
            if not p.is_alive:
                self.game_over = True
                self.winner = self.players[1 - self.players.index(p)].player_id
                return True
        return False

    def to_dict(self, for_player_id: str | None = None) -> dict:
        """
        Serialize state. If for_player_id is given, only include buffer
        for that player (private buffer).
        """
        data = {
            "turn_number": self.turn_number,
            "active_player_id": self.active_player.player_id,
            "game_over": self.game_over,
            "winner": self.winner,
            "players": [p.to_dict() for p in self.players],
            "last_action": self.last_action,
        }
        # Buffer is private — only send to active player
        if for_player_id and for_player_id == self.active_player.player_id:
            data["buffer"] = list(self.buffer)
        else:
            data["buffer"] = None
        return data
