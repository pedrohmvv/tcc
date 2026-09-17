#!/usr/bin/env python3
"""
06_avaliacao_exportacao.py — Avaliação final, ablação e exportação (spec 004)
=================================================================================

Spec: specs/004-avaliacao-e-ablacao/requirements.md
ADRs: 0006 (blocagem), 0007 (escopo do dicionário), 0008 (McNemar)

Objetivo:
    Consolidar a avaliação comparativa do Cross-Encoder fine-tuned contra
    os baselines (spec 002), com teste de McNemar + tamanho de efeito + IC,
    ablação (augmentation, mineração de negativos), pipeline progressivo e
    análise de erro qualitativa. Exportar todos os artefatos para
    `latex/tcc_artigo/`.

Entradas:
    dados/processados/teste.parquet (spec 001)
    modelos/adapter_lora/ (spec 003)
    resultados/metricas/baselines_comparacao.csv (spec 002)

Saídas (esperadas, ver spec 004):
    resultados/metricas/*.csv
    latex/tcc_artigo/tabelas/*.tex
    latex/tcc_artigo/figuras/*.eps

Status: esqueleto — implementação pendente (ver spec 004).

Regra: nunca escrever número/tabela manualmente no .tex — sempre gerar aqui
e usar \\input{}/\\includegraphics{} no LaTeX (ver skill abnt-latex).

Uso:
    uv run python scripts/06_avaliacao_exportacao.py
"""

from __future__ import annotations

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SEED = 42
RESULTADOS_METRICAS = Path("resultados/metricas")
LATEX_TABELAS = Path("latex/tcc_artigo/tabelas")
LATEX_FIGURAS = Path("latex/tcc_artigo/figuras")


def comparar_com_baselines(mcnemar: bool = True) -> None:
    """Compara Cross-Encoder fine-tuned vs. baselines (McNemar + effect size + IC — ADR-0008)."""
    raise NotImplementedError("Implementar conforme specs/004-avaliacao-e-ablacao/requirements.md")


def ablacao_augmentation_e_negativos() -> None:
    """Ablação: impacto da augmentation sintética e da mineração de negativos difíceis."""
    raise NotImplementedError("Implementar conforme specs/004-avaliacao-e-ablacao/requirements.md")


def exportar_para_latex(diretorio_tabelas: Path, diretorio_figuras: Path) -> None:
    """Exporta tabelas/figuras diretamente para latex/tcc_artigo/ (nunca editar o .tex à mão)."""
    raise NotImplementedError("Implementar conforme specs/004-avaliacao-e-ablacao/requirements.md")


def main() -> None:
    logger.info("Etapa 06 (avaliação/exportação) ainda não implementada — ver spec 004.")
    comparar_com_baselines()
    ablacao_augmentation_e_negativos()
    exportar_para_latex(LATEX_TABELAS, LATEX_FIGURAS)


if __name__ == "__main__":
    main()
