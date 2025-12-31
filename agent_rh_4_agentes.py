"""
Sistema de Atendimento RH com RAG - 4 Agentes Especializados
=============================================================

Este sistema possui 4 agentes especializados em RH:
1. Agente de Benefícios
2. Agente de Segurança do Trabalho
3. Agente de Ambulatório
4. Agente de Folha de Pagamento
"""

from dotenv import load_dotenv
from typing import Annotated, Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from pydantic import BaseModel, Field
import os
from pathlib import Path
from datetime import datetime
import pytz

# Load environment variables
load_dotenv()

# ============================================================================
# TIMEZONE E CUMPRIMENTOS CONTEXTUALIZADOS
# ============================================================================

def get_sao_paulo_time():
    """
    Retorna o horário atual no timezone de São Paulo (America/Sao_Paulo).
    
    Returns:
        datetime: Objeto datetime com timezone de São Paulo
    """
    sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
    return datetime.now(sao_paulo_tz)


def get_contextual_greeting():
    """
    Retorna um cumprimento contextualizado baseado no horário de São Paulo.
    
    Returns:
        str: "Bom dia", "Boa tarde" ou "Boa noite"
    """
    current_time = get_sao_paulo_time()
    hour = current_time.hour
    
    if 5 <= hour < 12:
        return "Bom dia"
    elif 12 <= hour < 18:
        return "Boa tarde"
    else:
        return "Boa noite"


def get_formatted_time():
    """
    Retorna o horário atual de São Paulo formatado.
    
    Returns:
        str: Horário formatado (ex: "14:30 - Terça-feira, 31/12/2025")
    """
    current_time = get_sao_paulo_time()
    weekdays = {
        0: "Segunda-feira",
        1: "Terça-feira",
        2: "Quarta-feira",
        3: "Quinta-feira",
        4: "Sexta-feira",
        5: "Sábado",
        6: "Domingo"
    }
    weekday = weekdays[current_time.weekday()]
    return current_time.strftime(f"%H:%M - {weekday}, %d/%m/%Y")

# ============================================================================
# PASSO 1: FUNÇÃO PARA CARREGAR DOCUMENTOS DE ARQUIVOS .TXT
# ============================================================================

def load_documents_from_directory(directory_path: str, category: str) -> list[Document]:
    """
    Carrega todos os arquivos .txt de um diretório e converte em Documents.
    
    Args:
        directory_path: Caminho do diretório com os arquivos .txt
        category: Categoria dos documentos (benefits, safety, clinic, payroll)
    
    Returns:
        Lista de Document objects
    """
    documents = []
    dir_path = Path(directory_path)
    
    if not dir_path.exists():
        print(f"⚠️  Diretório não encontrado: {directory_path}")
        return documents
    
    # Busca todos os arquivos .txt no diretório
    txt_files = list(dir_path.glob("*.txt"))
    
    if not txt_files:
        print(f"⚠️  Nenhum arquivo .txt encontrado em: {directory_path}")
        return documents
    
    for txt_file in txt_files:
        try:
            # Lê o conteúdo do arquivo
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Cria o Document com metadata
            doc = Document(
                page_content=content,
                metadata={
                    "source": txt_file.stem,  # Nome do arquivo sem extensão
                    "category": category,
                    "file_path": str(txt_file),
                    "version": "1.0"
                }
            )
            documents.append(doc)
            print(f"  ✓ Carregado: {txt_file.name}")
            
        except Exception as e:
            print(f"  ✗ Erro ao carregar {txt_file.name}: {e}")
    
    return documents


# ============================================================================
# PASSO 2: CARREGAR BASES DE CONHECIMENTO DOS ARQUIVOS
# ============================================================================

print("📚 Carregando bases de conhecimento dos arquivos...")
print()

# Diretório base RAG
RAG_BASE_DIR = "RAG"

