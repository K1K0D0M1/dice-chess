#!/usr/bin/env bash
# build.sh — запускается Render при каждом деплое

set -e

echo "==> Installing Python dependencies..."
pip install -r backend/requirements.txt

echo "==> Downloading Stockfish binary..."
mkdir -p /opt/stockfish
cd /tmp

# Скачиваем Stockfish 16 для Linux x86_64
SF_URL="https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-ubuntu-x86-64.tar"
curl -L "$SF_URL" -o stockfish.tar
tar -xf stockfish.tar
# Бинарник называется stockfish/stockfish-ubuntu-x86-64
cp stockfish/stockfish-ubuntu-x86-64 /opt/stockfish/stockfish
chmod +x /opt/stockfish/stockfish

echo "==> Stockfish installed at /opt/stockfish/stockfish"
/opt/stockfish/stockfish --version 2>/dev/null || echo "(version check skipped)"

echo "==> Build complete!"
