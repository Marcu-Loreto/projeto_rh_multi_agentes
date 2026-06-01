#!/bin/bash

echo "🛑 Parando serviços..."

# Diretório do script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Parar Streamlit pelo PID file
if [ -f logs/streamlit.pid ]; then
    STREAMLIT_PID=$(cat logs/streamlit.pid)
    if ps -p $STREAMLIT_PID > /dev/null 2>&1; then
        kill $STREAMLIT_PID
        echo "✅ Streamlit parado (PID: $STREAMLIT_PID)"
    else
        echo "⚠️  Streamlit já estava parado"
    fi
    rm logs/streamlit.pid
fi

# Parar LangGraph Studio se existir (rodadas antigas)
if [ -f logs/langgraph.pid ]; then
    LANGGRAPH_PID=$(cat logs/langgraph.pid)
    if ps -p $LANGGRAPH_PID > /dev/null 2>&1; then
        kill $LANGGRAPH_PID
        echo "✅ LangGraph Studio (legado) parado (PID: $LANGGRAPH_PID)"
    fi
    rm logs/langgraph.pid
fi

# Matar processos órfãos que possam ter ficado de execuções antigas
pkill -f "streamlit run app_streamlit.py" 2>/dev/null && echo "🧹 Streamlits órfãos finalizados"
pkill -f "langgraph dev" 2>/dev/null && echo "🧹 LangGraph dev órfão finalizado"

echo ""
echo "✅ Todos os serviços foram parados!"
