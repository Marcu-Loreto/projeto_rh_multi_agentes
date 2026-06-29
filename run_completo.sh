#!/usr/bin/env bash

echo "========================================"
echo "🚀 Iniciando Sistema de Atendimento RH"
echo "========================================"

# Diretório do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
cd "$SCRIPT_DIR"

# Caminhos do venv
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"
STREAMLIT="$VENV_DIR/bin/streamlit"

# Verifica se o venv e streamlit existem
if [ ! -f "$STREAMLIT" ]; then
    echo "❌ Streamlit não encontrado em $VENV_DIR"
    echo "   Execute primeiro: uv sync"
    exit 1
fi

# Cria pasta de logs se não existir
mkdir -p logs

# Mata processo anterior se existir
if [ -f logs/streamlit.pid ]; then
    OLD_PID=$(cat logs/streamlit.pid)
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "⚠️  Parando instância anterior (PID $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null
        sleep 1
    fi
fi

# Iniciar Streamlit em background usando o Python do venv diretamente
echo "📱 Iniciando Streamlit..."
"$PYTHON" -m streamlit run app_streamlit.py \
    --server.port 8501 \
    --server.headless true \
    > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo "$STREAMLIT_PID" > logs/streamlit.pid

# Aguarda e verifica se subiu
sleep 3

if kill -0 "$STREAMLIT_PID" 2>/dev/null; then
    echo ""
    echo "✅ Serviço iniciado!"
    echo ""
    echo "📱 Streamlit:    http://localhost:8501"
    echo "📊 Telemetria:   https://cloud.langfuse.com (acessar dashboard do projeto)"
    echo ""
    echo "PID Streamlit: $STREAMLIT_PID (salvo em logs/streamlit.pid)"
    echo "Para parar:    bash stop_services.sh"
    echo "Logs:          logs/streamlit.log"
else
    echo ""
    echo "❌ Streamlit falhou ao iniciar. Verifique os logs:"
    echo "   cat logs/streamlit.log"
    echo ""
    cat logs/streamlit.log
    exit 1
fi
