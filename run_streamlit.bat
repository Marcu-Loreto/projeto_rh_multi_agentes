@echo off
echo 🚀 Iniciando Assistente Virtual de RH...
echo.

REM Ativar ambiente virtual
call .venv\Scripts\activate.ps1

REM Executar Streamlit
streamlit run app_streamlit.py

pause
