# Relatório de Exceções — Asset Servicing

**Run:** `7e3c6df4b1f5`  ·  **Gerado:** 2026-06-21 23:53 UTC

- Total de documentos: **8**
- Auto-aprovados: **4** (50%)
- Para revisão humana: **4**
- Rejeitados: **0**
- Confiança média (campos): **97%**
- Mix de tipos: DIVIDENDO=2, JCP=4, GRUPAMENTO=1, BONIFICACAO=1

## Documentos que requerem atuação humana (4)

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
- **Data Quality:** 0.97 (HIGH)
- **Motivos:**
  - documento escaneado — leitura automática (OCR/visão); conferir os valores contra a imagem
- **Ações requeridas:**
  - validar os valores extraídos contra a imagem do documento

### 08_construtora_horizonte_bonificacao.pdf — `HUMAN_REVIEW`
- **Tipo:** BONIFICACAO (confiança 100%, entropia 0.00)
- **Identidade:** NONE — Nenhum identificador (ISIN/ticker/CNPJ/emissor) encontrado na base de referência — emissor desconhecido. Requer cadastro/validação humana.
- **Data Quality:** 0.82 (HIGH)
- **Motivos:**
  - emissor desconhecido (fora da base de referência)
- **Ações requeridas:**
  - cadastrar/validar o emissor na base de referência
