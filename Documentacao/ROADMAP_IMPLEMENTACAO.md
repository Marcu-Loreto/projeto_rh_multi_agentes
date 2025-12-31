# 🗺️ Roadmap de Implementação - Assistente RH

> **Guia completo para implementações futuras**  
> Versão: 1.0 | Data: 31/12/2025

Este documento contém roteiros detalhados para três melhorias principais do sistema:

1. [Adicionar Memória Persistente](#1-adicionar-memória-persistente)
2. [Integração com Keycloak (SSO)](#2-integração-com-keycloak-sso)
3. [Migração para Frontend React](#3-migração-para-frontend-react)

---

## 📋 Índice

- [1. Adicionar Memória Persistente](#1-adicionar-memória-persistente)
  - [1.1 Memória de Conversa (LangGraph Checkpointer)](#11-memória-de-conversa-langgraph-checkpointer)
  - [1.2 Histórico de Usuário (PostgreSQL)](#12-histórico-de-usuário-postgresql)
- [2. Integração com Keycloak (SSO)](#2-integração-com-keycloak-sso)
  - [2.1 Setup do Keycloak](#21-setup-do-keycloak)
  - [2.2 Integração com Streamlit](#22-integração-com-streamlit)
  - [2.3 Modificações no Backend](#23-modificações-no-backend)
- [3. Migração para Frontend React](#3-migração-para-frontend-react)
  - [3.1 Criar Backend FastAPI](#31-criar-backend-fastapi)
  - [3.2 Desenvolver Frontend React](#32-desenvolver-frontend-react)
  - [3.3 Deploy e Infraestrutura](#33-deploy-e-infraestrutura)

---

# 1. Adicionar Memória Persistente

## 1.1 Memória de Conversa (LangGraph Checkpointer)

### 🎯 Objetivo
Permitir que conversas sejam retomadas mesmo após reiniciar a aplicação.

### 📦 Dependências

```bash
pip install langgraph-checkpoint-sqlite
# ou para produção:
pip install langgraph-checkpoint-postgres
```

### 🔧 Implementação

#### Passo 1: Criar o Checkpointer

**Arquivo: `agent_rh_4_agentes.py`**

```python
from langgraph.checkpoint.sqlite import SqliteSaver
# ou para produção:
#from langgraph.checkpoint.postgres import PostgresSaver

# Após definir o graph_builder, antes de compilar:

# Opção 1: SQLite (desenvolvimento)
memory = SqliteSaver.from_conn_string("checkpoints.db")

# Opção 2: PostgreSQL (produção)
# from psycopg import Connection
# conn = Connection.connect("postgresql://user:pass@localhost/dbname")
# memory = PostgresSaver(conn)

# Compilar com checkpointer
app = graph_builder.compile(checkpointer=memory)
```

#### Passo 2: Usar Thread IDs

**Arquivo: `app_streamlit.py`**

```python
import streamlit as st
import uuid

# Inicializar session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# Ao invocar o agente
result = app.invoke(
    {"messages": [{"role": "user", "content": prompt}]},
    config={"configurable": {"thread_id": st.session_state.thread_id}}
)
```

#### Passo 3: Recuperar Conversas Anteriores

```python
# Listar threads do usuário
from langgraph.checkpoint.sqlite import SqliteSaver

memory = SqliteSaver.from_conn_string("checkpoints.db")

# Obter histórico de uma thread
history = memory.get_tuple(
    {"configurable": {"thread_id": "thread-123"}}
)

# Listar todas as threads
all_threads = memory.list({})
```

### 📊 Estrutura do Banco

```sql
-- SQLite cria automaticamente estas tabelas:
CREATE TABLE checkpoints (
    thread_id TEXT,
    checkpoint_id TEXT,
    parent_id TEXT,
    checkpoint BLOB,
    metadata TEXT,
    PRIMARY KEY (thread_id, checkpoint_id)
);

CREATE TABLE writes (
    thread_id TEXT,
    checkpoint_id TEXT,
    task_id TEXT,
    idx INTEGER,
    channel TEXT,
    value BLOB,
    PRIMARY KEY (thread_id, checkpoint_id, task_id, idx)
);
```

### ✅ Verificação

```python
# Testar persistência
print(f"Thread ID: {st.session_state.thread_id}")

# Reiniciar app e verificar se conversa continua
# usando o mesmo thread_id
```

---

## 1.2 Histórico de Usuário (PostgreSQL)

### 🎯 Objetivo
Armazenar histórico completo de conversas para analytics e auditoria.

### 📦 Dependências

```bash
pip install psycopg2-binary sqlalchemy
```

### 🔧 Implementação

#### Passo 1: Criar Modelo de Dados

**Arquivo: `database/models.py`** (novo)

```python
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Conversation(Base):
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    thread_id = Column(String(100), unique=True, index=True)
    user_id = Column(String(100), index=True)
    user_name = Column(String(200))
    user_email = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    thread_id = Column(String(100), index=True)
    role = Column(String(20))  # 'user' ou 'assistant'
    content = Column(Text)
    agent_type = Column(String(50))  # 'benefits', 'safety', etc
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# Criar engine e tabelas
engine = create_engine('postgresql://user:pass@localhost/assistente_rh')
Base.metadata.create_all(engine)

# Criar session
SessionLocal = sessionmaker(bind=engine)
```

#### Passo 2: Funções de Persistência

**Arquivo: `database/crud.py`** (novo)

```python
from sqlalchemy.orm import Session
from .models import Conversation, Message, SessionLocal
from datetime import datetime

def create_conversation(user_id: str, user_name: str, user_email: str, thread_id: str):
    """Cria nova conversa."""
    db = SessionLocal()
    try:
        conversation = Conversation(
            thread_id=thread_id,
            user_id=user_id,
            user_name=user_name,
            user_email=user_email
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation
    finally:
        db.close()

def save_message(thread_id: str, role: str, content: str, agent_type: str = None, metadata: dict = None):
    """Salva mensagem no histórico."""
    db = SessionLocal()
    try:
        message = Message(
            thread_id=thread_id,
            role=role,
            content=content,
            agent_type=agent_type,
            metadata=metadata or {}
        )
        db.add(message)
        db.commit()
        return message
    finally:
        db.close()

def get_user_conversations(user_id: str, limit: int = 10):
    """Retorna conversas do usuário."""
    db = SessionLocal()
    try:
        return db.query(Conversation)\
            .filter(Conversation.user_id == user_id)\
            .order_by(Conversation.updated_at.desc())\
            .limit(limit)\
            .all()
    finally:
        db.close()

def get_conversation_messages(thread_id: str):
    """Retorna mensagens de uma conversa."""
    db = SessionLocal()
    try:
        return db.query(Message)\
            .filter(Message.thread_id == thread_id)\
            .order_by(Message.created_at.asc())\
            .all()
    finally:
        db.close()
```

#### Passo 3: Integrar com Streamlit

**Arquivo: `app_streamlit.py`**

```python
from database.crud import create_conversation, save_message, get_user_conversations

# Ao iniciar nova conversa
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    
    # Criar conversa no banco (após autenticação)
    create_conversation(
        user_id=st.session_state.user_id,
        user_name=st.session_state.user_name,
        user_email=st.session_state.user_email,
        thread_id=st.session_state.thread_id
    )

# Ao enviar mensagem
if prompt := st.chat_input("Digite sua pergunta..."):
    # Salvar mensagem do usuário
    save_message(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt
    )
    
    # Processar com agente
    result = app.invoke(...)
    
    # Salvar resposta do assistente
    save_message(
        thread_id=st.session_state.thread_id,
        role="assistant",
        content=result['messages'][-1].content,
        agent_type=result.get('message_type'),
        metadata={
            'retrieved_docs': len(result.get('retrieved_context', '')),
            'timestamp': datetime.now().isoformat()
        }
    )
```

#### Passo 4: Adicionar Sidebar de Histórico

```python
with st.sidebar:
    st.markdown("### 📜 Conversas Anteriores")
    
    if st.session_state.get('user_id'):
        conversations = get_user_conversations(st.session_state.user_id)
        
        for conv in conversations:
            if st.button(
                f"💬 {conv.created_at.strftime('%d/%m %H:%M')}",
                key=f"conv_{conv.id}"
            ):
                st.session_state.thread_id = conv.thread_id
                # Carregar mensagens
                messages = get_conversation_messages(conv.thread_id)
                st.session_state.messages = [
                    {"role": msg.role, "content": msg.content}
                    for msg in messages
                ]
                st.rerun()
```

### 📊 Schema PostgreSQL Completo

```sql
-- Criar banco de dados
CREATE DATABASE assistente_rh;

-- Conectar ao banco
\c assistente_rh;

-- Tabela de conversas
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    user_name VARCHAR(200),
    user_email VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_thread_id ON conversations(thread_id);

-- Tabela de mensagens
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    agent_type VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES conversations(thread_id) ON DELETE CASCADE
);

CREATE INDEX idx_messages_thread_id ON messages(thread_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- View para analytics
CREATE VIEW conversation_stats AS
SELECT 
    c.user_id,
    c.user_name,
    COUNT(DISTINCT c.thread_id) as total_conversations,
    COUNT(m.id) as total_messages,
    MAX(c.updated_at) as last_activity
FROM conversations c
LEFT JOIN messages m ON c.thread_id = m.thread_id
GROUP BY c.user_id, c.user_name;
```

### ✅ Verificação

```sql
-- Ver conversas
SELECT * FROM conversations ORDER BY created_at DESC LIMIT 10;

-- Ver mensagens de uma conversa
SELECT * FROM messages WHERE thread_id = 'thread-123' ORDER BY created_at;

-- Estatísticas
SELECT * FROM conversation_stats;
```

---

# 2. Integração com Keycloak (SSO)

## 2.1 Setup do Keycloak

### 🎯 Objetivo
Configurar Keycloak para autenticação centralizada.

### 📦 Instalação com Docker

#### Passo 1: Docker Compose

**Arquivo: `docker-compose.keycloak.yml`** (novo)

```yaml
version: '3.8'

services:
  postgres-keycloak:
    image: postgres:15
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: keycloak_password
    volumes:
      - postgres_keycloak_data:/var/lib/postgresql/data
    networks:
      - keycloak-network

  keycloak:
    image: quay.io/keycloak/keycloak:23.0
    command: start-dev
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres-keycloak:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: keycloak_password
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
      KC_HOSTNAME: localhost
      KC_HTTP_PORT: 8080
    ports:
      - "8080:8080"
    depends_on:
      - postgres-keycloak
    networks:
      - keycloak-network

volumes:
  postgres_keycloak_data:

networks:
  keycloak-network:
    driver: bridge
```

#### Passo 2: Iniciar Keycloak

```bash
# Iniciar serviços
docker-compose -f docker-compose.keycloak.yml up -d

# Aguardar inicialização (1-2 minutos)
docker-compose -f docker-compose.keycloak.yml logs -f keycloak

# Acessar: http://localhost:8080
# Login: admin / admin
```

### ⚙️ Configuração do Keycloak

#### Passo 3: Criar Realm

1. Acesse http://localhost:8080
2. Login com `admin` / `admin`
3. Clique em **"Create Realm"**
4. Nome: `cpqd`
5. Clique em **"Create"**

#### Passo 4: Criar Client

1. No realm `cpqd`, vá em **Clients** → **Create client**
2. Configurações:
   ```
   Client ID: assistente-rh
   Client type: OpenID Connect
   ```
3. Clique **Next**
4. Configurações de capacidade:
   ```
   Client authentication: ON
   Authorization: OFF
   Standard flow: ON
   Direct access grants: ON
   ```
5. Clique **Next**
6. URLs:
   ```
   Root URL: http://localhost:8501
   Valid redirect URIs: http://localhost:8501/*
   Web origins: http://localhost:8501
   ```
7. Clique **Save**

#### Passo 5: Obter Client Secret

1. Vá em **Clients** → **assistente-rh** → **Credentials**
2. Copie o **Client Secret**
3. Salve no `.env`:
   ```env
   KEYCLOAK_SERVER_URL=http://localhost:8080
   KEYCLOAK_REALM=cpqd
   KEYCLOAK_CLIENT_ID=assistente-rh
   KEYCLOAK_CLIENT_SECRET=seu-secret-aqui
   ```

#### Passo 6: Criar Usuários de Teste

1. Vá em **Users** → **Add user**
2. Preencha:
   ```
   Username: joao.silva
   Email: joao.silva@cpqd.com.br
   First name: João
   Last name: Silva
   ```
3. Clique **Create**
4. Vá em **Credentials** → **Set password**
5. Defina senha: `senha123`
6. Desmarque **Temporary**
7. Clique **Save**

#### Passo 7: Configurar Atributos Customizados

1. Vá em **Realm settings** → **User profile**
2. Adicione atributos:
   - `department` (Departamento)
   - `employee_id` (Matrícula)
   - `job_title` (Cargo)

3. Vá em **Client scopes** → **assistente-rh-dedicated**
4. Adicione mappers para incluir atributos no token

---

## 2.2 Integração com Streamlit

### 📦 Dependências

```bash
pip install streamlit-keycloak python-keycloak
```

**Atualizar `requirements.txt`:**
```
streamlit-keycloak
python-keycloak
```

### 🔧 Implementação

#### Passo 1: Criar Módulo de Autenticação

**Arquivo: `auth/keycloak_auth.py`** (novo)

```python
import streamlit as st
from streamlit_keycloak import login
import os
from dotenv import load_dotenv

load_dotenv()

def init_keycloak():
    """Inicializa autenticação Keycloak."""
    
    keycloak = login(
        url=os.getenv("KEYCLOAK_SERVER_URL"),
        realm=os.getenv("KEYCLOAK_REALM"),
        client_id=os.getenv("KEYCLOAK_CLIENT_ID")
    )
    
    return keycloak

def get_user_info(keycloak):
    """Extrai informações do usuário do token."""
    
    if not keycloak.authenticated:
        return None
    
    user_info = keycloak.user_info
    
    return {
        "user_id": user_info.get("sub"),
        "username": user_info.get("preferred_username"),
        "name": user_info.get("name"),
        "email": user_info.get("email"),
        "first_name": user_info.get("given_name"),
        "last_name": user_info.get("family_name"),
        "department": user_info.get("department", ""),
        "employee_id": user_info.get("employee_id", ""),
        "job_title": user_info.get("job_title", ""),
        "groups": user_info.get("groups", [])
    }

def require_auth():
    """Decorator para exigir autenticação."""
    keycloak = init_keycloak()
    
    if not keycloak.authenticated:
        st.warning("🔒 Por favor, faça login para acessar o Assistente RH")
        st.stop()
    
    return get_user_info(keycloak)
```

#### Passo 2: Modificar app_streamlit.py

**Arquivo: `app_streamlit.py`**

```python
import streamlit as st
from auth.keycloak_auth import require_auth
from agent_rh_4_agentes import app, get_contextual_greeting, get_formatted_time

# ============================================================================
# AUTENTICAÇÃO
# ============================================================================

# Exigir autenticação
user_info = require_auth()

# Salvar no session state
st.session_state.user_info = user_info
st.session_state.user_id = user_info["user_id"]
st.session_state.user_name = user_info["name"]
st.session_state.user_email = user_info["email"]

# ============================================================================
# HEADER PERSONALIZADO
# ============================================================================

greeting = get_contextual_greeting()
st.markdown(f"# 🤖 Assistente Virtual de RH")
st.markdown(
    f'<p class="subtitle">{greeting}, {user_info["first_name"]}! 👋</p>', 
    unsafe_allow_html=True
)

# ============================================================================
# SIDEBAR COM INFO DO USUÁRIO
# ============================================================================

with st.sidebar:
    st.markdown("### 👤 Perfil")
    st.info(f"""
    **Nome:** {user_info['name']}  
    **Email:** {user_info['email']}  
    **Departamento:** {user_info.get('department', 'N/A')}  
    **Matrícula:** {user_info.get('employee_id', 'N/A')}
    """)
    
    st.markdown("---")
    
    # Botão de logout
    if st.button("🚪 Sair", use_container_width=True):
        # Limpar session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
```

#### Passo 3: Passar User Info para Agentes

**Arquivo: `agent_rh_4_agentes.py`**

```python
# Atualizar State
class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_type: str | None
    next_node: str | None
    retrieved_context: str | None
    current_time: str | None
    greeting: str | None
    user_name: str | None          # ✨ NOVO
    user_email: str | None         # ✨ NOVO
    user_department: str | None    # ✨ NOVO
    user_id: str | None            # ✨ NOVO

# Modificar receptionist_agent
def receptionist_agent(state: State):
    """Recepcionista do RH."""
    last_message = state["messages"][-1]
    greeting = state.get("greeting", "Olá")
    current_time = state.get("current_time", "")
    user_name = state.get("user_name", "")
    
    messages = [
        {
            "role": "system",
            "content": f"""Você é a recepcionista virtual do RH da CPQD. 
            
            INFORMAÇÕES DO USUÁRIO:
            - Nome: {user_name}
            - Horário atual: {current_time}
            - Cumprimento: {greeting}
            
            INSTRUÇÕES:
            - SEMPRE chame o usuário pelo primeiro nome
            - Use o cumprimento contextualizado
            - Seja cordial e personalizada
            ...
```

**Arquivo: `app_streamlit.py`** (ao invocar agente)

```python
# Ao processar pergunta
result = app.invoke({
    "messages": [{"role": "user", "content": prompt}],
    "user_name": st.session_state.user_name,
    "user_email": st.session_state.user_email,
    "user_department": st.session_state.user_info.get("department"),
    "user_id": st.session_state.user_id
})
```

### ✅ Verificação

1. Iniciar Keycloak: `docker-compose -f docker-compose.keycloak.yml up -d`
2. Iniciar Streamlit: `streamlit run app_streamlit.py`
3. Acessar: http://localhost:8501
4. Fazer login com usuário criado
5. Verificar se nome aparece no header e sidebar

---

## 2.3 Modificações no Backend

### 🔧 Adicionar Auditoria

**Arquivo: `database/models.py`**

```python
class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), index=True)
    user_name = Column(String(200))
    action = Column(String(50))  # 'query', 'login', 'logout'
    details = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Arquivo: `database/crud.py`**

```python
def log_action(user_id: str, user_name: str, action: str, details: dict = None):
    """Registra ação para auditoria."""
    db = SessionLocal()
    try:
        log = AuditLog(
            user_id=user_id,
            user_name=user_name,
            action=action,
            details=details or {},
            ip_address=details.get('ip_address'),
            user_agent=details.get('user_agent')
        )
        db.add(log)
        db.commit()
        return log
    finally:
        db.close()
```

**Uso no Streamlit:**

```python
from database.crud import log_action

# Ao fazer query
log_action(
    user_id=st.session_state.user_id,
    user_name=st.session_state.user_name,
    action='query',
    details={
        'query': prompt,
        'agent_type': result.get('message_type'),
        'timestamp': datetime.now().isoformat()
    }
)
```

---

# 3. Migração para Frontend React

## 3.1 Criar Backend FastAPI

### 🎯 Objetivo
Separar backend (API) do frontend (React).

### 📦 Estrutura do Projeto

```
Agente_Suporte_RH_Langgraphic/
├── backend/                    # ✨ NOVO
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py        # Endpoints de chat
│   │   │   └── auth.py        # Endpoints de auth
│   │   └── dependencies.py    # Dependências compartilhadas
│   ├── core/
│   │   ├── config.py          # Configurações
│   │   └── security.py        # JWT validation
│   ├── database/
│   │   ├── models.py
│   │   └── crud.py
│   ├── agent/
│   │   └── langgraph_agent.py # LangGraph logic
│   └── requirements.txt
├── frontend/                   # ✨ NOVO
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.tsx
│   ├── package.json
│   └── tsconfig.json
└── docker-compose.yml
```

### 🔧 Implementação Backend

#### Passo 1: Criar FastAPI App

**Arquivo: `backend/api/main.py`** (novo)

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Assistente RH API",
    description="API para o sistema de atendimento RH com LangGraph",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    agent_type: str
    thread_id: str
    timestamp: str

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Import routes
from .routes import chat, auth

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
```

#### Passo 2: Criar Endpoint de Chat

**Arquivo: `backend/api/routes/chat.py`** (novo)

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

from ..dependencies import get_current_user
from ...agent.langgraph_agent import invoke_agent
from ...database.crud import save_message

router = APIRouter()
security = HTTPBearer()

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    agent_type: str
    thread_id: str
    timestamp: str

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user)
):
    """
    Processa mensagem do usuário e retorna resposta do agente.
    """
    try:
        # Gerar ou usar thread_id existente
        thread_id = request.thread_id or str(uuid.uuid4())
        
        # Invocar agente LangGraph
        result = invoke_agent(
            message=request.message,
            thread_id=thread_id,
            user_info=current_user
        )
        
        # Salvar mensagens no banco
        save_message(
            thread_id=thread_id,
            role="user",
            content=request.message
        )
        
        save_message(
            thread_id=thread_id,
            role="assistant",
            content=result["message"],
            agent_type=result["agent_type"]
        )
        
        return ChatResponse(
            message=result["message"],
            agent_type=result["agent_type"],
            thread_id=thread_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{thread_id}")
async def get_history(
    thread_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Retorna histórico de uma conversa.
    """
    from ...database.crud import get_conversation_messages
    
    messages = get_conversation_messages(thread_id)
    
    return {
        "thread_id": thread_id,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    }
```

#### Passo 3: Validação JWT Keycloak

**Arquivo: `backend/core/security.py`** (novo)

```python
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from keycloak import KeycloakOpenID
import os

security = HTTPBearer()

# Configurar Keycloak
keycloak_openid = KeycloakOpenID(
    server_url=os.getenv("KEYCLOAK_SERVER_URL"),
    client_id=os.getenv("KEYCLOAK_CLIENT_ID"),
    realm_name=os.getenv("KEYCLOAK_REALM"),
    client_secret_key=os.getenv("KEYCLOAK_CLIENT_SECRET")
)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Valida token JWT do Keycloak.
    """
    try:
        token = credentials.credentials
        
        # Validar token
        token_info = keycloak_openid.introspect(token)
        
        if not token_info.get("active"):
            raise HTTPException(status_code=401, detail="Token inválido")
        
        # Decodificar informações do usuário
        user_info = keycloak_openid.userinfo(token)
        
        return user_info
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Erro na autenticação: {str(e)}")
```

**Arquivo: `backend/api/dependencies.py`** (novo)

```python
from fastapi import Depends
from ..core.security import verify_token

async def get_current_user(user_info: dict = Depends(verify_token)):
    """
    Retorna informações do usuário autenticado.
    """
    return {
        "user_id": user_info.get("sub"),
        "username": user_info.get("preferred_username"),
        "name": user_info.get("name"),
        "email": user_info.get("email"),
        "department": user_info.get("department", ""),
        "employee_id": user_info.get("employee_id", "")
    }
```

#### Passo 4: Adaptar LangGraph Agent

**Arquivo: `backend/agent/langgraph_agent.py`** (novo)

```python
# Mover lógica do agent_rh_4_agentes.py para cá
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
# ... outros imports

# Copiar todo o código do agent_rh_4_agentes.py

def invoke_agent(message: str, thread_id: str, user_info: dict):
    """
    Invoca o agente LangGraph com contexto do usuário.
    """
    result = app.invoke(
        {
            "messages": [{"role": "user", "content": message}],
            "user_name": user_info.get("name"),
            "user_email": user_info.get("email"),
            "user_department": user_info.get("department"),
            "user_id": user_info.get("user_id")
        },
        config={"configurable": {"thread_id": thread_id}}
    )
    
    return {
        "message": result["messages"][-1].content,
        "agent_type": result.get("message_type", "unknown")
    }
```

#### Passo 5: Requirements Backend

**Arquivo: `backend/requirements.txt`** (novo)

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-keycloak==3.9.0
python-jose[cryptography]==3.3.0
python-multipart==0.0.6
pydantic==2.5.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
langgraph==0.2.0
langchain-openai==0.2.0
langchain-chroma==0.1.0
chromadb==0.4.22
python-dotenv==1.0.0
pytz==2024.1
```

#### Passo 6: Executar Backend

```bash
cd backend
pip install -r requirements.txt

# Desenvolvimento
uvicorn api.main:app --reload --port 8000

# Produção
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### ✅ Testar API

```bash
# Health check
curl http://localhost:8000/health

# Documentação interativa
# Abrir: http://localhost:8000/docs
```

---

## 3.2 Desenvolver Frontend React

### 📦 Criar Projeto React

```bash
# Criar app React com TypeScript
npx create-react-app frontend --template typescript

cd frontend
```

### 🔧 Instalar Dependências

```bash
npm install @mui/material @emotion/react @emotion/styled
npm install @mui/icons-material
npm install axios
npm install react-router-dom
npm install @react-keycloak/web keycloak-js
npm install date-fns
npm install react-markdown
```

**Arquivo: `frontend/package.json`**

```json
{
  "name": "assistente-rh-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "@emotion/react": "^11.11.3",
    "@emotion/styled": "^11.11.0",
    "@mui/icons-material": "^5.15.6",
    "@mui/material": "^5.15.6",
    "@react-keycloak/web": "^3.4.0",
    "@testing-library/jest-dom": "^5.17.0",
    "@testing-library/react": "^13.4.0",
    "@testing-library/user-event": "^13.5.0",
    "@types/jest": "^27.5.2",
    "@types/node": "^16.18.80",
    "@types/react": "^18.2.48",
    "@types/react-dom": "^18.2.18",
    "axios": "^1.6.5",
    "date-fns": "^3.2.0",
    "keycloak-js": "^23.0.5",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-markdown": "^9.0.1",
    "react-router-dom": "^6.21.3",
    "react-scripts": "5.0.1",
    "typescript": "^4.9.5",
    "web-vitals": "^2.1.4"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  }
}
```

### 🏗️ Estrutura do Frontend

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── Chat/
│   │   │   ├── ChatContainer.tsx
│   │   │   ├── ChatMessage.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   └── AgentBadge.tsx
│   │   ├── Sidebar/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── UserProfile.tsx
│   │   │   └── ConversationList.tsx
│   │   └── Layout/
│   │       ├── Header.tsx
│   │       └── MainLayout.tsx
│   ├── services/
│   │   ├── api.ts
│   │   └── keycloak.ts
│   ├── types/
│   │   └── index.ts
│   ├── hooks/
│   │   └── useChat.ts
│   ├── App.tsx
│   ├── index.tsx
│   └── theme.ts
```

### 🔧 Implementação

#### Passo 1: Configurar Keycloak

**Arquivo: `frontend/src/services/keycloak.ts`**

```typescript
import Keycloak from 'keycloak-js';

const keycloak = new Keycloak({
  url: 'http://localhost:8080',
  realm: 'cpqd',
  clientId: 'assistente-rh'
});

export default keycloak;
```

#### Passo 2: Configurar API Client

**Arquivo: `frontend/src/services/api.ts`**

```typescript
import axios from 'axios';
import keycloak from './keycloak';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json'
  }
});

// Interceptor para adicionar token
api.interceptors.request.use(
  (config) => {
    if (keycloak.token) {
      config.headers.Authorization = `Bearer ${keycloak.token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        await keycloak.updateToken(30);
        error.config.headers.Authorization = `Bearer ${keycloak.token}`;
        return axios(error.config);
      } catch {
        keycloak.login();
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// Funções da API
export const chatAPI = {
  sendMessage: async (message: string, threadId?: string) => {
    const response = await api.post('/chat', { message, thread_id: threadId });
    return response.data;
  },
  
  getHistory: async (threadId: string) => {
    const response = await api.get(`/chat/history/${threadId}`);
    return response.data;
  }
};
```

#### Passo 3: Tipos TypeScript

**Arquivo: `frontend/src/types/index.ts`**

```typescript
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  agentType?: string;
}

export interface UserInfo {
  userId: string;
  username: string;
  name: string;
  email: string;
  department?: string;
  employeeId?: string;
}

export interface Conversation {
  id: string;
  threadId: string;
  createdAt: string;
  updatedAt: string;
}
```

#### Passo 4: Hook de Chat

**Arquivo: `frontend/src/hooks/useChat.ts`**

```typescript
import { useState, useCallback } from 'react';
import { chatAPI } from '../services/api';
import { Message } from '../types';
import { v4 as uuidv4 } from 'uuid';

export const useChat = (threadId?: string) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentThreadId, setCurrentThreadId] = useState(threadId || uuidv4());

  const sendMessage = useCallback(async (content: string) => {
    // Adicionar mensagem do usuário
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      // Enviar para API
      const response = await chatAPI.sendMessage(content, currentThreadId);
      
      // Adicionar resposta do assistente
      const assistantMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: response.message,
        timestamp: response.timestamp,
        agentType: response.agent_type
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      setCurrentThreadId(response.thread_id);
      
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error);
      // Adicionar mensagem de erro
      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro ao processar sua mensagem.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }, [currentThreadId]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentThreadId(uuidv4());
  }, []);

  return {
    messages,
    loading,
    threadId: currentThreadId,
    sendMessage,
    clearMessages
  };
};
```

#### Passo 5: Componente de Mensagem

**Arquivo: `frontend/src/components/Chat/ChatMessage.tsx`**

```typescript
import React from 'react';
import { Box, Paper, Typography, Chip } from '@mui/material';
import { Message } from '../../types';
import ReactMarkdown from 'react-markdown';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

interface ChatMessageProps {
  message: Message;
}

const agentColors: Record<string, string> = {
  benefits: '#667eea',
  safety: '#f5576c',
  clinic: '#00f2fe',
  payroll: '#38f9d7',
  receptionist: '#764ba2'
};

const agentLabels: Record<string, string> = {
  benefits: '💼 Benefícios',
  safety: '🦺 Segurança',
  clinic: '🏥 Ambulatório',
  payroll: '💰 Folha de Pagamento',
  receptionist: '👋 Recepcionista'
};

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 2
      }}
    >
      <Paper
        elevation={2}
        sx={{
          maxWidth: '70%',
          p: 2,
          background: isUser 
            ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
            : '#fff',
          color: isUser ? '#fff' : '#000',
          borderRadius: 2
        }}
      >
        {!isUser && message.agentType && (
          <Chip
            label={agentLabels[message.agentType] || 'Assistente'}
            size="small"
            sx={{
              mb: 1,
              background: agentColors[message.agentType] || '#667eea',
              color: '#fff'
            }}
          />
        )}
        
        <ReactMarkdown>{message.content}</ReactMarkdown>
        
        <Typography
          variant="caption"
          sx={{
            display: 'block',
            mt: 1,
            opacity: 0.7,
            textAlign: 'right'
          }}
        >
          {format(new Date(message.timestamp), 'HH:mm', { locale: ptBR })}
        </Typography>
      </Paper>
    </Box>
  );
};
```

#### Passo 6: Componente de Input

**Arquivo: `frontend/src/components/Chat/ChatInput.tsx`**

```typescript
import React, { useState } from 'react';
import { Box, TextField, IconButton, CircularProgress } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';

interface ChatInputProps {
  onSend: (message: string) => void;
  loading: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, loading }) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !loading) {
      onSend(input.trim());
      setInput('');
    }
  };

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{
        display: 'flex',
        gap: 1,
        p: 2,
        borderTop: '1px solid #e0e0e0',
        background: '#fff'
      }}
    >
      <TextField
        fullWidth
        variant="outlined"
        placeholder="Digite sua pergunta sobre RH..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        disabled={loading}
        autoFocus
      />
      <IconButton
        type="submit"
        color="primary"
        disabled={!input.trim() || loading}
        sx={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: '#fff',
          '&:hover': {
            background: 'linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%)'
          }
        }}
      >
        {loading ? <CircularProgress size={24} /> : <SendIcon />}
      </IconButton>
    </Box>
  );
};
```

#### Passo 7: Container Principal

**Arquivo: `frontend/src/components/Chat/ChatContainer.tsx`**

```typescript
import React, { useRef, useEffect } from 'react';
import { Box, Container } from '@mui/material';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { useChat } from '../../hooks/useChat';

