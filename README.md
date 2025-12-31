# 🤖 Sistema de Atendimento Inteligente com LangGraph

Um sistema completo de atendimento ao cliente que utiliza **LangGraph** para criar workflows inteligentes com grafos e estado persistente. O sistema classifica automaticamente consultas e roteia para agentes especializados, com monitoramento via **LangSmith**.

## 🎯 Sobre o Projeto

Este projeto demonstra como construir workflows de IA complexos usando LangGraph, indo além dos fluxos lineares tradicionais. O sistema implementa:

- **Routing Inteligente**: Classifica automaticamente saudações vs consultas específicas
- **Agentes Especializados**: Technical, Financial e Receptionist com funções distintas
- **Estado Compartilhado**: Mantém contexto ao longo de toda a conversação
- **Decisões Condicionais**: Fluxo adaptativo baseado no tipo de consulta
- **Monitoramento em Tempo Real**: Visualização completa do workflow via LangSmith

## 🛠️ Tecnologias Utilizadas

- **LangGraph**: Framework para workflows com grafos e estado persistente
- **LangSmith**: Plataforma de desenvolvimento e monitoramento para workflows LangGraph
- **OpenAI GPT-4 Mini**: Processamento de linguagem natural e classificação
- **Pydantic**: Validação e estruturação de dados
- **TypedDict**: Tipagem estática para estados compartilhados
- **UV**: Gerenciamento rápido de dependências Python

## 📋 Pré-requisitos

- Python 3.11+
- Chave da API OpenAI
- UV instalado

### Instalação do UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Via pip
pip install uv
```

## 🚀 Instalação e Configuração

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/langgraph-customer-service.git
cd langgraph-customer-service
```

### 2. Configure o ambiente com UV
```bash
# Cria ambiente virtual e instala dependências
uv sync

# Ativa o ambiente virtual
source .venv/bin/activate  # Linux/macOS
# ou
.venv\Scripts\activate     # Windows
```

### 3. Configure as variáveis de ambiente
```bash
# Crie o arquivo .env
cp .env.example .env

# Edite o arquivo .env e adicione suas chaves
OPENAI_API_KEY=sk-sua-chave-aqui
LANGSMITH_API_KEY=sua-chave-langsmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=customer-service-workflow
```

### 4. Execute com LangGraph Studio (Recomendado)
```bash
# Inicia o LangGraph Studio
langgraph dev

# Acesse http://localhost:8123 para ver a interface visual
```


## 📁 Estrutura do Projeto

```
langgraph-customer-service/
├── agent.py                # Workflow principal do LangGraph
├── main.py                 # Script para execução local (opcional)
├── langgraph.json         # Configuração do LangGraph Studio
├── pyproject.toml         # Configuração do UV e dependências
├── requirements.txt       # Lista de dependências (gerada pelo UV)
├── .env                   # Variáveis de ambiente
├── .env.example          # Exemplo de variáveis de ambiente
├── .gitignore            # Arquivos ignorados pelo Git
├── .python-version       # Versão do Python (3.13)
└── README.md             # Este arquivo
```

## ⚙️ Configuração do LangGraph Studio

O arquivo `langgraph.json` define a configuração para o LangGraph Studio:

```json
{
  "graphs": {
    "customer_service_agent": "agent:app"
  },
  "python_version": "3.13",
  "env": "./.env",
  "dependencies": [
    "."
  ]
}
```

### Explicação da Configuração:
- **graphs**: Define o ponto de entrada do workflow (`agent:app`)
- **python_version**: Especifica Python 3.13
- **env**: Localização do arquivo de variáveis de ambiente
- **dependencies**: Instala o projeto atual como dependência

## 🔧 Configuração das Dependências (pyproject.toml)

```toml
[project]
name = "langgraph-customer-service"
version = "0.1.0"
description = "Sistema de atendimento inteligente com LangGraph"
authors = ["Seu Nome <seu.email@example.com>"]
readme = "README.md"
requires-python = ">=3.13"

dependencies = [
    "langgraph>=0.2.0",
    "langchain-openai>=0.2.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.8.0",
    "langsmith>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "black>=24.0.0",
    "ruff>=0.6.0",
]
```

## 🖥️ LangGraph Studio - Desenvolvimento Visual

### Comandos Principais:
```bash
# Iniciar o LangGraph Studio
langgraph dev

# Especificar arquivo de configuração customizado
langgraph dev --config custom-langgraph.json

# Executar em porta específica
langgraph dev --port 8124
```

### Recursos do LangGraph Studio:
- **Interface Visual**: Veja o grafo do workflow em tempo real
- **Debug Interativo**: Execute step-by-step e inspecione estados
- **Monitoramento**: Acompanhe execuções e performance
- **Teste de Fluxos**: Teste diferentes cenários diretamente na interface
- **Logs Detalhados**: Visualize todas as chamadas de LLM e transições

## 💬 Como Usar

### Exemplo de Interação

```bash
You: Hello
Assistant: Hello! Welcome to our customer service center. I'm here to help you with any technical or financial questions you might have. How can I assist you today?

You: I can't log into my account
Assistant: I understand you're having trouble logging into your account. Let me help you troubleshoot this issue...

You: What's my current bill amount?
Assistant: I'd be happy to help you with your billing information. To access your current bill amount...
```

### Fluxo do Sistema

1. **Initial Router**: Analisa a mensagem e decide entre `receptionist` ou `classifier`
2. **Receptionist**: Lida com saudações e oferece ajuda geral
3. **Classifier**: Classifica consultas como `technical` ou `financial`
4. **Technical Agent**: Resolve problemas técnicos, login, conectividade
5. **Financial Agent**: Lida com billing, pagamentos, reembolsos

## 🧩 Componentes Principais

### State (Estado Compartilhado)
```python
class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_type: str | None
    next_node: str | None
```

### Pydantic Models
- **InitialRouter**: Decide entre receptionist/classifier
- **MessageClassifier**: Classifica como technical/financial

### Nodes (Funções do Workflow)
- `route_initial_message`: Router principal
- `receptionist_agent`: Agente de recepção
- `classify_message`: Classificador de consultas
- `technical_agent`: Especialista técnico
- `financial_agent`: Especialista financeiro

---

⭐ **Se este projeto te ajudou, deixe uma estrela no repositório!**