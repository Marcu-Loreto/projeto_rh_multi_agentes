@echo off
echo ========================================
echo 🚀 Iniciando Sistema Completo de RH
echo ========================================
echo.
echo Abrindo:
echo   1. Streamlit (Interface Web)
echo   2. LangGraph Studio (Visualizacao do Grafo)
echo.
echo ========================================
## comando para rodar os 2 bash run_completo.sh
REM Abrir Streamlit em nova janela
start "Streamlit - Interface Web" cmd /k "cd /d %~dp0 && call .venv/bin/activate && streamlit run app_streamlit.py"

REM Aguardar 2 segundos
timeout /t 2 /nobreak >nul

REM Abrir LangGraph Studio em nova janela
start "LangGraph Studio" cmd /k "cd /d %~dp0 && call .venv/bin/activate && langgraph dev"

echo.
echo ✅ Ambos os servicos foram iniciados!
echo.
echo 📱 Streamlit: http://localhost:8501
echo 📊 LangGraph Studio: https://smith.langchain.com/studio/
echo.
echo Pressione qualquer tecla para fechar esta janela...
pause >nul
