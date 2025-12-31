"""
Exemplo Completo: Agente LangGraph com RAG
==========================================

Este arquivo mostra um exemplo funcional de como integrar RAG
com agentes LangGraph. Use como referência antes de implementar.
"""

from dotenv import load_dotenv
from typing import Annotated, Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# ============================================================================
# PASSO 1: CONFIGURAR A BASE DE CONHECIMENTO (RAG)
# ============================================================================

print("📚 Criando base de conhecimento...")

# Embeddings para converter texto em vetores
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Documentos de exemplo - Base Técnica
technical_knowledge = [
    Document(
        page_content="""
        PROCEDIMENTO DE LOGIN:
        1. Acesse https://portal.empresa.com
        2. Digite seu email corporativo
        3. Digite sua senha
        4. Se esqueceu a senha, clique em 'Recuperar Senha'
        5. Você receberá um email com instruções
        """,
        metadata={"source": "manual_login", "category": "technical", "version": "2.0"}
    ),
    Document(
        page_content="""
        SOLUÇÃO PARA PROBLEMAS DE REDE:
        - Verifique se o cabo está conectado
        - Reinicie o roteador (desconecte por 30 segundos)
        - Teste a conexão em outro dispositivo
        - Se persistir, contate o suporte de TI: ti@empresa.com
        """,
        metadata={"source": "manual_rede", "category": "technical", "version": "1.5"}
    ),
    Document(
        page_content="""
        ERROS COMUNS DE AUTENTICAÇÃO:
        - Erro 401: Senha incorreta ou expirada
        - Erro 403: Conta bloqueada por múltiplas tentativas
        - Erro 500: Problema no servidor, tente novamente em 5 minutos
        
        Para redefinir senha: acesse portal.empresa.com/reset
        """,
        metadata={"source": "manual_auth", "category": "technical", "version": "2.1"}
    ),
]

# Documentos de exemplo - Base Financeira
financial_knowledge = [
    Document(
        page_content="""
        INFORMAÇÕES SOBRE FATURA:
        - Geração: Todo dia 5 do mês
        - Vencimento: Dia 15 do mês
        - Consulta: Portal > Minha Conta > Faturas
        - Formas de pagamento: Boleto, PIX, Cartão de Crédito
        """,
        metadata={"source": "manual_fatura", "category": "financial", "version": "3.0"}
    ),
    Document(
        page_content="""
        PROCESSO DE REEMBOLSO:
        1. Acesse: Portal > Financeiro > Solicitar Reembolso
        2. Anexe comprovantes (PDF ou imagem)
        3. Preencha justificativa
        4. Prazo de análise: 5 dias úteis
        5. Pagamento: Até 10 dias após aprovação
        
        Valores acima de R$ 1000 requerem aprovação gerencial.
        """,
        metadata={"source": "manual_reembolso", "category": "financial", "version": "2.5"}
    ),
]

# Criar vector store (banco de dados vetorial)
vectorstore = Chroma.from_documents(
    documents=technical_knowledge + financial_knowledge,
    embedding=embeddings,
    collection_name="knowledge_base",
    # persist_directory="./chroma_db"  # Descomente para persistir em disco
)

# Criar retriever
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 2}  # Retorna top 2 documentos mais relevantes
)

print("✅ Base de conhecimento criada com sucesso!\n")

# ============================================================================
# PASSO 2: DEFINIR O STATE COM CONTEXTO RAG
# ============================================================================

class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_type: str | None
    next_node: str | None
    retrieved_context: str | None  # NOVO: Contexto do RAG


# ============================================================================
# PASSO 3: CONFIGURAR LLM
# ============================================================================

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, max_tokens=300)


# ============================================================================
# PASSO 4: PYDANTIC MODELS (MESMOS DE ANTES)
# ============================================================================

class InitialRouter(BaseModel):
    """Determine whether to continue conversation or classify a user query."""
    next_node: Literal["receptionist", "classifier"] = Field(
        ...,
        description="Choose 'classifier' if the user presents a clear technical or financial question. Otherwise, choose 'receptionist'.",
    )