# Carregar documentos de cada categoria
print("📁 Benefícios:")
benefits_knowledge = load_documents_from_directory(
    f"{RAG_BASE_DIR}/beneficios",
    category="benefits"
)

print("\n📁 Segurança do Trabalho:")
safety_knowledge = load_documents_from_directory(
    f"{RAG_BASE_DIR}/seguranca",
    category="safety"
)

print("\n📁 Ambulatório:")
clinic_knowledge = load_documents_from_directory(
    f"{RAG_BASE_DIR}/ambulatorio",
    category="clinic"
)

print("\n📁 Folha de Pagamento:")
payroll_knowledge = load_documents_from_directory(
    f"{RAG_BASE_DIR}/folha_pagamento",
    category="payroll"
)

# Combinar todos os documentos
all_documents = benefits_knowledge + safety_knowledge + clinic_knowledge + payroll_knowledge

print(f"\n✅ Total de documentos carregados: {len(all_documents)}")

if len(all_documents) == 0:
    print("\n❌ ERRO: Nenhum documento foi carregado!")
    print("Verifique se os arquivos .txt existem nos diretórios RAG/")
    exit(1)

# ============================================================================
# PASSO 3: CRIAR VECTOR STORE
# ============================================================================

print("\n🔄 Criando vector store...")

# Embeddings para converter texto em vetores
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vectorstore = Chroma.from_documents(
    documents=all_documents,
    embedding=embeddings,
    collection_name="rh_knowledge_base",
    # persist_directory="./chroma_db_rh"  # Descomente para persistir em disco
)

# Criar retriever
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 2}  # Retorna top 2 documentos mais relevantes
)

print("✅ Vector store criado com sucesso!\n")


# ============================================================================
# PASSO 2: DEFINIR O STATE
# ============================================================================

class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_type: str | None
    next_node: str | None
    retrieved_context: str | None
    current_time: str | None
    greeting: str | None

# ============================================================================
# PASSO 3: CONFIGURAR LLM
# ============================================================================

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, max_tokens=400)

# ============================================================================
# PASSO 4: PYDANTIC MODELS
# ============================================================================

class InitialRouter(BaseModel):
    """Determine whether to continue conversation or classify a user query."""
    next_node: Literal["receptionist", "classifier"] = Field(
        ...,
        description="Choose 'classifier' if the user presents a clear HR question. Otherwise, choose 'receptionist'.",
    )


class MessageClassifier(BaseModel):
    """Classify the user's query into HR categories."""
    message_type: Literal["benefits", "safety", "clinic", "payroll"] = Field(
        ...,
        description="""Classify the message as:
        - 'benefits': plano de saúde, vale refeição, vale transporte, benefícios
        - 'safety': segurança do trabalho, EPIs, acidentes, treinamentos de segurança
        - 'clinic': ambulatório, atestados médicos, exames, saúde ocupacional
        - 'payroll': salário, férias, 13º, holerite, rescisão, folha de pagamento
        """,
    )

# ============================================================================
# PASSO 5: NODES DO GRAFO
# ============================================================================

def route_initial_message(state: State):
    """Router inicial."""
    last_message = state["messages"][-1]
    router_llm = llm.with_structured_output(InitialRouter)
    result = router_llm.invoke([
        {
            "role": "system",
            "content": """You are an expert at routing user messages for an HR support system.
            If the message is a simple greeting, thank you, or conversational, route to 'receptionist'.
            If the message contains a specific question about HR topics (benefits, safety, medical, payroll), route to 'classifier'.""",
        },
        {"role": "user", "content": last_message.content},
    ])
    
    # Adicionar informações de timezone e cumprimento ao state
    greeting = get_contextual_greeting()
    current_time = get_formatted_time()
    
    return {
        "next_node": result.next_node,
        "greeting": greeting,
        "current_time": current_time
    }


