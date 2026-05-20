@echo off
title [OLLAMA] qwen3:14b - Port 11434
color 0E
echo ============================================
echo    OLLAMA SERVER - Port 11434
echo ============================================
set OLLAMA_HOST=0.0.0.0:11434
ollama serve
pause