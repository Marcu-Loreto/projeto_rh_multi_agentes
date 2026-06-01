#!/bin/bash

echo "========================================"
echo "🚀 Iniciando Sistema de Atendimento RH"
echo "========================================"

# Diretório do script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Garante que o venv existe
if [ ! -f ".venv/bin/streamlit" ]; then
    echo "❌ Streamlit não encontrado no .venv."
    echo "   Execute primeiro: uv sync"
    exit 1
fi

# Cria pasta de logs se não existir
mkdir -p logs

# Ativar ambiente virtual
source .venv/bin/activate

# Iniciar Streamlit em background — usa o binário do venv explicitamente
echo "📱 Iniciando Streamlit..."
.venv/bin/streamlit run app_streamlit.py > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo $STREAMLIT_PID > logs/streamlit.pid

sleep 2

echo ""
echo "✅ Serviço iniciado!"
echo ""
echo "📱 Streamlit:    http://localhost:8501"
echo "📊 Telemetria:   https://cloud.langfuse.com (acessar dashboard do projeto)"
echo ""
echo "PID Streamlit: $STREAMLIT_PID (salvo em logs/streamlit.pid)"
echo "Para parar:    bash stop_services.sh"
echo "Logs:          logs/streamlit.log"