export const ChatContainer: React.FC = () => {
  const { messages, loading, sendMessage } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll para última mensagem
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
      }}
    >
      {/* Área de mensagens */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          p: 3
        }}
      >
        <Container maxWidth="md">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          <div ref={messagesEndRef} />
        </Container>
      </Box>

      {/* Input */}
      <Container maxWidth="md" sx={{ pb: 2 }}>
        <ChatInput onSend={sendMessage} loading={loading} />
      </Container>
    </Box>
  );
};
```

#### Passo 8: App Principal com Keycloak

**Arquivo: `frontend/src/App.tsx`**

```typescript
import React from 'react';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import { ThemeProvider, CssBaseline } from '@mui/material';
import keycloak from './services/keycloak';
import { ChatContainer } from './components/Chat/ChatContainer';
import theme from './theme';

const App: React.FC = () => {
  return (
    <ReactKeycloakProvider authClient={keycloak}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <ChatContainer />
      </ThemeProvider>
    </ReactKeycloakProvider>
  );
};

export default App;
```

#### Passo 9: Tema Material-UI

**Arquivo: `frontend/src/theme.ts`**

```typescript
import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      main: '#667eea',
    },
    secondary: {
      main: '#764ba2',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
});

export default theme;
```

### 🚀 Executar Frontend

```bash
cd frontend
npm start

