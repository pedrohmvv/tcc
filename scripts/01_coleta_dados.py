#!/usr/bin/env python3
"""
01_coleta_dados.py — Carregamento e validação dos dados brutos do projeto ALTA
================================================================================

Não corresponde a uma spec própria (ver `AGENTS.md`/`CLAUDE.md`: script 01 = "—").
Este script NÃO gera nem transforma dados — os arquivos em `dados/brutos/` já
existem e são imutáveis (coletados pela infraestrutura do projeto ALTA/Dharma-AI).
A responsabilidade deste script é apenas validar que os brutos esperados estão
presentes e com o schema mínimo, servindo de porta de entrada do pipeline.

Entradas:
    dados/brutos/todos_mercados_*.csv    (produtos coletados via PDV/API)
    dados/brutos/dicionario_canonico.csv (dicionário canônico ALTA)

Saídas:
    Nenhum arquivo novo. Loga estatísticas básicas (linhas, colunas) e falha
    com erro claro se algum bruto esperado estiver ausente ou com schema
    incompatível (ver `dados/brutos/README.md` e `specs/001-*/requirements.md`).

Uso:
    uv run python scripts/01_coleta_dados.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DADOS_BRUTOS = Path("dados/brutos")
COLUNAS_MERCADOS_MINIMAS = {"product_id", "description", "price", "source", "collected_at"}
COLUNAS_DICIONARIO_MINIMAS = {"desc_alim", "codg_item1", "cod_padrao"}


def localizar_arquivo_mercados(diretorio: Path) -> Path:
    """Localiza o CSV de produtos coletados (nome datado, ex. todos_mercados_2026-09-10.csv)."""
    candidatos = sorted(diretorio.glob("todos_mercados_*.csv"))
    if not candidatos:
        raise FileNotFoundError(
            f"Nenhum arquivo 'todos_mercados_*.csv' encontrado em {diretorio}/. "
            "Ver dados/brutos/README.md para a origem esperada (projeto ALTA)."
        )
    return candidatos[-1]


def validar_schema_produtos(df: pd.DataFrame, nome_arquivo: str = "produtos") -> None:
    """Valida (em memória, sem I/O) que `df` tem o schema mínimo de produtos coletados."""
    faltantes = COLUNAS_MERCADOS_MINIMAS - set(df.columns)
    if faltantes:
        raise ValueError(f"Colunas ausentes em {nome_arquivo}: {sorted(faltantes)}")


def validar_schema_dicionario(df: pd.DataFrame, nome_arquivo: str = "dicionario") -> None:
    """Valida (em memória, sem I/O) que `df` tem o schema mínimo do dicionário canônico."""
    faltantes = COLUNAS_DICIONARIO_MINIMAS - set(df.columns)
    if faltantes:
        raise ValueError(f"Colunas ausentes em {nome_arquivo}: {sorted(faltantes)}")


def validar_produtos_coletados(caminho: Path) -> pd.DataFrame:
    """Carrega o CSV de produtos coletados e valida seu schema mínimo."""
    df = pd.read_csv(caminho)
    validar_schema_produtos(df, nome_arquivo=caminho.name)
    logger.info(
        "Produtos coletados: %s (%d linhas, %d colunas)", caminho.name, len(df), df.shape[1]
    )
    return df


def validar_dicionario_canonico(caminho: Path) -> pd.DataFrame:
    """Carrega o CSV do dicionário canônico ALTA e valida seu schema mínimo."""
    if not caminho.exists():
        raise FileNotFoundError(f"Dicionário canônico não encontrado em {caminho}")
    df = pd.read_csv(caminho, sep=";")
    validar_schema_dicionario(df, nome_arquivo=caminho.name)
    logger.info("Dicionário canônico: %s (%d entradas)", caminho.name, len(df))
    return df


def main() -> None:
    if not DADOS_BRUTOS.exists():
        logger.error("Diretório %s não existe.", DADOS_BRUTOS)
        sys.exit(1)

    caminho_mercados = localizar_arquivo_mercados(DADOS_BRUTOS)
    caminho_dicionario = DADOS_BRUTOS / "dicionario_canonico.csv"

    validar_produtos_coletados(caminho_mercados)
    validar_dicionario_canonico(caminho_dicionario)

    logger.info("Dados brutos validados. Próxima etapa: scripts/02_analise_exploratoria.py")


if __name__ == "__main__":
    main()