def receptionist_agent(state: State):
    """Recepcionista do RH."""
    last_message = state["messages"][-1]
    greeting = state.get("greeting", "Olá")
    current_time = state.get("current_time", "")
    
    messages = [
        {
            "role": "system",
            "content": f"""Você é a recepcionista virtual do RH da CPQD. 
            
            INFORMAÇÕES CONTEXTUAIS:
            - Horário atual: {current_time} (horário de Brasília)
            - Cumprimento apropriado: {greeting}
            
            INSTRUÇÕES:
            - SEMPRE comece sua resposta com o cumprimento contextualizado ({greeting})
            - Seja cordial, profissional e acolhedora
            - Mencione o horário quando relevante
            - Ofereça ajuda com questões de:
              • Benefícios (plano de saúde, vale refeição, vale transporte)
              • Segurança do Trabalho (EPIs, acidentes, treinamentos)
              • Ambulatório (consultas, atestados, exames)
              • Folha de Pagamento (salário, férias, 13º)
            
            Mantenha a resposta breve, educada e humanizada.""",
        },
        {"role": "user", "content": last_message.content},
    ]
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


def classify_message(state: State):
    """Classificador de mensagens RH."""
    last_message = state["messages"][-1]
    classifier_llm = llm.with_structured_output(MessageClassifier)
    result = classifier_llm.invoke([
        {
            "role": "system",
            "content": """Classifique a mensagem do usuário em uma das categorias de RH:
            - 'benefits': plano de saúde, vale refeição, vale transporte, benefícios em geral
            - 'safety': segurança do trabalho, EPIs, acidentes, SESMT, treinamentos de segurança
            - 'clinic': ambulatório, atestados médicos, exames periódicos, saúde ocupacional
            - 'payroll': salário, holerite, férias, 13º salário, rescisão, folha de pagamento
            """,
        },
        {"role": "user", "content": last_message.content},
    ])
    return {"message_type": result.message_type}


def retrieve_knowledge(state: State):
    """Busca conhecimento relevante na base de dados."""
    last_message = state["messages"][-1]
    query = last_message.content
    
    print(f"\n🔍 Buscando conhecimento para: '{query}'")
    
    relevant_docs = retriever.invoke(query)
    
    if relevant_docs:
        context_parts = []
        for i, doc in enumerate(relevant_docs, 1):
            source = doc.metadata.get('source', 'unknown')
            category = doc.metadata.get('category', 'N/A')
            version = doc.metadata.get('version', 'N/A')
            context_parts.append(
                f"📄 Documento {i} [{category.upper()}] [Fonte: {source} v{version}]:\n{doc.page_content.strip()}"
            )
        context = "\n\n".join(context_parts)
        print(f"✅ Encontrados {len(relevant_docs)} documentos relevantes")
    else:
        context = "Nenhum documento relevante encontrado na base de conhecimento."
        print("⚠️ Nenhum documento encontrado")
    
    return {"retrieved_context": context}


# ============================================================================
# PASSO 6: AGENTES ESPECIALIZADOS COM RAG
# ============================================================================

def benefits_agent(state: State):
    """Agente especializado em Benefícios."""
    last_message = state["messages"][-1]
    context = state.get("retrieved_context", "")
    
    system_prompt = f"""Você é o especialista em BENEFÍCIOS do RH.

⏰ HORÁRIO ATUAL: {state.get('current_time', '')} (horário de Brasília)

📚 BASE DE CONHECIMENTO:
{context}

🎯 SUA MISSÃO:
- Use as informações da base de conhecimento para responder
- Seja específico com valores, prazos e procedimentos
- Se a base tiver informações relevantes, cite-as
- Sempre inclua contatos e ramais quando disponíveis
- Considere o horário atual ao mencionar prazos
- Responda em Português (BR)
- Seja profissional e prestativo

Áreas de especialidade: plano de saúde, vale refeição, vale alimentação, vale transporte."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_message.content},
    ]

    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


def safety_agent(state: State):
    """Agente especializado em Segurança do Trabalho."""
    last_message = state["messages"][-1]
    context = state.get("retrieved_context", "")
    
    system_prompt = f"""Você é o especialista em SEGURANÇA DO TRABALHO do RH.

