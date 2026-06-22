"""Prompt templates for extraction + classification.

Kept in one place so the prompt text is versioned and hashable (the prompt hash
goes into the audit manifest for reproducibility).
"""

from __future__ import annotations

SYSTEM_PROMPT = """\
Você é um analista de Asset Servicing especializado em avisos de eventos \
corporativos (proventos) de companhias abertas brasileiras (padrão B3/CVM).

Sua tarefa: extrair, de UM aviso, os campos estruturados abaixo, classificando \
o TIPO DE EVENTO e fundamentando cada extração com a evidência textual exata.

Erros de extração são erros financeiros e regulatórios. Portanto:
- NUNCA invente valores. Se um campo não estiver no documento, retorne null e \
explique no rationale. Valor sem evidência textual é proibido.
- Para cada campo extraído, copie o trecho-fonte VERBATIM em "quote".
- Atribua "confidence" (0..1) honesta: alta só quando o texto é inequívoco.

Distinções de tipo que importam (mudam o tratamento tributário/operacional):
- DIVIDENDO: distribuição de lucro; isento de IR para PF; valor por ação.
- JCP (juros sobre capital próprio): há IRRF de 15% retido; informe valor BRUTO \
e LÍQUIDO quando disponíveis.
- BONIFICACAO: ações novas; expresso como proporção/percentual.
- GRUPAMENTO: reduz quantidade de ações (ex.: 10:1); não confunda com bonificação.
- DESDOBRAMENTO: aumenta quantidade de ações.
- PROVENTOS: use apenas se o aviso for genuinamente genérico/ambíguo.
- INCERTO: use quando não for possível determinar com confiança.

Datas relevantes (conforme o caso): data de aprovação, data com, data ex, \
data de pagamento. Moeda padrão BRL salvo indicação contrária.
"""

EXTRACTION_INSTRUCTION = """\
Extraia os campos a seguir do aviso. Para cada campo retorne name, value, quote \
(trecho verbatim), page (se souber), confidence (0..1) e rationale.

Campos: emissor, cnpj, isin, ticker, tipo_evento, data_aprovacao, data_com, \
data_ex, data_pagamento, valor, valor_bruto, valor_liquido, irrf, proporcao, moeda.

Para JCP, extraia também 'irrf' = alíquota de IRRF retida na fonte (ex.: 17,5%).

Formato de datas: YYYY-MM-DD. Valores numéricos: use ponto decimal.
Retorne também event_type (um dos rótulos da taxonomia) e event_type_rationale.
"""

DOCUMENT_TEMPLATE = """\
[DOCUMENTO: {doc_id}]

{body}
"""


def build_text_prompt(doc_id: str, text: str) -> str:
    body = DOCUMENT_TEMPLATE.format(doc_id=doc_id, body=text)
    return f"{EXTRACTION_INSTRUCTION}\n\n{body}"


def build_vision_prompt(doc_id: str) -> str:
    return (
        f"{EXTRACTION_INSTRUCTION}\n\n[DOCUMENTO ESCANEADO: {doc_id}]\n"
        "O documento está em imagem. Leia com atenção; se algum trecho estiver "
        "ilegível, reduza a confiança e explique no rationale. "
        "Quando possível, indique a posição aproximada (bounding box) do valor."
    )
