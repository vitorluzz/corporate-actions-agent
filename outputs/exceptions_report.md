# Relatório de Exceções — Asset Servicing

**Run:** `5451aa15fe8e`  ·  **Gerado:** 2026-06-21 16:17 UTC

- Total de documentos: **8**
- Auto-aprovados: **3** (38%)
- Para revisão humana: **5**
- Rejeitados: **0**
- Confiança média (campos): **95%**
- Mix de tipos: DIVIDENDO=3, JCP=2, GRUPAMENTO=1, INCERTO=1, BONIFICACAO=1

## Documentos que requerem atuação humana (5)

### 03_siderurgica_paranaense_proventos.pdf — `HUMAN_REVIEW`
- **Tipo:** DIVIDENDO (confiança 100%, entropia 0.00)
- **Identidade:** EXACT — casou por isin, ticker, cnpj, emissor → Companhia Siderúrgica Paranaense S.A. (CSPR3).
- **Data Quality:** 0.89 (HIGH)
- **Motivos:**
  - falha de coerência: event_type_substance — classificado como dividendo, mas há retenção na fonte (líquido < bruto) — substância compatível com JCP; confirmar tipo e tratamento tributário
- **Ações requeridas:**
  - corrigir/validar: event_type_substance

### 04_rede_varejo_jcp_sem_data.pdf — `HUMAN_REVIEW`
- **Tipo:** JCP (confiança 100%, entropia 0.00)
- **Identidade:** EXACT — casou por isin, ticker, cnpj, emissor → Rede Varejo Brasil S.A. (RVBR3).
- **Data Quality:** 0.91 (HIGH)
- **Motivos:**
  - campos obrigatórios ausentes
- **Ações requeridas:**
  - preencher campos: data_pagamento

### 05_aurora_saneamento_dividendo_datas.pdf — `HUMAN_REVIEW`
- **Tipo:** DIVIDENDO (confiança 100%, entropia 0.00)
- **Identidade:** EXACT — casou por isin, ticker, cnpj, emissor → Aurora Saneamento S.A. (AURS3).
- **Data Quality:** 0.87 (HIGH)
- **Motivos:**
  - falha de coerência: date_order — data_ex (2026-07-16) deve preceder data_pagamento (2026-07-10)
- **Ações requeridas:**
  - corrigir/validar: date_order

### 07_telecom_norte_jcp_SCAN.pdf — `HUMAN_REVIEW`
- **Tipo:** INCERTO (confiança 100%, entropia 0.00)
- **Identidade:** NONE — Nenhum identificador (ISIN/ticker/CNPJ/emissor) encontrado na base de referência — emissor desconhecido. Requer cadastro/validação humana.
- **Data Quality:** 0.54 (LOW)
- **Motivos:**
  - tipo de evento ambíguo/genérico (INCERTO)
  - campos obrigatórios ausentes
  - documento escaneado não pôde ser lido automaticamente (sem camada de texto; requer visão/OCR ou leitura humana)
  - Data Quality abaixo do limiar (0.54 < 0.75)
- **Ações requeridas:**
  - classificar o tipo de evento manualmente
  - preencher campos: emissor, isin, ticker
  - ler o documento manualmente ou reprocessar com visão (Gemini)

### 08_construtora_horizonte_bonificacao.pdf — `HUMAN_REVIEW`
- **Tipo:** BONIFICACAO (confiança 100%, entropia 0.00)
- **Identidade:** NONE — Nenhum identificador (ISIN/ticker/CNPJ/emissor) encontrado na base de referência — emissor desconhecido. Requer cadastro/validação humana.
- **Data Quality:** 0.82 (HIGH)
- **Motivos:**
  - emissor desconhecido (fora da base de referência)
- **Ações requeridas:**
  - cadastrar/validar o emissor na base de referência
