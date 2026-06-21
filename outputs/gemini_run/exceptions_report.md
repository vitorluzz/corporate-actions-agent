# Relatório de Exceções — Asset Servicing

**Run:** `d69a17b5281c`  ·  **Gerado:** 2026-06-21 16:16 UTC

- Total de documentos: **7**
- Auto-aprovados: **4** (57%)
- Para revisão humana: **3**
- Rejeitados: **0**
- Confiança média (campos): **95%**
- Mix de tipos: DIVIDENDO=2, JCP=4, GRUPAMENTO=1

## Documentos que requerem atuação humana (3)

### 04_rede_varejo_jcp_sem_data.pdf — `HUMAN_REVIEW`
- **Tipo:** JCP (confiança 100%, entropia 0.00)
- **Identidade:** EXACT — casou por isin, ticker, cnpj, emissor → Rede Varejo Brasil S.A. (RVBR3).
- **Data Quality:** 0.92 (HIGH)
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
- **Tipo:** JCP (confiança 100%, entropia 0.00)
- **Identidade:** EXACT — casou por isin, ticker, cnpj, emissor → Telecom Norte Participações S.A. (TLNR4).
- **Data Quality:** 0.80 (MEDIUM)
- **Motivos:**
  - falha de coerência: groundedness — valores sem âncora na fonte (possível alucinação): data_aprovacao, data_com, data_ex, data_pagamento, moeda
  - campos de baixa confiança: data_com
  - documento escaneado — extração por visão; conferir a leitura
- **Ações requeridas:**
  - corrigir/validar: groundedness
  - revisar campos: data_com
  - validar valores contra a imagem