class MessageClassifier(BaseModel):
    """Classify the user's query into technical or financial."""
    message_type: Literal["technical", "financial"] = Field(
        ...,
        description="Classify the message as 'technical' or 'financial'.",
    )


# ============================================================================
# PASSO 5: NODES DO GRAFO
# ============================================================================

def route_initial_message(state: State):
    """Router inicial (sem mudanças)."""
    last_message = state["messages"][-1]
    router_llm = llm.with_structured_output(InitialRouter)
    result = router_llm.invoke([
        {
            "role": "system",
            "content": """You are an expert at routing user messages.
            If the message is a simple greeting, a thank you, or conversational fluff, route to the 'receptionist'.
            If the message contains a specific question or problem about technical or financial issues, route to the 'classifier'.""",
        },
        {"role": "user", "content": last_message.content},
    ])
    return {"next_node": result.next_node}


def receptionist_agent(state: State):
    """Receptionist (sem mudanças)."""
    last_message = state["messages"][-1]
    messages = [
        {
            "role": "system",
            "content": "You are a friendly and helpful AI receptionist for a customer service center. Greet the user, and ask them how you can help with their technical or financial questions. Keep your responses brief and polite.",
        },
        {"role": "user", "content": last_message.content},
    ]
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


def classify_message(state: State):
    """Classifier (sem mudanças)."""
    last_message = state["messages"][-1]
    classifier_llm = llm.with_structured_output(MessageClassifier)
    result = classifier_llm.invoke([
        {
            "role": "system",
            "content": """Classify the user message as either:
            - 'technical': if it asks for technical support, internet issues, message error, login problems, or any technical assistance
            - 'financial': if it asks for financial information, prices, billing, or payment issues
            """,
        },
        {"role": "user", "content": last_message.content},
    ])
    return {"message_type": result.message_type}


# ============================================================================
# PASSO 6: NOVO NODE - RETRIEVE KNOWLEDGE (RAG)
# ============================================================================

def retrieve_knowledge(state: State):
    """
    🆕 NODE NOVO: Busca conhecimento relevante na base de dados.
    
    Este node é executado DEPOIS do classifier e ANTES dos agentes.
    Ele busca documentos relevantes e adiciona ao state.
    """
    last_message = state["messages"][-1]
    query = last_message.content
    
    print(f"\n🔍 Buscando conhecimento para: '{query}'")
    
    # Busca documentos relevantes usando o retriever
    relevant_docs = retriever.invoke(query)
    
    # Formata o contexto com os documentos encontrados
    if relevant_docs:
        context_parts = []
        for i, doc in enumerate(relevant_docs, 1):
            source = doc.metadata.get('source', 'unknown')
            version = doc.metadata.get('version', 'N/A')
            context_parts.append(
                f"📄 Documento {i} [Fonte: {source} v{version}]:\n{doc.page_content.strip()}"
            )
        context = "\n\n".join(context_parts)
        print(f"✅ Encontrados {len(relevant_docs)} documentos relevantes")
    else:
        context = "Nenhum documento relevante encontrado na base de conhecimento."
        print("⚠️ Nenhum documento encontrado")
    
    return {"retrieved_context": context}


# ============================================================================
# PASSO 7: AGENTES MODIFICADOS PARA USAR RAG
# ============================================================================

