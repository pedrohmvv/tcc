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
from typing import TypedDict

import pandas as pd


class ContagensBasicas(TypedDict):
    """Contagens básicas exigidas por `main.tex` §4.7 (spec 001, tarefa 1.1.1)."""

    total_registros: int
    total_entradas_dicionario: int
    product_id_distintos: int
    descricoes_distintas: int
    distribuicao_source: dict[str, int]
    distribuicao_location: dict[str, int]
    distribuicao_estado: dict[str, int]


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SEED = 42
DADOS_BRUTOS = Path("dados/brutos")
RESULTADOS_METRICAS = Path("resultados/metricas")
RESULTADOS_FIGURAS = Path("resultados/figuras")


def extrair_estado(location: str) -> str:
    """Extrai a sigla do estado do campo `location` (formato "UF, Cidade, Loja")."""
    if "," not in location:
        raise ValueError(f"location sem o formato esperado 'UF, Cidade, Loja': {location!r}")
    return location.split(",", 1)[0].strip()


def calcular_contagens_basicas(
    df_produtos: pd.DataFrame, df_dicionario: pd.DataFrame
) -> ContagensBasicas:
    """Calcula as contagens básicas da amostra.

    Não lê `codg_item`, `desc_ref` nem `match_score` — apenas os campos
    descritivos da coleta (ADR-0010 trata `match_score` à parte, tarefa 1.1.3).
    """
    estados = df_produtos["location"].map(extrair_estado)
    return {
        "total_registros": len(df_produtos),
        "total_entradas_dicionario": len(df_dicionario),
        "product_id_distintos": df_produtos["product_id"].nunique(),
        "descricoes_distintas": df_produtos["description"].nunique(),
        "distribuicao_source": df_produtos["source"].value_counts().to_dict(),
        "distribuicao_location": df_produtos["location"].value_counts().to_dict(),
        "distribuicao_estado": estados.value_counts().to_dict(),
    }


def carregar_produtos(diretorio_brutos: Path) -> pd.DataFrame:
    """Localiza e carrega o CSV de produtos coletados (ver `01_coleta_dados.py`)."""
    candidatos = sorted(diretorio_brutos.glob("todos_mercados_*.csv"))
    if not candidatos:
        raise FileNotFoundError(
            f"Nenhum arquivo 'todos_mercados_*.csv' encontrado em {diretorio_brutos}/."
        )
    return pd.read_csv(candidatos[-1])


def carregar_dicionario(diretorio_brutos: Path) -> pd.DataFrame:
    """Carrega o dicionário canônico ALTA."""
    return pd.read_csv(diretorio_brutos / "dicionario_canonico.csv", sep=";")


def _salvar_contagens_escalares(contagens: ContagensBasicas, caminho: Path) -> None:
    linhas = [
        {"metrica": "total_registros", "valor": contagens["total_registros"]},
        {
            "metrica": "total_entradas_dicionario",
            "valor": contagens["total_entradas_dicionario"],
        },
        {"metrica": "product_id_distintos", "valor": contagens["product_id_distintos"]},
        {"metrica": "descricoes_distintas", "valor": contagens["descricoes_distintas"]},
    ]
    pd.DataFrame(linhas).to_csv(caminho, index=False)


def _salvar_distribuicoes(contagens: ContagensBasicas, caminho: Path) -> None:
    dimensoes: dict[str, dict[str, int]] = {
        "source": contagens["distribuicao_source"],
        "location": contagens["distribuicao_location"],
        "estado": contagens["distribuicao_estado"],
    }
    linhas = [
        {"dimensao": dimensao, "categoria": categoria, "contagem": contagem}
        for dimensao, distribuicao in dimensoes.items()
        for categoria, contagem in distribuicao.items()
    ]
    pd.DataFrame(linhas).to_csv(caminho, index=False)


def estatisticas_descritivas(
    diretorio_brutos: Path, diretorio_saida: Path = RESULTADOS_METRICAS
) -> ContagensBasicas:
    """Calcula e persiste as contagens básicas exigidas por `main.tex` §4.7 (spec 001, 1.1.1).

    Ver specs/001-construcao-dataset-ground-truth/requirements.md.
    """
    df_produtos = carregar_produtos(diretorio_brutos)
    df_dicionario = carregar_dicionario(diretorio_brutos)
    contagens = calcular_contagens_basicas(df_produtos, df_dicionario)

    diretorio_saida.mkdir(parents=True, exist_ok=True)
    _salvar_contagens_escalares(contagens, diretorio_saida / "estatisticas_descritivas.csv")
    _salvar_distribuicoes(contagens, diretorio_saida / "distribuicoes_categoricas.csv")
    logger.info(
        "EDA (1.1.1): %d registros, %d entradas no dicionário. Estatísticas em %s",
        contagens["total_registros"],
        contagens["total_entradas_dicionario"],
        diretorio_saida,
    )
    return contagens


def main() -> None:
    estatisticas_descritivas(DADOS_BRUTOS, RESULTADOS_METRICAS)


if __name__ == "__main__":
    main()
