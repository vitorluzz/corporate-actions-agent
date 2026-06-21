"""Domain enumerations for Brazilian corporate-event (provento) processing.

Event-type taxonomy is intentionally explicit because the *tax/operational
treatment* differs per type — misclassification is a financial/regulatory error
(see README "Modelagem de domínio"). ``OUTRO`` / ``INCERTO`` give the agent an
honest escape hatch instead of forcing a confident-but-wrong label.
"""

from __future__ import annotations

from enum import Enum


class EventType(str, Enum):
    """Corporate-event types (proventos e eventos societários) on B3/CVM."""

    DIVIDENDO = "DIVIDENDO"            # lucro distribuído; isento de IR p/ PF
    JCP = "JCP"                        # juros sobre capital próprio; IRRF 15%
    BONIFICACAO = "BONIFICACAO"        # ações novas; proporção %
    GRUPAMENTO = "GRUPAMENTO"          # reverse split; muda quantidade
    DESDOBRAMENTO = "DESDOBRAMENTO"    # split; muda quantidade
    SUBSCRICAO = "SUBSCRICAO"          # direito de subscrição
    RENDIMENTO = "RENDIMENTO"          # rendimento (fundos/FII)
    PROVENTOS = "PROVENTOS"            # guarda-chuva genérico/ambíguo
    OUTRO = "OUTRO"                    # tipo identificado fora da taxonomia
    INCERTO = "INCERTO"               # não foi possível determinar com confiança

    @property
    def is_taxable_jcp(self) -> bool:
        return self is EventType.JCP

    @property
    def is_cash_provento(self) -> bool:
        """Eventos que pagam caixa por ação (valor), não proporção."""
        return self in {EventType.DIVIDENDO, EventType.JCP, EventType.RENDIMENTO}

    @property
    def is_share_ratio_event(self) -> bool:
        """Eventos expressos como proporção/razão de ações."""
        return self in {
            EventType.BONIFICACAO,
            EventType.GRUPAMENTO,
            EventType.DESDOBRAMENTO,
        }

    @property
    def is_ambiguous(self) -> bool:
        return self in {EventType.PROVENTOS, EventType.OUTRO, EventType.INCERTO}


class ShareClass(str, Enum):
    """Classe da ação, inferível pelo sufixo do ticker."""

    ON = "ON"      # ordinária — ticker sufixo 3
    PN = "PN"      # preferencial — ticker sufixo 4 (e 5/6/7/8)
    UNIT = "UNIT"  # unit — ticker sufixo 11


class FieldName(str, Enum):
    """Campos canônicos extraídos (mínimo exigido pelo enunciado + apoio)."""

    EMISSOR = "emissor"
    CNPJ = "cnpj"
    ISIN = "isin"
    TICKER = "ticker"
    TIPO_EVENTO = "tipo_evento"
    DATA_APROVACAO = "data_aprovacao"
    DATA_COM = "data_com"
    DATA_EX = "data_ex"
    DATA_PAGAMENTO = "data_pagamento"
    VALOR = "valor"
    VALOR_BRUTO = "valor_bruto"
    VALOR_LIQUIDO = "valor_liquido"
    PROPORCAO = "proporcao"
    MOEDA = "moeda"


class GuardrailStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    NA = "NA"


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class GoldenMatchStatus(str, Enum):
    EXACT = "EXACT"        # todos os identificadores conferem
    PARTIAL = "PARTIAL"    # alguns conferem, outros ausentes
    CONFLICT = "CONFLICT"  # identificadores apontam para registros distintos
    NONE = "NONE"          # emissor não encontrado na base de referência


class RoutingDecision(str, Enum):
    AUTO_APPROVE = "AUTO_APPROVE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    REJECT = "REJECT"


class ConfidenceLabel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DocumentClass(str, Enum):
    NATIVE = "NATIVE"      # PDF com camada de texto
    SCANNED = "SCANNED"    # imagem/escaneado -> visão


class EvidenceSource(str, Enum):
    NATIVE_TEXT = "NATIVE_TEXT"  # extraído do texto + bbox via PyMuPDF
    VISION = "VISION"            # extraído por visão (scan) + bbox espacial
    DERIVED = "DERIVED"          # derivado/calculado, sem âncora textual direta
