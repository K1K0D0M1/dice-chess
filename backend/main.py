"""
Dice Chess — WebSocket сервер
FastAPI + WebSockets

Протокол событий (JSON):
  Клиент → Сервер:
    { "type": "join",       "name": "...", "room_id": "..." | null, "vs_ai": bool }
    { "type": "roll_dice" }
    { "type": "move",       "from": "e2", "to": "e4", "promotion": "q"|null }
    { "type": "end_turn" }
    { "type": "get_state" }

  Сервер → Клиент:
    { "type": "joined",     "room_id": "...", "role": "white"|"black", "state": {...} }
    { "type": "state",      ...полное состояние... }
    { "type": "dice_rolled","dice_value": N, "moves_left": N, "by": "white"|"black" }
    { "type": "moved",      "move": "e2e4", "fen": "...", "moves_left": N, ... }
    { "type": "turn_changed","current_turn": "white"|"black", ... }
    { "type": "game_over",  "winner": "...", "fen": "..." }
    { "type": "error",      "message": "..." }
    { "type": "opponent_joined", "name": "..." }
"""

import asyncio
import json
import random
import os
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from game import create_room, get_room, GameRoom, PlayerRole, GameStatus
from ai_adapter import get_ai_moves


app = FastAPI(title="Dice Chess Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# room_id -> list of websockets
connections: dict[str, list[WebSocket]] = {}
# websocket -> (room_id, player_id)
ws_meta: dict[WebSocket, tuple[str, str]] = {}


async def broadcast(room_id: str, message: dict, exclude: Optional[WebSocket] = None):
    """Отправить сообщение всем игрокам в комнате."""
    for ws in connections.get(room_id, []):
        if ws != exclude:
            try:
                await ws.send_json(message)
            except Exception:
                pass


async def send(ws: WebSocket, message: dict):
    try:
        await ws.send_json(message)
    except Exception:
        pass


async def run_ai_turn(room: GameRoom):
    """Запустить ход ИИ: бросок кубика + серия ходов."""
    await asyncio.sleep(0.8)  # пауза для реалистичности

    # Бросок кубика
    dice_value = random.randint(1, 6)
    from game import TurnState
    room.turn_state = TurnState(
        dice_value=dice_value,
        moves_left=dice_value,
        dice_rolled=True,
    )

    await broadcast(room.room_id, {
        "type": "dice_rolled",
        "dice_value": dice_value,
        "moves_left": dice_value,
        "by": "black",
    })

    await asyncio.sleep(0.6)

    # Получаем ходы от Stockfish
    ai_moves = await get_ai_moves(room.board.fen(), dice_value)

    for uci in ai_moves:
        if room.turn_state.moves_left <= 0:
            break
        try:
            result = room.make_move("ai", uci)
            await broadcast(room.room_id, {
                "type": "moved",
                "move": uci,
                "fen": result["fen"],
                "moves_left": result["moves_left"],
                "dice_value": result["dice_value"],
                "by": "black",
            })

            if result["game_over"]:
                await broadcast(room.room_id, {
                    "type": "game_over",
                    "winner": result["winner"],
                    "fen": result["fen"],
                })
                return

            await asyncio.sleep(0.5)  # задержка между ходами ИИ
        except Exception as e:
            print(f"AI move error: {e}")
            break

    # Завершаем ход ИИ
    turn_result = room.force_end_turn()
    await broadcast(room.room_id, {
        "type": "turn_changed",
        **turn_result,
    })


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    room_id: Optional[str] = None
    player_id: Optional[str] = None

    try:
        async for raw in ws.iter_text():
            try:
                msg = json.loads(raw)
                print("CLIENT:", msg)
            except json.JSONDecodeError:
                await send(ws, {"type": "error", "message": "Неверный формат JSON"})
                print("JOINED SENT")
                continue

            msg_type = msg.get("type")

            # ──────────────────────────────────────────────
            if msg_type == "join":
                name = msg.get("name", "Игрок")[:20]
                vs_ai = msg.get("vs_ai", False)
                requested_room = (msg.get("room_id") or "").strip().upper()

                if requested_room:
                    room = get_room(requested_room)
                    if room is None:
                        await send(ws, {"type": "error", "message": "Комната не найдена"})
                        continue
                    if room.status == GameStatus.FINISHED:
                        await send(ws, {"type": "error", "message": "Игра уже завершена"})
                        continue
                else:
                    room = create_room(vs_ai=vs_ai)

                import uuid
                player_id = str(uuid.uuid4())[:8]

                try:
                    role = room.add_player(player_id, name)
                except ValueError as e:
                    await send(ws, {"type": "error", "message": str(e)})
                    continue

                room_id = room.room_id
                ws_meta[ws] = (room_id, player_id)
                if room_id not in connections:
                    connections[room_id] = []
                connections[room_id].append(ws)

                await send(ws, {
                    "type": "joined",
                    "room_id": room_id,
                    "role": role.value,
                    "player_id": player_id,
                    "state": room.full_state(),
                })

                # Сообщить второму игроку, что кто-то зашёл
                await broadcast(room_id, {
                    "type": "opponent_joined",
                    "name": name,
                    "state": room.full_state(),
                }, exclude=ws)

            # ──────────────────────────────────────────────
            elif msg_type == "roll_dice":
                if not room_id or not player_id:
                    await send(ws, {"type": "error", "message": "Сначала подключитесь к комнате"})
                    continue
                room = get_room(room_id)
                if room is None:
                    continue
                try:
                    result = room.roll_dice(player_id)
                    await broadcast(room_id, {
                        "type": "dice_rolled",
                        "dice_value": result["dice_value"],
                        "moves_left": result["moves_left"],
                        "by": room.get_player_role(player_id).value,
                    })
                except ValueError as e:
                    await send(ws, {"type": "error", "message": str(e)})

            # ──────────────────────────────────────────────
            elif msg_type == "move":
                if not room_id or not player_id:
                    await send(ws, {"type": "error", "message": "Сначала подключитесь к комнате"})
                    continue
                room = get_room(room_id)
                if room is None:
                    continue

                from_sq = msg.get("from", "")
                to_sq = msg.get("to", "")
                promotion = msg.get("promotion", "")
                uci = from_sq + to_sq + (promotion or "")

                try:
                    result = room.make_move(player_id, uci)
                    by = room.get_player_role(player_id)

                    await broadcast(room_id, {
                        "type": "moved",
                        "move": uci,
                        "fen": result["fen"],
                        "moves_left": result["moves_left"],
                        "dice_value": result["dice_value"],
                        "by": by.value if by else "unknown",
                    })

                    if result["game_over"]:
                        await broadcast(room_id, {
                            "type": "game_over",
                            "winner": result["winner"],
                            "fen": result["fen"],
                        })
                    elif result["moves_left"] == 0:
                        # Автоматически завершаем ход
                        turn_result = room.force_end_turn()
                        await broadcast(room_id, {
                            "type": "turn_changed",
                            **turn_result,
                        })
                        # Если vs_ai и теперь ход чёрных — запускаем ИИ
                        if room.vs_ai and room.current_turn == PlayerRole.BLACK:
                            asyncio.create_task(run_ai_turn(room))

                except ValueError as e:
                    await send(ws, {"type": "error", "message": str(e)})

            # ──────────────────────────────────────────────
            elif msg_type == "end_turn":
                if not room_id or not player_id:
                    continue
                room = get_room(room_id)
                if room is None:
                    continue
                try:
                    result = room.end_turn(player_id)
                    await broadcast(room_id, {
                        "type": "turn_changed",
                        **result,
                    })
                    if room.vs_ai and room.current_turn == PlayerRole.BLACK:
                        asyncio.create_task(run_ai_turn(room))
                except ValueError as e:
                    await send(ws, {"type": "error", "message": str(e)})

            # ──────────────────────────────────────────────
            elif msg_type == "get_state":
                if not room_id:
                    continue
                room = get_room(room_id)
                if room:
                    await send(ws, {"type": "state", **room.full_state()})

            # ──────────────────────────────────────────────
            else:
                await send(ws, {"type": "error", "message": f"Неизвестный тип: {msg_type}"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS error: {e}")
    finally:
        if room_id and ws in connections.get(room_id, []):
            connections[room_id].remove(ws)
        if ws in ws_meta:
            del ws_meta[ws]


@app.get("/health")
async def health():
    return {"status": "ok", "rooms": len(connections)}


# Отдаём фронтенд — ищем index.html рядом с backend/ или в frontend/
_FRONTEND_CANDIDATES = [
    r"C:\Users\ASUS\Downloads\dice_chess\dice_chess\frontend\index.html",
    os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html"),
    os.path.join(os.path.dirname(__file__), "index.html"),
]
_FRONTEND_PATH = next((p for p in _FRONTEND_CANDIDATES if os.path.isfile(p)), None)


@app.get("/")
async def root():
    if _FRONTEND_PATH:
        return FileResponse(_FRONTEND_PATH, media_type="text/html")
    return {"message": "Dice Chess API", "ws": "/ws", "health": "/health"}
