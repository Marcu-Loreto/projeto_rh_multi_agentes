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
import csv
from pathlib import Path
from datetime import datetime
import pytz
from guardrails import scan_input, scan_output

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
# CARREGADOR DE PROMPTS EXTERNOS
# ============================================================================
#
# Os system prompts dos agentes ficam em arquivos .md sob o diretório definido
# em PROMPTS_DIR (.env). Isso desacopla conteúdo de código: editar/versionar
# prompts sem precisar mexer em Python.

PROMPTS_DIR = Path(os.getenv("PROMPTS_DIR", "./prompts")).resolve()

# Cache simples para evitar I/O repetido em cada chamada do node
_prompt_cache: dict[str, str] = {}


def load_prompt(name: str, **kwargs) -> str:
    """
    Carrega o template de prompt 'prompts/{name}.md' e aplica substituições.

    Placeholders no template seguem o formato {variavel}. Use {{ }} no .md
    para escapar chaves literais.

    Args:
        name: Nome do prompt (sem extensão), ex.: 'benefits_agent'
        **kwargs: Variáveis para interpolar no template

    Returns:
        String pronta para ser usada como system prompt.
    """
    # 🛡️ Validação contra path traversal
    if "/" in name or "\\" in name or ".." in name:
        raise ValueError(f"Nome de prompt inválido: '{name}'. Não use separadores de path.")

    if name not in _prompt_cache:
        prompt_path = PROMPTS_DIR / f"{name}.md"
        # Garante que o path resolvido está dentro de PROMPTS_DIR
        resolved = prompt_path.resolve()
        if not str(resolved).startswith(str(PROMPTS_DIR)):
            raise ValueError(f"Tentativa de acesso fora do diretório de prompts: '{name}'")
        if not resolved.exists():
            raise FileNotFoundError(
                f"Prompt '{name}' não encontrado em {resolved}. "
                f"Verifique PROMPTS_DIR no .env."
            )
        _prompt_cache[name] = resolved.read_text(encoding="utf-8")

    template = _prompt_cache[name]
    return template.format(**kwargs) if kwargs else template


print(f"📝 PROMPTS_DIR: {PROMPTS_DIR}")


# ============================================================================
# TELEMETRIA LANGFUSE (opcional)
# ============================================================================
#
# Se LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY estiverem definidas, ativa o
# callback handler que captura traces de TODOS os nodes do grafo, prompts,
# completions e custos. Sem credenciais, a função retorna None e a app roda
# sem telemetria — comportamento seguro por padrão.

_langfuse_callback = None


def get_langfuse_callback():
    """Retorna o CallbackHandler do Langfuse se configurado, ou None."""
    global _langfuse_callback
    if _langfuse_callback is not None:
        return _langfuse_callback

    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        print("📊 Langfuse: credenciais ausentes — telemetria desativada")
        return None

    try:
        from langfuse.langchain import CallbackHandler
        _langfuse_callback = CallbackHandler()
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        print(f"📊 Langfuse: telemetria ativa → {host}")
        return _langfuse_callback
    except Exception as e:
        print(f"⚠️  Langfuse: falha ao inicializar ({e}) — telemetria desativada")
        return None


def get_run_config() -> dict:
    """
    Retorna o config padrão para passar em `app.invoke(state, config=...)`.
    Inclui o callback do Langfuse se disponível.
    """
    cb = get_langfuse_callback()
    return {"callbacks": [cb]} if cb else {}


# Inicializa o callback no boot (lazy: só a primeira chamada)
get_langfuse_callback()


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


