# 🎯 Guia Rápido de Execução

## 🚀 Comandos Disponíveis

### 1️⃣ **Streamlit (Interface Web)**
```bash
streamlit run app_streamlit.py
```
ou
```bash
run_streamlit.bat
```
**Acesso**: http://localhost:8501

---

### 2️⃣ **LangGraph Studio (Visualização do Grafo)**
```bash
langgraph dev
```
**Acesso**: https://smith.langchain.com/studio/

---

### 3️⃣ **Ambos ao Mesmo Tempo** ⭐ (Recomendado)
```bash
run_completo.bat
```

Isso abre:
- ✅ Streamlit em uma janela
- ✅ LangGraph Studio em outra janela

---

## 📊 Comparação

| Ferramenta | Uso | Vantagens |
|------------|-----|-----------|
| **Streamlit** | Usuários finais | Interface amigável, chat interativo |
| **LangGraph Studio** | Desenvolvimento | Visualiza grafo, debug, testes |
| **Ambos** | Completo | Melhor experiência de desenvolvimento |

---

## 💡 Dicas

### Para Desenvolvimento:
Use `run_completo.bat` para ter:
- Interface web para testar como usuário
- Studio para ver o fluxo do grafo

### Para Demonstração:
Use apenas `streamlit run app_streamlit.py`

### Para Debug:
Use apenas `langgraph dev` para ver o grafo detalhado

---

## 🔧 Troubleshooting

### Porta já em uso?

**Streamlit (8501)**:
```bash
streamlit run app_streamlit.py --server.port 8502
```

**LangGraph (2024)**:
```bash
langgraph dev --port 2025
```

---

## 🎨 Screenshots

### Streamlit
- Chat interativo
- Badges coloridos dos agentes
- Estatísticas em tempo real

### LangGraph Studio
- Grafo visual dos 4 agentes
- Fluxo de execução
- Debug de mensagens

---

**Pronto para usar!** 🚀
