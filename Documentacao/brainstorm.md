# Brainstorm — Evolução do Assistente Virtual de RH

> Itens extraídos dos gaps para produção identificados na arquitetura atual.
> Use este documento como base para sessões de brainstorm e priorização.

---

## 🔐 Segurança & Acesso

| #   | Item                                                                    | Complexidade | Impacto |
| --- | ----------------------------------------------------------------------- | ------------ | ------- |
| 1   | Autenticação e autorização (JWT, RBAC, SSO corporativo)                 | Alta         | Alto    |
| 2   | Rate limiting server-side e throttling por usuário                      | Média        | Alto    |
| 3   | Secrets management (Vault, AWS Secrets Manager)                         | Média        | Alto    |
| 4   | Audit trail (quem perguntou, qual agente respondeu, qual contexto usou) | Média        | Médio   |

---

## 💾 Persistência & Dados

| #   | Item                                                                        | Complexidade | Impacto |
| --- | --------------------------------------------------------------------------- | ------------ | ------- |
| 5   | Persistência de sessão e histórico de conversas (banco de dados)            | Média        | Alto    |
| 6   | Vector store persistente e escalável (Chroma Server, Qdrant ou Weaviate)    | Média        | Médio   |
| 7   | Cache de respostas e embeddings (Redis)                                     | Baixa        | Médio   |
| 8   | Gestão de contexto e memória de longo prazo (summarization, sliding window) | Alta         | Alto    |

---

## 🔍 RAG & Qualidade de Resposta

| #   | Item                                                                         | Complexidade | Impacto |
| --- | ---------------------------------------------------------------------------- | ------------ | ------- |
| 9   | Chunking inteligente com overlap e metadata enrichment                       | Média        | Alto    |
| 10  | Reranker (cross-encoder) após retrieval para melhorar precisão               | Média        | Alto    |
| 11  | Ingestão automatizada de documentos (pipeline ETL, versionamento de KB)      | Alta         | Médio   |
| 12  | Fallback gracioso quando nenhum documento é relevante (escalada para humano) | Baixa        | Alto    |
| 13  | Monitoramento de drift de qualidade das respostas ao longo do tempo          | Alta         | Médio   |

---

## 🏗️ Arquitetura & Infraestrutura

| #   | Item                                                       | Complexidade | Impacto |
| --- | ---------------------------------------------------------- | ------------ | ------- |
| 14  | API REST/GraphQL desacoplada do frontend (FastAPI)         | Média        | Alto    |
| 15  | Containerização (Docker + Docker Compose)                  | Baixa        | Médio   |
| 16  | Health checks e readiness probes                           | Baixa        | Médio   |
| 17  | Escalabilidade horizontal (workers async, filas)           | Alta         | Médio   |
| 18  | Multi-tenancy (suportar múltiplas áreas/empresas)          | Alta         | Baixo   |
| 19  | Política de retry e dead-letter queue para chamadas de LLM | Média        | Médio   |

---

## 📊 Observabilidade & Monitoramento

| #   | Item                                                    | Complexidade | Impacto |
| --- | ------------------------------------------------------- | ------------ | ------- |
| 20  | Logging estruturado (structlog JSON → ELK/Loki)         | Baixa        | Médio   |
| 21  | Métricas e alertas (OpenTelemetry, Prometheus, Grafana) | Média        | Médio   |

---

## 🧪 Qualidade & CI/CD

| #   | Item                                                                    | Complexidade | Impacto |
| --- | ----------------------------------------------------------------------- | ------------ | ------- |
| 22  | Testes automatizados (unit, integration, eval de qualidade de resposta) | Média        | Alto    |
| 23  | CI/CD pipeline                                                          | Média        | Médio   |
| 24  | Versionamento de prompts com A/B testing                                | Alta         | Médio   |

---

## 👤 Experiência do Usuário

| #   | Item                                                           | Complexidade | Impacto |
| --- | -------------------------------------------------------------- | ------------ | ------- |
| 25  | Feedback loop do usuário (thumbs up/down → prompt improvement) | Baixa        | Alto    |
| 26  | Human-in-the-loop para perguntas de alta sensibilidade         | Média        | Alto    |
| 27  | Suporte a múltiplos idiomas (internacionalização)              | Alta         | Baixo   |
| 28  | Documentação de API (OpenAPI/Swagger)                          | Baixa        | Baixo   |

---

## 💡 Ideias Adicionais (para discussão)

- **HyDE (Hypothetical Document Embeddings)** — Gerar documento hipotético antes da busca para melhorar recall
- **Agente de Treinamento & Desenvolvimento** — Expandir para área de T&D (cursos, PDI, avaliação de desempenho)
- **Integração com sistemas corporativos** — SAP HR, TOTVS, SuccessFactors para dados em tempo real
- **Chatbot multimodal** — Aceitar imagens de holerites/atestados para extração automática
- **Voice interface** — Integração com STT/TTS para atendimento por voz
- **Knowledge Graph** — Complementar RAG vetorial com grafo de conhecimento para relações complexas entre entidades
- **Auto-avaliação de confiança** — Agente emitir score de confiança na resposta e escalar para humano quando baixo
- **Dashboard gerencial** — Painel para RH ver temas mais perguntados, gargalos, e satisfação

---

## 🎯 Sugestão de Priorização (Quick Wins)

Itens de baixa complexidade e alto impacto para implementar primeiro:

1. **Feedback loop** (#25) — botão 👍/👎 no Streamlit
2. **Fallback para humano** (#12) — quando score < threshold, exibir mensagem de escalada
3. **Rate limiting server-side** (#2) — nginx ou middleware simples
4. **Cache Redis** (#7) — evitar reprocessamento de perguntas repetidas
5. **Docker Compose** (#15) — facilita deploy e onboarding de devs

---

_Documento criado em 29/06/2026 — Base: gaps da arquitetura_solucao.md_