def load_csv_documents(directory_path: str, category: str) -> list[Document]:
    """
    Carrega arquivos .csv de um diretório, criando 1 Document por linha.

    Cada linha vira um texto formatado 'coluna: valor | coluna: valor', o que
    funciona bem para busca vetorial (mantém os campos como contexto semântico).

    Args:
        directory_path: Caminho do diretório com os arquivos .csv
        category: Categoria dos documentos (ex: 'vacation')

    Returns:
        Lista de Document objects, um por linha de cada CSV.
    """
    documents: list[Document] = []
    dir_path = Path(directory_path)

    if not dir_path.exists():
        print(f"⚠️  Diretório não encontrado: {directory_path}")
        return documents

    csv_files = list(dir_path.glob("*.csv"))

    if not csv_files:
        print(f"⚠️  Nenhum arquivo .csv encontrado em: {directory_path}")
        return documents

    for csv_file in csv_files:
        try:
            with open(csv_file, "r", encoding="utf-8", newline="") as f:
                # Detecta delimitador automaticamente (vírgula, ponto-e-vírgula, tab)
                sample = f.read(2048)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                except csv.Error:
                    dialect = csv.excel  # fallback: vírgula

                reader = csv.DictReader(f, dialect=dialect)
                row_count = 0
                for row in reader:
                    parts = [
                        f"{k.strip()}: {v.strip()}"
                        for k, v in row.items()
                        if k and v and v.strip()
                    ]
                    if not parts:
                        continue
                    content = " | ".join(parts)

                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": csv_file.stem,
                            "category": category,
                            "file_path": str(csv_file),
                            "row": row_count + 1,
                            "version": "1.0",
                        },
                    )
                    documents.append(doc)
                    row_count += 1

            print(f"  ✓ Carregado: {csv_file.name} ({row_count} linhas)")

        except Exception as e:
            print(f"  ✗ Erro ao carregar {csv_file.name}: {e}")

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

print("\n📁 Férias (CSV):")
vacation_knowledge = load_csv_documents(
    f"{RAG_BASE_DIR}/ferias",
    category="vacation"
)

# Combinar todos os documentos
all_documents = (
    benefits_knowledge
    + safety_knowledge
    + clinic_knowledge
    + payroll_knowledge
    + vacation_knowledge
)

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
    rewritten_queries: list[str] | None
    current_time: str | None
    greeting: str | None
    guardrail_blocked: bool | None
    guardrail_scores: dict | None

# ============================================================================
# PASSO 3: POOL DE LLMS POR COMPLEXIDADE
# ============================================================================
#
# Estratégia de seleção de modelo balanceando custo x qualidade:
#   - simple   → tarefas determinísticas (roteamento, classificação, saudação)
#   - medium   → tarefas de reformulação/expansão (query rewriting)
#   - complex  → respostas finais especializadas (agentes RH)
#
# Cada nível tem fallback automático para um modelo OpenAI conhecido caso
# a chave/endpoint do provedor preferido não esteja configurado.

