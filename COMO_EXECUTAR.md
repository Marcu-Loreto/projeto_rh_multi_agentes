# 🚀 Guia Rápido de Execução

## ✅ Ambiente Pronto!

O ambiente virtual foi recriado com sucesso. Agora você pode executar o agente de 3 formas:

---

## 📌 Opção 1: LangGraph Studio (Recomendado)

```bash
# Ative o ambiente virtual
.venv\Scripts\activate.ps1

# Inicie o LangGraph Studio
langgraph dev
```

Ou simplesmente execute:
```bash
start_langgraph.bat
```

Acesse: **http://localhost:8123**

---

## 📌 Opção 2: Modo Interativo

```bash
# Ative o ambiente virtual
.venv\Scripts\activate.ps1

# Execute o agente
python run_agent.py
```

Ou simplesmente execute:
```bash
run_agent.bat
```

---

## 📌 Opção 3: Consulta Única

```bash
.venv\Scripts\activate.ps1
python run_agent.py "Sua pergunta aqui"
```

---

## ⚠️ IMPORTANTE: Atualizar API Key

Antes de executar, atualize a chave da API OpenAI no arquivo `.env`:

1. Acesse: https://platform.openai.com/account/api-keys
2. Gere uma nova chave
3. Edite `.env` e substitua:

```env
OPENAI_API_KEY=sk-proj-SUA_NOVA_CHAVE_AQUI
```

---

## 🧪 Exemplos de Teste

**Saudação:**
```
Olá, bom dia!
```

**Problema Técnico:**
```
Não consigo fazer login no sistema
```

**Problema Financeiro:**
```
Qual é o valor da minha fatura?
```

---

**✨ Tudo instalado e pronto para usar!**
