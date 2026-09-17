#!/usr/bin/env python3
"""
03_construcao_dataset.py — Construção do dataset e ground truth (spec 001)
=============================================================================

Spec: specs/001-construcao-dataset-ground-truth/requirements.md
ADRs: 0004 (estratégia treino/teste), 0005 (confiabilidade teste-reteste),
      0006 (blocagem TF-IDF/BM25), 0007 (escopo do dicionário)

Objetivo:
    Produzir partições treino/validação/teste sem vazamento, combinando
    geração assistida (Dataset Generator, só treino) e anotação manual
    independente (teste), a partir dos dados reais do projeto ALTA.

Entradas:
    dados/brutos/todos_mercados_*.csv
    dados/brutos/dicionario_canonico.csv
    (arquivo de anotação manual, produzido fora do pipeline — ver
     docs/protocolo_anotacao.md)

Saídas (esperadas, ver spec 001):
    dados/processados/candidatos_blocagem.parquet
    dados/processados/{treino,validacao,teste}.parquet

Status: esqueleto — implementação pendente (ver spec 001).

[CRÍTICO] Nenhuma chamada ao Dataset Generator deve tocar os produtos
reservados ao teste — o particionamento por produto canônico precisa
ocorrer ANTES de qualquer geração/augmentation, com checagem explícita
(assert), não apenas por convenção (ADR-0004).

Uso:
    uv run python scripts/03_construcao_dataset.py
"""

from __future__ import annotations

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SEED = 42
DADOS_BRUTOS = Path("dados/brutos")
DADOS_PROCESSADOS = Path("dados/processados")


def gerar_candidatos_blocagem(diretorio_brutos: Path) -> None:
    """Gera candidatos via blocagem lexical (TF-IDF/BM25) — ADR-0006."""
    raise NotImplementedError(
        "Implementar conforme specs/001-construcao-dataset-ground-truth/requirements.md"
    )


def particionar_por_produto_canonico() -> None:
    """Particiona treino/validação/teste por produto canônico, antes de qualquer geração.

    [CRÍTICO] validar com assert que nenhum produto do teste aparece no treino.
    """
    raise NotImplementedError(
        "Implementar conforme specs/001-construcao-dataset-ground-truth/requirements.md"
    )


def main() -> None:
    logger.info("Etapa 03 (construção do dataset) ainda não implementada — ver spec 001.")
    gerar_candidatos_blocagem(DADOS_BRUTOS)
    particionar_por_produto_canonico()


if __name__ == "__main__":
    main()