def _build_llm(level: str) -> ChatOpenAI:
    """Cria uma instância de LLM para o nível de complexidade indicado."""
    cfg = {
        "simple": {
            "model_env": "LLM_SIMPLE_MODEL",
            "default_model": "nvidia/nemotron-40b-instruct:free",
            "provider": os.getenv("LLM_SIMPLE_PROVIDER", "openrouter").lower(),
            "temperature": 0.0,
            "max_tokens": 300,
            "fallback_model": "gpt-4o-mini",
        },
        "medium": {
            "model_env": "LLM_MEDIUM_MODEL",
            "default_model": "gpt-4o-mini",
            "provider": os.getenv("LLM_MEDIUM_PROVIDER", "openai").lower(),
            "temperature": 0.3,
            "max_tokens": 250,
            "fallback_model": "gpt-4o-mini",
        },
        "complex": {
            "model_env": "LLM_COMPLEX_MODEL",
            "default_model": "gpt-4o-mini",
            "provider": os.getenv("LLM_COMPLEX_PROVIDER", "openai").lower(),
            "temperature": 0.0,
            "max_tokens": 500,
            "fallback_model": "gpt-4o-mini",
        },
    }[level]

    model_name = os.getenv(cfg["model_env"], cfg["default_model"])
    provider = cfg["provider"]

    # OpenRouter — endpoint compatível com OpenAI, acesso a modelos free e pagos.
    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        if not api_key:
            print(
                f"⚠️  OPENROUTER_API_KEY não configurada — fallback para "
                f"OpenAI/{cfg['fallback_model']} no nível '{level}'"
            )
            return ChatOpenAI(
                model=cfg["fallback_model"],
                temperature=cfg["temperature"],
                max_tokens=cfg["max_tokens"],
            )
        return ChatOpenAI(
            model=model_name,
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
            api_key=api_key,
            base_url=base_url,
        )

    # MiniMax expõe API compatível com OpenAI; basta apontar base_url + api_key próprios.
    if provider == "minimax":
        api_key = os.getenv("MINIMAX_API_KEY")
        base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.chat/v1")
        if not api_key:
            print(
                f"⚠️  MINIMAX_API_KEY não configurada — fallback para "
                f"OpenAI/{cfg['fallback_model']} no nível '{level}'"
            )
            return ChatOpenAI(
                model=cfg["fallback_model"],
                temperature=cfg["temperature"],
                max_tokens=cfg["max_tokens"],
            )
        return ChatOpenAI(
            model=model_name,
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
            api_key=api_key,
            base_url=base_url,
        )

    # Provedor padrão: OpenAI
    return ChatOpenAI(
        model=model_name,
        temperature=cfg["temperature"],
        max_tokens=cfg["max_tokens"],
    )


# Instâncias do pool (criadas uma única vez no boot)
llm_simple = _build_llm("simple")
llm_medium = _build_llm("medium")
llm_complex = _build_llm("complex")

# Alias mantido para compatibilidade com código legado que ainda referencia `llm`
llm = llm_complex

print("🤖 Pool de LLMs inicializado:")
print(f"   • simple  → {llm_simple.model_name}")
print(f"   • medium  → {llm_medium.model_name}")
print(f"   • complex → {llm_complex.model_name}\n")

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
    message_type: Literal["benefits", "safety", "clinic", "payroll", "vacation"] = Field(
        ...,
        description="""Classify the message as:
        - 'benefits': plano de saúde, vale refeição, vale transporte, benefícios
        - 'safety': segurança do trabalho, EPIs, acidentes, treinamentos de segurança
        - 'clinic': ambulatório, atestados médicos, exames, saúde ocupacional
        - 'payroll': salário, 13º, holerite, rescisão, folha de pagamento (NÃO inclua férias aqui)
        - 'vacation': férias, período aquisitivo/concessivo, abono pecuniário, venda de férias, programação de férias
        """,
    )


class RewrittenQueries(BaseModel):
    """Reformulações da pergunta do usuário para melhorar a busca semântica."""
    queries: list[str] = Field(
        ...,
        description=(
            "Lista de 3 reformulações em Português (BR) da pergunta original, "
            "expandindo termos técnicos, sinônimos e variações que ajudem na busca "
            "vetorial. Cada item deve ser uma frase declarativa curta, focada em "
            "palavras-chave do domínio de RH."
        ),
        min_length=3,
        max_length=3,
    )

# ============================================================================
# PASSO 5: NODES DO GRAFO
# ============================================================================

