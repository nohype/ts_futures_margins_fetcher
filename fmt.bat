@echo off

echo ===== Running `black .` =====
%~dp0\.venv\Scripts\black.exe .

echo.
echo ===== Running `isort --profile black .` =====
%~dp0\.venv\Scripts\isort.exe --profile black .

echo.
echo ===== Finished =====

