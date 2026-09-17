#!/usr/bin/env python3
"""
02_analise_exploratoria.py — Análise exploratória da base ALTA (spec 001)
===========================================================================

Spec: specs/001-construcao-dataset-ground-truth/requirements.md
ADRs: 0006 (blocagem TF-IDF/BM25), 0007 (escopo do dicionário)

Objetivo:
    Caracterizar a base real de produtos coletados (heterogeneidade de
    descrições, cobertura do dicionário canônico, distribuição por fonte/
    localização) para embasar as decisões de blocagem e amostragem do
    conjunto de teste anotado manualmente.

Entradas:
    dados/brutos/todos_mercados_*.csv
    dados/brutos/dicionario_canonico.csv

Saídas (esperadas, ver spec 001):
    resultados/metricas/estatisticas_descritivas.csv
    resultados/figuras/*.png

Status: esqueleto — implementação pendente (ver spec 001).

Uso:
    uv run python scripts/02_analise_exploratoria.py
"""

from __future__ import annotations

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SEED = 42
DADOS_BRUTOS = Path("dados/brutos")
RESULTADOS_METRICAS = Path("resultados/metricas")
RESULTADOS_FIGURAS = Path("resultados/figuras")


def estatisticas_descritivas(diretorio_brutos: Path) -> None:
    """Calcula estatísticas descritivas da base real (heterogeneidade, cobertura).

    Ver specs/001-construcao-dataset-ground-truth/requirements.md.
    """
    raise NotImplementedError(
        "Implementar conforme specs/001-construcao-dataset-ground-truth/requirements.md"
    )


def main() -> None:
    logger.info("Etapa 02 (EDA) ainda não implementada — ver spec 001.")
    estatisticas_descritivas(DADOS_BRUTOS)


if __name__ == "__main__":
    main()