# Abre em: http://localhost:3000
```

---

## 3.3 Deploy e Infraestrutura

### 🐳 Docker Compose Completo

**Arquivo: `docker-compose.yml`** (raiz do projeto)

```yaml
version: '3.8'

services:
  # PostgreSQL
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: assistente_rh
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - app-network

  # Keycloak PostgreSQL
  postgres-keycloak:
    image: postgres:15
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: keycloak
    volumes:
      - postgres_keycloak_data:/var/lib/postgresql/data
    networks:
      - app-network

  # Keycloak
  keycloak:
    image: quay.io/keycloak/keycloak:23.0
    command: start-dev
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres-keycloak:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: keycloak
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
      KC_HOSTNAME: localhost
    ports:
      - "8080:8080"
    depends_on:
      - postgres-keycloak
    networks:
      - app-network

  # Backend FastAPI
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/assistente_rh
      KEYCLOAK_SERVER_URL: http://keycloak:8080
      KEYCLOAK_REALM: cpqd
      KEYCLOAK_CLIENT_ID: assistente-rh
      KEYCLOAK_CLIENT_SECRET: ${KEYCLOAK_CLIENT_SECRET}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - keycloak
    networks:
      - app-network
    volumes:
      - ./backend:/app
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

  # Frontend React
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - app-network

