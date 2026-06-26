"""
Dice Chess — Game Logic
Кубик определяет бюджет ходов за раунд (1-6).
Игрок может ходить несколькими фигурами, главное — уложиться в бюджет.
Бюджет = количество ходов (не клеток), каждый ход = 1 единица бюджета.
"""

import chess
import random
import uuid
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class GameStatus(str, Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    FINISHED = "finished"


class PlayerRole(str, Enum):
    WHITE = "white"
    BLACK = "black"
    AI = "ai"


@dataclass
class Player:
    id: str
    name: str
    role: PlayerRole


@dataclass
class TurnState:
    dice_value: int = 0          # выпавшее число
    moves_left: int = 0          # оставшийся бюджет
    moves_made: list = field(default_factory=list)  # ходы в этом раунде
    dice_rolled: bool = False    # кинул ли кубик


@dataclass
class GameRoom:
    room_id: str
    board: chess.Board = field(default_factory=chess.Board)
    players: dict = field(default_factory=dict)   # role -> Player
    status: GameStatus = GameStatus.WAITING
    current_turn: PlayerRole = PlayerRole.WHITE
    turn_state: TurnState = field(default_factory=TurnState)
    history: list = field(default_factory=list)   # список ходов всей партии
    winner: Optional[str] = None
    vs_ai: bool = False

    def add_player(self, player_id: str, name: str) -> PlayerRole:
        """Добавить игрока, вернуть его роль."""
        if PlayerRole.WHITE not in self.players:
            role = PlayerRole.WHITE
        elif PlayerRole.BLACK not in self.players:
            role = PlayerRole.BLACK
        else:
            raise ValueError("Комната заполнена")
        self.players[role] = Player(id=player_id, name=name, role=role)
        if self.vs_ai:
            self.status = GameStatus.ACTIVE
        elif len(self.players) == 2:
            self.status = GameStatus.ACTIVE
        return role

    def get_player_role(self, player_id: str) -> Optional[PlayerRole]:
        for role, p in self.players.items():
            if p.id == player_id:
                return role
        return None

    def roll_dice(self, player_id: str) -> dict:
        """Бросить кубик — только если сейчас твой ход и кубик ещё не брошен."""
        role = self.get_player_role(player_id)
        if self.vs_ai and role == PlayerRole.WHITE:
            pass  # белые = человек
        if role != self.current_turn:
            raise ValueError("Сейчас не ваш ход")
        if self.turn_state.dice_rolled:
            raise ValueError("Кубик уже брошен в этом раунде")
        if self.status != GameStatus.ACTIVE:
            raise ValueError("Игра не активна")

        value = random.randint(1, 6)
        self.turn_state = TurnState(
            dice_value=value,
            moves_left=value,
            dice_rolled=True,
        )
        return {"dice_value": value, "moves_left": value}

    def make_move(self, player_id: str, uci_move: str) -> dict:
        """Сделать ход фигурой. Возвращает обновлённое состояние."""
        role = self.get_player_role(player_id)
        if role is None and not (self.vs_ai and player_id == "ai"):
            raise ValueError("Игрок не найден")

        if player_id != "ai" and role != self.current_turn:
            raise ValueError("Сейчас не ваш ход")

        if not self.turn_state.dice_rolled:
            raise ValueError("Сначала бросьте кубик")
        if self.turn_state.moves_left <= 0:
            raise ValueError("Бюджет ходов исчерпан")

        move = chess.Move.from_uci(uci_move)
        if move not in self.board.legal_moves:
            raise ValueError(f"Недопустимый ход: {uci_move}")

        # Проверяем цвет фигуры
        piece = self.board.piece_at(move.from_square)
        if piece is None:
            raise ValueError("На клетке нет фигуры")
        expected_color = chess.WHITE if self.current_turn == PlayerRole.WHITE else chess.BLACK
        if piece.color != expected_color:
            raise ValueError("Вы не можете ходить чужой фигурой")

        # ─── ИСПРАВЛЕННЫЙ БЛОК: Точный расчет стоимости по типам фигур ───
        from_sq = move.from_square
        to_sq = move.to_square
        file_dist = abs(chess.square_file(from_sq) - chess.square_file(to_sq))
        rank_dist = abs(chess.square_rank(from_sq) - chess.square_rank(to_sq))

        if piece.piece_type == chess.KNIGHT:
            move_cost = 3  # Конь прыгает на любую доступную ему клетку за 3 очка бюджета
        elif piece.piece_type == chess.PAWN:
            # Если идет прямо (file_dist == 0), то цена равна пройденным клеткам (1 или 2)
            # Если бьет наискосок, то смещение всегда 1 клетка
            move_cost = rank_dist if file_dist == 0 else 1
        else:
            # Для Ладьи, Слона, Ферзя и Короля цена — это количество пройденных клеток
            move_cost = max(file_dist, rank_dist)

        if move_cost > self.turn_state.moves_left:
            raise ValueError(f"Недостаточно бюджета клеток. Нужно: {move_cost}, осталось: {self.turn_state.moves_left}")

        self.board.push(move)
        self.turn_state.moves_made.append(uci_move)
        self.turn_state.moves_left -= move_cost  # Списываем стоимость клеток

        # ─── ИСПРАВЛЕНИЕ ОШИБКИ №1: Удерживаем ход, если бюджет остался ───
        if self.turn_state.moves_left > 0:
            self.board.turn = chess.WHITE if self.current_turn == PlayerRole.WHITE else chess.BLACK

        # Записываем в историю
        self.history.append({
            "turn": self.current_turn.value,
            "move": uci_move,
            "dice": self.turn_state.dice_value,
        })

        result = {
            "move": uci_move,
            "fen": self.board.fen(),
            "moves_left": self.turn_state.moves_left,
            "dice_value": self.turn_state.dice_value,
            "game_over": False,
            "winner": None,
        }

        # Проверка победы: мат
        if self.board.is_checkmate():
            self.status = GameStatus.FINISHED
            winner_role = self.current_turn
            self.winner = self.players.get(winner_role, Player("ai", "AI", PlayerRole.BLACK)).name
            result["game_over"] = True
            result["winner"] = self.winner
            return result

        # Проверка ничьей
        if self.board.is_stalemate() or self.board.is_insufficient_material():
            self.status = GameStatus.FINISHED
            result["game_over"] = True
            result["winner"] = "draw"
            return result

        return result

    def end_turn(self, player_id: str) -> dict:
        """Завершить свой ход досрочно (потратил не весь бюджет)."""
        role = self.get_player_role(player_id)
        if role != self.current_turn and player_id != "ai":
            raise ValueError("Сейчас не ваш ход")
        if not self.turn_state.dice_rolled:
            raise ValueError("Нельзя завершить ход до броска кубика")

        self._switch_turn()
        return self._state_snapshot()

    def force_end_turn(self) -> dict:
        """Принудительно завершить ход (бюджет = 0)."""
        self._switch_turn()
        return self._state_snapshot()

    def _switch_turn(self):
        if self.current_turn == PlayerRole.WHITE:
            self.current_turn = PlayerRole.BLACK
        else:
            self.current_turn = PlayerRole.WHITE
        self.turn_state = TurnState()
        
        # СИНХРОНИЗАЦИЯ: передаем ход на доске новому игроку при смене раунда
        self.board.turn = chess.WHITE if self.current_turn == PlayerRole.WHITE else chess.BLACK

    def _state_snapshot(self) -> dict:
        return {
            "fen": self.board.fen(),
            "current_turn": self.current_turn.value,
            "status": self.status.value,
            "dice_value": self.turn_state.dice_value,
            "moves_left": self.turn_state.moves_left,
            "dice_rolled": self.turn_state.dice_rolled,
            "winner": self.winner,
        }

    def full_state(self) -> dict:
        snap = self._state_snapshot()
        snap["players"] = {
            role.value: {"name": p.name, "role": role.value}
            for role, p in self.players.items()
        }
        snap["history"] = self.history[-20:]  # последние 20 ходов
        snap["room_id"] = self.room_id
        return snap


# Глобальное хранилище комнат (in-memory)
rooms: dict[str, GameRoom] = {}


def create_room(vs_ai: bool = False) -> GameRoom:
    room_id = str(uuid.uuid4())[:8].upper()
    room = GameRoom(room_id=room_id, vs_ai=vs_ai)
    if vs_ai:
        # Чёрные = ИИ, не нужен второй игрок
        room.players[PlayerRole.BLACK] = Player(id="ai", name="AI (Stockfish)", role=PlayerRole.BLACK)
    rooms[room_id] = room
    return room


def get_room(room_id: str) -> Optional[GameRoom]:
    return rooms.get(room_id.upper())