⏰ HORÁRIO ATUAL: {state.get('current_time', '')} (horário de Brasília)

📚 BASE DE CONHECIMENTO:
{context}

🎯 SUA MISSÃO:
- Use as informações da base de conhecimento para responder
- Priorize a segurança do colaborador sempre
- Seja claro sobre procedimentos de emergência
- Cite normas regulamentadoras (NRs) quando relevante
- Sempre inclua contatos do SESMT
- Considere o horário atual ao mencionar prazos
- Responda em Português (BR)
- Seja firme mas empático

Áreas de especialidade: EPIs, acidentes de trabalho, treinamentos de segurança, SESMT."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_message.content},
    ]

    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


def clinic_agent(state: State):
    """Agente especializado em Ambulatório."""
    last_message = state["messages"][-1]
    context = state.get("retrieved_context", "")
    
    system_prompt = f"""Você é o especialista em AMBULATÓRIO E SAÚDE OCUPACIONAL do RH.

⏰ HORÁRIO ATUAL: {state.get('current_time', '')} (horário de Brasília)

📚 BASE DE CONHECIMENTO:
{context}

🎯 SUA MISSÃO:
- Use as informações da base de conhecimento para responder
- Seja claro sobre horários de atendimento e procedimentos
- Explique prazos para entrega de atestados
- Oriente sobre exames ocupacionais
- Sempre inclua contatos do ambulatório
- Considere o horário atual ao mencionar prazos e horários de atendimento
- Responda em Português (BR)
- Seja empático e acolhedor

Áreas de especialidade: ambulatório, atestados médicos, exames periódicos, saúde ocupacional."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_message.content},
    ]

    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


def payroll_agent(state: State):
    """Agente especializado em Folha de Pagamento."""
    last_message = state["messages"][-1]
    context = state.get("retrieved_context", "")
    
    system_prompt = f"""Você é o especialista em FOLHA DE PAGAMENTO do RH.

⏰ HORÁRIO ATUAL: {state.get('current_time', '')} (horário de Brasília)

📚 BASE DE CONHECIMENTO:
{context}

🎯 SUA MISSÃO:
- Use as informações da base de conhecimento para responder
- Seja preciso com datas, valores e cálculos
- Explique descontos e proventos claramente
- Oriente sobre procedimentos no Portal RH
- Cite legislação trabalhista quando relevante
- Considere o horário atual ao mencionar prazos de pagamento
- Responda em Português (BR)
- Seja claro e objetivo

Áreas de especialidade: salário, holerite, férias, 13º salário, rescisão, adiantamento."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_message.content},
    ]

    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


# ============================================================================
# PASSO 7: CONSTRUIR O GRAFO
# ============================================================================

graph_builder = StateGraph(State)

# Adicionar todos os nodes
graph_builder.add_node("initial_router", route_initial_message)
graph_builder.add_node("receptionist", receptionist_agent)
graph_builder.add_node("classifier", classify_message)
graph_builder.add_node("retrieve_knowledge", retrieve_knowledge)
graph_builder.add_node("benefits", benefits_agent)
graph_builder.add_node("safety", safety_agent)
graph_builder.add_node("clinic", clinic_agent)
graph_builder.add_node("payroll", payroll_agent)

# Definir o fluxo
graph_builder.add_edge(START, "initial_router")

# Router inicial
graph_builder.add_conditional_edges(
    "initial_router",
    lambda state: state.get("next_node"),
    {"receptionist": "receptionist", "classifier": "classifier"},
)