def technical_agent(state: State):
    """
    🔄 MODIFICADO: Agente técnico agora usa contexto do RAG.
    """
    last_message = state["messages"][-1]
    
    # 🆕 Pega o contexto recuperado do RAG
    context = state.get("retrieved_context", "")
    
    # 🆕 Monta o prompt incluindo o contexto da base de conhecimento
    system_prompt = f"""You are a technical support specialist.

📚 KNOWLEDGE BASE CONTEXT:
{context}

🎯 YOUR MISSION:
- Use the information from the knowledge base above to answer the user's question
- If the knowledge base has relevant information, cite it in your answer
- If the knowledge base doesn't cover the topic, provide general technical guidance
- Always be clear, helpful, and professional
- Answer in Portuguese (BR)
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_message.content},
    ]

    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


def financial_agent(state: State):
    """
    🔄 MODIFICADO: Agente financeiro agora usa contexto do RAG.
    """
    last_message = state["messages"][-1]
    
    # 🆕 Pega o contexto recuperado do RAG
    context = state.get("retrieved_context", "")
    
    # 🆕 Monta o prompt incluindo o contexto da base de conhecimento
    system_prompt = f"""You are a financial support specialist.

📚 KNOWLEDGE BASE CONTEXT:
{context}

🎯 YOUR MISSION:
- Use the information from the knowledge base above to answer the user's question
- If the knowledge base has relevant information, cite it in your answer
- If the knowledge base doesn't cover the topic, provide general financial guidance
- Always be empathetic, precise, and professional
- Answer in Portuguese (BR)
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_message.content},
    ]

    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


# ============================================================================
# PASSO 8: CONSTRUIR O GRAFO COM RAG
# ============================================================================

graph_builder = StateGraph(State)

# Adicionar todos os nodes
graph_builder.add_node("initial_router", route_initial_message)
graph_builder.add_node("receptionist", receptionist_agent)
graph_builder.add_node("classifier", classify_message)
graph_builder.add_node("retrieve_knowledge", retrieve_knowledge)  # 🆕 NOVO NODE
graph_builder.add_node("technical", technical_agent)
graph_builder.add_node("financial", financial_agent)

# Definir o fluxo
graph_builder.add_edge(START, "initial_router")

# Router inicial decide entre receptionist e classifier
graph_builder.add_conditional_edges(
    "initial_router",
    lambda state: state.get("next_node"),
    {"receptionist": "receptionist", "classifier": "classifier"},
)

# 🆕 MODIFICADO: Classifier agora vai para retrieve_knowledge
graph_builder.add_conditional_edges(
    "classifier",
    lambda state: state.get("message_type"),
    {
        "technical": "retrieve_knowledge",  # Vai buscar conhecimento primeiro
        "financial": "retrieve_knowledge",  # Vai buscar conhecimento primeiro
    },
)

# 🆕 NOVO: Depois de recuperar conhecimento, vai para o agente apropriado
graph_builder.add_conditional_edges(
    "retrieve_knowledge",
    lambda state: state.get("message_type"),
    {
        "technical": "technical",
        "financial": "financial",
    },
)

# Definir onde o grafo termina
graph_builder.add_edge("receptionist", END)
graph_builder.add_edge("technical", END)
graph_builder.add_edge("financial", END)

# Compilar o grafo
app = graph_builder.compile()

print("✅ Grafo compilado com sucesso!\n")


# ============================================================================
# PASSO 9: TESTAR O SISTEMA
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 TESTANDO AGENTE COM RAG")
    print("=" * 70)
    
    # Teste 1: Consulta Técnica
    print("\n📝 TESTE 1: Consulta Técnica")
    print("-" * 70)
    test_query_1 = "Não consigo fazer login no sistema"
    print(f"Usuário: {test_query_1}\n")
    
    result_1 = app.invoke({
        "messages": [{"role": "user", "content": test_query_1}]
    })
    
    print(f"\n🤖 Assistente: {result_1['messages'][-1].content}\n")
    
    # Teste 2: Consulta Financeira
    print("\n" + "=" * 70)
    print("📝 TESTE 2: Consulta Financeira")
    print("-" * 70)
    test_query_2 = "Como faço para solicitar reembolso?"
    print(f"Usuário: {test_query_2}\n")
    
    result_2 = app.invoke({
        "messages": [{"role": "user", "content": test_query_2}]
    })
    
    print(f"\n🤖 Assistente: {result_2['messages'][-1].content}\n")
    
    print("=" * 70)
    print("✅ Testes concluídos!")
    print("=" * 70)
