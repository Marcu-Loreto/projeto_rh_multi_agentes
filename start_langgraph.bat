@echo off
REM Script para iniciar o LangGraph Studio usando Python global
REM Como o ambiente virtual está sem pip, usamos a instalação global

echo ========================================
echo  Iniciando LangGraph Studio
echo ========================================
echo.

REM Verifica se o langgraph-cli está instalado
python -c "import langgraph" 2>nul
if errorlevel 1 (
    echo [ERRO] LangGraph não está instalado!
    echo.
    echo Instalando dependências...
    python -m pip install --user python-dotenv langchain-openai langgraph langgraph-cli pydantic
    echo.
)

REM Inicia o LangGraph Studio
echo Iniciando LangGraph Studio em http://localhost:8123
echo Pressione Ctrl+C para parar
echo.

python -m langgraph_cli dev

pause
