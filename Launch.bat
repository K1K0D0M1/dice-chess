@echo off
title Dice Chess Launcher
chcp 65001 > nul

echo ====================================================
echo  ЗАПУСК DICE CHESS И ЛОКАЛЬНОГО ТУННЕЛЯ
echo ====================================================

:: 1. Переходим в директорию проекта
cd /d "C:\Users\ASUS\Downloads\dice_chess\dice_chess\backend"

:: 2. Запускаем Бэкенд Uvicorn в отдельном фоновом окне
echo Запуск сервера Uvicorn...
start "Dice Chess Backend" cmd /k "uvicorn main:app --host 127.0.0.1 --port 8000"

:: 3. Запускаем LocalTunnel в отдельном фоновом окне
echo Запуск LocalTunnel...
start "LocalTunnel" cmd /k "lt --port 8000"

:: 4. Пауза 2 секунды, чтобы порты освободились, и открытие локальной игры
timeout /t 2 > nul
echo Открытие игры в браузере...
start http://127.0.0.1:8000

echo ====================================================
echo  ВСЁ ГОТОВО!
echo  1. Скопируйте ссылку из окна LocalTunnel и отправьте другу.
echo  2. Друг сам увидит ваш IP на экране и сможет войти.
echo ====================================================
echo.
pause