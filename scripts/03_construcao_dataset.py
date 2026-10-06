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
    dados/brutos/todos_mercados_*.csv        (só a limpeza lê os brutos)
    dados/brutos/dicionario_canonico.csv
    (arquivo de anotação manual, produzido fora do pipeline — ver
     docs/protocolo_anotacao.md)

Saídas:
    dados/processados/produtos_limpos.parquet    (RF0, implementado)
    dados/processados/dicionario_limpo.parquet   (RF0, implementado)
    dados/processados/relatorio_limpeza.json     (RF0, implementado)
    dados/processados/candidatos_blocagem.parquet       (pendente)
    dados/processados/{treino,validacao,teste}.parquet  (pendente)

Etapas seguintes consomem a base limpa, nunca os brutos. Nenhuma saída em
dados/processados/ contém codg_item/desc_ref/match_score (ADR-0011).

Status: limpeza (RF0) implementada; blocagem e partição pendentes (spec 001).

[CRÍTICO] Nenhuma chamada ao Dataset Generator deve tocar os produtos
reservados ao teste — o particionamento por produto canônico precisa
ocorrer ANTES de qualquer geração/augmentation, com checagem explícita
(assert), não apenas por convenção (ADR-0004).

Uso:
    uv run python scripts/03_construcao_dataset.py
"""

from __future__ import annotations

import hashlib
import json
import logging
import unicodedata
from pathlib import Path
from typing import TypedDict

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SEED = 42
DADOS_BRUTOS = Path("dados/brutos")
DADOS_PROCESSADOS = Path("dados/processados")

# ADR-0011: predições do matcher ALTA nunca entram em dados/processados/.
COLUNAS_MATCHER_ALTA = ("codg_item", "desc_ref", "match_score")


# ── Limpeza da base (spec 001, RF0; critérios em docs/limpeza_dados.md) ──────


class RelatorioLimpeza(TypedDict):
    registros_brutos: int
    duplicatas_exatas_removidas: int
    registros_limpos: int
    grupos_texto_repetido_na_loja: int
    linhas_texto_repetido_na_loja: int
    precos_invalidos: int
    colunas_removidas_dicionario: list[str]


def normalizar_texto(texto: str) -> str:
    """Uppercase, sem acento e sem espaços nas pontas (igual à normalização da EDA, script 02)."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.upper().strip()


def remover_duplicatas_exatas(df: pd.DataFrame) -> pd.DataFrame:
    """Remove linhas idênticas em todas as colunas, mantendo a primeira ocorrência."""
    return df.loc[~df.duplicated(keep="first")].reset_index(drop=True)


def marcar_texto_repetido_na_loja(df: pd.DataFrame) -> pd.DataFrame:
    """Marca registros cuja descrição normalizada se repete na mesma loja (SKUs distintos).

    Não remove: são produtos distintos do catálogo da loja com o mesmo texto,
    não defeito de coleta comprovado (docs/limpeza_dados.md, critério C2).
    """
    descricao_normalizada = df["description"].map(normalizar_texto)
    repetido = df.assign(_desc=descricao_normalizada).duplicated(["_desc", "source"], keep=False)
    return df.assign(texto_repetido_na_loja=repetido.to_numpy())


def marcar_preco_invalido(df: pd.DataFrame) -> pd.DataFrame:
    """Marca preço não positivo sem alterar o valor (preço não entra no matching)."""
    return df.assign(preco_invalido=(df["price"] <= 0).to_numpy())


def remover_colunas_matcher_alta(df: pd.DataFrame) -> pd.DataFrame:
    """Remove as predições do matcher ALTA (ADR-0011): o baseline as lê direto dos brutos."""
    return df.drop(columns=[c for c in COLUNAS_MATCHER_ALTA if c in df.columns])


def limpar_dicionario(df_dicionario: pd.DataFrame) -> pd.DataFrame:
    """Remove as colunas sem nome e totalmente vazias do CSV original do dicionário."""
    vazias = [
        c
        for c in df_dicionario.columns
        if str(c).startswith("Unnamed") and df_dicionario[c].isna().all()
    ]
    return df_dicionario.drop(columns=vazias)


