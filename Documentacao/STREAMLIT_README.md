# 🎨 Interface Streamlit - Assistente Virtual de RH

## 🚀 Como Executar

### Opção 1: Usando o script .bat (Mais Fácil)

```bash
run_streamlit.bat
```

### Opção 2: Manualmente

```bash
# Ativar ambiente virtual
.venv\Scripts\activate.ps1

# Instalar Streamlit (se ainda não instalou)
pip install streamlit

# Executar
streamlit run app_streamlit.py
```

---

## ✨ Funcionalidades

### 🎨 Interface Moderna
- ✅ Design com gradientes vibrantes
- ✅ Tema roxo/azul profissional
- ✅ Animações suaves
- ✅ Responsivo

### 💬 Chat Interativo
- ✅ Histórico de conversas
- ✅ Badges coloridos para cada agente
- ✅ Animação de digitação
- ✅ Mensagens formatadas

### 📊 Estatísticas em Tempo Real
- ✅ Contador de mensagens
- ✅ Agentes mais consultados
- ✅ Histórico de interações

### 🤖 4 Agentes Especializados
- 💼 **Benefícios** (roxo)
- 🦺 **Segurança do Trabalho** (rosa)
- 🏥 **Ambulatório** (azul)
- 💰 **Folha de Pagamento** (verde)

---

## 📸 Preview

A interface possui:

1. **Header**: Título grande com gradiente
2. **Sidebar**: 
   - Lista de agentes com badges coloridos
   - Instruções de uso
   - Estatísticas de uso
   - Botão para limpar conversa
3. **Área de Chat**: 
   - Mensagens do usuário (gradiente roxo)
   - Respostas do assistente (branco com borda)
   - Badges indicando qual agente respondeu
4. **Input**: Campo de texto arredondado na parte inferior
5. **Footer**: Informações do sistema

---

## 🎯 Exemplo de Uso

1. Abra o navegador em `http://localhost:8501`
2. Digite uma pergunta: "Qual o valor do vale refeição?"
3. O sistema:
   - Identifica que é sobre Benefícios
   - Busca na base de conhecimento
   - Mostra badge 💼 Benefícios
   - Responde com informações precisas

---

## 🔧 Personalização

### Cores dos Agentes

Você pode personalizar as cores editando o CSS em `app_streamlit.py`:

```css
.badge-benefits { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.badge-safety { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
.badge-clinic { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
.badge-payroll { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
```

### Título e Subtítulo

Edite as linhas:
```python
st.markdown("# 🤖 Assistente Virtual de RH")
st.markdown('<p class="subtitle">Seu suporte especializado em Recursos Humanos</p>')
```

---

## 📦 Dependências

- `streamlit` - Interface web
- `agent_rh_4_agentes` - Sistema de agentes
- Todas as dependências do sistema RAG

---

## 🎉 Pronto!

Agora você tem uma interface web moderna e profissional para o chatbot de RH! 🚀