def route_initial_message(state: State):
    """Router inicial."""
    last_message = state["messages"][-1]
    router_llm = llm_simple.with_structured_output(InitialRouter)
    result = router_llm.invoke([
        {
            "role": "system",
            "content": load_prompt("initial_router"),
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
            "content": load_prompt(
                "receptionist",
                greeting=greeting,
                current_time=current_time,
            ),
        },
        {"role": "user", "content": last_message.content},
    ]
    reply = llm_simple.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


def classify_message(state: State):
    """Classificador de mensagens RH."""
    last_message = state["messages"][-1]
    classifier_llm = llm_simple.with_structured_output(MessageClassifier)
    result = classifier_llm.invoke([
        {
            "role": "system",
            "content": load_prompt("classifier"),
        },
        {"role": "user", "content": last_message.content},
    ])
    return {"message_type": result.message_type}


# Vocabulário por categoria para guiar a expansão da query
CATEGORY_VOCABULARY: dict[str, str] = {
    "benefits": (
        "plano de saúde, dependentes, coparticipação, rede credenciada, "
        "vale refeição, vale alimentação, vale transporte, auxílio creche, "
        "previdência privada, reembolso, carência"
    ),
    "safety": (
        "EPI, EPC, NR-6, NR-10, NR-35, CIPA, SESMT, acidente de trabalho, "
        "CAT, treinamento de segurança, brigada de incêndio, ergonomia, riscos ocupacionais"
    ),
    "clinic": (
        "atestado médico, exame admissional, exame periódico, exame demissional, "
        "ASO, médico do trabalho, ambulatório, afastamento, INSS, perícia médica"
    ),
    "payroll": (
        "salário base, holerite, contracheque, 13º salário, "
        "rescisão contratual, FGTS, INSS, IRRF, "
        "horas extras, banco de horas, adiantamento"
    ),
    "vacation": (
        "férias, período aquisitivo, período concessivo, abono pecuniário, "
        "venda de 1/3 de férias, terço constitucional, fracionamento de férias, "
        "férias coletivas, férias proporcionais, programação de férias, "
        "aviso prévio de férias, prescrição de férias, art. 129 a 153 CLT"
    ),
}


def rewrite_query(state: State):
    """Reescreve a pergunta do usuário em múltiplas variações para melhorar a busca."""
    last_message = state["messages"][-1]
    original_query = last_message.content
    category = state.get("message_type", "")
    vocabulary = CATEGORY_VOCABULARY.get(category, "")

    rewriter_llm = llm_medium.with_structured_output(RewrittenQueries)

    system_prompt = load_prompt(
        "query_rewriter",
        category=category,
        vocabulary=vocabulary,
    )

    try:
        result = rewriter_llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Pergunta original: {original_query}"},
        ])
        rewritten = result.queries
        print(f"\n✏️  Query Rewriting ({category}):")
        print(f"   Original: {original_query}")
        for i, q in enumerate(rewritten, 1):
            print(f"   Variação {i}: {q}")
    except Exception as e:
        print(f"⚠️  Falha no query rewriting, usando original: {e}")
        rewritten = []

    return {"rewritten_queries": rewritten}


