"""
Naruto Battle — WebSocket Server

Handles:
- Room/lobby management (2 players per match)
- WebRTC signaling relay (offer/answer/ICE)
- Game action dispatch → engine → broadcast state
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import os

# Add parent dir so we can import config_loader
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import websockets
from websockets.server import WebSocketServerProtocol

from game_engine import GameEngine
from game_state import GameState
from message_types import MessageType
from inference_worker import InferenceWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("naruto-server")

# ---- Inference Setup ----
model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "naruto_cnn.pth")
detector_worker = InferenceWorker(model_path)

# ---- Server State ----
rooms: dict[str, "Room"] = {}          # room_id → Room
player_ws: dict[str, WebSocketServerProtocol] = {}   # player_id → ws


class Room:
    """A game room for 2 players."""

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: list[dict] = []    # [{id, name, ws}]
        self.ready_players: set[str] = set() # player_ids who are ready
        self.engine: GameEngine = GameEngine()
        self.game: GameState | None = None
        self.started = False

    @property
    def is_full(self) -> bool:
        return len(self.players) >= 2

    def add_player(self, player_id: str, name: str, ws: WebSocketServerProtocol) -> None:
        self.players.append({"id": player_id, "name": name, "ws": ws})

    def get_opponent_ws(self, player_id: str) -> WebSocketServerProtocol | None:
        for p in self.players:
            if p["id"] != player_id:
                return p["ws"]
        return None

    def start_game(self) -> None:
        p1, p2 = self.players[0], self.players[1]
        self.game = self.engine.create_game(p1["id"], p1["name"], p2["id"], p2["name"])
        self.started = True

    async def broadcast(self, msg: dict) -> None:
        """Send a message to all players in the room."""
        data = json.dumps(msg)
        for p in self.players:
            try:
                await p["ws"].send(data)
            except websockets.ConnectionClosed:
                logger.warning(f"Player {p['id']} disconnected during broadcast")

    async def send_state(self) -> None:
        """Send personalized game state to each player (private buffer)."""
        for p in self.players:
            state = self.game.to_dict(for_player_id=p["id"])
            msg = {
                "type": MessageType.GAME_STATE_UPDATE, 
                "state": state,
                "config": self.engine.config.get("shadow_clone", {})
            }
            try:
                await p["ws"].send(json.dumps(msg))
            except websockets.ConnectionClosed:
                pass

    async def send_to(self, player_id: str, msg: dict) -> None:
        for p in self.players:
            if p["id"] == player_id:
                try:
                    await p["ws"].send(json.dumps(msg))
                except websockets.ConnectionClosed:
                    pass
                return


# ---- Message Handlers ----

async def handle_join(ws: WebSocketServerProtocol, data: dict) -> None:
    """Handle PLAYER_JOINED: assign to room."""
    player_id = data["player_id"]
    name = data.get("name", f"Player_{player_id[:6]}")
    room_id = data.get("room_id", "default")

    if room_id not in rooms:
        rooms[room_id] = Room(room_id)

    room = rooms[room_id]

    if room.is_full:
        await ws.send(json.dumps({
            "type": MessageType.ACTION_ERROR,
            "error": "Room is full",
        }))
        return

    room.add_player(player_id, name, ws)
    player_ws[player_id] = ws
    logger.info(f"Player {name} ({player_id}) joined room {room_id}")

    # Notify room
    await room.broadcast({
        "type": MessageType.PLAYER_JOINED,
        "player_id": player_id,
        "name": name,
        "players_count": len(room.players),
    })

    # Wait for both players to complete calibration and send PLAYER_READY
    logger.info(f"Room {room_id} has {len(room.players)} players. Waiting for Calibration...")


async def handle_sign_detected(room: Room, data: dict) -> None:
    """Handle SIGN_DETECTED: add sign to buffer if started, else relay to calibration."""
    player_id = data["player_id"]
    sign = data["sign"]

    if room.started:
        # Shadow Clone is immediate — bypass buffer
        if sign == "shadow_clone":
            await handle_shadow_clone(room, data)
            return

        result = room.engine.add_sign(player_id, sign)
        if result["success"]:
            await room.send_state()
        else:
            await room.send_to(player_id, {
                "type": MessageType.ACTION_ERROR,
                "error": result.get("error", "Unknown error"),
            })
    else:
        # Pre-match Calibration Relay to frontends
        await room.broadcast({
            "type": "CALIBRATION_SIGN",
            "player_id": player_id,
            "sign": sign,
            "confidence": data.get("confidence", 1.0)
        })


async def handle_action_submit(room: Room, data: dict) -> None:
    """Handle ACTION_SUBMIT: activate buffer (Ram)."""
    player_id = data["player_id"]

    result = room.engine.activate_buffer(player_id)

    # Send turn result to everyone
    await room.broadcast({
        "type": MessageType.TURN_RESULT,
        "result": result,
    })

    # 1. ALWAYS broadcast state update so players see direct consequences (e.g. 0 HP)
    await room.send_state()

    # 2. Check for game over and broadcast end with delay
    if room.engine.state.game_over:
        await room.broadcast({
            "type": MessageType.MATCH_END,
            "winner": room.engine.state.winner,
        })


async def handle_shadow_clone(room: Room, data: dict) -> None:
    """Handle SHADOW_CLONE_TRIGGER."""
    player_id = data["player_id"]

    result = room.engine.trigger_shadow_clone(player_id)

    await room.broadcast({
        "type": MessageType.TURN_RESULT,
        "result": result,
    })

    # 1. ALWAYS broadcast state update
    await room.send_state()

    # 2. Check for game over
    if room.engine.state.game_over:
        await room.broadcast({
            "type": MessageType.MATCH_END,
            "winner": room.engine.state.winner,
        })


async def handle_rtc_signal(room: Room, data: dict) -> None:
    """Relay WebRTC signaling messages to the other player."""
    player_id = data["player_id"]
    opponent_ws = room.get_opponent_ws(player_id)
    if opponent_ws:
        try:
            await opponent_ws.send(json.dumps(data))
        except websockets.ConnectionClosed:
            pass


# ---- Find Room by Player ----

def find_room_for_player(player_id: str) -> Room | None:
    for room in rooms.values():
        for p in room.players:
            if p["id"] == player_id:
                return room
    return None


# ---- WebSocket Handler ----

async def handler(ws: WebSocketServerProtocol) -> None:
    """Main WebSocket connection handler."""
    player_id = None
    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            if msg_type == MessageType.PLAYER_JOINED:
                player_id = data.get("player_id")
                await handle_join(ws, data)

            elif msg_type == MessageType.PLAYER_READY:
                room = find_room_for_player(data.get("player_id", ""))
                if room:
                    room.ready_players.add(data["player_id"])
                    logger.info(f"Player {data.get('player_id')} is READY in room {room.room_id} ({len(room.ready_players)}/2)")
                    
                    if len(room.ready_players) >= 2:
                        room.start_game()
                        logger.info(f"Both players ready. Game starting in room {room.room_id}")
                        await room.broadcast({
                            "type": MessageType.MATCH_START,
                            "players": [{"id": p["id"], "name": p["name"]} for p in room.players],
                        })
                        await room.send_state()

            elif msg_type in (
                MessageType.RTC_OFFER,
                MessageType.RTC_ANSWER,
                MessageType.RTC_ICE_CANDIDATE,
            ):
                room = find_room_for_player(data.get("player_id", ""))
                if room:
                    await handle_rtc_signal(room, data)

            elif msg_type == "FRAME_LANDMARKS":
                room = find_room_for_player(data.get("player_id", ""))
                if room:
                    landmarks = data.get("landmarks", [])
                    res = detector_worker.process_landmarks(landmarks, data["player_id"])
                    
                    if res["confirmed"]:
                        confirmed = res["confirmed"]
                        data["sign"] = confirmed
                        data["confidence"] = res["confidence"]
                        
                        # Special immediate mechanics
                        if confirmed == "shadow_clone":
                            await handle_shadow_clone(room, data)
                        elif confirmed == "ram":
                            await handle_action_submit(room, data)
                        elif confirmed == "scrap":
                            # If they make the scrap sign, just clear it
                            result = room.engine.scrap_buffer(data["player_id"])
                            await room.send_state()
                        else:
                            await handle_sign_detected(room, data)
                    else:
                        # Relay unconfirmed predictions to calibration screen
                        if not room.started and res["prediction"] != "unknown":
                             await room.broadcast({
                                "type": "CALIBRATION_SIGN",
                                "player_id": data["player_id"],
                                "sign": res["prediction"],
                                "confidence": res["confidence"]
                             })

            elif msg_type == MessageType.SIGN_DETECTED:
                room = find_room_for_player(data["player_id"])
                if room and room.started:
                    await handle_sign_detected(room, data)

            elif msg_type == MessageType.ACTION_SUBMIT:
                room = find_room_for_player(data["player_id"])
                if room and room.started:
                    await handle_action_submit(room, data)

            elif msg_type == MessageType.SHADOW_CLONE_TRIGGER:
                room = find_room_for_player(data["player_id"])
                if room and room.started:
                    await handle_shadow_clone(room, data)

            else:
                logger.warning(f"Unknown message type: {msg_type}")

    except websockets.ConnectionClosed:
        logger.info(f"Player {player_id} disconnected")
    finally:
        # Clean up on disconnect
        if player_id:
            player_ws.pop(player_id, None)
            room = find_room_for_player(player_id)
            if room:
                room.players = [p for p in room.players if p["id"] != player_id]
                if not room.players:
                    rooms.pop(room.room_id, None)
                    logger.info(f"Room {room.room_id} closed (empty)")
                else:
                    await room.broadcast({
                        "type": MessageType.ACTION_ERROR,
                        "error": "Opponent disconnected",
                    })


# ---- Entry Point ----

async def main():
    host = "0.0.0.0"
    port = 8765
    logger.info(f"Naruto Battle server starting on ws://{host}:{port}")
    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
