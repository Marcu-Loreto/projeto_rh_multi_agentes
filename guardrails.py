"""
🛡️ Guardrails de Segurança - Sistema de Atendimento RH
========================================================

Módulo centralizado de guardrails usando LLM-Guard.
Implementa validações de INPUT (entrada do usuário) e OUTPUT (resposta do agente).

Arquitetura:
- scan_input(): valida a mensagem do usuário antes de processar
- scan_output(): valida a resposta do agente antes de entregar ao usuário
- InputGuardrailResult / OutputGuardrailResult: resultados tipados

Uso:
    from guardrails import scan_input, scan_output

    # Antes de enviar ao agente
    input_result = scan_input(user_message)
    if not input_result.is_safe:
        return input_result.blocked_message

    # Depois de receber resposta do agente
    output_result = scan_output(prompt=user_message, response=agent_response)
    if not output_result.is_safe:
        return output_result.sanitized_response
"""

from dataclasses import dataclass, field
from typing import Optional
import logging

# LLM-Guard Input Scanners
from llm_guard.input_scanners import (
    Anonymize,
    BanTopics,
    PromptInjection,
    TokenLimit,
    Toxicity as InputToxicity,
)

# LLM-Guard Output Scanners
from llm_guard.output_scanners import (
    BanTopics as OutputBanTopics,
    NoRefusal,
    Relevance,
    Sensitive as OutputSensitive,
    Toxicity as OutputToxicity,
)

# Vault para gerenciar dados anonimizados
from llm_guard.vault import Vault

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

# Tópicos proibidos (tentativas de manipulação ou fora do escopo)
BANNED_INPUT_TOPICS = [
    "política",
    "religião",
    "investimentos financeiros",
    "apostas",
    "armas",
    "drogas",
]

BANNED_OUTPUT_TOPICS = [
    "política",
    "religião",
    "investimentos financeiros",
]

# Limite de tokens por mensagem de entrada
MAX_INPUT_TOKENS = 500

# Threshold de confiança para os scanners (0.0 a 1.0)
PROMPT_INJECTION_THRESHOLD = 0.5
TOXICITY_THRESHOLD = 0.7


# ============================================================================
# DATACLASSES DE RESULTADO
# ============================================================================


@dataclass
class InputGuardrailResult:
    """Resultado da validação de input."""

    is_safe: bool
    sanitized_prompt: str
    blocked_message: str = ""
    failed_scanners: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        if self.is_safe:
            return "✅ Input aprovado"
        return f"🚫 Input bloqueado por: {', '.join(self.failed_scanners)}"


@dataclass
class OutputGuardrailResult:
    """Resultado da validação de output."""

    is_safe: bool
    sanitized_response: str
    original_response: str
    failed_scanners: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        if self.is_safe:
            return "✅ Output aprovado"
        return f"⚠️ Output sanitizado por: {', '.join(self.failed_scanners)}"


# ============================================================================
# VAULT (para anonimização reversível)
# ============================================================================

_vault = Vault()


# ============================================================================
# INPUT SCANNERS (lazy initialization)
# ============================================================================

_input_scanners = None


def _get_input_scanners():
    """Inicializa os scanners de input (lazy loading para performance)."""
    global _input_scanners
    if _input_scanners is not None:
        return _input_scanners

    logger.info("🛡️ Inicializando input guardrails...")

    _input_scanners = [
        # 1. Detecção de Prompt Injection
        PromptInjection(threshold=PROMPT_INJECTION_THRESHOLD),
        # 2. Anonimização de dados sensíveis (CPF, email, telefone, etc.)
        Anonymize(vault=_vault),
        # 3. Detecção de toxicidade
        InputToxicity(threshold=TOXICITY_THRESHOLD),
        # 4. Limite de tokens (evita ataques de flooding)
        TokenLimit(limit=MAX_INPUT_TOKENS),
        # 5. Tópicos banidos
        BanTopics(topics=BANNED_INPUT_TOPICS, threshold=0.75),
    ]

    logger.info(f"✅ {len(_input_scanners)} input scanners carregados")
    return _input_scanners


# ============================================================================
# OUTPUT SCANNERS (lazy initialization)
# ============================================================================

_output_scanners = None


def _get_output_scanners():
    """Inicializa os scanners de output (lazy loading para performance)."""
    global _output_scanners
    if _output_scanners is not None:
        return _output_scanners

    logger.info("🛡️ Inicializando output guardrails...")

    _output_scanners = [
        # 1. Detecção de dados sensíveis na resposta
        OutputSensitive(),
        # 2. Detecção de toxicidade na resposta
        OutputToxicity(threshold=TOXICITY_THRESHOLD),
        # 3. Verificar relevância da resposta em relação ao prompt
        Relevance(),
        # 4. Tópicos banidos no output
        OutputBanTopics(topics=BANNED_OUTPUT_TOPICS, threshold=0.75),
        # 5. Detectar quando o modelo se recusa a responder (para logging)
        NoRefusal(),
    ]

    logger.info(f"✅ {len(_output_scanners)} output scanners carregados")
    return _output_scanners


# ============================================================================
# FUNÇÕES PRINCIPAIS
# ============================================================================


