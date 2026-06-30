<div align="center">

# ♟️🎲 Dice Chess

**Шахматы, где случай встречает стратегию**

Классические шахматы с механикой кубика: каждый раунд вы бросаете кубик и получаете бюджет ходов. Тратьте его на любые фигуры в любом порядке — выиграет тот, кто умнее распорядится удачей.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-WebSocket-009688?style=flat-square&logo=fastapi&logoColor=white)
![chess.js](https://img.shields.io/badge/chess.js-0.10-orange?style=flat-square)
![Stockfish](https://img.shields.io/badge/AI-Stockfish-black?style=flat-square)

</div>

---

## 🎮 Как играть

```
1. Бросьте кубик → получите бюджет от 1 до 6
2. Ходите любыми фигурами, пока хватает бюджета
3. Поставьте мат королю соперника
```

Выпало **5** — можно двинуть пешку (1), коня (2) и ещё раз пешку (2). Или ферзя на 5 клеток. Или как угодно ещё — решать вам.

---

## 💰 Стоимость ходов

| Фигура | Стоимость |
|--------|-----------|
| ♙ Пешка | По клеткам (1 или 2). При взятии — **1** |
| ♘ Конь | Всегда **2** |
| ♗ Слон | По клеткам |
| ♖ Ладья | По клеткам |
| ♕ Ферзь | По клеткам |
| ♔ Король | По клеткам (обычно 1) |

> ⚠️ За один раунд можно съесть **только одну фигуру** — после взятия ход сразу переходит сопернику.

---

## ✨ Особенности

| | |
|---|---|
| 🎲 | Случайный бюджет делает каждую партию уникальной |
| ⚔️ | Несколько ходов за один раунд — любыми фигурами |
| 🤖 | Игра против ИИ на базе Stockfish |
| 🌐 | Мультиплеер через браузер, без установки клиента |
| 🏳️ | Можно сдаться в любой момент |
| 🔄 | Реванш прямо из экрана окончания игры |
| 💾 | Страница восстанавливает игру после обновления |

---

## 📂 Структура проекта

```
dice-chess/
├── backend/
│   ├── main.py          # FastAPI-сервер, WebSocket-протокол
│   ├── game.py          # Игровая логика, бюджет, сдача, реванш
│   ├── ai_adapter.py    # Интеграция со Stockfish
│   └── requirements.txt
└── frontend/
    └── index.html       # Весь клиент: UI + chess.js
```

---

## 🚀 Быстрый старт

### 1. Установите зависимости

```bash
cd backend
pip install -r requirements.txt
```

### 2. Установите Stockfish (для режима vs AI)

<details>
<summary><b>Windows</b></summary>

1. Скачайте с [stockfishchess.org](https://stockfishchess.org/download/)
2. Распакуйте архив
3. Укажите путь к `stockfish.exe` в массиве `_SF_CANDIDATES` в файле `backend/ai_adapter.py`

</details>

<details>
<summary><b>Linux (Ubuntu / Debian)</b></summary>

```bash
sudo apt update && sudo apt install stockfish
```

</details>

<details>
<summary><b>macOS</b></summary>

```bash
brew install stockfish
```

</details>

### 3. Запустите сервер

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Откройте в браузере: **http://localhost:8000**

---

## 🌐 Игра с другом через интернет

Используйте [LocalTunnel](https://theboroer.github.io/localtunnel-www/) для публикации локального сервера:

```bash
# Установка (нужен Node.js)
npm install -g localtunnel

# Запуск туннеля
lt --port 8000
```

Вы получите ссылку вида `https://xxxx.loca.lt` — отправьте её другу.

> **Примечание:** При первом открытии LocalTunnel попросит ввести ваш внешний IP. Узнать его можно на [2ip.ru](https://2ip.ru).

---

## 📡 WebSocket-протокол

<details>
<summary>Клиент → Сервер</summary>

| Тип | Описание |
|-----|----------|
| `join` | Подключиться к комнате или создать новую |
| `roll_dice` | Бросить кубик |
| `move` | Сделать ход (`from`, `to`, `promotion?`) |
| `end_turn` | Завершить ход досрочно |
| `surrender` | Сдаться |
| `rematch` | Проголосовать за реванш |
| `get_state` | Запросить текущее состояние |

</details>

<details>
<summary>Сервер → Клиент</summary>

| Тип | Описание |
|-----|----------|
| `joined` | Подтверждение входа + полное состояние |
| `opponent_joined` | Соперник подключился |
| `dice_rolled` | Результат броска кубика |
| `moved` | Ход сделан, новый FEN |
| `turn_changed` | Ход перешёл к другому игроку |
| `game_over` | Игра завершена (`winner`, `by_surrender?`) |
| `rematch_vote` | Текущий счёт голосов за реванш |
| `rematch_start` | Реванш начался, новое состояние |
| `state` | Полный снимок состояния игры |
| `error` | Сообщение об ошибке |

</details>

---

## 🗺️ Пример раунда

Выпало **4**:

```
♙ e2→e4   стоимость 2   осталось 2
♘ g1→f3   стоимость 2   осталось 0  ✓ (конь теперь стоит 2, а не 3!)
─────────────────────────────────────
Ход переходит сопернику
```

---

<div align="center">

Сделано с ♟️ и 🎲

</div>