# Classifier vai para retrieve_knowledge
graph_builder.add_conditional_edges(
    "classifier",
    lambda state: state.get("message_type"),
    {
        "benefits": "retrieve_knowledge",
        "safety": "retrieve_knowledge",
        "clinic": "retrieve_knowledge",
        "payroll": "retrieve_knowledge",
    },
)

# Retrieve_knowledge vai para o agente apropriado
graph_builder.add_conditional_edges(
    "retrieve_knowledge",
    lambda state: state.get("message_type"),
    {
        "benefits": "benefits",
        "safety": "safety",
        "clinic": "clinic",
        "payroll": "payroll",
    },
)

# Definir onde o grafo termina
graph_builder.add_edge("receptionist", END)
graph_builder.add_edge("benefits", END)
graph_builder.add_edge("safety", END)
graph_builder.add_edge("clinic", END)
graph_builder.add_edge("payroll", END)

# Compilar o grafo
app = graph_builder.compile()

print("✅ Grafo RH compilado com sucesso!\n")


# ============================================================================
# PASSO 8: TESTAR O SISTEMA
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 TESTANDO SISTEMA DE ATENDIMENTO RH COM 4 AGENTES")
    print("=" * 70)
    
    # Teste 1: Benefícios
    print("\n📝 TESTE 1: Consulta sobre Benefícios")
    print("-" * 70)
    test_query_1 = "Como faço para incluir meu filho no plano de saúde?"
    print(f"Usuário: {test_query_1}\n")
    
    result_1 = app.invoke({
        "messages": [{"role": "user", "content": test_query_1}]
    })
    
    print(f"\n🤖 Agente de Benefícios: {result_1['messages'][-1].content}\n")
    
    # Teste 2: Segurança do Trabalho
    print("\n" + "=" * 70)
    print("📝 TESTE 2: Consulta sobre Segurança do Trabalho")
    print("-" * 70)
    test_query_2 = "Sofri um acidente no trabalho, o que devo fazer?"
    print(f"Usuário: {test_query_2}\n")
    
    result_2 = app.invoke({
        "messages": [{"role": "user", "content": test_query_2}]
    })
    
    print(f"\n🤖 Agente de Segurança: {result_2['messages'][-1].content}\n")
    
    # Teste 3: Ambulatório
    print("\n" + "=" * 70)
    print("📝 TESTE 3: Consulta sobre Ambulatório")
    print("-" * 70)
    test_query_3 = "Preciso entregar um atestado médico, qual o prazo?"
    print(f"Usuário: {test_query_3}\n")
    
    result_3 = app.invoke({
        "messages": [{"role": "user", "content": test_query_3}]
    })
    
    print(f"\n🤖 Agente do Ambulatório: {result_3['messages'][-1].content}\n")
    
    # Teste 4: Folha de Pagamento
    print("\n" + "=" * 70)
    print("📝 TESTE 4: Consulta sobre Folha de Pagamento")
    print("-" * 70)
    test_query_4 = "Quando recebo a primeira parcela do 13º salário?"
    print(f"Usuário: {test_query_4}\n")
    
    result_4 = app.invoke({
        "messages": [{"role": "user", "content": test_query_4}]
    })
    
    print(f"\n🤖 Agente de Folha de Pagamento: {result_4['messages'][-1].content}\n")
    
    print("=" * 70)
    print("✅ Todos os testes concluídos!")
    print("=" * 70)
# Adicione isso no final do agent_rh_4_agentes.py ou crie um novo arquivo

if __name__ == "__main__":
    print("💬 Modo Interativo - Digite 'sair' para encerrar\n")
    
    while True:
        pergunta = input("\nVocê: ").strip()
        
        if pergunta.lower() in ['sair', 'exit', 'quit']:
            print("👋 Até logo!")
            break
        
        if not pergunta:
            continue
        
        result = app.invoke({
            "messages": [{"role": "user", "content": pergunta}]
        })
        
        print(f"\n🤖 Assistente: {result['messages'][-1].content}")