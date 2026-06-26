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
    r"C:\Users\ASUS\Downloads\dice_chess\dice_chess\backend\stockfish.exe",
    "/opt/stockfish/stockfish",
    "/usr/games/stockfish",
    "/usr/bin/stockfish",
    shutil.which("stockfish") or "",
]
STOCKFISH_PATH = next((p for p in _SF_CANDIDATES if p and os.path.isfile(p)), "stockfish")


async def get_ai_moves(fen: str, budget: int, depth: int = 8) -> list[str]:
    """Возвращает список UCI-ходов для ИИ с учётом бюджета клеток."""
    board = chess.Board(fen)
    if board.is_game_over():
        return []

    moves_to_make = []
    remaining_budget = budget
    current_board = board.copy()

    try:
        transport, engine = await chess.engine.popen_uci(STOCKFISH_PATH)

        while remaining_budget > 0:
            if current_board.is_game_over():
                break
            legal = list(current_board.legal_moves)
            if not legal:
                break

            cur_depth = max(4, depth - len(moves_to_make) * 2)

            try:
                result = await asyncio.wait_for(
                    engine.play(current_board, chess.engine.Limit(depth=cur_depth)),
                    timeout=2.0
                )
                move = result.move
            except asyncio.TimeoutError:
                move = random.choice(legal)

            # ─── ИСПРАВЛЕННЫЙ БЛОК ДЛЯ ИИ: Точный расчет стоимости ───
            piece = current_board.piece_at(move.from_square)
            f_dist = abs(chess.square_file(move.from_square) - chess.square_file(move.to_square))
            r_dist = abs(chess.square_rank(move.from_square) - chess.square_rank(move.to_square))

            if piece and piece.piece_type == chess.KNIGHT:
                cost = 3
            elif piece and piece.piece_type == chess.PAWN:
                cost = r_dist if f_dist == 0 else 1
            else:
                cost = max(f_dist, r_dist)

            if cost > remaining_budget:
                # Если у ИИ не хватает бюджета на этот ход, завершаем серию
                break

            moves_to_make.append(move.uci())
            current_board.push(move)
            remaining_budget -= cost

            if current_board.is_checkmate():
                break

            # Возвращаем ход ИИ (Черным), чтобы Stockfish на следующем шаге думал за Черных
            if remaining_budget > 0:
                current_board.turn = chess.BLACK

            if remaining_budget >= 3 and random.random() < 0.2:
                break

        await engine.quit()

    except Exception as e:
        print(f"Stockfish error: {e}")
        # Простейший фолбек на случайные ходы
        current_board = board.copy()
        legal = list(current_board.legal_moves)
        if legal:
            move = random.choice(legal)
            moves_to_make.append(move.uci())

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
