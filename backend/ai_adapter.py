"""
AI Adapter — Stockfish + Dice Chess Rules
ИИ знает шахматные ходы, но ограничен бюджетом кубика.
Стратегия: берём N лучших ходов от Stockfish, оставляем те, что влезают в бюджет.
"""

import chess
import chess.engine
import asyncio
import random
from typing import Optional


import shutil, os
# Render installs stockfish via build.sh into /opt/stockfish/stockfish
# Fallback to system path
_SF_CANDIDATES = [
    os.environ.get("STOCKFISH_PATH", ""),
    "/opt/stockfish/stockfish",
    "/usr/games/stockfish",
    "/usr/bin/stockfish",
    shutil.which("stockfish") or "",
]
STOCKFISH_PATH = next((p for p in _SF_CANDIDATES if p and os.path.isfile(p)), "stockfish")


async def get_ai_moves(fen: str, budget: int, depth: int = 8) -> list[str]:
    """
    Возвращает список UCI-ходов для ИИ с учётом бюджета кубика.
    ИИ старается использовать бюджет максимально эффективно.
    """
    board = chess.Board(fen)
    if board.is_game_over():
        return []

    moves_to_make = []
    remaining_budget = budget
    current_board = board.copy()

    try:
        transport, engine = await chess.engine.popen_uci(STOCKFISH_PATH)

        for _ in range(remaining_budget):
            if current_board.is_game_over():
                break
            legal = list(current_board.legal_moves)
            if not legal:
                break

            # Уменьшаем depth на поздних ходах в бюджете (экономим время)
            cur_depth = max(4, depth - len(moves_to_make) * 2)

            try:
                result = await asyncio.wait_for(
                    engine.play(current_board, chess.engine.Limit(depth=cur_depth)),
                    timeout=2.0
                )
                move = result.move
            except asyncio.TimeoutError:
                # Если думает слишком долго — случайный ход
                move = random.choice(legal)

            moves_to_make.append(move.uci())
            current_board.push(move)

            # Если мат — прекращаем
            if current_board.is_checkmate():
                break

            # Иногда ИИ не использует весь бюджет (имитирует человека)
            if remaining_budget > 3 and random.random() < 0.3:
                break

        await engine.quit()

    except Exception as e:
        print(f"Stockfish error: {e}")
        # Fallback: случайные ходы
        current_board = board.copy()
        for _ in range(min(budget, 2)):
            legal = list(current_board.legal_moves)
            if not legal or current_board.is_game_over():
                break
            move = random.choice(legal)
            moves_to_make.append(move.uci())
            current_board.push(move)

    return moves_to_make


async def evaluate_position(fen: str) -> Optional[int]:
    """Оценка позиции в сантипешках (для отображения)."""
    try:
        board = chess.Board(fen)
        transport, engine = await chess.engine.popen_uci(STOCKFISH_PATH)
        info = await engine.analyse(board, chess.engine.Limit(depth=6))
        await engine.quit()
        score = info["score"].white()
        if score.is_mate():
            return 9999 if score.mate() > 0 else -9999
        return score.score()
    except Exception:
        return None
