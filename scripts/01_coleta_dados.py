#!/usr/bin/env python3
"""
01_coleta_dados.py — Validação dos brutos do ALTA e limpeza da base
=====================================================================

Spec: specs/001-construcao-dataset-ground-truth/requirements.md (RF0)
ADRs: 0011 (papéis das colunas), 0012 (limpeza no script 01)

Valida que os brutos esperados estão presentes e com o schema mínimo e, em
seguida, grava a base limpa que todo o pipeline consome (critérios C1–C5 de
`docs/limpeza_dados.md`). `dados/brutos/` é imutável: nada é escrito ali.

Entradas:
    dados/brutos/todos_mercados_*.csv    (produtos coletados via PDV/API)
    dados/brutos/dicionario_canonico.csv (dicionário canônico ALTA)

Saídas:
    dados/processados/produtos_limpos.parquet   (sem codg_item/desc_ref/match_score — ADR-0011)
    dados/processados/dicionario_limpo.parquet
    dados/processados/relatorio_limpeza.json    (contagens + SHA-256 dos brutos e do conteúdo limpo)
    Falha com erro claro se algum bruto esperado estiver ausente ou com schema
    incompatível (ver `dados/brutos/README.md`).

Uso:
    uv run python scripts/01_coleta_dados.py
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import unicodedata
from pathlib import Path
from typing import TypedDict

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DADOS_BRUTOS = Path("dados/brutos")
DADOS_PROCESSADOS = Path("dados/processados")
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
    """Valida os brutos (imutáveis), limpa e grava base limpa + relatório em dados/processados/."""
    caminho_produtos = localizar_arquivo_mercados(diretorio_brutos)
    caminho_dicionario = diretorio_brutos / "dicionario_canonico.csv"
    df_produtos = validar_produtos_coletados(caminho_produtos)
    df_dicionario = validar_dicionario_canonico(caminho_dicionario)

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


def main() -> None:
    if not DADOS_BRUTOS.exists():
        logger.error("Diretório %s não existe.", DADOS_BRUTOS)
        sys.exit(1)

    executar_limpeza(DADOS_BRUTOS, DADOS_PROCESSADOS)

    logger.info(
        "Brutos validados e base limpa gravada. Próxima etapa: scripts/02_analise_exploratoria.py"
    )


if __name__ == "__main__":
    main()