volumes:
  postgres_data:
  postgres_keycloak_data:

networks:
  app-network:
    driver: bridge
```

### 📦 Dockerfile Backend

**Arquivo: `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Expor porta
EXPOSE 8000

# Comando
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 📦 Dockerfile Frontend

**Arquivo: `frontend/Dockerfile`**

```dockerfile
# Build stage
FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Arquivo: `frontend/nginx.conf`**

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 🚀 Executar Tudo

```bash
# Criar arquivo .env na raiz
cat > .env << EOF
KEYCLOAK_CLIENT_SECRET=seu-secret-aqui
OPENAI_API_KEY=sk-sua-chave-aqui
EOF

# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f

# Acessar:
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# Keycloak: http://localhost:8080
```

### ✅ Checklist de Deploy

- [ ] PostgreSQL rodando
- [ ] Keycloak configurado
- [ ] Realm e Client criados
- [ ] Usuários de teste criados
- [ ] Backend FastAPI respondendo
- [ ] Frontend React carregando
- [ ] Autenticação funcionando
- [ ] Chat funcionando end-to-end

---

## 📚 Recursos Adicionais

### Documentação

- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [Keycloak](https://www.keycloak.org/documentation)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Material-UI](https://mui.com/)

### Monitoramento

- **Sentry**: Rastreamento de erros
- **Prometheus + Grafana**: Métricas
- **ELK Stack**: Logs centralizados

### CI/CD

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and Deploy
        run: |
          docker-compose build
          docker-compose up -d
```

---

## 🎯 Próximos Passos

1. **Fase 1**: Implementar memória persistente (1-2 dias)
2. **Fase 2**: Integrar Keycloak (2-3 dias)
3. **Fase 3**: Desenvolver backend FastAPI (1 semana)
4. **Fase 4**: Desenvolver frontend React (2-3 semanas)
5. **Fase 5**: Testes e deploy (1 semana)

**Tempo total estimado**: 6-8 semanas

---

## 📞 Suporte

Para dúvidas ou problemas durante a implementação:
- Consulte a documentação oficial de cada tecnologia
- Revise os logs de erro
- Teste cada componente isoladamente

**Boa sorte com a implementação! 🚀**