def scan_input(prompt: str) -> InputGuardrailResult:
    """
    Valida a entrada do usuário contra todos os guardrails de input.

    Args:
        prompt: Mensagem do usuário

    Returns:
        InputGuardrailResult com status de segurança e prompt sanitizado
    """
    if not prompt or not prompt.strip():
        return InputGuardrailResult(
            is_safe=False,
            sanitized_prompt="",
            blocked_message="Por favor, digite uma mensagem válida.",
            failed_scanners=["empty_input"],
        )

    scanners = _get_input_scanners()
    sanitized_prompt = prompt
    failed_scanners = []
    scores = {}

    for scanner in scanners:
        try:
            sanitized_prompt, is_valid, risk_score = scanner.scan(sanitized_prompt)
            scanner_name = scanner.__class__.__name__

            scores[scanner_name] = risk_score

            if not is_valid:
                failed_scanners.append(scanner_name)
                logger.warning(
                    f"🚫 Input scanner falhou: {scanner_name} "
                    f"(score: {risk_score:.2f})"
                )
        except Exception as e:
            scanner_name = scanner.__class__.__name__
            logger.error(f"❌ Erro no scanner {scanner_name}: {e}")
            # Fail-closed para scanners críticos de segurança
            critical_scanners = {"PromptInjection", "Anonymize", "Toxicity"}
            if scanner_name in critical_scanners:
                failed_scanners.append(scanner_name)
                logger.warning(
                    f"🔒 Fail-closed ativado para scanner crítico: {scanner_name}"
                )
            # Scanners não-críticos (BanTopics, TokenLimit): fail-open
            continue

    is_safe = len(failed_scanners) == 0

    # Mensagem amigável para o usuário quando bloqueado
    blocked_message = ""
    if not is_safe:
        if "PromptInjection" in failed_scanners:
            blocked_message = (
                "🚫 Desculpe, sua mensagem foi identificada como uma possível "
                "tentativa de manipulação. Por favor, reformule sua pergunta "
                "sobre RH de forma direta."
            )
        elif "Toxicity" in failed_scanners:
            blocked_message = (
                "🚫 Sua mensagem contém conteúdo inapropriado. "
                "Por favor, mantenha um tom respeitoso ao conversar comigo."
            )
        elif "BanTopics" in failed_scanners:
            blocked_message = (
                "🚫 Esse assunto está fora do meu escopo. "
                "Posso ajudar com questões de RH como benefícios, "
                "férias, folha de pagamento, segurança e ambulatório."
            )
        elif "TokenLimit" in failed_scanners:
            blocked_message = (
                "🚫 Sua mensagem é muito longa. "
                "Por favor, resuma sua pergunta em poucas frases."
            )
        else:
            blocked_message = (
                "🚫 Não foi possível processar sua mensagem. "
                "Por favor, tente reformulá-la."
            )

    result = InputGuardrailResult(
        is_safe=is_safe,
        sanitized_prompt=sanitized_prompt,
        blocked_message=blocked_message,
        failed_scanners=failed_scanners,
        scores=scores,
    )

    logger.info(f"Input scan: {result.summary}")
    return result


def scan_output(prompt: str, response: str) -> OutputGuardrailResult:
    """
    Valida a resposta do agente contra todos os guardrails de output.

    Args:
        prompt: Mensagem original do usuário (para análise de relevância)
        response: Resposta gerada pelo agente

    Returns:
        OutputGuardrailResult com status e resposta sanitizada
    """
    if not response or not response.strip():
        return OutputGuardrailResult(
            is_safe=False,
            sanitized_response="Desculpe, não consegui gerar uma resposta. Tente novamente.",
            original_response=response or "",
            failed_scanners=["empty_output"],
        )

    scanners = _get_output_scanners()
    sanitized_response = response
    failed_scanners = []
    scores = {}

    for scanner in scanners:
        try:
            sanitized_response, is_valid, risk_score = scanner.scan(
                prompt, sanitized_response
            )
            scanner_name = scanner.__class__.__name__

            scores[scanner_name] = risk_score

            if not is_valid:
                failed_scanners.append(scanner_name)
                logger.warning(
                    f"⚠️ Output scanner falhou: {scanner_name} "
                    f"(score: {risk_score:.2f})"
                )
        except Exception as e:
            logger.error(f"❌ Erro no output scanner {scanner.__class__.__name__}: {e}")
            continue

    is_safe = len(failed_scanners) == 0

    # Se output não é seguro, sanitizar ou substituir
    if not is_safe:
        # Se toxicidade ou dados sensíveis, substitui a resposta
        critical_failures = {"Toxicity", "Sensitive"}
        if critical_failures.intersection(failed_scanners):
            sanitized_response = (
                "Desculpe, tive um problema ao formular a resposta. "
                "Por favor, tente reformular sua pergunta."
            )

    result = OutputGuardrailResult(
        is_safe=is_safe,
        sanitized_response=sanitized_response,
        original_response=response,
        failed_scanners=failed_scanners,
        scores=scores,
    )

    logger.info(f"Output scan: {result.summary}")
    return result


# ============================================================================
# FUNÇÃO UTILITÁRIA PARA INTEGRAÇÃO COM O GRAFO
# ============================================================================


def validate_interaction(
    user_prompt: str, agent_response: Optional[str] = None
) -> tuple[InputGuardrailResult, Optional[OutputGuardrailResult]]:
    """
    Validação completa de uma interação (input + output).

    Útil para validar toda a conversa de uma vez.

    Args:
        user_prompt: Mensagem do usuário
        agent_response: Resposta do agente (None se ainda não gerada)

    Returns:
        Tupla com (resultado_input, resultado_output_ou_None)
    """
    input_result = scan_input(user_prompt)

    output_result = None
    if agent_response is not None:
        output_result = scan_output(user_prompt, agent_response)

    return input_result, output_result
