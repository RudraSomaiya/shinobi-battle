"""
Game Engine — core gameplay logic for Naruto Battle.

Handles: buffer management, jutsu resolution, Shadow Clone, Focus,
turn switching, cooldowns, buffs/debuffs, and win condition.
"""

from __future__ import annotations
import random
from typing import Any

from game_state import GameState, PlayerState, Buff, Debuff
from config_loader import load_config


class GameEngine:
    """Authoritative game logic engine."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or load_config()
        self.jutsu_table: dict[str, dict] = {}
        self._build_jutsu_table()

        # Config values
        self.passive_regen: int = self.config["passive_regen"]
        self.focus_bonus: int = self.config["focus_bonus"]
        self.base_penalty: int = self.config["base_penalty"]
        self.per_sign_penalty: int = self.config["per_sign_penalty"]
        self.max_buffer: int = self.config["max_buffer_length"]
        self.max_buffs: int = self.config["max_buffs"]
        self.max_debuffs: int = self.config["max_debuffs"]
        self.shadow_clone_cfg = self.config["shadow_clone"]

        self.state: GameState | None = None

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    def _build_jutsu_table(self) -> None:
        """Index jutsu by their sign sequence (as tuple) for O(1) lookup."""
        for jutsu in self.config["jutsu"]:
            key = tuple(jutsu["sign_sequence"])
            self.jutsu_table[key] = jutsu

    def create_game(self, player1_id: str, player1_name: str,
                    player2_id: str, player2_name: str) -> GameState:
        """Initialize a new game between two players."""
        pcfg = self.config["player"]
        p1 = PlayerState(
            player_id=player1_id, name=player1_name,
            hp=pcfg["starting_hp"], max_hp=pcfg["max_hp"],
            chakra=pcfg["starting_chakra"], max_chakra=pcfg["max_chakra"],
        )
        p2 = PlayerState(
            player_id=player2_id, name=player2_name,
            hp=pcfg["starting_hp"], max_hp=pcfg["max_hp"],
            chakra=pcfg["starting_chakra"], max_chakra=pcfg["max_chakra"],
        )
        self.state = GameState(players=[p1, p2])
        return self.state

    # ------------------------------------------------------------------
    # Buffer Management
    # ------------------------------------------------------------------
    def add_sign(self, player_id: str, sign: str) -> dict:
        """
        Add a sign to the active player's buffer.
        Returns result dict with success/error info.
        """
        gs = self.state
        if gs.game_over:
            return {"success": False, "error": "Game is over"}
        if player_id != gs.active_player.player_id:
            return {"success": False, "error": "Not your turn"}

        # Shadow Clone is handled separately
        if sign == "shadow_clone":
            return {"success": False, "error": "Shadow Clone uses trigger_shadow_clone()"}

        # Ram = activate
        if sign == "ram":
            return self.activate_buffer(player_id)

        # Scrap = clear
        if sign == "scrap":
            return self.scrap_buffer(player_id)

        # Unknown = ignore
        if sign == "unknown":
            return {"success": False, "error": "Unknown sign — ignored"}

        # Buffer full check
        if len(gs.buffer) >= self.max_buffer:
            return {"success": False, "error": "Buffer full (max 6). Activate or Scrap."}

        # Consecutive same sign check
        if gs.buffer and gs.buffer[-1] == sign:
            return {"success": False, "error": f"Consecutive same sign '{sign}' — use a different sign."}

        gs.buffer.append(sign)
        return {
            "success": True,
            "action": "sign_added",
            "sign": sign,
            "buffer": list(gs.buffer),
        }

    # ------------------------------------------------------------------
    # Activation (Ram)
    # ------------------------------------------------------------------
    def activate_buffer(self, player_id: str) -> dict:
        """Process the current buffer: Focus (empty) or Jutsu resolution."""
        gs = self.state
        if gs.game_over:
            return {"success": False, "error": "Game is over"}
        if player_id != gs.active_player.player_id:
            return {"success": False, "error": "Not your turn"}

        # Empty buffer → Focus
        if len(gs.buffer) == 0:
            return self._do_focus(player_id)

        # Look up jutsu
        seq = tuple(gs.buffer)
        jutsu = self.jutsu_table.get(seq)

        if jutsu is None:
            # Failed sequence → penalty
            result = self._apply_failure_penalty(player_id, len(gs.buffer))
            self._end_turn()
            return result

        # Found jutsu — resolve it
        result = self._resolve_jutsu(jutsu)
        self._end_turn()
        return result

    # ------------------------------------------------------------------
    # Scrap
    # ------------------------------------------------------------------
    def scrap_buffer(self, player_id: str) -> dict:
        """Clear buffer without ending turn."""
        gs = self.state
        if player_id != gs.active_player.player_id:
            return {"success": False, "error": "Not your turn"}

        gs.buffer.clear()
        return {"success": True, "action": "scrap", "buffer": []}

    # ------------------------------------------------------------------
    # Shadow Clone (immediate, bypasses buffer)
    # ------------------------------------------------------------------
    def trigger_shadow_clone(self, player_id: str) -> dict:
        """Trigger Shadow Clone — immediate, no buffer, no Ram needed."""
        gs = self.state
        if gs.game_over:
            return {"success": False, "error": "Game is over"}
        if player_id != gs.active_player.player_id:
            return {"success": False, "error": "Not your turn"}

        player = gs.active_player
        enemy = gs.inactive_player

        # Check cooldown
        cd = player.cooldowns.get("Shadow Clone", 0)
        if cd > 0:
            return {
                "success": False,
                "error": f"Shadow Clone on cooldown ({cd} turns remaining)",
            }

        # Cost = 50% of current chakra
        cost = int(player.chakra * self.shadow_clone_cfg["chakra_cost_percent"] / 100)
        if cost > player.chakra:
            return {"success": False, "error": "Insufficient chakra for Shadow Clone"}

        player.chakra -= cost
        player.clamp_chakra()
        player.shadow_clone_active = True

        # Apply debuff to enemy: +50% miss on their next attack
        # duration=99 ensures it does not naturally expire until they use an offensive jutsu
        miss_debuff = Debuff(
            name="Shadow Clone Confusion",
            effect="increase_miss",
            value=self.shadow_clone_cfg["miss_increase_percent"],
            duration=99,
        )
        self._add_debuff(enemy, miss_debuff)

        # Set cooldown
        player.cooldowns["Shadow Clone"] = self.shadow_clone_cfg["cooldown_turns"]

        result = {
            "success": True,
            "action": "shadow_clone",
            "chakra_cost": cost,
            "player_id": player_id,
        }
        gs.last_action = result
        self._end_turn()
        return result

    # ------------------------------------------------------------------
    # Focus (empty buffer + Ram)
    # ------------------------------------------------------------------
    def _do_focus(self, player_id: str) -> dict:
        """Focus: empty buffer activated → gain bonus chakra."""
        player = self.state.active_player
        gained = self.focus_bonus  # Passive regen added at end_turn
        player.chakra += gained
        player.clamp_chakra()

        result = {
            "success": True,
            "action": "focus",
            "chakra_gained": gained,
            "player_id": player_id,
        }
        self.state.last_action = result
        self._end_turn()
        return result

    # ------------------------------------------------------------------
    # Jutsu Resolution
    # ------------------------------------------------------------------
    def _resolve_jutsu(self, jutsu: dict) -> dict:
        gs = self.state
        player = gs.active_player
        enemy = gs.inactive_player

        # --- Cooldown check ---
        cd = player.cooldowns.get(jutsu["name"], 0)
        if cd > 0:
            result = {
                "success": False,
                "action": "cooldown_blocked",
                "jutsu": jutsu["name"],
                "turns_remaining": cd,
                "error": f"{jutsu['name']} on cooldown ({cd} turns)",
            }
            gs.last_action = result
            return result

        # --- Chakra check ---
        if player.chakra < jutsu["chakra_cost_self"]:
            result = self._apply_failure_penalty(player.player_id, len(gs.buffer))
            result["error"] = f"Insufficient chakra for {jutsu['name']} (need {jutsu['chakra_cost_self']}, have {player.chakra + self.base_penalty + self.per_sign_penalty * len(gs.buffer)})"
            return result

        # --- Deduct chakra ---
        player.chakra -= jutsu["chakra_cost_self"]
        player.clamp_chakra()

        # Enemy chakra drain
        if jutsu["chakra_cost_enemy"] > 0:
            enemy.chakra -= jutsu["chakra_cost_enemy"]
            enemy.clamp_chakra()

        # --- Miss check ---
        miss_rate = jutsu["miss_rate"] + player.get_miss_bonus()
        missed = random.random() < miss_rate

        result = {
            "success": True,
            "action": "jutsu",
            "jutsu_name": jutsu["name"],
            "jutsu_type": jutsu["type"],
            "missed": missed,
            "player_id": player.player_id,
            "details": {},
        }

        # --- Shadow Clone dispel mechanic ---
        if jutsu["type"] in ("attack", "debuff"):
            # If the current player (who is acting) uses an offensive move, 
            # it targets the enemy and dissipates the enemy's shadow clone.
            player.debuffs = [d for d in player.debuffs if d.name != "Shadow Clone Confusion"]
            enemy.shadow_clone_active = False

        if missed:
            result["details"]["message"] = f"{jutsu['name']} missed!"
        else:
            # --- Apply damage to enemy ---
            raw_dmg = jutsu["dmg_to_enemy"]
            reduction = enemy.get_damage_reduction()
            extra_taken = enemy.get_extra_damage_taken()
            final_dmg = max(0, raw_dmg - reduction + extra_taken)

            if final_dmg > 0:
                enemy.hp -= final_dmg
                enemy.clamp_hp()
                result["details"]["damage_dealt"] = final_dmg

            # --- Self damage ---
            self_dmg = jutsu["dmg_to_self"]
            if self_dmg > 0:
                player.hp -= self_dmg
                player.clamp_hp()
                result["details"]["self_damage"] = self_dmg
            elif self_dmg < 0:
                # Healing
                player.hp -= self_dmg  # Subtracting negative = adding
                player.clamp_hp()
                result["details"]["self_heal"] = abs(self_dmg)

            # --- Apply buff ---
            if jutsu.get("buff"):
                buff_data = jutsu["buff"]
                buff = Buff(
                    name=buff_data["name"],
                    effect=buff_data["effect"],
                    value=buff_data["value"],
                    duration=buff_data["duration"],
                )
                added = self._add_buff(player, buff)
                result["details"]["buff_applied"] = buff.to_dict() if added else None

            # --- Apply debuff to enemy ---
            if jutsu.get("debuff"):
                debuff_data = jutsu["debuff"]
                debuff = Debuff(
                    name=debuff_data["name"],
                    effect=debuff_data["effect"],
                    value=debuff_data["value"],
                    duration=debuff_data["duration"],
                )
                added = self._add_debuff(enemy, debuff)
                result["details"]["debuff_applied"] = debuff.to_dict() if added else None

        # --- Set cooldown ---
        player.cooldowns[jutsu["name"]] = jutsu["cooldown_turns"]

        gs.last_action = result
        gs.check_game_over()
        return result

    # ------------------------------------------------------------------
    # Failure Penalty
    # ------------------------------------------------------------------
    def _apply_failure_penalty(self, player_id: str, buffer_len: int) -> dict:
        """Apply chakra penalty for incorrect sequence."""
        player = self.state.active_player
        penalty = self.base_penalty + self.per_sign_penalty * buffer_len
        player.chakra -= penalty
        player.clamp_chakra()

        result = {
            "success": False,
            "action": "failed_sequence",
            "error": f"Unknown jutsu sequence. Lost {penalty} chakra.",
            "chakra_lost": penalty,
            "player_id": player_id,
        }
        self.state.last_action = result
        return result

    # ------------------------------------------------------------------
    # Buff / Debuff Management
    # ------------------------------------------------------------------
    def _add_buff(self, player: PlayerState, buff: Buff) -> bool:
        """Add buff to player. Replaces oldest if at cap."""
        if len(player.buffs) >= self.max_buffs:
            player.buffs.pop(0)  # Remove oldest
        player.buffs.append(buff)
        return True

    def _add_debuff(self, player: PlayerState, debuff: Debuff) -> bool:
        """Add debuff to player. Replaces oldest if at cap."""
        if len(player.debuffs) >= self.max_debuffs:
            player.debuffs.pop(0)
        player.debuffs.append(debuff)
        return True

    # ------------------------------------------------------------------
    # Turn Management
    # ------------------------------------------------------------------
    def _end_turn(self) -> None:
        """End current turn: cleanup previous player, switch, start next player turn."""
        gs = self.state
        player = gs.active_player  # Expiring active player

        # --- Tick cooldowns ---
        self._tick_cooldowns(player)
        # NOTE: shadow_clone_active is NOT reset here.
        # It persists until the enemy uses an offensive jutsu (handled in _resolve_jutsu).

        # --- Check game over ---
        gs.check_game_over()

        if not gs.game_over:
            gs.switch_turn()
            # Now we apply effects to the NEW active player whose turn is starting!
            new_player = gs.active_player
            
            # 1. Apply Effects (DOT/Tick Effects, HOT)
            self._tick_debuff_effects(new_player)
            self._tick_buff_effects(new_player)
            
            # 2. Passive chakra regen
            new_player.chakra += self.passive_regen
            new_player.clamp_chakra()

            # 3. Tick buff durations / remove expired
            self._tick_buffs(new_player)
            self._tick_debuffs(new_player)

    def _tick_debuff_effects(self, player: PlayerState) -> None:
        """Apply debuff effects (DOT, chakra drain) before they tick down."""
        for d in player.debuffs:
            if d.effect == "dot":
                player.hp -= d.value
                player.clamp_hp()
            elif d.effect == "chakra_drain":
                player.chakra -= d.value
                player.clamp_chakra()

    def _tick_buff_effects(self, player: PlayerState) -> None:
        """Apply buff effects (HOT) before they tick down."""
        for b in player.buffs:
            if b.effect == "hot":
                player.hp += b.value
                player.clamp_hp()

    def _tick_buffs(self, player: PlayerState) -> None:
        """Tick buff durations — remove expired."""
        player.buffs = [b for b in player.buffs if not b.tick()]

    def _tick_debuffs(self, player: PlayerState) -> None:
        """Tick debuff durations — remove expired."""
        player.debuffs = [d for d in player.debuffs if not d.tick()]

    def _tick_cooldowns(self, player: PlayerState) -> None:
        """Tick all cooldowns down by 1, remove those at 0."""
        expired = []
        for name, turns in player.cooldowns.items():
            player.cooldowns[name] = turns - 1
            if player.cooldowns[name] <= 0:
                expired.append(name)
        for name in expired:
            del player.cooldowns[name]
