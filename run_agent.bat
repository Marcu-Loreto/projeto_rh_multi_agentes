@echo off
REM Script para executar o agente interativamente

echo ========================================
echo  Agente de Suporte RH - Modo Interativo
echo ========================================
echo.

REM Verifica se as dependências estão instaladas
python -c "import dotenv" 2>nul
if errorlevel 1 (
    echo [ERRO] Dependências não instaladas!
    echo.
    echo Instalando dependências...
    python -m pip install --user python-dotenv langchain-openai langgraph pydantic
    echo.
)

REM Executa o agente
python run_agent.py %*
