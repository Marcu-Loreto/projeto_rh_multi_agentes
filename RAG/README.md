# 📚 Como Adicionar Documentos à Base de Conhecimento

## 📁 Estrutura de Diretórios

```
RAG/
├── beneficios/          # Documentos sobre benefícios
│   ├── plano_saude.txt
│   ├── vale_refeicao.txt
│   └── ...
├── seguranca/           # Documentos sobre segurança do trabalho
│   ├── epis.txt
│   ├── acidentes.txt
│   └── ...
├── ambulatorio/         # Documentos sobre ambulatório
│   ├── horarios.txt
│   ├── atestados.txt
│   └── ...
└── folha_pagamento/     # Documentos sobre folha de pagamento
    ├── salario.txt
    ├── ferias.txt
    └── ...
```

## ✅ Como Adicionar Novos Documentos

### 1. Escolha a Categoria

Determine em qual categoria seu documento se encaixa:
- **beneficios**: Plano de saúde, vale refeição, vale transporte, etc.
- **seguranca**: EPIs, acidentes, treinamentos de segurança, etc.
- **ambulatorio**: Atestados, exames, horários de atendimento, etc.
- **folha_pagamento**: Salário, férias, 13º, rescisão, etc.

### 2. Crie um Arquivo .txt

1. Navegue até a pasta correspondente em `RAG/`
2. Crie um novo arquivo `.txt` com nome descritivo
3. Escreva o conteúdo do documento

**Exemplo**: `RAG/beneficios/vale_transporte.txt`

```
VALE TRANSPORTE

Solicitação: Pelo portal RH > Benefícios > Vale Transporte
Prazo: Até dia 20 do mês anterior
Desconto: 6% do salário base
Tipos: Ônibus, metrô, trem
Alteração de rota: Até 5 dias antes do início do mês
Crédito: Último dia útil do mês anterior

CONTATO:
Email: beneficios@empresa.com
Ramal: 3001
```

### 3. Execute o Sistema

O sistema carregará automaticamente todos os arquivos `.txt`:

```bash
python agent_rh_4_agentes.py
```

Você verá a confirmação de carregamento:

```
📚 Carregando bases de conhecimento dos arquivos...

📁 Benefícios:
  ✓ Carregado: plano_saude.txt
  ✓ Carregado: vale_refeicao.txt
  ✓ Carregado: vale_transporte.txt

📁 Segurança do Trabalho:
  ✓ Carregado: epis.txt
  ✓ Carregado: acidentes.txt

...

✅ Total de documentos carregados: 8
```

## 📝 Dicas para Escrever Bons Documentos

### ✅ Boas Práticas

1. **Seja específico**: Inclua valores, datas, prazos exatos
2. **Use formatação clara**: Listas, tópicos, seções
3. **Inclua contatos**: Emails, ramais, links
4. **Mantenha atualizado**: Revise periodicamente
5. **Nome descritivo**: Use nomes de arquivo que descrevam o conteúdo

### ❌ Evite

1. Informações genéricas ou vagas
2. Textos muito longos (prefira dividir em múltiplos arquivos)
3. Informações desatualizadas
4. Duplicação de conteúdo

## 🔄 Atualizar Documentos Existentes

1. Abra o arquivo `.txt` que deseja atualizar
2. Faça as modificações necessárias
3. Salve o arquivo
4. Execute o sistema novamente

O sistema carregará automaticamente a versão atualizada!

## 🗑️ Remover Documentos

Simplesmente delete o arquivo `.txt` da pasta correspondente.

## 📊 Exemplo Completo

**Arquivo**: `RAG/folha_pagamento/13_salario.txt`

```
13º SALÁRIO

PRIMEIRA PARCELA:
- Data de pagamento: Até 30 de novembro
- Valor: 50% do salário base
- Sem descontos

SEGUNDA PARCELA:
- Data de pagamento: Até 20 de dezembro
- Valor: Saldo restante (50%)
- Descontos: INSS e IRRF

CÁLCULO:
- Base: Salário de dezembro
- Proporcional: Para quem trabalhou menos de 12 meses
- Fórmula: (Salário ÷ 12) × meses trabalhados

OBSERVAÇÕES:
- Descontos aplicados apenas na 2ª parcela
- Consulte seu holerite no Portal RH

DÚVIDAS:
Email: rh@empresa.com
Ramal: 2001
```

## 🚀 Pronto!

Agora você pode adicionar, atualizar e remover documentos facilmente sem mexer no código! 🎉