def retrieve_knowledge(state: State):
    """Busca conhecimento relevante na base de dados usando multi-query com scores."""
    last_message = state["messages"][-1]
    original_query = last_message.content
    rewritten = state.get("rewritten_queries") or []

    # Lista final de queries: original + reescritas (deduplicadas, preservando ordem)
    all_queries: list[str] = []
    seen_q: set[str] = set()
    for q in [original_query, *rewritten]:
        norm = q.strip().lower()
        if norm and norm not in seen_q:
            seen_q.add(norm)
            all_queries.append(q.strip())

    print(f"\n🔍 Busca multi-query ({len(all_queries)} variações):")
    for i, q in enumerate(all_queries, 1):
        print(f"   {i}. {q}")

    # Executa cada query e agrega resultados deduplicando por (source, page_content)
    aggregated: dict[tuple, tuple[Document, float]] = {}
    for q in all_queries:
        try:
            hits = vectorstore.similarity_search_with_score(q, k=3)
        except Exception as e:
            print(f"⚠️  Erro na busca para '{q}': {e}")
            continue

        for doc, distance in hits:
            # Chroma retorna distância (menor = melhor). Convertemos em similaridade.
            similarity = 1.0 - float(distance)
            key = (doc.metadata.get("source", ""), doc.page_content[:120])
            # Mantém o melhor score caso o mesmo doc apareça em queries diferentes
            if key not in aggregated or similarity > aggregated[key][1]:
                aggregated[key] = (doc, similarity)

    # Ordena por score desc e pega top 4
    ranked = sorted(aggregated.values(), key=lambda x: x[1], reverse=True)[:4]

    if ranked:
        context_parts = []
        for i, (doc, score) in enumerate(ranked, 1):
            source = doc.metadata.get("source", "unknown")
            category = doc.metadata.get("category", "N/A")
            version = doc.metadata.get("version", "N/A")
            context_parts.append(
                f"📄 Documento {i} [{category.upper()}] [Fonte: {source} v{version}] "
                f"[score: {score:.3f}]:\n{doc.page_content.strip()}"
            )
            print(f"   ✓ {source} (score={score:.3f})")
        context = "\n\n".join(context_parts)
        print(f"✅ {len(ranked)} documentos selecionados após deduplicação")
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
    current_time = state.get("current_time", "")

    system_prompt = load_prompt(
        "benefits_agent",
        current_time=current_time,
        context=context,
    )

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
    current_time = state.get("current_time", "")

    system_prompt = load_prompt(
        "safety_agent",
        current_time=current_time,
        context=context,
    )

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
    current_time = state.get("current_time", "")

    system_prompt = load_prompt(
        "clinic_agent",
        current_time=current_time,
        context=context,
    )

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
    current_time = state.get("current_time", "")

    system_prompt = load_prompt(
        "payroll_agent",
        current_time=current_time,
        context=context,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_message.content},
    ]

    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


def vacation_agent(state: State):
    """Agente especializado em Férias."""
    last_message = state["messages"][-1]
    context = state.get("retrieved_context", "")
    current_time = state.get("current_time", "")

    system_prompt = load_prompt(
        "vacation_agent",
        current_time=current_time,
        context=context,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_message.content},
    ]

    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


# ============================================================================
# PASSO 7: GUARDRAILS NODES
# ============================================================================


def input_guardrail_node(state: State):
    """
    🛡️ Guardrail de INPUT — primeiro node do grafo.
    Valida a mensagem do usuário antes de qualquer processamento.
    Se bloqueado, marca guardrail_blocked=True e injeta mensagem de erro.
    """
    last_message = state["messages"][-1]
    result = scan_input(last_message.content)

    if not result.is_safe:
        return {
            "messages": [{"role": "assistant", "content": result.blocked_message}],
            "guardrail_blocked": True,
            "guardrail_scores": result.scores,
        }

    # Input seguro — continua o fluxo normal
    # Se o prompt foi sanitizado (ex: PII anonimizado), atualiza a mensagem
    return {
        "guardrail_blocked": False,
        "guardrail_scores": result.scores,
    }


def output_guardrail_node(state: State):
    """
    🛡️ Guardrail de OUTPUT — último node antes do END.
    Valida a resposta do agente antes de entregar ao usuário.
    """
    # Se foi bloqueado no input, não precisa validar output
    if state.get("guardrail_blocked"):
        return {}

    messages = state["messages"]
    if len(messages) < 2:
        return {}

    # Pega o prompt original do usuário e a última resposta do agente
    user_message = None
    for msg in messages:
        if hasattr(msg, "type") and msg.type == "human":
            user_message = msg.content
        elif hasattr(msg, "content") and getattr(msg, "role", None) == "user":
            user_message = msg.content

    agent_response = messages[-1].content if messages else ""

    if not user_message or not agent_response:
        return {}

    result = scan_output(prompt=user_message, response=agent_response)

    if not result.is_safe:
        # Substitui a última mensagem pela versão sanitizada
        return {
            "messages": [{"role": "assistant", "content": result.sanitized_response}],
            "guardrail_scores": {
                **(state.get("guardrail_scores") or {}),
                "output": result.scores,
            },
        }

    return {}


