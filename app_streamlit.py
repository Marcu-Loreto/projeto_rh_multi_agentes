"""
🤖 Interface Streamlit - Sistema de Atendimento RH
===================================================

Interface web moderna para interagir com os 5 agentes especializados de RH.
"""

import streamlit as st
from agent_rh_4_agentes import (
    app,
    get_sao_paulo_time,
    get_contextual_greeting,
    get_formatted_time,
    get_run_config,
)
import time

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Assistente RH - CPQD",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CSS CUSTOMIZADO
# ============================================================================

st.markdown("""
<style>
    /* Tema principal */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Container do chat */
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Mensagens do usuário */
    .stChatMessage[data-testid="user-message"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Mensagens do assistente */
    .stChatMessage[data-testid="assistant-message"] {
        background-color: white;
        border-left: 4px solid #667eea;
    }
    
    /* Título */
    h1 {
        color: white;
        text-align: center;
        font-size: 3em;
        margin-bottom: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Subtítulo */
    .subtitle {
        color: white;
        text-align: center;
        font-size: 1.2em;
        margin-bottom: 30px;
        opacity: 0.9;
    }
    
    /* Badges dos agentes */
    .agent-badge {
        display: inline-block;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9em;
        font-weight: bold;
        margin: 5px;
    }
    
    .badge-benefits {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .badge-safety {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
    }
    
    .badge-clinic {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
    }
    
    .badge-payroll {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
    }

    .badge-vacation {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        color: white;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: rgba(255, 255, 255, 0.95);
    }
    
    /* Input de texto */
    .stTextInput input {
        border-radius: 25px;
        border: 2px solid #667eea;
        padding: 12px 20px;
        font-size: 1em;
    }
    
    /* Botões */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 25px;
        padding: 10px 30px;
        border: none;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# INICIALIZAÇÃO DO SESSION STATE
# ============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_history" not in st.session_state:
    st.session_state.agent_history = []

# ============================================================================
# HEADER
# ============================================================================

st.markdown("# 🤖 Assistente Virtual de RH")
st.markdown('<p class="subtitle">Seu suporte especializado em Recursos Humanos</p>', unsafe_allow_html=True)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("## 📋 Agentes Especializados")
    
    st.markdown("""
    <div class="agent-badge badge-benefits">💼 Benefícios</div>
    <div class="agent-badge badge-safety">🦺 Segurança</div>
    <div class="agent-badge badge-clinic">🏥 Ambulatório</div>
    <div class="agent-badge badge-payroll">💰 Folha de Pagamento</div>
    <div class="agent-badge badge-vacation">🏖️ Férias</div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Exibir horário e cumprimento
    st.markdown("⏰ **Horário Atual**")
    current_time_display = get_formatted_time()
    greeting_display = get_contextual_greeting()
    st.info(f"{greeting_display}!\n\n{current_time_display}")
    
    st.markdown("---")
    
    st.markdown("### 💡 Como usar")
    st.markdown("""
    1. Digite sua pergunta no campo abaixo
    2. O sistema identificará o agente adequado
    3. Receba uma resposta baseada em nossa base de conhecimento
    """)
    
    st.markdown("---")
    
    st.markdown("### 📊 Estatísticas")
    st.metric("Mensagens enviadas", len(st.session_state.messages) // 2)
    
    if st.session_state.agent_history:
        agent_counts = {}
        for agent in st.session_state.agent_history:
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        st.markdown("#### Agentes consultados:")
        for agent, count in agent_counts.items():
            emoji = {
                "benefits": "💼",
                "safety": "🦺", 
                "clinic": "🏥",
                "payroll": "💰",
                "vacation": "🏖️",
                "receptionist": "👋"
            }.get(agent, "🤖")
            st.markdown(f"{emoji} **{agent.title()}**: {count}x")
    
    st.markdown("---")
    
    if st.button("🗑️ Limpar Conversa", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent_history = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📚 Base de Conhecimento")
    st.info("8 documentos carregados")

# ============================================================================
# ÁREA DE CHAT
# ============================================================================

# Container para mensagens
chat_container = st.container()

with chat_container:
    # Exibir mensagens anteriores
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# ============================================================================
# INPUT DO USUÁRIO
# ============================================================================

if prompt := st.chat_input("Digite sua pergunta sobre RH..."):
    # Adicionar mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Exibir mensagem do usuário
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Processar com o agente
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Mostrar indicador de carregamento
        with st.spinner("🤔 Processando sua pergunta..."):
            try:
                # Invocar o grafo LangGraph (com telemetria Langfuse se configurada)
                result = app.invoke(
                    {"messages": [{"role": "user", "content": prompt}]},
                    config=get_run_config(),
                )
                
                # Extrair resposta
                assistant_message = result['messages'][-1].content
                
                # Detectar qual agente respondeu (baseado no tipo de mensagem)
                message_type = result.get('message_type', 'unknown')
                st.session_state.agent_history.append(message_type)
                
                # Adicionar badge do agente
                agent_badges = {
                    "benefits": '<span class="agent-badge badge-benefits">💼 Benefícios</span>',
                    "safety": '<span class="agent-badge badge-safety">🦺 Segurança</span>',
                    "clinic": '<span class="agent-badge badge-clinic">🏥 Ambulatório</span>',
                    "payroll": '<span class="agent-badge badge-payroll">💰 Folha de Pagamento</span>',
                    "vacation": '<span class="agent-badge badge-vacation">🏖️ Férias</span>',
                }
                
                badge = agent_badges.get(message_type, "")
                
                # Exibir resposta com animação de digitação
                full_response = ""
                for chunk in assistant_message.split():
                    full_response += chunk + " "
                    time.sleep(0.02)
                    message_placeholder.markdown(badge + "\n\n" + full_response + "▌", unsafe_allow_html=True)
                
                message_placeholder.markdown(badge + "\n\n" + assistant_message, unsafe_allow_html=True)
                
            except Exception as e:
                error_message = f"❌ Erro ao processar: {str(e)}"
                message_placeholder.error(error_message)
                assistant_message = error_message
        
        # Adicionar resposta ao histórico
        st.session_state.messages.append({"role": "assistant", "content": assistant_message})

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: white; opacity: 0.8;'>
    <p>🤖 Powered by LangGraph + OpenAI | 📚 Base de Conhecimento RAG</p>
    <p style='font-size: 0.9em;'>CPQD - Centro de Pesquisa e Desenvolvimento em Telecomunicações</p>
</div>
""", unsafe_allow_html=True)