def limpar_base(
    df_produtos: pd.DataFrame, df_dicionario: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, RelatorioLimpeza]:
    """Aplica os critérios de docs/limpeza_dados.md sem alterar os DataFrames de entrada.

    Só remove o que é defeito objetivo de coleta (duplicata exata); ruído
    linguístico de PDV é o objeto de estudo do TCC e nunca é removido.
    """
    sem_duplicatas = remover_duplicatas_exatas(df_produtos)
    produtos = marcar_preco_invalido(marcar_texto_repetido_na_loja(sem_duplicatas))
    produtos = remover_colunas_matcher_alta(produtos)
    assert not set(COLUNAS_MATCHER_ALTA) & set(produtos.columns), "ADR-0011 violado"

    dicionario = limpar_dicionario(df_dicionario)
    repetidos = produtos[produtos["texto_repetido_na_loja"]]
    relatorio: RelatorioLimpeza = {
        "registros_brutos": len(df_produtos),
        "duplicatas_exatas_removidas": len(df_produtos) - len(sem_duplicatas),
        "registros_limpos": len(produtos),
        "grupos_texto_repetido_na_loja": int(
            repetidos.assign(_desc=repetidos["description"].map(normalizar_texto))
            .groupby(["_desc", "source"])
            .ngroups
        ),
        "linhas_texto_repetido_na_loja": len(repetidos),
        "precos_invalidos": int(produtos["preco_invalido"].sum()),
        "colunas_removidas_dicionario": [
            c for c in df_dicionario.columns if c not in dicionario.columns
        ],
    }
    return produtos, dicionario, relatorio


def _sha256_arquivo(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _sha256_conteudo(df: pd.DataFrame) -> str:
    return hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()


def executar_limpeza(
    diretorio_brutos: Path = DADOS_BRUTOS, diretorio_processados: Path = DADOS_PROCESSADOS
) -> RelatorioLimpeza:
    """Lê os brutos (imutáveis), limpa e grava a base limpa + relatório em dados/processados/."""
    caminho_produtos = sorted(diretorio_brutos.glob("todos_mercados_*.csv"))[-1]
    caminho_dicionario = diretorio_brutos / "dicionario_canonico.csv"
    df_produtos = pd.read_csv(caminho_produtos)
    df_dicionario = pd.read_csv(caminho_dicionario, sep=";")

    produtos, dicionario, relatorio = limpar_base(df_produtos, df_dicionario)

    diretorio_processados.mkdir(parents=True, exist_ok=True)
    produtos.to_parquet(diretorio_processados / "produtos_limpos.parquet", index=False)
    dicionario.to_parquet(diretorio_processados / "dicionario_limpo.parquet", index=False)
    rastreio = {
        **relatorio,
        "sha256_brutos": {
            caminho_produtos.name: _sha256_arquivo(caminho_produtos),
            caminho_dicionario.name: _sha256_arquivo(caminho_dicionario),
        },
        "sha256_conteudo_limpo": {
            "produtos_limpos": _sha256_conteudo(produtos),
            "dicionario_limpo": _sha256_conteudo(dicionario),
        },
    }
    (diretorio_processados / "relatorio_limpeza.json").write_text(
        json.dumps(rastreio, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(
        "Limpeza: %d → %d registros (%d duplicatas exatas removidas).",
        relatorio["registros_brutos"],
        relatorio["registros_limpos"],
        relatorio["duplicatas_exatas_removidas"],
    )
    return relatorio


def gerar_candidatos_blocagem(diretorio_processados: Path) -> None:
    """Gera candidatos via blocagem lexical (TF-IDF/BM25) sobre a base limpa — ADR-0006."""
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
    executar_limpeza(DADOS_BRUTOS, DADOS_PROCESSADOS)
    gerar_candidatos_blocagem(DADOS_PROCESSADOS)
    particionar_por_produto_canonico()


if __name__ == "__main__":
    main()