# ============================================================================
# PASSO 8: CONSTRUIR O GRAFO
# ============================================================================

graph_builder = StateGraph(State)

# Adicionar todos os nodes
graph_builder.add_node("input_guardrail", input_guardrail_node)
graph_builder.add_node("initial_router", route_initial_message)
graph_builder.add_node("receptionist", receptionist_agent)
graph_builder.add_node("classifier", classify_message)
graph_builder.add_node("rewrite_query", rewrite_query)
graph_builder.add_node("retrieve_knowledge", retrieve_knowledge)
graph_builder.add_node("benefits", benefits_agent)
graph_builder.add_node("safety", safety_agent)
graph_builder.add_node("clinic", clinic_agent)
graph_builder.add_node("payroll", payroll_agent)
graph_builder.add_node("vacation", vacation_agent)
graph_builder.add_node("output_guardrail", output_guardrail_node)

# Fluxo: START → input_guardrail
graph_builder.add_edge(START, "input_guardrail")

# Input guardrail: se bloqueado → END, senão → initial_router
graph_builder.add_conditional_edges(
    "input_guardrail",
    lambda state: "blocked" if state.get("guardrail_blocked") else "safe",
    {"blocked": END, "safe": "initial_router"},
)

# Router inicial
graph_builder.add_conditional_edges(
    "initial_router",
    lambda state: state.get("next_node"),
    {"receptionist": "receptionist", "classifier": "classifier"},
)

# Classifier vai para rewrite_query (otimiza a busca antes de buscar)
graph_builder.add_conditional_edges(
    "classifier",
    lambda state: state.get("message_type"),
    {
        "benefits": "rewrite_query",
        "safety": "rewrite_query",
        "clinic": "rewrite_query",
        "payroll": "rewrite_query",
        "vacation": "rewrite_query",
    },
)

# rewrite_query vai para retrieve_knowledge
graph_builder.add_edge("rewrite_query", "retrieve_knowledge")

# Retrieve_knowledge vai para o agente apropriado
graph_builder.add_conditional_edges(
    "retrieve_knowledge",
    lambda state: state.get("message_type"),
    {
        "benefits": "benefits",
        "safety": "safety",
        "clinic": "clinic",
        "payroll": "payroll",
        "vacation": "vacation",
    },
)

# Agentes → output_guardrail → END
graph_builder.add_edge("receptionist", "output_guardrail")
graph_builder.add_edge("benefits", "output_guardrail")
graph_builder.add_edge("safety", "output_guardrail")
graph_builder.add_edge("clinic", "output_guardrail")
graph_builder.add_edge("payroll", "output_guardrail")
graph_builder.add_edge("vacation", "output_guardrail")
graph_builder.add_edge("output_guardrail", END)

# Compilar o grafo
app = graph_builder.compile()

print("✅ Grafo RH compilado com sucesso!\n")


# ============================================================================
# PASSO 9: TESTAR O SISTEMA
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("=" * 70)
        print("🧪 TESTANDO SISTEMA DE ATENDIMENTO RH COM 5 AGENTES")
        print("=" * 70)
        
        test_queries = [
            ("Benefícios", "Como faço para incluir meu filho no plano de saúde?"),
            ("Segurança", "Sofri um acidente no trabalho, o que devo fazer?"),
            ("Ambulatório", "Preciso entregar um atestado médico, qual o prazo?"),
            ("Folha de Pagamento", "Quando recebo a primeira parcela do 13º salário?"),
        ]

        for label, query in test_queries:
            print(f"\n📝 TESTE: {label}")
            print("-" * 70)
            print(f"Usuário: {query}\n")
            result = app.invoke({"messages": [{"role": "user", "content": query}]})
            print(f"🤖 Resposta: {result['messages'][-1].content}\n")

        print("=" * 70)
        print("✅ Todos os testes concluídos!")
        print("=" * 70)
    else:
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