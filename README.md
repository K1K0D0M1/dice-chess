# ♟️🎲 Dice Chess — Шахматы с кубиком

Мультиплеерные шахматы с кубиком.
Кубик (d6) определяет **количество ходов за раунд** — трать их на любые фигуры.

---

## Структура проекта

```
dice_chess/
├── backend/
│   ├── main.py          — FastAPI WebSocket сервер
│   ├── game.py          — игровая логика + правила кубика
│   ├── ai_adapter.py    — Stockfish AI интеграция
│   └── requirements.txt
└── frontend/
    └── index.html       — полный клиент (React + chess.js в браузере)
```

---

## Быстрый старт

### 1. Установить зависимости

```bash
# Stockfish (шахматный движок)
# Ubuntu/Debian:
sudo apt install stockfish

# macOS:
brew install stockfish

# Windows: скачать с https://stockfishchess.org/download/

# Python зависимости
cd backend
pip install -r requirements.txt
```

### 2. Запустить сервер

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Открыть игру

Открыть в браузере: `frontend/index.html`

Или (если нужен HTTPS для WebSocket):
```bash
cd frontend
python3 -m http.server 3000
# Открыть http://localhost:3000
```

---

## Как играть с другом

1. Игрок 1 нажимает **"Играть с другом"** → получает **код комнаты** (8 символов)
2. Игрок 1 копирует ссылку (клик по коду комнаты вверху)
3. Игрок 2 вставляет ссылку в браузер → попадает в ту же комнату
4. Игра начинается!

---

## Правила (Dice Chess — вариант с бюджетом ходов)

| Событие | Описание |
|---------|----------|
| 🎲 Бросок кубика | Выпадает 1–6 — это ваш бюджет ходов |
| ♟ Ходы | Двигайте любые фигуры в любом порядке |
| 💰 Бюджет | Каждый ход = 1 единица бюджета |
| ✋ Завершение | Бюджет = 0 → автоматический переход хода; или кнопка "Завершить раньше" |
| 🏆 Победа | Стандартный мат королю соперника |

### Пример

Выпало **4** → можно сделать 4 хода:
- Пешка e2–e4 (1)
- Конь g1–f3 (2)
- Слон f1–c4 (3)
- Ферзь d1–h5 (4) — **буддет исчерпан, ход переходит**

---

## Деплой на Render.com (бесплатно)

1. Создать аккаунт на https://render.com
2. New → Web Service → подключить GitHub репозиторий
3. Settings:
   - **Build command:** `pip install -r backend/requirements.txt && apt-get install -y stockfish`
   - **Start command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. В файле `frontend/index.html` изменить `WS_URL` на адрес Render-сервиса
5. Фронтенд можно задеплоить на GitHub Pages или Vercel

---

## Настройки AI

В файле `backend/ai_adapter.py`:

```python
STOCKFISH_PATH = "/usr/games/stockfish"  # путь к бинарнику

# depth в get_ai_moves() — глубина просчёта (4-15)
# 4-6 = слабый ИИ (подходит для начинающих)
# 8-12 = средний ИИ
# 15+ = сильный ИИ
```

---

## WebSocket протокол

```
Клиент → Сервер:
  join       { name, room_id|null, vs_ai }
  roll_dice  {}
  move       { from, to, promotion? }
  end_turn   {}

Сервер → Клиент:
  joined         { room_id, role, player_id, state }
  dice_rolled    { dice_value, moves_left, by }
  moved          { move, fen, moves_left, dice_value, by }
  turn_changed   { current_turn, fen, ... }
  game_over      { winner, fen }
  error          { message }
```
