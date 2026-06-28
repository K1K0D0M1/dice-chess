"""
AI Adapter — Stockfish + Dice Chess Rules
ИИ знает шахматные ходы, но ограничен бюджетом кубика.
Стратегия: берём N лучших ходов от Stockfish, оставляем те, что влезают в бюджет.
Ограничение: за раунд ИИ тоже может съесть не более одной фигуры.
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
    "/usr/games/stockfish",
    "/usr/bin/stockfish",
    shutil.which("stockfish") or "",
]
STOCKFISH_PATH = next((p for p in _SF_CANDIDATES if p and os.path.isfile(p)), "stockfish")


async def get_ai_moves(fen: str, budget: int, depth: int = 8) -> list[str]:
    """Возвращает список UCI-ходов для ИИ с учётом бюджета клеток и лимита взятий."""
    board = chess.Board(fen)
    if board.is_game_over():
        return []

    moves_to_make = []
    remaining_budget = budget
    captures_made = 0        # счётчик взятий за раунд (лимит: 1)
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

            # ─── Расчет стоимости хода ───
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
                break

            # ─── Проверка лимита взятий ───
            is_capture = current_board.is_capture(move)
            if is_capture and captures_made >= 1:
                # Нельзя брать вторую фигуру — ищем альтернативный ход без взятия
                non_capture_moves = [m for m in legal if not current_board.is_capture(m)]
                if not non_capture_moves:
                    break  # все оставшиеся ходы — взятия, заканчиваем раунд

                # Спрашиваем Stockfish лучший ход без взятия
                # (упрощение: берём случайный из не-взятий)
                move = random.choice(non_capture_moves)

                # Пересчитываем стоимость нового хода
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
                    break

                is_capture = False

            if is_capture:
                captures_made += 1

            moves_to_make.append(move.uci())
            current_board.push(move)
            remaining_budget -= cost

            # ─── ИСПРАВЛЕНО: НЕ переключаем board.turn вручную ───
            # chess.push() уже передаёт ход другой стороне.
            # Для следующей итерации Stockfish сам разберётся со стороной по FEN.
            # Принудительное переключение ломало логику и детекцию мата.

            if current_board.is_checkmate():
                break

            # Случайный выход: ИИ не всегда использует весь бюджет
            if remaining_budget >= 3 and random.random() < 0.2:
                break

        await engine.quit()

    except Exception as e:
        print(f"Stockfish error: {e}")
        # Фолбек на случайный ход
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
