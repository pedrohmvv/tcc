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
    dados/processados/{produtos_limpos,dicionario_limpo}.parquet
        (base limpa gravada pelo script 01 — ADR-0012; o 03 nunca lê os brutos)
    configs/blocagem.yaml (seed, tamanho da amostra, varredura de k, método e k congelados)
    configs/blocagem_pxp.yaml (1b: pool em lotes, método e k, alocação do teste, τ da partição)
    (arquivo de anotação manual, produzido fora do pipeline — ver
     docs/protocolo_anotacao.md)

Saídas (ver spec 001):
    dados/processados/anotacoes_amostra_cega.csv   (planilha SEM candidatos; nunca sobrescrita)
    resultados/metricas/recall_blocagem.csv        (só depois de a planilha estar toda anotada)
    latex/tcc_artigo/tabelas/tab_recall_blocagem.tex  (idem; gerada a partir do recall)
    dados/processados/candidatos_blocagem.parquet  (só com `metodo` e `k` congelados no YAML)
    dados/processados/anotacoes_teste_pxp.csv      (teste p×p, SEM rótulo; nunca sobrescrita)
    dados/processados/componentes_pxp.parquet      (componente e partição de cada produto p×p)
    dados/processados/pool_cego/lote_NN.csv        (1b: pool a anotar, em lotes; nunca sobrescrito)
    resultados/metricas/recall_blocagem_pxp.csv    (1b: só depois da parada do pool)
    dados/processados/pares_teste_pxp.csv          (1b: 300 pares sorteados, SEM rótulo; uma vez)
    dados/processados/componentes_pxp.parquet      (componente e partição de cada produto p×p)
    resultados/metricas/{particao,vazamento_residual}_pxp.csv   (resumo e limite do critério τ)
    dados/processados/validacao_pxp.parquet        (pares do pool na validação, rótulo do autor)
    dados/processados/produtos_treino_pxp.parquet  (só produtos; entrada da geração de treino)
    dados/processados/pares_b2_pxp.csv             (1b: pares do treino a anotar, congelados; B2)
    dados/processados/anotacoes_treino_b2_pxp.csv  (1b: planilha do B2, SEM rótulo; nunca sobrescr.)
    dados/processados/pares_treino_auto_pxp.parquet (parte A do treino: negativos por tamanho e
                                                     positivos por perturbação; ADR-0015)
    dados/processados/treino_pxp.parquet           (treino p×p: parte A + anotação B2 + TAIL)
    dados/processados/teste_pxp.parquet            (pendente: só sai da anotação do autor)

Nenhuma saída em dados/processados/ contém codg_item/desc_ref/match_score (ADR-0011).

Status: blocagem produto × dicionário (1.2a) implementada. Produto × produto (1.2b) implementada
até a partição (T0 a T12): pool, recall, teste, planilha do teste, componentes, validação e
produtos de treino. Pendentes: partição produto × dicionário, pares de treino, TAIL e ingestão do
teste anotado.

[CRÍTICO] Nenhuma chamada ao Dataset Generator deve tocar os produtos
reservados ao teste — o particionamento por produto canônico precisa
ocorrer ANTES de qualquer geração/augmentation, com checagem explícita
(assert), não apenas por convenção (ADR-0004).

Uso:
    uv run python scripts/03_construcao_dataset.py
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import logging
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Callable, Sequence
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any, NamedTuple, TypedDict
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
import yaml
from rank_bm25 import BM25Okapi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from sklearn.feature_extraction.text import TfidfVectorizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DADOS_PROCESSADOS = Path("dados/processados")
RESULTADOS_METRICAS = Path("resultados/metricas")
LATEX_TABELAS = Path("latex/tcc_artigo/tabelas")
CONFIG_BLOCAGEM = Path("configs/blocagem.yaml")
CONFIG_BLOCAGEM_PXP = Path("configs/blocagem_pxp.yaml")
CONFIG_PARES_TREINO_PXP = Path("configs/pares_treino_pxp.yaml")
CONFIG_PARES_TAIL_PXP = Path("configs/pares_tail_pxp.yaml")
DADOS_BRUTOS_TAIL = Path("dados/brutos/tail")

METODOS = ("tfidf", "bm25")
SEM_ENTRADA = "sem_entrada"
INCERTO = "incerto"
COLUNAS_MATCHER_ALTA = ("codg_item", "desc_ref", "match_score")
COLUNAS_PLANILHA = [
    "id_produto",
    "descricao",
    "tipo_par",
    "origem",
    "und_val",
    "und_med",
    "entrada_indicada",
    "observacao",
    "timestamp_anotacao",
]
COLUNAS_RANKING = ["id_produto", "metodo", "rank", "desc_alim", "score"]
_LOTE_PRODUTOS = 2000


def _carregar_script(nome_arquivo: str) -> ModuleType:
    """Carrega outro script numerado para reaproveitar a normalização (sem duplicá-la)."""
    spec = importlib.util.spec_from_file_location(
        nome_arquivo, Path(__file__).resolve().parent / nome_arquivo
    )
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


normalizar_texto = _carregar_script("01_coleta_dados.py").normalizar_texto
tokenizar = _carregar_script("02_analise_exploratoria.py").tokenizar


class ConfigBlocagem(TypedDict):
    seed: int
    n_amostra: int
    ks: list[int]
    metodos: list[str]
    metodo: str | None
    k: int | None


def carregar_config(caminho: Path) -> ConfigBlocagem:
    """Lê o YAML versionado da blocagem e valida método e k congelados."""
    cfg: dict[str, Any] = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    if cfg["metodo"] is not None and cfg["metodo"] not in METODOS:
        raise ValueError(f"metodo inválido em {caminho}: {cfg['metodo']!r} (esperado {METODOS})")
    if cfg["k"] is not None and cfg["k"] not in cfg["ks"]:
        raise ValueError(f"k inválido em {caminho}: {cfg['k']!r} fora da varredura {cfg['ks']}")
    if (cfg["metodo"] is None) != (cfg["k"] is None):
        raise ValueError(f"metodo e k devem ser congelados juntos em {caminho}")
    return ConfigBlocagem(
        seed=int(cfg["seed"]),
        n_amostra=int(cfg["n_amostra"]),
        ks=[int(k) for k in cfg["ks"]],
        metodos=list(cfg["metodos"]),
        metodo=cfg["metodo"],
        k=None if cfg["k"] is None else int(cfg["k"]),
    )


# ── Deduplicação por texto normalizado (critério C2 de docs/limpeza_dados.md) ──


def deduplicar_por_texto_normalizado(df_produtos: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por texto normalizado, para o anotador não rotular a mesma descrição duas vezes.

    A escolha da linha representante e o `id_produto` (hash do texto normalizado) não dependem
    da ordem de entrada. Só passam adiante id, texto e metadado de unidade: nada do matcher ALTA.
    """
    base = df_produtos.assign(texto_normalizado=df_produtos["description"].map(normalizar_texto))
    base = base.sort_values(["texto_normalizado", "description"], kind="stable")
    n_registros = base.groupby("texto_normalizado").size()
    dedup = base.drop_duplicates("texto_normalizado", keep="first")
    return pd.DataFrame(
        {
            "id_produto": dedup["texto_normalizado"].map(
                lambda t: hashlib.sha1(t.encode("utf-8")).hexdigest()[:12]
            ),
            "descricao": dedup["description"],
            "texto_normalizado": dedup["texto_normalizado"],
            "n_registros": dedup["texto_normalizado"].map(n_registros),
            "und_val": dedup["und_val"] if "und_val" in dedup else np.nan,
            "und_med": dedup["und_med"] if "und_med" in dedup else np.nan,
        }
    ).reset_index(drop=True)


# ── Blocagem lexical: TF-IDF e BM25 sobre o dicionário (ADR-0006) ────────────


def _tokens(texto: str) -> list[str]:
    return tokenizar(texto, normalizar=True)


def _top_k(
    scores: np.ndarray, ids: np.ndarray, nomes: np.ndarray, k: int, metodo: str
) -> dict[str, np.ndarray]:
    """Top-k por linha, desempate pelo índice do dicionário, descartando score zero."""
    ordem = np.argsort(-scores, axis=1, kind="stable")[:, :k]
    melhores = np.take_along_axis(scores, ordem, axis=1)
    linhas, colunas = np.nonzero(melhores > 0)
    return {
        "id_produto": ids[linhas],
        "metodo": np.full(len(linhas), metodo, dtype=object),
        "rank": colunas + 1,
        "desc_alim": nomes[ordem[linhas, colunas]],
        "score": melhores[linhas, colunas],
    }


def _montar_ranking(
    lotes: list[dict[str, np.ndarray]], colunas: list[str] = COLUNAS_RANKING
) -> pd.DataFrame:
    if not lotes:
        return pd.DataFrame(columns=colunas)
    return pd.DataFrame({col: np.concatenate([lote[col] for lote in lotes]) for col in colunas})


def ranquear_tfidf(produtos: pd.DataFrame, dicionario: pd.DataFrame, k: int) -> pd.DataFrame:
    """Top-k do dicionário por cosseno TF-IDF; o vocabulário e o IDF vêm só do dicionário."""
    nomes = dicionario["desc_alim"].to_numpy()
    ids = produtos["id_produto"].to_numpy()
    vetorizador = TfidfVectorizer(analyzer=_tokens)
    matriz_dicionario = vetorizador.fit_transform(nomes)
    matriz_produtos = vetorizador.transform(produtos["descricao"])
    lotes = []
    for ini in range(0, len(ids), _LOTE_PRODUTOS):
        fim = ini + _LOTE_PRODUTOS
        scores = (matriz_produtos[ini:fim] @ matriz_dicionario.T).toarray()
        lotes.append(_top_k(scores, ids[ini:fim], nomes, k, "tfidf"))
    return _montar_ranking(lotes)


def ranquear_bm25(produtos: pd.DataFrame, dicionario: pd.DataFrame, k: int) -> pd.DataFrame:
    """Top-k do dicionário por BM25 (Okapi), com o produto como consulta."""
    nomes = dicionario["desc_alim"].to_numpy()
    ids = produtos["id_produto"].to_numpy()
    bm25 = BM25Okapi([_tokens(nome) for nome in nomes])
    consultas = [_tokens(texto) for texto in produtos["descricao"]]
    lotes = []
    for ini in range(0, len(ids), _LOTE_PRODUTOS):
        fim = ini + _LOTE_PRODUTOS
        scores = np.vstack([bm25.get_scores(c) for c in consultas[ini:fim]])
        lotes.append(_top_k(scores, ids[ini:fim], nomes, k, "bm25"))
    return _montar_ranking(lotes)


_RANQUEADORES = {"tfidf": ranquear_tfidf, "bm25": ranquear_bm25}


# ── Amostra cega (docs/protocolo_anotacao.md §2.1) ───────────────────────────


def sortear_amostra_cega(produtos_dedup: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """Sorteia n produtos distintos com seed fixa, independente da ordem de entrada."""
    if n > len(produtos_dedup):
        raise ValueError(f"amostra de {n} maior que os {len(produtos_dedup)} produtos distintos")
    ordenado = produtos_dedup.sort_values("id_produto").reset_index(drop=True)
    return ordenado.sample(n=n, random_state=seed).reset_index(drop=True)


def montar_planilha_amostra_cega(amostra: pd.DataFrame) -> pd.DataFrame:
    """Planilha para anotar: só o produto, sem candidatos, scores nem colunas do matcher ALTA."""
    planilha = pd.DataFrame(
        {
            "id_produto": amostra["id_produto"],
            "descricao": amostra["descricao"],
            "tipo_par": "produto_canonico",
            "origem": "amostra_cega",
            "und_val": amostra["und_val"],
            "und_med": amostra["und_med"],
            "entrada_indicada": "",
            "observacao": "",
            "timestamp_anotacao": "",
        }
    )[COLUNAS_PLANILHA]
    assert not set(COLUNAS_MATCHER_ALTA) & set(planilha.columns), "ADR-0011 violado"
    return planilha


def _entrada(valor: object) -> str:
    return "" if valor is None or pd.isna(valor) else str(valor).strip()


def validar_anotacao_amostra_cega(planilha: pd.DataFrame, dicionario: pd.DataFrame) -> None:
    """Valida só a forma da anotação: entrada do dicionário, `sem_entrada` ou `incerto`."""
    validas = set(dicionario["desc_alim"]) | {SEM_ENTRADA, INCERTO}
    vazias = [
        i
        for i, e in zip(planilha["id_produto"], planilha["entrada_indicada"], strict=True)
        if _entrada(e) == ""
    ]
    inexistentes = [
        i
        for i, e in zip(planilha["id_produto"], planilha["entrada_indicada"], strict=True)
        if _entrada(e) != "" and _entrada(e) not in validas
    ]
    if vazias or inexistentes:
        raise ValueError(
            f"Anotação inválida. Células vazias: {vazias}. "
            f"Entradas fora do dicionário (copie o desc_alim exato): {inexistentes}."
        )


def calcular_recall_por_k(
    rankings: pd.DataFrame,
    anotacao: pd.DataFrame,
    ks: list[int],
    metodos: list[str] | None = None,
) -> pd.DataFrame:
    """Recall da blocagem isolada por método e k, sobre os produtos que têm entrada.

    `sem_entrada` e `incerto` ficam fora do denominador e são contados à parte.
    """
    entradas = anotacao.assign(entrada=anotacao["entrada_indicada"].map(_entrada))
    n_sem = int((entradas["entrada"] == SEM_ENTRADA).sum())
    n_incerto = int((entradas["entrada"] == INCERTO).sum())
    com_entrada = entradas[~entradas["entrada"].isin([SEM_ENTRADA, INCERTO])]
    linhas = []
    for metodo in metodos or list(dict.fromkeys(rankings["metodo"])):
        do_metodo = rankings[rankings["metodo"] == metodo]
        achados = com_entrada.merge(
            do_metodo, left_on=["id_produto", "entrada"], right_on=["id_produto", "desc_alim"]
        )
        for k in ks:
            acertos = int(achados.loc[achados["rank"] <= k, "id_produto"].nunique())
            linhas.append(
                {
                    "metodo": metodo,
                    "k": k,
                    "recall": acertos / len(com_entrada) if len(com_entrada) else float("nan"),
                    "n_com_entrada": len(com_entrada),
                    "n_acertos": acertos,
                    "n_sem_entrada": n_sem,
                    "n_incerto": n_incerto,
                }
            )
    return pd.DataFrame(linhas)


_NOMES_METODO = {"tfidf": "TF-IDF", "bm25": "BM25"}


def montar_tabela_recall_tex(recall: pd.DataFrame) -> str:
    """Tabela LaTeX do recall da blocagem isolada: k nas linhas, um método por coluna.

    Os números vêm do `recall_blocagem.csv` (nunca digitados no `main.tex`); a nota de rodapé
    traz o denominador e os produtos que ficam fora do cálculo.
    """
    metodos = list(dict.fromkeys(recall["metodo"]))
    por_k = recall.pivot(index="k", columns="metodo", values="recall").sort_index()
    cabecalho = " & ".join(["\\textbf{k}"] + [f"\\textbf{{{_NOMES_METODO[m]}}}" for m in metodos])
    linhas = "\n".join(
        " & ".join(
            [str(k)] + [f"{por_k.at[k, m] * 100:.1f}".replace(".", ",") + "\\%" for m in metodos]
        )
        + " \\\\"
        for k in por_k.index
    )
    ref = recall.iloc[0]
    nota = (
        f"Elaborado pelo autor (amostra cega: {ref['n_com_entrada']} produtos com entrada "
        f"correspondente; {ref['n_sem_entrada']} sem entrada e {ref['n_incerto']} incertos, "
        "fora do cálculo)"
    )
    return (
        "% Gerado automaticamente por scripts/03_construcao_dataset.py — não editar à mão.\n"
        "\\begin{table}[htbp]\n"
        "\\centering\n"
        "\\caption{Recall da blocagem isolada, por método e número de candidatos (k), "
        "na amostra cega}\n"
        "\\label{tab:recall-blocagem}\n"
        "\\small\n"
        f"\\begin{{tabular}}{{l{'c' * len(metodos)}}}\n"
        "\\toprule\n"
        f"{cabecalho} \\\\\n"
        "\\midrule\n"
        f"{linhas}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\vspace{2mm}\n"
        f"\\fonte{{{nota}}}\n"
        "\\end{table}\n"
    )


# ── Orquestração da blocagem 1.2a ────────────────────────────────────────────


def executar_blocagem(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    diretorio_metricas: Path = RESULTADOS_METRICAS,
    caminho_config: Path = CONFIG_BLOCAGEM,
    *,
    diretorio_latex_tabelas: Path,
) -> None:
    """Três etapas idempotentes: planilha cega, recall (se anotada) e candidatos (se congelado)."""
    cfg = carregar_config(caminho_config)
    produtos = pd.read_parquet(diretorio_processados / "produtos_limpos.parquet")
    dicionario = pd.read_parquet(diretorio_processados / "dicionario_limpo.parquet")
    dedup = deduplicar_por_texto_normalizado(produtos)
    logger.info(
        "Produtos: %d registros → %d textos normalizados distintos.", len(produtos), len(dedup)
    )

    caminho_planilha = diretorio_processados / "anotacoes_amostra_cega.csv"
    if caminho_planilha.exists():
        logger.info("Planilha da amostra cega já existe; não sobrescrita: %s", caminho_planilha)
    else:
        amostra = sortear_amostra_cega(dedup, cfg["n_amostra"], cfg["seed"])
        montar_planilha_amostra_cega(amostra).to_csv(caminho_planilha, sep=";", index=False)
        logger.info(
            "Planilha da amostra cega (%d produtos) gravada: %s", len(amostra), caminho_planilha
        )

    planilha = pd.read_csv(caminho_planilha, sep=";", dtype=str, keep_default_na=False)
    if (planilha["entrada_indicada"].map(_entrada) == "").any():
        logger.info("Recall aguardando anotação da amostra cega (%s).", caminho_planilha)
    else:
        validar_anotacao_amostra_cega(planilha, dicionario)
        ausentes = set(planilha["id_produto"]) - set(dedup["id_produto"])
        assert not ausentes, (
            f"Planilha com produtos que não estão na base limpa: {sorted(ausentes)}"
        )
        amostra = dedup[dedup["id_produto"].isin(planilha["id_produto"])]
        rankings = pd.concat(
            [_RANQUEADORES[m](amostra, dicionario, max(cfg["ks"])) for m in cfg["metodos"]],
            ignore_index=True,
        )
        recall = calcular_recall_por_k(rankings, planilha, cfg["ks"], cfg["metodos"])
        diretorio_metricas.mkdir(parents=True, exist_ok=True)
        recall.to_csv(diretorio_metricas / "recall_blocagem.csv", index=False)
        diretorio_latex_tabelas.mkdir(parents=True, exist_ok=True)
        (diretorio_latex_tabelas / "tab_recall_blocagem.tex").write_text(
            montar_tabela_recall_tex(recall), encoding="utf-8"
        )
        logger.info("Recall da blocagem por método e k gravado em %s.", diretorio_metricas)

    if cfg["metodo"] is None or cfg["k"] is None:
        logger.info(
            "Método e k ainda não congelados em %s; candidatos não gerados.", caminho_config
        )
        return
    candidatos = _RANQUEADORES[cfg["metodo"]](dedup, dicionario, cfg["k"])
    assert not set(COLUNAS_MATCHER_ALTA) & set(candidatos.columns), "ADR-0011 violado"
    candidatos.to_parquet(diretorio_processados / "candidatos_blocagem.parquet", index=False)
    logger.info("Candidatos (%s, k=%d) gravados.", cfg["metodo"], cfg["k"])


# ── Blocagem 1.2b: produto × produto, entre lojas (spec 001, RF1 "1b") ───────


class ConfigPxp(TypedDict):
    seed: int
    lote_ancoras: int
    alvo_ancoras_com_positivo: int
    max_ancoras: int
    profundidade_pool: int
    ngramas: list[int]
    ks: list[int]
    metodo: str | None
    k: int | None
    tau_particao: float
    n_teste: int
    fracao_digito_divergente: float
    faixas: list[float] | None
    n_por_estrato: dict[str, int] | None
    score_minimo_digito_divergente: float | None
    b2_cosseno_minimo: float | None
    n_reteste: int | None
    seed_reteste: int | None


def carregar_config_pxp(caminho: Path) -> ConfigPxp:
    """Lê o YAML da 1b e valida método e k congelados, parada do pool e fração de dígito.

    O método oficial é só TF-IDF ou BM25: o de n-gramas serve apenas para formar o pool.
    """
    cfg: dict[str, Any] = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    if cfg["metodo"] is not None and cfg["metodo"] not in METODOS:
        raise ValueError(f"metodo inválido em {caminho}: {cfg['metodo']!r} (esperado {METODOS})")
    if cfg["k"] is not None and cfg["k"] not in cfg["ks"]:
        raise ValueError(f"k inválido em {caminho}: {cfg['k']!r} fora da varredura {cfg['ks']}")
    if (cfg["metodo"] is None) != (cfg["k"] is None):
        raise ValueError(f"metodo e k devem ser congelados juntos em {caminho}")
    if cfg["alvo_ancoras_com_positivo"] > cfg["max_ancoras"]:
        raise ValueError(
            f"alvo_ancoras_com_positivo ({cfg['alvo_ancoras_com_positivo']}) acima de "
            f"max_ancoras ({cfg['max_ancoras']}) em {caminho}"
        )
    if not 0 <= cfg["fracao_digito_divergente"] <= 1:
        raise ValueError(
            f"fracao_digito_divergente fora de [0, 1] em {caminho}: "
            f"{cfg['fracao_digito_divergente']!r}"
        )
    faixas = None if cfg.get("faixas") is None else [float(f) for f in cfg["faixas"]]
    n_por_estrato = cfg.get("n_por_estrato")
    if faixas is not None:
        _validar_faixas(faixas)
    if n_por_estrato is not None:
        if faixas is None:
            raise ValueError(f"n_por_estrato exige faixas em {caminho}")
        esperados = {
            ESTRATO_TEXTO_IDENTICO,
            ESTRATO_DIGITO_DIVERGENTE,
            *_rotulos_das_faixas(faixas),
        }
        if set(n_por_estrato) != esperados:
            raise ValueError(
                f"estratos de n_por_estrato diferentes dos esperados em {caminho}: "
                f"faltam {sorted(esperados - set(n_por_estrato))}, "
                f"sobram {sorted(set(n_por_estrato) - esperados)}"
            )
        if any(int(n) < 0 for n in n_por_estrato.values()):
            raise ValueError(f"n_por_estrato com contagem negativa em {caminho}: {n_por_estrato}")
        if sum(n_por_estrato.values()) != cfg["n_teste"]:
            raise ValueError(
                f"soma de n_por_estrato ({sum(n_por_estrato.values())}) diferente de n_teste "
                f"({cfg['n_teste']}) em {caminho}"
            )
        fracao = n_por_estrato[ESTRATO_DIGITO_DIVERGENTE] / cfg["n_teste"]
        if abs(fracao - cfg["fracao_digito_divergente"]) > 1e-9:
            raise ValueError(
                f"n_por_estrato['digito_divergente'] / n_teste ({fracao:.3f}) diferente de "
                f"fracao_digito_divergente ({cfg['fracao_digito_divergente']}) em {caminho}"
            )
    minimo = cfg.get("score_minimo_digito_divergente")
    if minimo is not None and not 0 <= minimo <= 1:
        raise ValueError(f"score_minimo_digito_divergente fora de [0, 1] em {caminho}: {minimo!r}")
    b2 = cfg.get("b2_cosseno_minimo")
    if b2 is not None and not 0 < b2 <= 1:
        raise ValueError(f"b2_cosseno_minimo fora de (0, 1] em {caminho}: {b2!r}")
    if "proporcao_treino" in cfg:
        raise ValueError(
            f"proporcao_treino obsoleta em {caminho}: a partição é por componente conexo "
            "(validação = pool fora dos componentes do teste, treino = o restante); remova a chave"
        )
    n_reteste = cfg.get("n_reteste")
    seed_reteste = cfg.get("seed_reteste")
    if (n_reteste is None) != (seed_reteste is None):
        raise ValueError(f"n_reteste e seed_reteste devem ser definidos juntos em {caminho}")
    if n_reteste is not None:
        minimo_reteste = int(np.ceil(FRACAO_MINIMA_RETESTE * cfg["n_teste"]))
        if not minimo_reteste <= n_reteste <= cfg["n_teste"]:
            raise ValueError(
                f"n_reteste ({n_reteste}) fora de [{minimo_reteste}, {cfg['n_teste']}] "
                f"(≥ 50% e ≤ n_teste, ADR-0005) em {caminho}"
            )
    return ConfigPxp(
        seed=int(cfg["seed"]),
        lote_ancoras=int(cfg["lote_ancoras"]),
        alvo_ancoras_com_positivo=int(cfg["alvo_ancoras_com_positivo"]),
        max_ancoras=int(cfg["max_ancoras"]),
        profundidade_pool=int(cfg["profundidade_pool"]),
        ngramas=[int(n) for n in cfg["ngramas"]],
        ks=[int(k) for k in cfg["ks"]],
        metodo=cfg["metodo"],
        k=None if cfg["k"] is None else int(cfg["k"]),
        tau_particao=float(cfg["tau_particao"]),
        n_teste=int(cfg["n_teste"]),
        fracao_digito_divergente=float(cfg["fracao_digito_divergente"]),
        faixas=faixas,
        n_por_estrato=None
        if n_por_estrato is None
        else {k: int(v) for k, v in n_por_estrato.items()},
        score_minimo_digito_divergente=None if minimo is None else float(minimo),
        b2_cosseno_minimo=None if b2 is None else float(b2),
        n_reteste=None if n_reteste is None else int(n_reteste),
        seed_reteste=None if seed_reteste is None else int(seed_reteste),
    )


def _hash_curto(texto: str) -> str:
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:12]


def deduplicar_por_texto_e_loja(df_produtos: pd.DataFrame) -> pd.DataFrame:
    """Universo da 1b: uma linha por (texto normalizado, loja), com a loja vinda de `source`.

    `id_texto` é o mesmo hash do `id_produto` da 1a, para cruzar as duas fatias; `id_produto`
    inclui a loja, então o mesmo texto em duas lojas são dois produtos. A linha representante e
    os ids não dependem da ordem de entrada. Nada do matcher ALTA passa adiante.
    """
    base = df_produtos.assign(
        texto_normalizado=df_produtos["description"].map(normalizar_texto),
        loja=df_produtos["source"],
    ).sort_values(["texto_normalizado", "loja", "description"], kind="stable")
    dedup = base.drop_duplicates(["texto_normalizado", "loja"], keep="first")
    return pd.DataFrame(
        {
            "id_produto": [
                _hash_curto(f"{t}|{loja}")
                for t, loja in zip(dedup["texto_normalizado"], dedup["loja"], strict=True)
            ],
            "id_texto": dedup["texto_normalizado"].map(_hash_curto),
            "descricao": dedup["description"],
            "texto_normalizado": dedup["texto_normalizado"],
            "loja": dedup["loja"],
            "und_val": dedup["und_val"] if "und_val" in dedup else np.nan,
            "und_med": dedup["und_med"] if "und_med" in dedup else np.nan,
        }
    ).reset_index(drop=True)


_NUMERO_COM_UNIDADE = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(kg|gr|g|ml|lt|l)(?![a-z])", re.IGNORECASE
)
# unidade → (dimensão, fator até a unidade-base: g para massa, ml para volume)
_UNIDADES: dict[str, tuple[str, Decimal]] = {
    "g": ("massa", Decimal(1)),
    "gr": ("massa", Decimal(1)),
    "kg": ("massa", Decimal(1000)),
    "ml": ("volume", Decimal(1)),
    "l": ("volume", Decimal(1000)),
    "lt": ("volume", Decimal(1000)),
}


def tokens_numericos(texto: str) -> frozenset[tuple[Decimal, str]]:
    """Tamanhos do texto como (valor na unidade-base, dimensão): 900ML e 0,9L dão o mesmo token.

    Só contam números colados a g, gr, kg, ml, l ou lt; a conta é em `Decimal`, sem erro de
    ponto flutuante. Serve para selecionar pares (negativos difíceis); nunca para rotular.
    """
    tokens = set()
    for numero, unidade in _NUMERO_COM_UNIDADE.findall(texto):
        dimensao, fator = _UNIDADES[unidade.lower()]
        tokens.add(((Decimal(numero.replace(",", ".")) * fator).normalize(), dimensao))
    return frozenset(tokens)


def divergencia_numerica(texto_a: str, texto_b: str) -> bool:
    """Os dois lados têm tamanho em g/gr/kg/ml/l/lt e os conjuntos diferem após normalizar."""
    tokens_a, tokens_b = tokens_numericos(texto_a), tokens_numericos(texto_b)
    return bool(tokens_a and tokens_b and tokens_a != tokens_b)


COLUNAS_RANKING_PXP = ["id_produto", "id_candidato", "metodo", "rank", "score"]
_LOTE_PXP = 500  # consulta × universo inteiro em float64: 500 linhas ≈ 115 MB com 29 mil produtos


def _top_k_por_lotes(
    pontuar: Callable[[np.ndarray], np.ndarray],
    posicoes: np.ndarray,
    ids: np.ndarray,
    lojas: np.ndarray,
    k: int,
    metodo: str,
) -> pd.DataFrame:
    """Top-k das consultas em `posicoes` contra o universo inteiro, em lotes.

    `pontuar(posicoes_do_lote)` devolve os scores contra todas as colunas do universo. Os
    candidatos com o mesmo rótulo em `lojas` (e o próprio produto) são zerados e o score é
    arredondado a 12 casas antes do top-k (com um rótulo distinto por produto, só o próprio
    produto é excluído; ver `ranquear_vizinhos`), para o
    desempate por `id_candidato` (universo ordenado por id) não depender de ruído de ponto
    flutuante.
    """
    lotes = []
    for ini in range(0, len(posicoes), _LOTE_PXP):
        pos = posicoes[ini : ini + _LOTE_PXP]
        scores = np.round(pontuar(pos), 12)
        scores[lojas[pos, None] == lojas[None, :]] = 0.0
        lote = _top_k(scores, ids[pos], ids, k, metodo)
        lote["id_candidato"] = lote.pop("desc_alim")
        lotes.append(lote)
    return _montar_ranking(lotes, COLUNAS_RANKING_PXP)


def _posicoes_dos_ancoras(ids: np.ndarray, ids_ancoras: list[str]) -> np.ndarray:
    """Posições dos âncoras no universo ordenado; levanta `ValueError` se algum não está nele."""
    fora_do_universo = sorted(set(ids_ancoras) - set(ids))
    if fora_do_universo:
        raise ValueError(f"ids de âncora fora do universo: {fora_do_universo}")
    return np.flatnonzero(np.isin(ids, ids_ancoras))


def ranquear_entre_lojas(
    universo: pd.DataFrame, metodo: str, k: int, ids_ancoras: list[str] | None = None
) -> pd.DataFrame:
    """Top-k de cada produto entre os produtos de **outras** lojas, por TF-IDF ou BM25.

    O corpus é o próprio universo (vocabulário e IDF vêm dele inteiro, sem rótulo). A mesma loja
    e o próprio produto são zerados antes do top-k, então nunca viram candidato (CA-1b-01).
    O universo é ordenado por `id_produto` e o score é arredondado a 12 casas, para o desempate
    por `id_candidato` crescente não depender da ordem das linhas nem de ruído de ponto flutuante.
    Com `ids_ancoras`, só esses produtos são consultas (o corpus continua sendo o universo todo);
    sem ele, todos são. Levanta `ValueError` se algum âncora não está no universo.
    """
    if metodo not in METODOS:
        raise ValueError(f"metodo inválido: {metodo!r} (esperado {METODOS})")
    universo = universo.sort_values("id_produto").reset_index(drop=True)
    ids = universo["id_produto"].to_numpy()
    lojas = pd.factorize(universo["loja"])[0]
    textos = universo["descricao"]

    if metodo == "tfidf":
        matriz = TfidfVectorizer(analyzer=_tokens).fit_transform(textos)

        def pontuar(pos: np.ndarray) -> np.ndarray:
            return (matriz[pos] @ matriz.T).toarray()

    else:
        bm25 = BM25Okapi([_tokens(t) for t in textos])
        consultas = [_tokens(t) for t in textos]

        def pontuar(pos: np.ndarray) -> np.ndarray:
            return np.vstack([bm25.get_scores(consultas[i]) for i in pos])

    posicoes = (
        np.arange(len(ids)) if ids_ancoras is None else _posicoes_dos_ancoras(ids, ids_ancoras)
    )
    return _top_k_por_lotes(pontuar, posicoes, ids, lojas, k, metodo)


def ranquear_vizinhos(universo: pd.DataFrame, k: int) -> pd.DataFrame:
    """Top-k TF-IDF de cada produto entre **todos** os outros, inclusive os da mesma loja.

    Mesmo vocabulário e mesmo desempate de `ranquear_entre_lojas`; só o próprio produto é
    excluído. Serve para minerar negativos de tamanho diferente dentro da mesma loja (o mesmo item
    em 1 L e em 500 ml), que também são SKUs distintos com certeza.
    """
    universo = universo.sort_values("id_produto").reset_index(drop=True)
    ids = universo["id_produto"].to_numpy()
    matriz = TfidfVectorizer(analyzer=_tokens).fit_transform(universo["descricao"])

    def pontuar(pos: np.ndarray) -> np.ndarray:
        return (matriz[pos] @ matriz.T).toarray()

    posicoes = np.arange(len(ids))
    return _top_k_por_lotes(pontuar, posicoes, ids, posicoes, k, "tfidf")


def ranquear_ngramas(
    universo: pd.DataFrame, ids_ancoras: list[str], k: int, ngramas: tuple[int, int] = (3, 5)
) -> pd.DataFrame:
    """Top-k por TF-IDF de n-gramas de caracteres (`char_wb`), só para os âncoras pedidos.

    Serve apenas para formar o pool de avaliação do recall (ADR-0006, spec 001 RF1 "1b"): fica
    fora de `METODOS` e de `_RANQUEADORES`, então nunca é a blocagem oficial. Pega o que as
    palavras perdem (`CAFE` × `NESCAFE`). O corpus é o universo inteiro; a mesma loja e o próprio
    âncora nunca viram candidato. Levanta `ValueError` se algum âncora não está no universo.
    """
    universo = universo.sort_values("id_produto").reset_index(drop=True)
    ids = universo["id_produto"].to_numpy()
    posicoes = _posicoes_dos_ancoras(ids, ids_ancoras)
    lojas = pd.factorize(universo["loja"])[0]
    matriz = TfidfVectorizer(analyzer="char_wb", ngram_range=ngramas).fit_transform(
        universo["texto_normalizado"]
    )

    def pontuar(pos: np.ndarray) -> np.ndarray:
        return (matriz[pos] @ matriz.T).toarray()

    return _top_k_por_lotes(pontuar, posicoes, ids, lojas, k, "ngramas")


def sortear_ancoras(universo: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Permutação única e semeada de todo o universo; os lotes do pool são fatias dela em ordem.

    Sem filtro de similaridade: filtrar âncoras pelo que a blocagem acha fácil inflaria o recall
    (design-1b.md §5). Parte do universo ordenado por `id_produto`, então a ordem das linhas de
    entrada não muda o resultado.
    """
    ordenado = universo.sort_values("id_produto").reset_index(drop=True)
    return ordenado.sample(frac=1.0, random_state=seed).reset_index(drop=True)


class DecisaoLote(NamedTuple):
    """`motivo`: "alvo", "teto" ou "continuar"; `tamanho_proximo_lote` é 0 quando para."""

    motivo: str
    tamanho_proximo_lote: int


def decidir_proximo_lote(
    n_sorteados: int,
    n_com_positivo: int,
    *,
    alvo_ancoras_com_positivo: int,
    max_ancoras: int,
    lote_ancoras: int,
) -> DecisaoLote:
    """Regra de parada do pool (Q2, confirmada em 2026-10-31), só com contagens de âncoras.

    Para com `alvo_ancoras_com_positivo` âncoras com pelo menos um `match` ou ao chegar a
    `max_ancoras` sorteados; o alvo vence se os dois valem. Nunca recebe o recall: a decisão
    não pode olhar o resultado. O último lote é truncado para não passar do teto.
    """
    if min(alvo_ancoras_com_positivo, max_ancoras, lote_ancoras) <= 0:
        raise ValueError(
            "parâmetro não positivo: "
            f"alvo={alvo_ancoras_com_positivo}, max_ancoras={max_ancoras}, "
            f"lote_ancoras={lote_ancoras}"
        )
    if not 0 <= n_com_positivo <= n_sorteados:
        raise ValueError(
            f"contagem impossível: {n_com_positivo} âncoras com positivo de {n_sorteados} sorteadas"
        )
    if n_com_positivo >= alvo_ancoras_com_positivo:
        return DecisaoLote("alvo", 0)
    if n_sorteados >= max_ancoras:
        return DecisaoLote("teto", 0)
    return DecisaoLote("continuar", min(lote_ancoras, max_ancoras - n_sorteados))


COLUNAS_POOL = ["id_produto", "id_candidato"]
COLUNAS_PLANILHA_POOL = [
    "id_par",
    "id_ancora",
    "descricao_ancora",
    "und_val_ancora",
    "und_med_ancora",
    "id_candidato",
    "descricao_candidato",
    "und_val_candidato",
    "und_med_candidato",
    "tipo_par",
    "origem",
    "rotulo",
    "ancora_concluida",
    "observacao",
    "timestamp_anotacao",
]
_PROIBIDAS_NA_PLANILHA_POOL = (*COLUNAS_MATCHER_ALTA, "metodo", "rank", "score")


def montar_pool(rankings: list[pd.DataFrame], profundidade: int) -> pd.DataFrame:
    """União dos pares (âncora, candidato) de todos os métodos, até `profundidade`.

    Descarta método, rank e score: o autor não pode saber de onde veio cada candidato.
    """
    if profundidade < 1:
        raise ValueError(f"profundidade do pool deve ser >= 1, recebido {profundidade}")
    partes = [r.loc[r["rank"] <= profundidade, COLUNAS_POOL] for r in rankings]
    if not partes:
        return pd.DataFrame(columns=COLUNAS_POOL)
    return pd.concat(partes).drop_duplicates().sort_values(COLUNAS_POOL).reset_index(drop=True)


def montar_planilha_pool(
    ancoras: pd.DataFrame, universo: pd.DataFrame, pool: pd.DataFrame
) -> pd.DataFrame:
    """Planilha do lote: uma linha por (âncora, candidato), sem método, rank nem score.

    Os âncoras seguem a ordem do sorteio e os candidatos de cada um, a ordem alfabética do texto
    normalizado (desempate por id), para a posição não sugerir similaridade. O autor preenche só
    `rotulo` (`match` ou `incerto`; vazio é não-match), `ancora_concluida`, `observacao` e
    `timestamp_anotacao`. Âncora sem nenhum candidato no pool não gera linha: não há o que
    anotar, e ela conta como âncora sem positivo.
    """
    ordem_ancoras = pd.DataFrame(
        {"id_ancora": ancoras["id_produto"].to_numpy(), "ordem_ancora": range(len(ancoras))}
    )
    colunas = ["id_produto", "descricao", "und_val", "und_med"]
    lado_ancora = universo[colunas].rename(
        columns={
            "id_produto": "id_ancora",
            "descricao": "descricao_ancora",
            "und_val": "und_val_ancora",
            "und_med": "und_med_ancora",
        }
    )
    lado_candidato = universo[[*colunas, "texto_normalizado"]].rename(
        columns={
            "id_produto": "id_candidato",
            "descricao": "descricao_candidato",
            "und_val": "und_val_candidato",
            "und_med": "und_med_candidato",
            "texto_normalizado": "texto_candidato",
        }
    )
    pares = (
        pool.rename(columns={"id_produto": "id_ancora"})
        .merge(ordem_ancoras, on="id_ancora")
        .merge(lado_ancora, on="id_ancora", how="left")
        .merge(lado_candidato, on="id_candidato", how="left")
    )
    fora = pares[pares["descricao_ancora"].isna() | pares["descricao_candidato"].isna()]
    if len(fora):
        ids = sorted(set(fora["id_ancora"]) | set(fora["id_candidato"]))
        raise ValueError(f"ids do pool fora do universo: {ids}")
    pares = pares.sort_values(["ordem_ancora", "texto_candidato", "id_candidato"])
    planilha = pares.assign(
        id_par=[
            _hash_curto(f"{a}|{c}")
            for a, c in zip(pares["id_ancora"], pares["id_candidato"], strict=True)
        ],
        tipo_par="produto_produto",
        origem="amostra_cega",
        rotulo="",
        ancora_concluida="",
        observacao="",
        timestamp_anotacao="",
    )[COLUNAS_PLANILHA_POOL].reset_index(drop=True)
    assert not set(_PROIBIDAS_NA_PLANILHA_POOL) & set(planilha.columns), "ADR-0011 violado"
    return planilha


def gravar_planilha_pool(planilha: pd.DataFrame, diretorio: Path, numero_lote: int) -> Path:
    """Grava `lote_NN.csv` (separador `;`). Nunca sobrescreve: é onde o autor anota."""
    if numero_lote < 1:
        raise ValueError(f"numero do lote deve ser >= 1, recebido {numero_lote}")
    caminho = diretorio / f"lote_{numero_lote:02d}.csv"
    if caminho.exists():
        raise FileExistsError(f"Planilha do lote já existe; não sobrescrita: {caminho}")
    diretorio.mkdir(parents=True, exist_ok=True)
    planilha.to_csv(caminho, sep=";", index=False)
    return caminho


ROTULOS_POOL = ("match", "incerto")  # vazio, em âncora concluída, é não-match
ANCORA_CONCLUIDA = "sim"


def validar_anotacao_pool(planilha: pd.DataFrame, pool: pd.DataFrame) -> None:
    """Valida só a forma da planilha do pool anotada; nunca o mérito do rótulo.

    `pool` são os pares esperados do lote (`id_produto`, `id_candidato`). Falha cedo, com os ids,
    se faltar coluna, houver coluna proibida, `id_par` repetido, rótulo ou flag fora do domínio,
    flag misturada dentro de uma âncora, par fora do pool ou linha apagada (que viraria não-match
    sem decisão do autor). Âncora sem `ancora_concluida` não é erro: só fica fora das contas.
    """
    faltando = [c for c in COLUNAS_PLANILHA_POOL if c not in planilha.columns]
    if faltando:
        raise ValueError(f"colunas ausentes na planilha do pool: {faltando}")
    proibidas = [c for c in _PROIBIDAS_NA_PLANILHA_POOL if c in planilha.columns]
    if proibidas:
        raise ValueError(f"colunas proibidas na planilha do pool: {proibidas}")
    if planilha.empty:
        raise ValueError("planilha do pool vazia")
    repetidos = sorted(set(planilha.loc[planilha["id_par"].duplicated(), "id_par"]))
    if repetidos:
        raise ValueError(f"id_par duplicado na planilha do pool: {repetidos}")

    rotulo = planilha["rotulo"].map(_entrada)
    invalidos = sorted(planilha.loc[~rotulo.isin(["", *ROTULOS_POOL]), "id_par"])
    if invalidos:
        raise ValueError(f"rotulo fora do domínio (vazio, {ROTULOS_POOL}) em: {invalidos}")
    flag = planilha["ancora_concluida"].map(_entrada)
    invalidos = sorted(planilha.loc[~flag.isin(["", ANCORA_CONCLUIDA]), "id_par"])
    if invalidos:
        raise ValueError(f"ancora_concluida fora do domínio (vazio ou 'sim') em: {invalidos}")
    concluida = (flag == ANCORA_CONCLUIDA).groupby(planilha["id_ancora"]).nunique()
    mistas = sorted(concluida[concluida > 1].index)
    if mistas:
        raise ValueError(
            f"ancora_concluida misto dentro da âncora (todas as linhas ou nenhuma): {mistas}"
        )

    na_planilha = set(zip(planilha["id_ancora"], planilha["id_candidato"], strict=True))
    esperados = set(zip(pool["id_produto"], pool["id_candidato"], strict=True))
    fora = sorted(f"{a}-{c}" for a, c in na_planilha - esperados)
    if fora:
        raise ValueError(f"pares fora do pool do lote: {fora}")
    apagados = sorted(f"{a}-{c}" for a, c in esperados - na_planilha)
    if apagados:
        raise ValueError(f"faltam pares do pool na planilha (linha apagada?): {apagados}")


COLUNAS_RECALL_PXP = [
    "metodo",
    "k",
    "recall",
    "n_positivos",
    "n_acertos",
    "acerto_ancora",
    "n_ancoras_com_positivo",
    "n_ancoras_acerto",
    "n_ancoras_sorteadas",
    "n_ancoras_concluidas",
    "n_ancoras_sem_positivo",
    "n_ancoras_nao_concluidas",
    "n_pares_incerto",
]


def resumir_ancoras_pool(planilha: pd.DataFrame, ancoras_sorteados: list[str]) -> pd.DataFrame:
    """Uma linha por âncora sorteada: concluída?, nº de candidatos, de `match` e de `incerto`.

    Âncora sem nenhuma linha na planilha não tinha candidato no pool: conta como concluída e sem
    positivo. Âncora da planilha que não está entre as sorteadas é erro.
    """
    fora = sorted(set(planilha["id_ancora"]) - set(ancoras_sorteados))
    if fora:
        raise ValueError(f"âncoras da planilha fora dos sorteados: {fora}")
    rotulo = planilha["rotulo"].map(_entrada)
    por_ancora = (
        pd.DataFrame(
            {
                "id_ancora": planilha["id_ancora"],
                "concluida": planilha["ancora_concluida"].map(_entrada) == ANCORA_CONCLUIDA,
                "match": rotulo == "match",
                "incerto": rotulo == "incerto",
            }
        )
        .groupby("id_ancora")
        .agg(
            concluida=("concluida", "all"),
            n_candidatos=("concluida", "size"),
            n_match=("match", "sum"),
            n_incerto=("incerto", "sum"),
        )
        .reindex(ancoras_sorteados)
    )
    sem_candidato = por_ancora["n_candidatos"].isna()
    por_ancora["concluida"] = por_ancora["concluida"].where(~sem_candidato, True).astype(bool)
    for coluna in ("n_candidatos", "n_match", "n_incerto"):
        por_ancora[coluna] = por_ancora[coluna].fillna(0).astype(int)
    por_ancora.index.name = "id_ancora"
    return por_ancora.reset_index()


def calcular_recall_pxp(
    rankings: pd.DataFrame,
    planilha: pd.DataFrame,
    ancoras_sorteados: list[str],
    ks: list[int],
    metodos: list[str] | None = None,
) -> pd.DataFrame:
    """Recall da blocagem entre lojas no pool, por método e k.

    Denominador: pares `match` das âncoras **concluídas**. `recall` é por par (micro) e
    `acerto_ancora` é a fração de âncoras com positivo que têm ao menos um no top-k. Positivo que
    o método não devolveu (rank > k ou ausente) é perda. Pares `incerto`, âncoras sem positivo e
    âncoras não concluídas ficam fora do denominador e são contados à parte. O recall é um limite
    superior: o mesmo SKU fora do pool nunca foi visto pelo autor.
    """
    resumo = resumir_ancoras_pool(planilha, ancoras_sorteados)
    concluidas = set(resumo.loc[resumo["concluida"], "id_ancora"])
    rotulo = planilha["rotulo"].map(_entrada)
    das_concluidas = planilha["id_ancora"].isin(concluidas)
    positivos = planilha.loc[(rotulo == "match") & das_concluidas, ["id_ancora", "id_candidato"]]
    com_positivo = set(positivos["id_ancora"])
    contagens = {
        "n_positivos": len(positivos),
        "n_ancoras_com_positivo": len(com_positivo),
        "n_ancoras_sorteadas": len(set(ancoras_sorteados)),
        "n_ancoras_concluidas": len(concluidas),
        "n_ancoras_sem_positivo": len(concluidas - com_positivo),
        "n_ancoras_nao_concluidas": len(set(ancoras_sorteados) - concluidas),
        "n_pares_incerto": int(((rotulo == "incerto") & das_concluidas).sum()),
    }
    linhas = []
    for metodo in metodos or list(dict.fromkeys(rankings["metodo"])):
        achados = positivos.merge(
            rankings[rankings["metodo"] == metodo],
            left_on=["id_ancora", "id_candidato"],
            right_on=["id_produto", "id_candidato"],
        )
        for k in ks:
            no_topo = achados[achados["rank"] <= k]
            n_acertos = len(no_topo.drop_duplicates(["id_ancora", "id_candidato"]))
            n_ancoras_acerto = no_topo["id_ancora"].nunique()
            linhas.append(
                {
                    "metodo": metodo,
                    "k": k,
                    "recall": n_acertos / len(positivos) if len(positivos) else float("nan"),
                    "n_acertos": n_acertos,
                    "acerto_ancora": n_ancoras_acerto / len(com_positivo)
                    if com_positivo
                    else float("nan"),
                    "n_ancoras_acerto": n_ancoras_acerto,
                    **contagens,
                }
            )
    return pd.DataFrame(linhas)[COLUNAS_RECALL_PXP]


def _percentual(valor: float) -> str:
    return "--" if pd.isna(valor) else f"{valor * 100:.1f}".replace(".", ",") + "\\%"


def montar_tabela_recall_pxp_tex(recall: pd.DataFrame) -> str:
    """Tabela LaTeX do recall entre lojas: k nas linhas; por método, recall por par e por âncora.

    Os números vêm do `recall_blocagem_pxp.csv`, nunca digitados no `main.tex`. A nota traz os
    denominadores, o que fica fora do cálculo e a limitação de limite superior (viés de pooling).
    """
    metodos = list(dict.fromkeys(recall["metodo"]))
    por_k = {m: recall[recall["metodo"] == m].set_index("k").sort_index() for m in metodos}
    ks = list(por_k[metodos[0]].index)
    cabecalho_metodos = " & ".join(
        f"\\multicolumn{{2}}{{c}}{{\\textbf{{{_NOMES_METODO[m]}}}}}" for m in metodos
    )
    intervalos = "".join(f"\\cmidrule(lr){{{2 + 2 * i}-{3 + 2 * i}}}" for i in range(len(metodos)))
    cabecalho_colunas = " & ".join(["\\textbf{k}"] + ["Pares & Âncoras"] * len(metodos))
    linhas = "\n".join(
        " & ".join(
            [str(k)]
            + [
                _percentual(por_k[m].at[k, col])
                for m in metodos
                for col in ("recall", "acerto_ancora")
            ]
        )
        + " \\\\"
        for k in ks
    )
    ref = recall.iloc[0]
    nota = (
        f"Elaborado pelo autor (pool cego entre lojas: {ref['n_ancoras_com_positivo']} âncoras "
        f"com positivo e {ref['n_positivos']} pares positivos; {ref['n_ancoras_sem_positivo']} "
        f"âncoras sem positivo e {ref['n_pares_incerto']} pares incertos, fora do cálculo). "
        "Recall é um limite superior: o mesmo SKU fora do pool não foi visto pelo autor"
    )
    return (
        "% Gerado automaticamente por scripts/03_construcao_dataset.py — não editar à mão.\n"
        "\\begin{table}[htbp]\n"
        "\\centering\n"
        "\\caption{Recall da blocagem produto $\\times$ produto isolada, por método e número de "
        "candidatos (k): por par positivo e por âncora com positivo}\n"
        "\\label{tab:recall-blocagem-pxp}\n"
        "\\small\n"
        f"\\begin{{tabular}}{{l{'cc' * len(metodos)}}}\n"
        "\\toprule\n"
        f" & {cabecalho_metodos} \\\\\n"
        f"{intervalos}\n"
        f"{cabecalho_colunas} \\\\\n"
        "\\midrule\n"
        f"{linhas}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\vspace{2mm}\n"
        f"\\fonte{{{nota}}}\n"
        "\\end{table}\n"
    )


_LOTE_POOL_RE = re.compile(r"lote_(\d+)\.csv$")


def gravar_ancoras_lote(ids_ancoras: list[str], diretorio: Path, numero_lote: int) -> Path:
    """Registra as âncoras sorteadas do lote, inclusive as sem candidato (que não têm linha).

    Sem esse manifesto não dá para saber quantas âncoras já foram sorteadas, e a regra de parada
    depende disso. É idempotente se o conteúdo for o mesmo e falha se for diferente.
    """
    caminho = diretorio / f"ancoras_lote_{numero_lote:02d}.csv"
    if caminho.exists():
        existentes = list(pd.read_csv(caminho, sep=";", dtype=str)["id_ancora"])
        if existentes != ids_ancoras:
            raise FileExistsError(f"Manifesto do lote já existe com outras âncoras: {caminho}")
        return caminho
    diretorio.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"id_ancora": ids_ancoras}).to_csv(caminho, sep=";", index=False)
    return caminho


def _ler_lotes_pool(diretorio_pool: Path) -> list[tuple[int, pd.DataFrame, list[str]]]:
    """Lotes já gravados, em ordem: (número, planilha como o autor deixou, âncoras sorteadas)."""
    if not diretorio_pool.exists():
        return []
    numeros = sorted(
        int(m.group(1))
        for p in diretorio_pool.glob("lote_*.csv")
        if (m := _LOTE_POOL_RE.search(p.name))
    )
    if numeros != list(range(1, len(numeros) + 1)):
        raise ValueError(f"lotes do pool fora de sequência em {diretorio_pool}: {numeros}")
    lotes = []
    for n in numeros:
        manifesto = diretorio_pool / f"ancoras_lote_{n:02d}.csv"
        if not manifesto.exists():
            raise ValueError(
                f"falta {manifesto.name} do lote {n}: ele registra as âncoras sorteadas, "
                "inclusive as sem candidato"
            )
        ids = list(pd.read_csv(manifesto, sep=";", dtype=str)["id_ancora"])
        planilha = pd.read_csv(
            diretorio_pool / f"lote_{n:02d}.csv", sep=";", dtype=str, keep_default_na=False
        )
        lotes.append((n, planilha, ids))
    return lotes


def _pool_do_lote(universo: pd.DataFrame, ids_ancoras: list[str], cfg: ConfigPxp) -> pd.DataFrame:
    """Pool do lote: top-`profundidade_pool` de TF-IDF, BM25 e n-gramas, só dos âncoras."""
    k = cfg["profundidade_pool"]
    n_min, n_max = cfg["ngramas"]
    rankings = [ranquear_entre_lojas(universo, m, k, ids_ancoras=ids_ancoras) for m in METODOS]
    rankings.append(ranquear_ngramas(universo, ids_ancoras, k, (n_min, n_max)))
    return montar_pool(rankings, k)


def executar_blocagem_pxp(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    diretorio_metricas: Path = RESULTADOS_METRICAS,
    caminho_config: Path = CONFIG_BLOCAGEM_PXP,
    *,
    diretorio_latex_tabelas: Path,
) -> None:
    """Pool cego da 1b em lotes (RF1 "1b", design-1b.md §1 e §5). Cada execução avança um passo.

    O estado vem dos arquivos de `pool_cego/`: sem lote, gera o 1; com lote anotado e completo,
    aplica a regra de parada (só contagens de âncoras) e gera o próximo ou, na parada, calcula o
    recall; com lote incompleto, só avisa. O recall nunca é calculado antes da parada. Valida a
    forma de cada planilha e nunca sobrescreve uma planilha existente.
    """
    cfg = carregar_config_pxp(caminho_config)
    if max(cfg["ks"]) > cfg["profundidade_pool"]:
        raise ValueError(
            f"max(ks)={max(cfg['ks'])} acima de profundidade_pool={cfg['profundidade_pool']} "
            f"em {caminho_config}: positivos além do pool nunca foram vistos"
        )
    produtos = pd.read_parquet(diretorio_processados / "produtos_limpos.parquet")
    universo = deduplicar_por_texto_e_loja(produtos)
    permutacao = sortear_ancoras(universo, cfg["seed"])
    diretorio_pool = diretorio_processados / "pool_cego"

    lotes = _ler_lotes_pool(diretorio_pool)
    sorteados = [i for _, _, ids in lotes for i in ids]
    if sorteados != list(permutacao["id_produto"].iloc[: len(sorteados)]):
        raise ValueError(
            f"âncoras gravadas em {diretorio_pool} não seguem a permutação da seed {cfg['seed']}"
        )
    resumos = []
    for numero, planilha, ids in lotes:
        validar_anotacao_pool(planilha, _pool_do_lote(universo, ids, cfg))
        resumo = resumir_ancoras_pool(planilha, ids)
        if not resumo["concluida"].all():
            logger.info("Aguardando conclusão da anotação do lote %d (%s).", numero, diretorio_pool)
            return
        resumos.append(resumo)

    n_com_positivo = int((pd.concat(resumos)["n_match"] > 0).sum()) if resumos else 0
    decisao = decidir_proximo_lote(
        len(sorteados),
        n_com_positivo,
        alvo_ancoras_com_positivo=cfg["alvo_ancoras_com_positivo"],
        max_ancoras=cfg["max_ancoras"],
        lote_ancoras=cfg["lote_ancoras"],
    )
    if decisao.motivo == "continuar":
        inicio = len(sorteados)
        ancoras = permutacao.iloc[inicio : inicio + decisao.tamanho_proximo_lote]
        if ancoras.empty:
            raise ValueError(f"universo esgotado: só há {len(permutacao)} produtos para sortear")
        ids = list(ancoras["id_produto"])
        planilha = montar_planilha_pool(ancoras, universo, _pool_do_lote(universo, ids, cfg))
        if planilha.empty:
            raise ValueError(f"lote {len(lotes) + 1} sem nenhum candidato no pool: nada a anotar")
        gravar_ancoras_lote(ids, diretorio_pool, len(lotes) + 1)
        caminho = gravar_planilha_pool(planilha, diretorio_pool, len(lotes) + 1)
        logger.info(
            "Lote %d (%d âncoras, %d itens) gravado em %s; %d de %d âncoras com positivo até "
            "agora.",
            len(lotes) + 1,
            len(ids),
            len(planilha),
            caminho,
            n_com_positivo,
            cfg["alvo_ancoras_com_positivo"],
        )
        return

    rankings = pd.concat(
        [ranquear_entre_lojas(universo, m, max(cfg["ks"]), ids_ancoras=sorteados) for m in METODOS],
        ignore_index=True,
    )
    recall = calcular_recall_pxp(
        rankings,
        pd.concat([p for _, p, _ in lotes], ignore_index=True),
        sorteados,
        cfg["ks"],
        list(METODOS),
    )
    diretorio_metricas.mkdir(parents=True, exist_ok=True)
    recall.to_csv(diretorio_metricas / "recall_blocagem_pxp.csv", index=False)
    diretorio_latex_tabelas.mkdir(parents=True, exist_ok=True)
    (diretorio_latex_tabelas / "tab_recall_blocagem_pxp.tex").write_text(
        montar_tabela_recall_pxp_tex(recall), encoding="utf-8"
    )
    logger.info(
        "Parada do pool por %s: %d âncoras sorteadas, %d com positivo. Recall gravado em %s.",
        decisao.motivo,
        len(sorteados),
        n_com_positivo,
        diretorio_metricas,
    )
    _etapas_pos_pool(diretorio_processados, diretorio_metricas, caminho_config, cfg)


def _etapas_pos_pool(
    diretorio_processados: Path,
    diretorio_metricas: Path,
    caminho_config: Path,
    cfg: ConfigPxp,
) -> None:
    """Etapas 3 a 5, só depois da parada do pool: teste, planilha do teste e partição.

    Cada passo é idempotente e nunca sobrescreve o que o autor anotou: o teste é sorteado uma
    única vez, a planilha do teste só é validada se já existe, e a partição e os conjuntos são
    regeneráveis. Sem método e k congelados, ou sem a alocação do teste (`n_por_estrato`) decidida,
    o teste não é sorteado e o passo só avisa (CA-1b-04 vale para `gerar_pares_teste_pxp`).
    """
    if cfg["metodo"] is None or cfg["k"] is None:
        logger.info(
            "metodo e k ainda não congelados em %s: o teste não é sorteado.", caminho_config
        )
        return
    if cfg["n_por_estrato"] is None:
        logger.info(
            "Alocação do teste (n_por_estrato) não definida em %s: o teste não é sorteado.",
            caminho_config,
        )
        return
    if (diretorio_processados / "pares_teste_pxp.csv").exists():
        logger.info("Teste já sorteado em %s; não sorteado de novo.", diretorio_processados)
    else:
        gerar_pares_teste_pxp(diretorio_processados, caminho_config)
    gerar_planilha_teste_pxp(diretorio_processados, caminho_config)
    gerar_conjuntos_pxp(diretorio_processados, diretorio_metricas, caminho_config)
    if cfg["b2_cosseno_minimo"] is None:
        logger.info(
            "b2_cosseno_minimo não definido em %s: planilha do B2 não gerada.", caminho_config
        )
    else:
        gerar_planilha_b2_pxp(diretorio_processados, caminho_config)


FAIXAS_EXPLORATORIAS = [0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
COLUNAS_TAXAS_FAIXA = [
    "faixa",
    "n_pares",
    "n_match",
    "n_incerto",
    "taxa_match",
    "n_digito_divergente",
    "n_match_digito_divergente",
]
ESTRATO_TEXTO_IDENTICO = "texto_identico"
ESTRATO_TOTAL = "total"


ESTRATO_DIGITO_DIVERGENTE = "digito_divergente"


def _validar_faixas(faixas: list[float]) -> None:
    if (
        len(faixas) < 2
        or faixas[0] != 0.0
        or faixas[-1] != 1.0
        or any(b <= a for a, b in zip(faixas, faixas[1:], strict=False))
    ):
        raise ValueError(f"faixas inválidas (crescentes, de 0.0 a 1.0): {faixas}")


def _rotulos_das_faixas(faixas: list[float]) -> list[str]:
    rotulos = [f"[{a:.2f}, {b:.2f})" for a, b in zip(faixas, faixas[1:], strict=False)]
    rotulos[-1] = rotulos[-1][:-1] + "]"
    return rotulos


def taxas_positivos_por_faixa(
    rankings: pd.DataFrame,
    planilha: pd.DataFrame,
    universo: pd.DataFrame,
    *,
    metodo: str,
    k: int,
    faixas: list[float],
) -> pd.DataFrame:
    """Taxa de `match` por faixa de score entre os pares do top-k do pool anotado (T9).

    Só calibra a alocação do teste: lê o pool já anotado e nunca toca nos pares do teste nem
    rotula nada. Cada par do top-k do `metodo` das âncoras concluídas cai num estrato: texto
    normalizado idêntico entre lojas (Q7, estrato próprio) ou a faixa do seu score. `taxa_match`
    é `n_match / (n_pares - n_incerto)`: o incerto não integra o teste final, então fica fora do
    denominador e é contado à parte. `n_digito_divergente` conta os pares de tamanho divergente
    (T2), a reserva dos negativos difíceis. Falha se um par do top-k não estiver na planilha.
    """
    _validar_faixas(faixas)
    if metodo not in set(rankings["metodo"]):
        raise ValueError(f"método {metodo!r} ausente dos rankings")

    flag = planilha["ancora_concluida"].map(_entrada) == ANCORA_CONCLUIDA
    por_ancora = flag.groupby(planilha["id_ancora"]).all()
    concluidas = set(por_ancora.index[por_ancora])
    rotulos = (
        planilha[planilha["id_ancora"].isin(concluidas)][["id_ancora", "id_candidato", "rotulo"]]
        .rename(columns={"id_ancora": "id_produto"})
        .assign(rotulo=lambda d: d["rotulo"].map(_entrada))
    )
    topo = rankings[
        (rankings["metodo"] == metodo)
        & (rankings["rank"] <= k)
        & rankings["id_produto"].isin(concluidas)
    ]
    pares = topo.merge(rotulos, on=["id_produto", "id_candidato"], how="left", indicator=True)
    ausentes = pares[pares["_merge"] == "left_only"]
    if not ausentes.empty:
        ids = sorted(
            f"{a}-{c}"
            for a, c in zip(ausentes["id_produto"], ausentes["id_candidato"], strict=True)
        )
        raise ValueError(f"pares do top-{k} fora da planilha do pool: {ids}")

    id_texto = universo.set_index("id_produto")["id_texto"]
    descricao = universo.set_index("id_produto")["descricao"]
    identico = (
        pares["id_produto"].map(id_texto).to_numpy()
        == pares["id_candidato"].map(id_texto).to_numpy()
    )
    divergente = np.array(
        [
            divergencia_numerica(descricao[a], descricao[c])
            for a, c in zip(pares["id_produto"], pares["id_candidato"], strict=True)
        ],
        dtype=bool,
    )
    nomes = np.array(_rotulos_das_faixas(faixas))
    posicao = np.searchsorted(faixas, pares["score"].round(12).to_numpy(), side="right") - 1
    estrato = np.where(identico, ESTRATO_TEXTO_IDENTICO, nomes[np.clip(posicao, 0, len(nomes) - 1)])
    match = (pares["rotulo"] == "match").to_numpy()
    incerto = (pares["rotulo"] == "incerto").to_numpy()

    def linha(nome: str, mascara: np.ndarray) -> tuple[object, ...]:
        n_match, n_incerto = int(match[mascara].sum()), int(incerto[mascara].sum())
        n_pares = int(mascara.sum())
        decididos = n_pares - n_incerto
        return (
            nome,
            n_pares,
            n_match,
            n_incerto,
            n_match / decididos if decididos else float("nan"),
            int(divergente[mascara].sum()),
            int((divergente & match)[mascara].sum()),
        )

    linhas = [linha(ESTRATO_TEXTO_IDENTICO, estrato == ESTRATO_TEXTO_IDENTICO)]
    linhas += [linha(nome, estrato == nome) for nome in nomes]
    linhas.append(linha(ESTRATO_TOTAL, np.ones(len(pares), dtype=bool)))
    return pd.DataFrame(linhas, columns=COLUNAS_TAXAS_FAIXA)


def gravar_taxas_positivos_por_faixa_pxp(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    diretorio_metricas: Path = RESULTADOS_METRICAS,
    caminho_config: Path = CONFIG_BLOCAGEM_PXP,
    faixas: list[float] | None = None,
) -> pd.DataFrame:
    """Grava `taxas_positivos_por_faixa_pxp.csv` do pool anotado, com o método e k congelados.

    Exige `metodo` e `k` congelados e todos os lotes concluídos. Só lê o pool; não grava nada
    nele, não toca nos pares do teste e não decide faixas nem alocação (são do autor).
    """
    cfg = carregar_config_pxp(caminho_config)
    if cfg["metodo"] is None or cfg["k"] is None:
        raise ValueError(
            f"metodo e k ainda não congelados em {caminho_config}: congele antes de calibrar"
        )
    produtos = pd.read_parquet(diretorio_processados / "produtos_limpos.parquet")
    universo = deduplicar_por_texto_e_loja(produtos)
    lotes = _ler_lotes_pool(diretorio_processados / "pool_cego")
    if not lotes:
        raise ValueError("nenhum lote em pool_cego: gere e anote o pool antes de calibrar")
    for numero, planilha, ids in lotes:
        validar_anotacao_pool(planilha, _pool_do_lote(universo, ids, cfg))
        if not resumir_ancoras_pool(planilha, ids)["concluida"].all():
            raise ValueError(f"lote {numero} com âncoras não concluídas: conclua a anotação antes")
    sorteados = [i for _, _, ids in lotes for i in ids]
    rankings = ranquear_entre_lojas(universo, cfg["metodo"], cfg["k"], ids_ancoras=sorteados)
    taxas = taxas_positivos_por_faixa(
        rankings,
        pd.concat([p for _, p, _ in lotes], ignore_index=True),
        universo,
        metodo=cfg["metodo"],
        k=cfg["k"],
        faixas=FAIXAS_EXPLORATORIAS if faixas is None else faixas,
    )
    diretorio_metricas.mkdir(parents=True, exist_ok=True)
    taxas.to_csv(diretorio_metricas / "taxas_positivos_por_faixa_pxp.csv", index=False)
    logger.info("Taxas de positivos por faixa (%s, k=%d):\n%s", cfg["metodo"], cfg["k"], taxas)
    return taxas


COLUNAS_PARES_TESTE_PXP = ["id_a", "id_b", "estrato", "prob_inclusao"]


def sortear_pares_teste(
    candidatos: pd.DataFrame, universo: pd.DataFrame, cfg: ConfigPxp
) -> pd.DataFrame:
    """Sorteia os pares do teste produto × produto, estratificados, sem rótulo (T10, CA-1b-05).

    `candidatos` são os pares (`id_produto`, `id_candidato`, `score`) do top-k do método congelado
    para todos os produtos, entre lojas; um par listado nos dois sentidos conta uma vez. Cada par
    cai em um único estrato, nesta ordem: texto normalizado idêntico, tamanho divergente com score
    >= `score_minimo_digito_divergente`, ou a faixa do seu score. O sorteio de cada estrato é
    semeado (`seed` da config) e sempre parte dos pares ordenados, então não depende da ordem de
    entrada. Cada produto entra em no máximo um par. `prob_inclusao` é o alocado sobre os
    candidatos do estrato: nominal, porque a regra de um par por produto não é modelada. Falha com
    `ValueError` se o método ou o k não estiverem congelados, se a alocação faltar na config ou se
    um estrato não tiver pares utilizáveis o bastante; nunca reduz a alocação em silêncio. Só
    seleciona: o rótulo é sempre do autor.
    """
    if cfg["metodo"] is None or cfg["k"] is None:
        raise ValueError("metodo e k ainda não congelados: congele antes de sortear o teste")
    faixas, n_por_estrato = cfg["faixas"], cfg["n_por_estrato"]
    minimo = cfg["score_minimo_digito_divergente"]
    faltando = [
        nome
        for nome, valor in (
            ("faixas", faixas),
            ("n_por_estrato", n_por_estrato),
            ("score_minimo_digito_divergente", minimo),
        )
        if valor is None
    ]
    if faltando or faixas is None or n_por_estrato is None or minimo is None:
        raise ValueError(f"config do teste sem {faltando}: preencha antes de sortear")
    _validar_faixas(faixas)
    if sum(n_por_estrato.values()) != cfg["n_teste"]:
        raise ValueError(
            f"soma de n_por_estrato ({sum(n_por_estrato.values())}) diferente de n_teste "
            f"({cfg['n_teste']})"
        )

    a, b = candidatos["id_produto"].to_numpy(), candidatos["id_candidato"].to_numpy()
    pares = (
        pd.DataFrame(
            {
                "id_a": np.where(a < b, a, b),
                "id_b": np.where(a < b, b, a),
                "score": candidatos["score"].round(12).to_numpy(),
            }
        )
        .groupby(["id_a", "id_b"], as_index=False)["score"]
        .max()
        .sort_values(["id_a", "id_b"], kind="stable")
        .reset_index(drop=True)
    )
    loja = universo.set_index("id_produto")["loja"]
    if (pares["id_a"].map(loja) == pares["id_b"].map(loja)).any():
        raise ValueError("candidato da mesma loja do produto: o teste é só entre lojas")
    id_texto = universo.set_index("id_produto")["id_texto"]
    descricao = universo.set_index("id_produto")["descricao"]
    idem = (pares["id_a"].map(id_texto) == pares["id_b"].map(id_texto)).to_numpy()
    avaliar = ~idem & (pares["score"].to_numpy() >= minimo)
    divergente = np.zeros(len(pares), dtype=bool)
    for i in np.flatnonzero(avaliar):
        divergente[i] = divergencia_numerica(
            descricao[pares["id_a"].iat[i]], descricao[pares["id_b"].iat[i]]
        )
    nomes = _rotulos_das_faixas(faixas)
    posicao = np.searchsorted(faixas, pares["score"].to_numpy(), side="right") - 1
    faixa = np.array(nomes)[np.clip(posicao, 0, len(nomes) - 1)]
    pares["estrato"] = np.where(
        idem, ESTRATO_TEXTO_IDENTICO, np.where(divergente, ESTRATO_DIGITO_DIVERGENTE, faixa)
    )

    ordem = [ESTRATO_TEXTO_IDENTICO, ESTRATO_DIGITO_DIVERGENTE, *reversed(nomes)]
    usados: set[str] = set()
    sorteados = []
    for indice, estrato in enumerate(ordem):
        alocados = int(n_por_estrato[estrato])
        candidatos_do_estrato = pares[pares["estrato"] == estrato].reset_index(drop=True)
        escolhidos: list[tuple[str, str]] = []
        rng = np.random.default_rng([int(cfg["seed"]), indice])
        for posicao_sorteada in rng.permutation(len(candidatos_do_estrato)):
            if len(escolhidos) == alocados:
                break
            par = candidatos_do_estrato.iloc[int(posicao_sorteada)]
            if par["id_a"] in usados or par["id_b"] in usados:
                continue
            usados.update((par["id_a"], par["id_b"]))
            escolhidos.append((par["id_a"], par["id_b"]))
        if len(escolhidos) < alocados:
            raise ValueError(
                f"estrato {estrato!r}: só {len(escolhidos)} pares utilizáveis (de "
                f"{len(candidatos_do_estrato)} candidatos) para {alocados} alocados"
            )
        sorteados += [
            (id_a, id_b, estrato, alocados / len(candidatos_do_estrato))
            for id_a, id_b in sorted(escolhidos)
        ]
    return pd.DataFrame(sorteados, columns=COLUNAS_PARES_TESTE_PXP)


def gerar_pares_teste_pxp(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    caminho_config: Path = CONFIG_BLOCAGEM_PXP,
) -> pd.DataFrame:
    """Sorteia e grava `pares_teste_pxp.csv` (sem rótulo) com o método e k congelados.

    O teste é sorteado uma única vez: se o arquivo já existe, falha com `FileExistsError` sem
    reescrever. Falha com `ValueError`, sem gravar, se método ou k não estiverem congelados
    (CA-1b-04). Não usa nenhuma anotação do pool.
    """
    cfg = carregar_config_pxp(caminho_config)
    if cfg["metodo"] is None or cfg["k"] is None:
        raise ValueError(
            f"metodo e k ainda não congelados em {caminho_config}: congele antes de sortear o teste"
        )
    destino = diretorio_processados / "pares_teste_pxp.csv"
    if destino.exists():
        raise FileExistsError(f"{destino} já existe: o teste é sorteado uma única vez")
    produtos = pd.read_parquet(diretorio_processados / "produtos_limpos.parquet")
    universo = deduplicar_por_texto_e_loja(produtos)
    ranking = ranquear_entre_lojas(universo, cfg["metodo"], cfg["k"])
    pares = sortear_pares_teste(ranking[["id_produto", "id_candidato", "score"]], universo, cfg)
    assert not set(COLUNAS_MATCHER_ALTA) & set(pares.columns), "ADR-0011 violado"
    pares.to_csv(destino, index=False)
    logger.info(
        "Teste produto × produto sorteado (%d pares) em %s:\n%s",
        len(pares),
        destino,
        pares["estrato"].value_counts().to_string(),
    )
    return pares


# ── Planilha de anotação do teste produto × produto (T10b; protocolo §5, CA-1b-05) ──────────

COLUNAS_PLANILHA_TESTE_PXP = [
    "id_par",
    "id_a",
    "descricao_a",
    "und_val_a",
    "und_med_a",
    "id_b",
    "descricao_b",
    "und_val_b",
    "und_med_b",
    "tipo_par",
    "origem",
    "rotulo",
    "observacao",
    "timestamp_anotacao",
    "reteste",
]
# No teste o autor decide cada par nos dois sentidos: não há "vazio = não-match" como no pool.
ROTULOS_TESTE = ("match", "nao_match", "incerto")
_PROIBIDAS_NA_PLANILHA_TESTE = (
    *COLUNAS_MATCHER_ALTA,
    "metodo",
    "rank",
    "score",
    "estrato",
    "prob_inclusao",
)
ARQUIVO_PLANILHA_TESTE_PXP = "anotacoes_teste_pxp.csv"


def montar_planilha_teste_pxp(
    pares: pd.DataFrame, universo: pd.DataFrame, seed: int, origem: str = "teste"
) -> pd.DataFrame:
    """Planilha para o autor anotar os pares do teste às cegas: um par por linha, sem rótulo.

    Não traz estrato, probabilidade de inclusão, score nem método. O sorteio escreve os estratos
    em blocos, então as linhas são embaralhadas com `seed`, a partir de uma ordem canônica (por
    `id_par`), de modo que a ordem não depende da ordem de entrada nem revela o estrato.
    `id_par` é um hash de (id_a, id_b), estável. `reteste` sai vazia: marcá-la na primeira
    passada diria ao autor quais pares voltam.
    """
    colunas = ["id_produto", "descricao", "und_val", "und_med"]
    lado_a = universo[colunas].rename(
        columns={
            "id_produto": "id_a",
            "descricao": "descricao_a",
            "und_val": "und_val_a",
            "und_med": "und_med_a",
        }
    )
    lado_b = universo[colunas].rename(
        columns={
            "id_produto": "id_b",
            "descricao": "descricao_b",
            "und_val": "und_val_b",
            "und_med": "und_med_b",
        }
    )
    juntos = (
        pares[["id_a", "id_b"]]
        .merge(lado_a, on="id_a", how="left")
        .merge(lado_b, on="id_b", how="left")
    )
    fora = juntos[juntos["descricao_a"].isna() | juntos["descricao_b"].isna()]
    if len(fora):
        ids = sorted(
            set(fora.loc[fora["descricao_a"].isna(), "id_a"])
            | set(fora.loc[fora["descricao_b"].isna(), "id_b"])
        )
        raise ValueError(f"ids dos pares fora do universo: {ids}")
    juntos = juntos.assign(
        id_par=[
            _hash_curto(f"{a}|{b}") for a, b in zip(juntos["id_a"], juntos["id_b"], strict=True)
        ]
    ).sort_values("id_par")
    ordem = np.random.default_rng(seed).permutation(len(juntos))
    planilha = (
        juntos.iloc[ordem]
        .assign(
            tipo_par="produto_produto",
            origem=origem,
            rotulo="",
            observacao="",
            timestamp_anotacao="",
            reteste="",
        )[COLUNAS_PLANILHA_TESTE_PXP]
        .reset_index(drop=True)
    )
    assert not set(_PROIBIDAS_NA_PLANILHA_TESTE) & set(planilha.columns), "ADR-0011 violado"
    return planilha


def validar_anotacao_teste_pxp(
    planilha: pd.DataFrame, pares: pd.DataFrame, completa: bool = False, nome: str = "teste"
) -> None:
    """Valida só a forma da planilha do teste; nunca o mérito do rótulo.

    `pares` são os pares sorteados (`id_a`, `id_b`). Rótulo vazio é "ainda não anotado" e só é
    erro com `completa=True`. Falha cedo, com os ids, se faltar coluna, houver coluna proibida,
    planilha vazia, `id_par` repetido, rótulo fora de {match, nao_match, incerto}, par fora do
    teste ou par apagado.
    """
    faltando = [c for c in COLUNAS_PLANILHA_TESTE_PXP if c not in planilha.columns]
    if faltando:
        raise ValueError(f"colunas ausentes na planilha do {nome}: {faltando}")
    proibidas = [c for c in _PROIBIDAS_NA_PLANILHA_TESTE if c in planilha.columns]
    if proibidas:
        raise ValueError(f"colunas proibidas na planilha do {nome}: {proibidas}")
    if planilha.empty:
        raise ValueError(f"planilha do {nome} vazia")
    repetidos = sorted(set(planilha.loc[planilha["id_par"].duplicated(), "id_par"]))
    if repetidos:
        raise ValueError(f"id_par duplicado na planilha do {nome}: {repetidos}")

    rotulo = planilha["rotulo"].map(_entrada)
    invalidos = sorted(planilha.loc[~rotulo.isin(["", *ROTULOS_TESTE]), "id_par"])
    if invalidos:
        raise ValueError(f"rotulo fora do domínio {ROTULOS_TESTE} em: {invalidos}")
    if completa:
        vazios = sorted(planilha.loc[rotulo == "", "id_par"])
        if vazios:
            raise ValueError(f"{len(vazios)} pares sem rotulo, por exemplo: {vazios[:10]}")

    na_planilha = set(zip(planilha["id_a"], planilha["id_b"], strict=True))
    esperados = set(zip(pares["id_a"], pares["id_b"], strict=True))
    fora_do_teste = sorted(f"{a}-{b}" for a, b in na_planilha - esperados)
    if fora_do_teste:
        raise ValueError(f"pares fora do {nome}: {fora_do_teste}")
    apagados = sorted(f"{a}-{b}" for a, b in esperados - na_planilha)
    if apagados:
        raise ValueError(f"faltam pares do {nome} na planilha (linha apagada?): {apagados}")


def gravar_planilha_teste_pxp(
    planilha: pd.DataFrame, diretorio: Path, nome_arquivo: str = ARQUIVO_PLANILHA_TESTE_PXP
) -> Path:
    """Grava `anotacoes_teste_pxp.csv` (separador `;`). Nunca sobrescreve: é onde o autor anota.

    O nome casa com a exceção `anotacoes*.csv` do `.gitignore`: o padrão-ouro é versionável.
    """
    caminho = diretorio / nome_arquivo
    if caminho.exists():
        raise FileExistsError(f"Planilha já existe; não sobrescrita: {caminho}")
    diretorio.mkdir(parents=True, exist_ok=True)
    planilha.to_csv(caminho, sep=";", index=False)
    return caminho


def gerar_planilha_teste_pxp(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    caminho_config: Path = CONFIG_BLOCAGEM_PXP,
) -> Path:
    """Gera `anotacoes_teste_pxp.csv` a partir de `pares_teste_pxp.csv`, uma única vez.

    Se a planilha já existe, não a reescreve: lê como o autor a deixou, valida a forma (linha
    apagada ou rótulo inválido levantam `ValueError`) e registra quantos pares já estão anotados.
    """
    pares_csv = diretorio_processados / "pares_teste_pxp.csv"
    if not pares_csv.exists():
        raise FileNotFoundError(
            f"{pares_csv} não existe: sorteie o teste (gerar_pares_teste_pxp) antes da planilha"
        )
    pares = pd.read_csv(pares_csv, dtype=str)
    destino = diretorio_processados / ARQUIVO_PLANILHA_TESTE_PXP
    if destino.exists():
        planilha = pd.read_csv(destino, sep=";", dtype=str, keep_default_na=False)
        validar_anotacao_teste_pxp(planilha, pares)
        anotados = int((planilha["rotulo"].map(_entrada) != "").sum())
        logger.info(
            "Planilha do teste já existe (%s): %d de %d pares anotados; não reescrita.",
            destino,
            anotados,
            len(planilha),
        )
        return destino
    cfg = carregar_config_pxp(caminho_config)
    produtos = pd.read_parquet(diretorio_processados / "produtos_limpos.parquet")
    universo = deduplicar_por_texto_e_loja(produtos)
    planilha = montar_planilha_teste_pxp(pares, universo, cfg["seed"])
    validar_anotacao_teste_pxp(planilha, pares)
    caminho = gravar_planilha_teste_pxp(planilha, diretorio_processados)
    logger.info("Planilha do teste (%d pares, sem rótulo) gravada em %s.", len(planilha), caminho)
    return caminho


# ── Reteste do teste produto × produto (ADR-0005; protocolo §4; tasks-1b T10c) ───────────────
#
# Consistência intra-anotador: ≥ 50% do teste reanotado às cegas, ≥ 7 dias depois da primeira
# passada. Decisões do autor (2026-11-16): 150 pares, sorteio estratificado, `incerto` entra no
# sorteio, Kappa de 3 classes e binário. Nada disto roda no `main()`: a planilha do reteste só
# nasce quando o autor pede.

ARQUIVO_PLANILHA_RETESTE_PXP = "anotacoes_teste_pxp_reteste.csv"
FRACAO_MINIMA_RETESTE = 0.5
_ROTULO_INCERTO = "incerto"


def _ids_de_pares(pares: pd.DataFrame) -> list[str]:
    return [_hash_curto(f"{a}|{b}") for a, b in zip(pares["id_a"], pares["id_b"], strict=True)]


def sortear_pares_reteste(
    primeira: pd.DataFrame, pares: pd.DataFrame, n: int, seed: int
) -> pd.DataFrame:
    """Sorteia `n` pares do teste para o reteste, estratificado pelo estrato do sorteio original.

    `primeira` é a planilha do teste com a primeira passada completa; `pares` traz `id_a`, `id_b`
    e `estrato` (`pares_teste_pxp.csv`). A alocação por estrato é proporcional ao tamanho dele
    (maiores restos para a sobra, desempate pelo nome do estrato). O sorteio **não olha o rótulo**
    da primeira passada: `incerto` entra como qualquer outro, e mudar os rótulos não muda quais
    pares voltam. Falha, com os ids, se `n` < 50% do teste ou > o total, se a primeira passada
    estiver incompleta ou inválida, ou se algum par da planilha não tiver estrato. Devolve
    `id_par` e `estrato`, ordenados por `id_par`.
    """
    total = len(primeira)
    minimo = int(np.ceil(FRACAO_MINIMA_RETESTE * total))
    if n < minimo:
        raise ValueError(f"n={n} abaixo de 50% do teste ({minimo} de {total} pares)")
    if n > total:
        raise ValueError(f"n={n} acima do total do teste ({total} pares)")

    estrato = pd.Series(pares["estrato"].to_numpy(), index=_ids_de_pares(pares))
    sem_estrato = sorted(set(primeira["id_par"]) - set(estrato.index))
    if sem_estrato:
        raise ValueError(f"pares da planilha sem estrato em pares_teste: {sem_estrato[:10]}")
    validar_anotacao_teste_pxp(primeira, pares, completa=True)

    por_estrato = estrato.loc[sorted(primeira["id_par"])]
    tamanhos = por_estrato.value_counts().sort_index()
    exato = tamanhos * n / total
    cotas = np.floor(exato).astype(int)
    sobra = n - int(cotas.sum())
    restos = (exato - cotas).reset_index()
    restos.columns = ["estrato", "resto"]
    ordem_sobra = restos.sort_values(["resto", "estrato"], ascending=[False, True])["estrato"]
    for nome in list(ordem_sobra)[:sobra]:
        cotas[nome] += 1
    assert int(cotas.sum()) == n, "alocação do reteste não soma n"

    rng = np.random.default_rng(seed)
    escolhidos: list[str] = []
    for nome in tamanhos.index:  # ordem do índice: independente da ordem de entrada
        ids = sorted(por_estrato.index[por_estrato == nome])
        escolhidos.extend(rng.choice(ids, size=int(cotas[nome]), replace=False))
    sorteio = pd.DataFrame({"id_par": sorted(escolhidos)})
    return sorteio.assign(estrato=sorteio["id_par"].map(estrato)).reset_index(drop=True)


def montar_planilha_reteste_pxp(
    primeira: pd.DataFrame, sorteio: pd.DataFrame, seed: int
) -> pd.DataFrame:
    """Planilha do reteste: os pares sorteados, às cegas, em outra ordem.

    Copia o texto e a unidade da primeira passada, mas deixa `rotulo`, `observacao` e
    `timestamp_anotacao` vazios (o autor não vê o que marcou). `reteste` sai `sim` em todas as
    linhas: como todos os pares voltam, a marca não revela nada. Sem estrato, score ou método.
    A ordem é embaralhada com `seed` a partir de uma ordem canônica (por `id_par`).
    """
    fora = sorted(set(sorteio["id_par"]) - set(primeira["id_par"]))
    if fora:
        raise ValueError(f"pares do sorteio fora da primeira passada: {fora[:10]}")
    base = (
        primeira[primeira["id_par"].isin(set(sorteio["id_par"]))]
        .sort_values("id_par")
        .reset_index(drop=True)
    )
    ordem = np.random.default_rng(seed).permutation(len(base))
    planilha = (
        base.iloc[ordem]
        .assign(rotulo="", observacao="", timestamp_anotacao="", reteste="sim")[
            COLUNAS_PLANILHA_TESTE_PXP
        ]
        .reset_index(drop=True)
    )
    assert not set(_PROIBIDAS_NA_PLANILHA_TESTE) & set(planilha.columns), "ADR-0011 violado"
    return planilha


def _kappa_cohen(r1: pd.Series, r2: pd.Series, nome: str) -> tuple[float, float]:
    """(kappa, concordância observada). Falha, nomeando a versão, se o kappa for indefinido."""
    n = len(r1)
    if n == 0:
        raise ValueError(f"kappa {nome} indefinido: nenhum par comparável")
    observada = float((r1.to_numpy() == r2.to_numpy()).mean())
    p1 = r1.value_counts(normalize=True)
    p2 = r2.value_counts(normalize=True)
    esperada = float(sum(p1.get(c, 0.0) * p2.get(c, 0.0) for c in set(p1.index) | set(p2.index)))
    if esperada >= 1.0:
        raise ValueError(f"kappa {nome} indefinido: só um rótulo nas duas passadas ({n} pares)")
    return (observada - esperada) / (1.0 - esperada), observada


def calcular_kappa_reteste(primeira: pd.DataFrame, reteste: pd.DataFrame) -> dict[str, float]:
    """Cohen's Kappa intra-anotador entre a primeira passada e o reteste (ADR-0005).

    Considera só os pares que voltaram. Devolve o Kappa de 3 classes (`match`, `nao_match`,
    `incerto`) e o binário (só os pares sem `incerto` nas duas passadas), com as concordâncias
    observadas e as contagens. Deve ser chamado uma vez por tipo de par (hoje, só produto ×
    produto). Falha, com os ids, se o reteste tiver par fora da primeira passada ou rótulo vazio
    ou inválido; falha se o kappa for indefinido (nunca devolve `nan`).
    """
    fora = sorted(set(reteste["id_par"]) - set(primeira["id_par"]))
    if fora:
        raise ValueError(f"pares do reteste fora da primeira passada: {fora[:10]}")
    juntos = reteste[["id_par", "rotulo"]].merge(
        primeira[["id_par", "rotulo"]], on="id_par", suffixes=("_reteste", "_primeira")
    )
    for passada in ("primeira", "reteste"):
        rotulo = juntos[f"rotulo_{passada}"].map(_entrada)
        vazios = sorted(juntos.loc[rotulo == "", "id_par"])
        if vazios:
            raise ValueError(f"pares sem rotulo na passada {passada}: {vazios[:10]}")
        invalidos = sorted(juntos.loc[~rotulo.isin(ROTULOS_TESTE), "id_par"])
        if invalidos:
            raise ValueError(f"rotulo fora do domínio {ROTULOS_TESTE} na {passada}: {invalidos}")
        juntos[f"rotulo_{passada}"] = rotulo
    r1, r2 = juntos["rotulo_primeira"], juntos["rotulo_reteste"]
    kappa3, concordancia3 = _kappa_cohen(r1, r2, "de 3 classes")
    sem_incerto = (r1 != _ROTULO_INCERTO) & (r2 != _ROTULO_INCERTO)
    kappa2, concordancia2 = _kappa_cohen(r1[sem_incerto], r2[sem_incerto], "binário")
    return {
        "kappa_3_classes": kappa3,
        "kappa_binario": kappa2,
        "concordancia_3_classes": concordancia3,
        "concordancia_binaria": concordancia2,
        "n_pares": len(juntos),
        "n_binario": int(sem_incerto.sum()),
    }


def _instantes(planilha: pd.DataFrame, nome: str) -> pd.Series:
    texto = planilha["timestamp_anotacao"].map(_entrada)
    ausentes = sorted(planilha.loc[texto == "", "id_par"])
    if ausentes:
        raise ValueError(f"timestamp_anotacao ausente na {nome}: {ausentes[:10]}")
    return pd.to_datetime(texto, utc=True)


def calcular_intervalo_reteste(primeira: pd.DataFrame, reteste: pd.DataFrame) -> pd.Timedelta:
    """Intervalo do **último** timestamp da primeira passada ao **primeiro** do reteste.

    Leitura conservadora do "intervalo ≥ 7 dias" do ADR-0005. Falha se faltar timestamp.
    """
    fim = _instantes(primeira, "primeira passada").max()
    inicio = _instantes(reteste, "reteste").min()
    return inicio - fim


def verificar_intervalo_reteste(
    primeira: pd.DataFrame, reteste: pd.DataFrame, dias: int = 7
) -> None:
    """Falha se o reteste começou menos de `dias` dias depois do fim da primeira passada."""
    intervalo = calcular_intervalo_reteste(primeira, reteste)
    if intervalo < pd.Timedelta(days=dias):
        raise ValueError(
            f"reteste começou menos de {dias} dias depois da primeira passada "
            f"(intervalo: {intervalo})"
        )


def _ler_planilha_teste(diretorio: Path, nome_arquivo: str, descricao: str) -> pd.DataFrame:
    caminho = diretorio / nome_arquivo
    if not caminho.exists():
        raise FileNotFoundError(f"{caminho} não existe: {descricao}")
    return pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False)


def gerar_planilha_reteste_pxp(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    caminho_config: Path = CONFIG_BLOCAGEM_PXP,
) -> Path:
    """Gera `anotacoes_teste_pxp_reteste.csv` a partir da primeira passada, uma única vez.

    Exige `n_reteste` e `seed_reteste` no YAML e a primeira passada completa. Nunca altera
    `anotacoes_teste_pxp.csv` e nunca reescreve a planilha do reteste: se ela já existe, lê como
    o autor a deixou, confere a forma contra o sorteio (determinístico: linha apagada ou rótulo
    inválido levantam `ValueError`) e registra quantos pares já foram reanotados. O intervalo de
    7 dias é verificado só na hora do Kappa, sobre os timestamps (`gerar_kappa_reteste_pxp`).
    """
    cfg = carregar_config_pxp(caminho_config)
    if cfg["n_reteste"] is None or cfg["seed_reteste"] is None:
        raise ValueError(
            f"n_reteste e seed_reteste não definidos em {caminho_config}: "
            "defina-os antes de gerar o reteste"
        )
    primeira = _ler_planilha_teste(
        diretorio_processados,
        ARQUIVO_PLANILHA_TESTE_PXP,
        "gere e anote o teste (primeira passada) antes do reteste",
    )
    pares_csv = diretorio_processados / "pares_teste_pxp.csv"
    if not pares_csv.exists():
        raise FileNotFoundError(f"{pares_csv} não existe: sorteie o teste antes do reteste")
    pares = pd.read_csv(pares_csv, dtype=str)
    sorteio = sortear_pares_reteste(primeira, pares, cfg["n_reteste"], cfg["seed_reteste"])
    destino = diretorio_processados / ARQUIVO_PLANILHA_RETESTE_PXP
    if destino.exists():
        reteste = pd.read_csv(destino, sep=";", dtype=str, keep_default_na=False)
        esperados = primeira[primeira["id_par"].isin(set(sorteio["id_par"]))]
        validar_anotacao_teste_pxp(reteste, esperados[["id_a", "id_b"]], nome="reteste")
        feitos = int((reteste["rotulo"].map(_entrada) != "").sum())
        logger.info(
            "Planilha do reteste já existe (%s): %d de %d pares reanotados; não reescrita.",
            destino,
            feitos,
            len(reteste),
        )
        return destino
    planilha = montar_planilha_reteste_pxp(primeira, sorteio, cfg["seed_reteste"])
    caminho = gravar_planilha_teste_pxp(
        planilha, diretorio_processados, ARQUIVO_PLANILHA_RETESTE_PXP
    )
    logger.info("Planilha do reteste (%d pares, às cegas) gravada em %s.", len(planilha), caminho)
    return caminho


ARQUIVO_KAPPA_RETESTE_PXP = "kappa_reteste_pxp.csv"
COLUNAS_KAPPA_RETESTE = [
    "tipo_par",
    "kappa_3_classes",
    "kappa_binario",
    "concordancia_3_classes",
    "concordancia_binaria",
    "n_pares",
    "n_binario",
    "intervalo_horas",
    "intervalo_minimo_cumprido",
]
INTERVALO_MINIMO_RETESTE = pd.Timedelta(days=7)


def gerar_kappa_reteste_pxp(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    diretorio_metricas: Path = RESULTADOS_METRICAS,
    aceitar_intervalo_curto: bool = False,
) -> pd.DataFrame | None:
    """Calcula o Kappa do reteste, por tipo de par, e grava `kappa_reteste_pxp.csv`.

    Devolve `None`, sem gravar, enquanto o reteste não estiver inteiramente anotado. Com ele
    completo, verifica o intervalo mínimo de 7 dias (ADR-0005; `ValueError` se menor) e calcula
    o Kappa de 3 classes e o binário (`calcular_kappa_reteste`). Tudo ou nada: nada é gravado se
    qualquer verificação falhar. O Kappa é reportado mesmo abaixo de 0,75.

    `aceitar_intervalo_curto` é o desvio explícito do ADR-0005 (decisão do autor, 2026-11-16: o
    reteste foi feito 39 minutos depois da primeira passada). Com ele, o Kappa é calculado, mas o
    CSV registra `intervalo_horas` e `intervalo_minimo_cumprido=False`, e o log avisa: o número
    mede sobretudo memória de curto prazo e não pode ser apresentado como teste-reteste de 7 dias.
    """
    reteste = _ler_planilha_teste(
        diretorio_processados,
        ARQUIVO_PLANILHA_RETESTE_PXP,
        "gere o reteste (gerar_planilha_reteste_pxp) antes de calcular o Kappa",
    )
    primeira = _ler_planilha_teste(
        diretorio_processados, ARQUIVO_PLANILHA_TESTE_PXP, "primeira passada ausente"
    )
    pendentes = int((reteste["rotulo"].map(_entrada) == "").sum())
    if pendentes:
        logger.info("Kappa do reteste aguardando a anotação: %d pares pendentes.", pendentes)
        return None
    intervalo = calcular_intervalo_reteste(primeira, reteste)
    cumprido = intervalo >= INTERVALO_MINIMO_RETESTE
    if not cumprido:
        if not aceitar_intervalo_curto:
            verificar_intervalo_reteste(primeira, reteste)  # levanta ValueError
        logger.warning(
            "DESVIO DO ADR-0005: reteste com intervalo de %s (< 7 dias), aceito pelo autor. "
            "O Kappa é um limite superior da consistência (memória de curto prazo).",
            intervalo,
        )
    por_tipo = primeira.set_index("id_par")["tipo_par"]
    linhas = []
    for tipo in sorted(set(por_tipo.loc[reteste["id_par"]])):
        ids = set(por_tipo.index[por_tipo == tipo])
        resultado = calcular_kappa_reteste(
            primeira[primeira["id_par"].isin(ids)], reteste[reteste["id_par"].isin(ids)]
        )
        linhas.append(
            {
                "tipo_par": tipo,
                **resultado,
                "intervalo_horas": intervalo.total_seconds() / 3600,
                "intervalo_minimo_cumprido": cumprido,
            }
        )
    tabela = pd.DataFrame(linhas)[COLUNAS_KAPPA_RETESTE]
    diretorio_metricas.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(diretorio_metricas / ARQUIVO_KAPPA_RETESTE_PXP, index=False)
    logger.info("Kappa do reteste gravado em %s.", diretorio_metricas / ARQUIVO_KAPPA_RETESTE_PXP)
    return tabela


# ── Pares do treino que o autor anota (opção B2; design-treino-pxp §8; pendência A5) ─────────

ARQUIVO_PLANILHA_B2_PXP = "anotacoes_treino_b2_pxp.csv"
ARQUIVO_PARES_B2_PXP = "pares_b2_pxp.csv"
ORIGEM_B2 = "treino_b2"
COLUNAS_PARES_B2_PXP = ["id_a", "id_b", "score"]


def selecionar_pares_b2(
    produtos_treino: pd.DataFrame, k: int, cosseno_minimo: float
) -> pd.DataFrame:
    """Pares do treino que o autor anota: lojas diferentes, **mesmo tamanho**, cosseno ≥ corte.

    Top-`k` TF-IDF entre lojas dentro dos produtos de treino (vocabulário e IDF só do treino).
    Só entram pares com tamanho reconhecível e igual nos dois lados (`tokens_numericos`): tamanho
    diferente já é não-match pelo protocolo (§3.4) e não precisa de anotação, e sem tamanho não há
    como saber. Um par por linha, não ordenado (`id_a` < `id_b`), em ordem canônica, com o score.
    O score é cosseno TF-IDF, então o método é sempre TF-IDF, qualquer que seja o método oficial.
    """
    if not 0 < cosseno_minimo <= 1:
        raise ValueError(f"cosseno mínimo deve estar em (0, 1], recebido {cosseno_minimo}")
    universo = produtos_treino[["id_produto", "descricao", "loja"]]
    ranking = ranquear_entre_lojas(universo, "tfidf", k)
    tamanho = dict(
        zip(universo["id_produto"], universo["descricao"].map(tokens_numericos), strict=True)
    )
    mesmo_tamanho = np.array(
        [
            bool(tamanho[a]) and tamanho[a] == tamanho[b]
            for a, b in zip(ranking["id_produto"], ranking["id_candidato"], strict=True)
        ],
        dtype=bool,
    )
    ranking = ranking[mesmo_tamanho & (ranking["score"] >= cosseno_minimo - _TOLERANCIA_COSSENO)]
    pares = pd.DataFrame(
        {
            "id_a": [
                min(a, b)
                for a, b in zip(ranking["id_produto"], ranking["id_candidato"], strict=True)
            ],
            "id_b": [
                max(a, b)
                for a, b in zip(ranking["id_produto"], ranking["id_candidato"], strict=True)
            ],
            "score": ranking["score"].to_numpy(),
        }
    )
    pares = (
        pares.sort_values(["id_a", "id_b"])
        .drop_duplicates(["id_a", "id_b"])
        .reset_index(drop=True)[COLUNAS_PARES_B2_PXP]
    )
    if pares.empty:
        raise ValueError(f"nenhum par de mesmo tamanho com cosseno >= {cosseno_minimo} no treino")
    return pares


def montar_planilha_b2(
    pares: pd.DataFrame, produtos_treino: pd.DataFrame, seed: int
) -> pd.DataFrame:
    """Planilha de cartão por par para o autor anotar, igual à do teste (mesma ferramenta).

    Sem score nem cosseno (nada que sugira o rótulo), em ordem embaralhada com `seed` e
    independente da ordem de entrada, com `origem = treino_b2`.
    """
    return montar_planilha_teste_pxp(
        pares[["id_a", "id_b"]], produtos_treino, seed, origem=ORIGEM_B2
    )


def validar_anotacao_b2(
    planilha: pd.DataFrame, pares: pd.DataFrame, completa: bool = False
) -> None:
    """Valida só a forma da planilha do B2, com as mesmas regras da planilha do teste."""
    validar_anotacao_teste_pxp(planilha, pares, completa, nome="treino B2")


def gravar_planilha_b2(planilha: pd.DataFrame, diretorio: Path) -> Path:
    """Grava `anotacoes_treino_b2_pxp.csv` (`;`). Nunca sobrescreve: o autor anota nela."""
    return gravar_planilha_teste_pxp(planilha, diretorio, ARQUIVO_PLANILHA_B2_PXP)


def gerar_planilha_b2_pxp(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    caminho_config: Path = CONFIG_BLOCAGEM_PXP,
) -> Path:
    """Congela os pares do B2 e gera a planilha para o autor anotar, uma única vez.

    Exige método e k congelados, `b2_cosseno_minimo` no YAML e `produtos_treino_pxp.parquet`;
    sem qualquer um deles falha sem gravar nada. Os pares ficam em `pares_b2_pxp.csv` e nunca são
    resorteados: se a planilha já existe, só valida a forma contra eles e registra o progresso.
    """
    cfg = carregar_config_pxp(caminho_config)
    if cfg["metodo"] is None or cfg["k"] is None:
        raise ValueError(
            f"metodo e k ainda não congelados em {caminho_config}: congele antes de gerar o B2"
        )
    if cfg["b2_cosseno_minimo"] is None:
        raise ValueError(f"b2_cosseno_minimo não definido em {caminho_config}")
    arquivo_treino = diretorio_processados / "produtos_treino_pxp.parquet"
    if not arquivo_treino.exists():
        raise FileNotFoundError(
            f"{arquivo_treino} não existe: rode a partição (gerar_conjuntos_pxp) antes do B2"
        )
    treino = pd.read_parquet(arquivo_treino)
    destino_pares = diretorio_processados / ARQUIVO_PARES_B2_PXP
    destino_planilha = diretorio_processados / ARQUIVO_PLANILHA_B2_PXP

    if destino_pares.exists():
        pares = pd.read_csv(destino_pares, dtype={"id_a": str, "id_b": str})
        fora = sorted((set(pares["id_a"]) | set(pares["id_b"])) - set(treino["id_produto"]))
        if fora:
            raise ValueError(
                f"pares congelados do B2 com produtos fora do treino atual: {fora[:10]}"
            )
    elif destino_planilha.exists():
        raise ValueError(
            f"{destino_planilha} existe sem {destino_pares.name}: pares não congelados"
        )
    else:
        pares = selecionar_pares_b2(treino, cfg["k"], cfg["b2_cosseno_minimo"])

    if destino_planilha.exists():
        planilha = pd.read_csv(destino_planilha, sep=";", dtype=str, keep_default_na=False)
        validar_anotacao_b2(planilha, pares)
        anotados = int((planilha["rotulo"].map(_entrada) != "").sum())
        logger.info(
            "Planilha do B2 já existe (%s): %d de %d pares anotados; não reescrita.",
            destino_planilha,
            anotados,
            len(planilha),
        )
        return destino_planilha
    planilha = montar_planilha_b2(pares, treino, cfg["seed"])
    validar_anotacao_b2(planilha, pares)
    if not destino_pares.exists():
        pares.to_csv(destino_pares, index=False)
    caminho = gravar_planilha_b2(planilha, diretorio_processados)
    logger.info("Planilha do B2 (%d pares, sem rótulo) gravada em %s.", len(planilha), caminho)
    return caminho


# ── Partição por componente conexo (T11; design-1b C9 e C10; CA-1b-06) ──────────────────────

PARTICOES = ("treino", "validacao", "teste")
COLUNAS_PARTICAO_PXP = ["id_produto", "componente", "particao"]
COLUNAS_RESUMO_PARTICAO = [
    "particao",
    "n_componentes",
    "n_produtos",
    "fracao_base",
    "maior_componente",
]
COLUNAS_VAZAMENTO_RESIDUAL = [
    "tau",
    "n_positivos_pool",
    "n_positivos_separados",
    "vazamento_residual",
    "n_pares_validacao",
    "n_match_validacao",
    "n_incerto_validacao",
]
_TOLERANCIA_COSSENO = 1e-9  # vetores idênticos dão 0,9999999999999999: τ = 1 precisa ligá-los


def componentes_conexos(
    universo: pd.DataFrame, tau: float, arestas_extra: pd.DataFrame | None = None
) -> pd.Series:
    """Componente de cada produto: arestas = cosseno TF-IDF de palavras >= `tau`, mais as extras.

    Vale entre todos os produtos, inclusive da mesma loja (o vazamento entre treino e teste não
    respeita loja). O vocabulário e o IDF vêm do universo inteiro, sem rótulo. `arestas_extra`
    (`id_a`, `id_b`) são os pares do teste. O rótulo do componente é o menor `id_produto` dele,
    então a saída não depende da ordem das linhas. Retorna uma série indexada por `id_produto`,
    em ordem crescente, de nome `componente`.
    """
    if not 0 < tau <= 1:
        raise ValueError(f"tau deve estar em (0, 1], recebido {tau}")
    repetidos = sorted(set(universo.loc[universo["id_produto"].duplicated(), "id_produto"]))
    if repetidos:
        raise ValueError(f"id_produto duplicado no universo: {repetidos}")
    if universo.empty:
        raise ValueError("universo vazio: não há produtos para agrupar")
    universo = universo.sort_values("id_produto").reset_index(drop=True)
    ids = universo["id_produto"].to_numpy()
    n = len(ids)
    posicao = {i: k for k, i in enumerate(ids)}

    matriz = TfidfVectorizer(analyzer=_tokens).fit_transform(universo["descricao"]).tocsr()
    limiar = max(tau - _TOLERANCIA_COSSENO, 1e-12)
    linhas: list[np.ndarray] = []
    colunas: list[np.ndarray] = []
    for ini in range(0, n, _LOTE_PXP):
        scores = (matriz[ini : ini + _LOTE_PXP] @ matriz.T).toarray()
        r, c = np.where(scores >= limiar)
        r = r + ini
        acima_da_diagonal = c > r  # cada aresta uma vez; descarta o próprio produto
        linhas.append(r[acima_da_diagonal])
        colunas.append(c[acima_da_diagonal])
    if arestas_extra is not None and len(arestas_extra):
        fora = sorted((set(arestas_extra["id_a"]) | set(arestas_extra["id_b"])) - set(posicao))
        if fora:
            raise ValueError(f"ids das arestas extra fora do universo: {fora}")
        linhas.append(arestas_extra["id_a"].map(posicao).to_numpy(dtype=np.int64))
        colunas.append(arestas_extra["id_b"].map(posicao).to_numpy(dtype=np.int64))
    origem = np.concatenate(linhas)
    destino = np.concatenate(colunas)
    grafo = coo_matrix((np.ones(len(origem)), (origem, destino)), shape=(n, n))
    rotulos = connected_components(grafo, directed=False)[1]
    # `ids` está em ordem crescente: a primeira ocorrência de cada componente é o menor id dele
    representante = pd.Series(ids).groupby(rotulos).transform("first").to_numpy()
    return pd.Series(
        representante, index=pd.Index(ids, name="id_produto"), name="componente", dtype=object
    )


def verificar_particao_por_componente(particao: pd.DataFrame) -> None:
    """Falha se um componente estiver em mais de uma partição ou a partição sair do domínio.

    É `AssertionError` explícito (e não `assert`) para valer também com `python -O` (CA-1b-06).
    """
    fora = sorted(set(particao["particao"]) - set(PARTICOES))
    if fora:
        raise AssertionError(f"particao fora do domínio {PARTICOES}: {fora}")
    em_varias = particao.groupby("componente")["particao"].nunique()
    duplos = sorted(em_varias[em_varias > 1].index)
    if duplos:
        raise AssertionError(f"componentes em mais de uma partição: {duplos}")


def particionar_componentes(
    componentes: pd.Series, ids_teste: list[str], ids_pool: list[str]
) -> pd.DataFrame:
    """Cada componente vai inteiro para uma partição, antes de gerar ou aumentar qualquer coisa.

    O componente que toca o teste é do teste; o que toca o pool (e não o teste) é da validação;
    o restante é treino. O teste vence: produto do pool dentro de um componente do teste não vai
    à validação. Decisão do autor de 2026-11-13, com τ = 0,7: sem proporção a ajustar.
    """
    if len(ids_teste) == 0:
        raise ValueError("ids do teste vazios: não há o que separar do treino")
    if len(ids_pool) == 0:
        raise ValueError("ids do pool vazios: a validação ficaria sem nenhum par anotado")
    fora = sorted((set(ids_teste) | set(ids_pool)) - set(componentes.index))
    if fora:
        raise ValueError(f"ids do teste ou do pool fora do universo: {fora}")
    componentes = componentes.sort_index()
    do_teste = set(componentes.loc[list(set(ids_teste))])
    do_pool = set(componentes.loc[list(set(ids_pool))]) - do_teste
    particao = np.select(
        [componentes.isin(do_teste), componentes.isin(do_pool)], ["teste", "validacao"], "treino"
    )
    resultado = pd.DataFrame(
        {
            "id_produto": componentes.index.to_numpy(),
            "componente": componentes.to_numpy(),
            "particao": particao.astype(object),
        }
    )[COLUNAS_PARTICAO_PXP]
    verificar_particao_por_componente(resultado)
    return resultado.reset_index(drop=True)


def vazamento_residual(positivos: pd.DataFrame, componentes: pd.Series) -> float:
    """Fração dos positivos (`id_a`, `id_b`) cujos dois lados caem em componentes diferentes.

    É o limite do critério τ: um par do mesmo SKU que o grafo não ligou pode ter um lado no treino
    e o outro no teste (CA-1b-06). Sem positivos a fração é indefinida e levanta `ValueError`.
    """
    if len(positivos) == 0:
        raise ValueError("sem positivos: o vazamento residual não está definido")
    fora = sorted((set(positivos["id_a"]) | set(positivos["id_b"])) - set(componentes.index))
    if fora:
        raise ValueError(f"ids dos positivos fora do mapa de componentes: {fora}")
    separados = (
        componentes.loc[positivos["id_a"]].to_numpy()
        != componentes.loc[positivos["id_b"]].to_numpy()
    )
    return float(separados.mean())


def resumir_particao(particao: pd.DataFrame) -> pd.DataFrame:
    """Produtos, componentes, fração da base e maior componente de cada partição.

    Uma linha por partição de `PARTICOES`, inclusive a vazia (com zeros).
    """
    linhas = []
    for nome in PARTICOES:
        parte = particao[particao["particao"] == nome]
        tamanhos = parte.groupby("componente").size()
        linhas.append(
            {
                "particao": nome,
                "n_componentes": int(len(tamanhos)),
                "n_produtos": int(len(parte)),
                "fracao_base": len(parte) / len(particao) if len(particao) else 0.0,
                "maior_componente": int(tamanhos.max()) if len(tamanhos) else 0,
            }
        )
    return pd.DataFrame(linhas, columns=COLUNAS_RESUMO_PARTICAO)


class _ParticaoPxp(NamedTuple):
    """Tudo o que a partição calcula, antes de gravar qualquer arquivo."""

    universo: pd.DataFrame
    pool: pd.DataFrame
    ids_teste: list[str]
    ids_pool: list[str]
    particao: pd.DataFrame
    resumo: pd.DataFrame
    vazamento: pd.DataFrame


def _calcular_particao_pxp(diretorio_processados: Path, caminho_config: Path) -> _ParticaoPxp:
    """Lê teste e pool, valida o pool, particiona e mede o vazamento. Não grava nada.

    Exige os pares do teste e o pool anotado e concluído (cada lote validado na forma). Não usa
    rótulo nenhum além do `match` do pool, só para medir o vazamento e contar os pares da validação.
    """
    cfg = carregar_config_pxp(caminho_config)
    pares_csv = diretorio_processados / "pares_teste_pxp.csv"
    if not pares_csv.exists():
        raise FileNotFoundError(
            f"{pares_csv} não existe: sorteie o teste (gerar_pares_teste_pxp) antes da partição"
        )
    pares = pd.read_csv(pares_csv, dtype=str)
    diretorio_pool = diretorio_processados / "pool_cego"
    lotes = _ler_lotes_pool(diretorio_pool)
    if not lotes:
        raise ValueError(f"nenhum lote do pool em {diretorio_pool}: anote o pool antes da partição")

    produtos = pd.read_parquet(diretorio_processados / "produtos_limpos.parquet")
    universo = deduplicar_por_texto_e_loja(produtos)
    for numero, planilha, ids in lotes:
        validar_anotacao_pool(planilha, _pool_do_lote(universo, ids, cfg))
        if not resumir_ancoras_pool(planilha, ids)["concluida"].all():
            raise ValueError(
                f"âncoras não concluídas no lote {numero} de {diretorio_pool}: "
                "conclua a anotação do pool antes da partição"
            )
    pool = pd.concat([planilha for _, planilha, _ in lotes], ignore_index=True)
    ids_pool = sorted(
        set(pool["id_ancora"]) | set(pool["id_candidato"]) | {i for _, _, ids in lotes for i in ids}
    )
    ids_teste = sorted(set(pares["id_a"]) | set(pares["id_b"]))

    componentes = componentes_conexos(universo, cfg["tau_particao"], pares[["id_a", "id_b"]])
    particao = particionar_componentes(componentes, ids_teste, ids_pool)
    assert not set(COLUNAS_MATCHER_ALTA) & set(particao.columns), "ADR-0011 violado"

    rotulo = pool["rotulo"].map(_entrada)
    positivos = pool.loc[rotulo == "match", ["id_ancora", "id_candidato"]].rename(
        columns={"id_ancora": "id_a", "id_candidato": "id_b"}
    )
    vazamento = vazamento_residual(positivos, componentes)
    por_produto = dict(zip(particao["id_produto"], particao["particao"], strict=True))
    na_validacao = np.array(
        [
            por_produto[a] == por_produto[c] == "validacao"
            for a, c in zip(pool["id_ancora"], pool["id_candidato"], strict=True)
        ],
        dtype=bool,
    )
    resumo_vazamento = pd.DataFrame(
        [
            {
                "tau": cfg["tau_particao"],
                "n_positivos_pool": len(positivos),
                "n_positivos_separados": int(round(vazamento * len(positivos))),
                "vazamento_residual": vazamento,
                "n_pares_validacao": int(na_validacao.sum()),
                "n_match_validacao": int((na_validacao & (rotulo == "match")).sum()),
                "n_incerto_validacao": int((na_validacao & (rotulo == "incerto")).sum()),
            }
        ],
        columns=COLUNAS_VAZAMENTO_RESIDUAL,
    )
    return _ParticaoPxp(
        universo=universo,
        pool=pool,
        ids_teste=ids_teste,
        ids_pool=ids_pool,
        particao=particao,
        resumo=resumir_particao(particao),
        vazamento=resumo_vazamento,
    )


def _gravar_particao_pxp(
    calculo: _ParticaoPxp, diretorio_processados: Path, diretorio_metricas: Path
) -> None:
    diretorio_processados.mkdir(parents=True, exist_ok=True)
    diretorio_metricas.mkdir(parents=True, exist_ok=True)
    calculo.particao.to_parquet(diretorio_processados / "componentes_pxp.parquet", index=False)
    calculo.resumo.to_csv(diretorio_metricas / "particao_pxp.csv", index=False)
    calculo.vazamento.to_csv(diretorio_metricas / "vazamento_residual_pxp.csv", index=False)
    v = calculo.vazamento.iloc[0]
    logger.info(
        "Partição p×p (τ=%.2f) em %s:\n%s\nvazamento residual %.1f%% (%d de %d positivos do "
        "pool); validação: %d pares, %d match, %d incerto.",
        v["tau"],
        diretorio_processados,
        calculo.resumo.to_string(index=False),
        100 * v["vazamento_residual"],
        v["n_positivos_separados"],
        v["n_positivos_pool"],
        v["n_pares_validacao"],
        v["n_match_validacao"],
        v["n_incerto_validacao"],
    )


def gerar_particao_pxp(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    diretorio_metricas: Path = RESULTADOS_METRICAS,
    caminho_config: Path = CONFIG_BLOCAGEM_PXP,
) -> pd.DataFrame:
    """Particiona o universo por componente conexo e grava partição, resumo e vazamento residual.

    Tudo é calculado antes de gravar: se algo falha, nada é escrito. As saídas são regeneráveis
    (`componentes_pxp.parquet`, `particao_pxp.csv`, `vazamento_residual_pxp.csv`) e não incluem
    nenhuma coluna do matcher ALTA (ADR-0011).
    """
    calculo = _calcular_particao_pxp(diretorio_processados, caminho_config)
    _gravar_particao_pxp(calculo, diretorio_processados, diretorio_metricas)
    return calculo.particao


# ── Conjuntos derivados da partição (T12; design-1b C11) ────────────────────────────────────

COLUNAS_VALIDACAO_PXP = [
    "id_par",
    "id_a",
    "descricao_a",
    "und_val_a",
    "und_med_a",
    "id_b",
    "descricao_b",
    "und_val_b",
    "und_med_b",
    "tipo_par",
    "origem",
    "rotulo",
]
COLUNAS_PRODUTOS_TREINO_PXP = [
    "id_produto",
    "descricao",
    "texto_normalizado",
    "loja",
    "und_val",
    "und_med",
    "componente",
]
ROTULO_NAO_MATCH = "nao_match"


def montar_validacao_pxp(
    pool: pd.DataFrame, universo: pd.DataFrame, particao: pd.DataFrame
) -> pd.DataFrame:
    """Pares do pool com os dois lados na validação, com o rótulo do autor (design-1b C11).

    Uma linha por par **não ordenado** (`id_a` < `id_b`): o par visto dos dois lados, como âncora
    de um e de outro, conta uma vez, e rótulos diferentes nos dois sentidos levantam `ValueError`
    com os ids (inconsistência que só o autor resolve). Vazio em âncora concluída é `nao_match`;
    `incerto` fica de fora. O texto e a unidade vêm do universo, não da planilha do pool.
    """
    por_produto = dict(zip(particao["id_produto"], particao["particao"], strict=True))
    fora = sorted((set(pool["id_ancora"]) | set(pool["id_candidato"])) - set(por_produto))
    if fora:
        raise ValueError(f"ids do pool fora da partição: {fora}")
    rotulo = pool["rotulo"].map(_entrada)
    invalidos = sorted(set(rotulo) - {"", *ROTULOS_POOL})
    if invalidos:
        raise ValueError(f"rotulo fora do domínio (vazio, {ROTULOS_POOL}) no pool: {invalidos}")
    ambos = np.array(
        [
            por_produto[a] == por_produto[c] == "validacao"
            for a, c in zip(pool["id_ancora"], pool["id_candidato"], strict=True)
        ],
        dtype=bool,
    )
    pares = pd.DataFrame(
        {
            "id_a": [
                min(a, c) for a, c in zip(pool["id_ancora"], pool["id_candidato"], strict=True)
            ],
            "id_b": [
                max(a, c) for a, c in zip(pool["id_ancora"], pool["id_candidato"], strict=True)
            ],
            "rotulo": rotulo.where(rotulo != "", ROTULO_NAO_MATCH),
        }
    )[ambos]
    distintos = pares.groupby(["id_a", "id_b"])["rotulo"].nunique()
    conflitos = sorted(f"{a}-{b}" for a, b in distintos[distintos > 1].index)
    if conflitos:
        raise ValueError(f"pares com rótulos diferentes nos dois sentidos do pool: {conflitos}")
    pares = (
        pares.drop_duplicates()
        .loc[lambda d: d["rotulo"] != INCERTO]
        .sort_values(["id_a", "id_b"])
        .reset_index(drop=True)
    )
    if pares.empty:
        raise ValueError("validação sem pares: nenhum par do pool tem os dois lados nela")

    colunas = ["descricao", "und_val", "und_med"]
    base = universo.set_index("id_produto")[colunas]
    ausentes = sorted((set(pares["id_a"]) | set(pares["id_b"])) - set(base.index))
    if ausentes:
        raise ValueError(f"ids da validação fora do universo: {ausentes}")
    for lado in ("a", "b"):
        for coluna in colunas:
            pares[f"{coluna}_{lado}"] = pares[f"id_{lado}"].map(base[coluna])
    pares["id_par"] = [
        _hash_curto(f"{a}|{b}") for a, b in zip(pares["id_a"], pares["id_b"], strict=True)
    ]
    pares["tipo_par"] = "produto_produto"
    pares["origem"] = "amostra_cega"
    validacao = pares[COLUNAS_VALIDACAO_PXP]
    assert not set(COLUNAS_MATCHER_ALTA) & set(validacao.columns), "ADR-0011 violado"
    return validacao


def montar_produtos_treino_pxp(universo: pd.DataFrame, particao: pd.DataFrame) -> pd.DataFrame:
    """Só os produtos da partição de treino, sem par e sem rótulo (design-1b C11).

    É a única entrada permitida para gerar pares de treino: nenhum produto do teste ou da
    validação chega à geração (ADR-0004). Levanta `ValueError` se a partição não cobrir o universo
    (ou o contrário) ou se o treino ficar vazio.
    """
    sem_particao = sorted(set(universo["id_produto"]) - set(particao["id_produto"]))
    if sem_particao:
        raise ValueError(f"produtos do universo fora da partição: {sem_particao}")
    sem_universo = sorted(set(particao["id_produto"]) - set(universo["id_produto"]))
    if sem_universo:
        raise ValueError(f"produtos da partição fora do universo: {sem_universo}")
    treino = particao.loc[particao["particao"] == "treino", ["id_produto", "componente"]]
    if treino.empty:
        raise ValueError("treino vazio: a partição não deixou nenhum produto para treinar")
    colunas = ["id_produto", "descricao", "texto_normalizado", "loja", "und_val", "und_med"]
    produtos = (
        universo[colunas]
        .merge(treino, on="id_produto")
        .sort_values("id_produto")
        .reset_index(drop=True)
    )[COLUNAS_PRODUTOS_TREINO_PXP]
    assert not set(COLUNAS_MATCHER_ALTA) & set(produtos.columns), "ADR-0011 violado"
    return produtos


def gerar_conjuntos_pxp(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    diretorio_metricas: Path = RESULTADOS_METRICAS,
    caminho_config: Path = CONFIG_BLOCAGEM_PXP,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Partição + `validacao_pxp.parquet` + `produtos_treino_pxp.parquet`, tudo ou nada.

    Calcula a partição, monta a validação e os produtos de treino, confere que nenhum produto do
    teste nem do pool está no treino e só então grava os cinco arquivos. Se qualquer passo falha
    (pool não concluído, par com rótulos conflitantes, validação vazia), nada é escrito. Os pares
    de treino (`treino_pxp.parquet`) são montados em `gerar_treino_pxp` e não saem aqui.
    """
    calculo = _calcular_particao_pxp(diretorio_processados, caminho_config)
    validacao = montar_validacao_pxp(calculo.pool, calculo.universo, calculo.particao)
    treino = montar_produtos_treino_pxp(calculo.universo, calculo.particao)
    vazados = set(treino["id_produto"]) & (set(calculo.ids_teste) | set(calculo.ids_pool))
    if vazados:  # [CRÍTICO] ADR-0004; AssertionError explícito para valer também com `python -O`
        raise AssertionError(f"produtos do teste ou do pool no treino: {sorted(vazados)[:10]}")
    _gravar_particao_pxp(calculo, diretorio_processados, diretorio_metricas)
    validacao.to_parquet(diretorio_processados / "validacao_pxp.parquet", index=False)
    treino.to_parquet(diretorio_processados / "produtos_treino_pxp.parquet", index=False)
    n_match = int((validacao["rotulo"] == "match").sum())
    logger.info(
        "Validação p×p: %d pares únicos (%d match, %d nao_match); produtos de treino: %d.",
        len(validacao),
        n_match,
        len(validacao) - n_match,
        len(treino),
    )
    if n_match == 0:
        logger.warning("A validação não tem nenhum match: PR-AUC e recall ficam indefinidos.")
    return validacao, treino


# ── Parte A dos pares de treino (design-treino-pxp §5; ADR-0015) ────────────────────────────

TIPOS_PERTURBACAO = ("unidade", "ordem", "abreviacao", "ruido")
ORIGEM_NEGATIVO_TAMANHO = "neg_tamanho"
ORIGENS_POSITIVAS = tuple(f"pos_{t}" for t in TIPOS_PERTURBACAO)
COLUNAS_PARES_TREINO_PXP = [
    "id_par",
    "id_a",
    "descricao_a",
    "und_val_a",
    "und_med_a",
    "id_b",
    "descricao_b",
    "und_val_b",
    "und_med_b",
    "tipo_par",
    "origem",
    "rotulo",
]
ARQUIVO_PARES_TREINO_AUTO_PXP = "pares_treino_auto_pxp.parquet"
_PREFIXO_SINTETICO = "sint_"
_TAMANHO_MINIMO_PARA_TROCA = Decimal(100)  # abaixo de 100 g ou 100 ml a forma trocada não existe


class ConfigTreinoPxp(TypedDict):
    seed: int
    k: int
    incluir_mesma_loja: bool
    faixas_cosseno: list[float]
    n_negativos_por_faixa: dict[str, int]
    teto_negativos_por_produto: int
    n_positivos: int
    pesos_perturbacao: dict[str, float]
    abreviacoes: dict[str, list[str]]


def _sem_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c))


def carregar_config_treino_pxp(caminho: Path) -> ConfigTreinoPxp:
    """Lê o YAML da parte A dos pares de treino e valida cada chave, nomeando a que falhar.

    As chaves da tabela de abreviações são normalizadas (minúsculas, sem acento). A chave
    `incluir_mesma_loja` é obrigatória e booleana: um default silencioso mudaria a amostra.
    """
    cfg: dict[str, Any] = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    obrigatorias = ConfigTreinoPxp.__annotations__
    ausentes = [c for c in obrigatorias if c not in cfg]
    if ausentes:
        raise ValueError(f"chaves obrigatórias ausentes em {caminho}: {ausentes}")
    if not isinstance(cfg["incluir_mesma_loja"], bool):
        raise ValueError(
            f"incluir_mesma_loja deve ser booleano em {caminho}: {cfg['incluir_mesma_loja']!r}"
        )
    if int(cfg["k"]) < 1:
        raise ValueError(f"k deve ser >= 1 em {caminho}: {cfg['k']!r}")
    faixas = [float(f) for f in cfg["faixas_cosseno"]]
    _validar_faixas(faixas)
    esperados = set(_rotulos_das_faixas(faixas))
    negativos = cfg["n_negativos_por_faixa"]
    if set(negativos) != esperados:
        raise ValueError(
            f"n_negativos_por_faixa diferente das faixas em {caminho}: "
            f"faltam {sorted(esperados - set(negativos))}, "
            f"sobram {sorted(set(negativos) - esperados)}"
        )
    if any(int(n) < 0 for n in negativos.values()):
        raise ValueError(f"n_negativos_por_faixa com contagem negativa em {caminho}: {negativos}")
    if int(cfg["teto_negativos_por_produto"]) < 1:
        raise ValueError(
            f"teto_negativos_por_produto deve ser >= 1 em {caminho}: "
            f"{cfg['teto_negativos_por_produto']!r}"
        )
    if int(cfg["n_positivos"]) < 0:
        raise ValueError(f"n_positivos negativo em {caminho}: {cfg['n_positivos']!r}")
    pesos = {str(t): float(v) for t, v in cfg["pesos_perturbacao"].items()}
    desconhecidos = sorted(set(pesos) - set(TIPOS_PERTURBACAO))
    if desconhecidos:
        raise ValueError(f"pesos_perturbacao com tipos desconhecidos em {caminho}: {desconhecidos}")
    if any(v < 0 for v in pesos.values()) or sum(pesos.values()) <= 0:
        raise ValueError(
            f"pesos_perturbacao deve ser >= 0 e somar mais que 0 em {caminho}: {pesos}"
        )
    abreviacoes: dict[str, list[str]] = {}
    for palavra, formas in cfg["abreviacoes"].items():
        chave = _sem_acentos(str(palavra)).lower()
        normalizadas = [_sem_acentos(str(f)).lower() for f in (formas or [])]
        if not normalizadas:
            raise ValueError(f"abreviacoes sem nenhuma forma para {palavra!r} em {caminho}")
        for forma in normalizadas:
            if not forma.isalpha() or len(forma) >= len(chave):
                raise ValueError(
                    f"abreviacoes: {forma!r} não é uma forma alfabética mais curta que "
                    f"{palavra!r} em {caminho}"
                )
        abreviacoes[chave] = normalizadas
    return ConfigTreinoPxp(
        seed=int(cfg["seed"]),
        k=int(cfg["k"]),
        incluir_mesma_loja=cfg["incluir_mesma_loja"],
        faixas_cosseno=faixas,
        n_negativos_por_faixa={str(r): int(n) for r, n in negativos.items()},
        teto_negativos_por_produto=int(cfg["teto_negativos_por_produto"]),
        n_positivos=int(cfg["n_positivos"]),
        pesos_perturbacao=pesos,
        abreviacoes=abreviacoes,
    )


# Perturbações do próprio texto (positivos da fonte b). Cada uma devolve `None` se não se aplica,
# nunca muda o conjunto de tamanhos e nunca mexe em palavra com dígito.


def perturbar_unidade(texto: str) -> str | None:
    """Troca a primeira expressão de tamanho por uma equivalente: 900ML ↔ 0,9L, 1KG ↔ 1000G.

    G e ML só viram KG e L a partir de 100 (0,06KG não existe em texto de PDV). Mantém o formato
    de caixa da unidade original.
    """
    achado = _NUMERO_COM_UNIDADE.search(texto)
    if achado is None:
        return None
    numero, unidade = achado.group(1), achado.group(2)
    dimensao, fator = _UNIDADES[unidade.lower()]
    base = Decimal(numero.replace(",", ".")) * fator  # em g ou ml
    if dimensao == "massa":
        if unidade.lower() == "kg":
            valor, nova = base, "g"
        elif base >= _TAMANHO_MINIMO_PARA_TROCA:
            valor, nova = base / 1000, "kg"
        else:
            return None
    elif unidade.lower() in ("l", "lt"):
        valor, nova = base, "ml"
    elif base >= _TAMANHO_MINIMO_PARA_TROCA:
        valor, nova = base / 1000, "l"
    else:
        return None
    nova = nova.upper() if any(c.isupper() for c in unidade) else nova
    expressao = format(valor.normalize(), "f").replace(".", ",") + nova
    novo = texto[: achado.start()] + expressao + texto[achado.end() :]
    if novo == texto or tokens_numericos(novo) != tokens_numericos(texto):
        return None
    return novo


def _blocos(texto: str) -> list[str]:
    """Tokens do texto, com cada expressão de tamanho (`750 ML`, `7/9 Kg`) como um bloco só."""
    tokens = list(re.finditer(r"\S+", texto))
    expressoes = [m.span() for m in _NUMERO_COM_UNIDADE.finditer(texto)]
    blocos: list[str] = []
    i = 0
    while i < len(tokens):
        inicio, fim = tokens[i].span()
        tocadas = [e for e in expressoes if e[0] < fim and e[1] > inicio]
        if not tocadas:
            blocos.append(tokens[i].group())
            i += 1
            continue
        limite = max(e[1] for e in tocadas)
        ultimo = i
        while ultimo + 1 < len(tokens) and tokens[ultimo + 1].span()[0] < limite:
            ultimo += 1
        blocos.append(texto[inicio : tokens[ultimo].span()[1]])
        i = ultimo + 1
    return blocos


def _preserva_tamanhos(texto: str, novo: str | None) -> str | None:
    """Rede de segurança de toda perturbação: `None` se o texto não mudou ou o tamanho mudou."""
    if novo is None or novo == texto or tokens_numericos(novo) != tokens_numericos(texto):
        return None
    return novo


def perturbar_ordem(texto: str, rng: np.random.Generator) -> str | None:
    """Troca de lugar dois blocos diferentes (inversão parcial), sem tocar em nenhum bloco.

    Um bloco é um token ou uma expressão de tamanho inteira, para a troca nunca separar o número
    da unidade (`750 ML`). Achado na base real: sem isso, 13 de 6.000 positivos mudavam o tamanho.
    """
    blocos = _blocos(texto)
    pares = [
        (i, j)
        for i in range(len(blocos))
        for j in range(i + 1, len(blocos))
        if blocos[i] != blocos[j]
    ]
    if len(blocos) < 3 or not pares:
        return None
    i, j = pares[int(rng.integers(len(pares)))]
    blocos[i], blocos[j] = blocos[j], blocos[i]
    return _preserva_tamanhos(texto, " ".join(blocos))


def _formato_de_caixa(modelo: str, forma: str) -> str:
    if modelo.isupper():
        return forma.upper()
    if modelo[:1].isupper():
        return forma.capitalize()
    return forma.lower()


def perturbar_abreviacao(
    texto: str, abreviacoes: dict[str, list[str]], rng: np.random.Generator
) -> str | None:
    """Troca palavras da **tabela fechada** pelas formas abreviadas dela (VINHO → VH).

    Só mexe em palavra da tabela (sem acento e sem diferença de caixa) e nunca em token com
    dígito, então a marca, que não está na tabela, e o tamanho ficam intactos.
    """
    tokens = texto.split()
    candidatos = [
        i
        for i, t in enumerate(tokens)
        if not any(c.isdigit() for c in t) and _sem_acentos(t).lower() in abreviacoes
    ]
    if not candidatos:
        return None
    n = int(rng.integers(1, len(candidatos) + 1))
    escolhidos = sorted(int(i) for i in rng.choice(candidatos, size=n, replace=False))
    for i in escolhidos:
        formas = abreviacoes[_sem_acentos(tokens[i]).lower()]
        forma = str(formas[int(rng.integers(len(formas)))])
        tokens[i] = _formato_de_caixa(tokens[i], forma)
    return _preserva_tamanhos(texto, " ".join(tokens))


def perturbar_ruido_tipografico(texto: str, rng: np.random.Generator) -> str | None:
    """Tira os acentos ou uma letra interior de uma palavra longa (≥ 6 letras, sem dígito)."""
    tokens = texto.split()
    com_acento = [i for i, t in enumerate(tokens) if _sem_acentos(t) != t]
    longas = [
        i
        for i, t in enumerate(tokens)
        if len(t) >= 6 and not any(c.isdigit() for c in t) and _sem_acentos(t).isalpha()
    ]
    operacoes = (["acento"] if com_acento else []) + (["letra"] if longas else [])
    if not operacoes:
        return None
    if operacoes[int(rng.integers(len(operacoes)))] == "acento":
        tokens = [_sem_acentos(t) for t in tokens]
    else:
        i = longas[int(rng.integers(len(longas)))]
        base = _sem_acentos(tokens[i])
        posicao = int(rng.integers(1, len(base) - 1))
        tokens[i] = base[:posicao] + base[posicao + 1 :]
    return _preserva_tamanhos(texto, " ".join(tokens))


def _amostrar_por_faixa(
    pares: pd.DataFrame,
    faixas: list[float],
    alocacao: dict[str, int],
    teto: int,
    seed: int,
) -> pd.DataFrame:
    """Sorteia `alocacao[faixa]` pares por faixa de cosseno, das mais difíceis para as mais fáceis.

    `pares` traz `id_a`, `id_b` e `score`, um por par não ordenado e já ordenado. Cada produto
    entra em no máximo `teto` pares. Falha com `ValueError` nomeando a faixa se faltar candidato
    (não reduz em silêncio). Devolve `id_a`, `id_b`, `score` e `faixa`, ordenado por (id_a, id_b).
    """
    rotulos = _rotulos_das_faixas(faixas)
    indice = np.clip(
        np.searchsorted(faixas, pares["score"].to_numpy(), side="right") - 1, 0, len(rotulos) - 1
    )
    pares = pares.assign(faixa=np.array(rotulos, dtype=object)[indice])
    rng = np.random.default_rng(seed)
    uso: Counter[str] = Counter()
    escolhidos = []
    for rotulo in reversed(rotulos):
        alocado = alocacao[rotulo]
        candidatos = pares[pares["faixa"] == rotulo].reset_index(drop=True)
        feitos = 0
        for posicao in rng.permutation(len(candidatos)):
            if feitos == alocado:
                break
            linha = candidatos.iloc[int(posicao)]
            if uso[linha["id_a"]] < teto and uso[linha["id_b"]] < teto:
                uso[linha["id_a"]] += 1
                uso[linha["id_b"]] += 1
                escolhidos.append(linha)
                feitos += 1
        if feitos < alocado:
            raise ValueError(
                f"faixa {rotulo}: alocados {alocado}, mas só {feitos} disponíveis "
                f"({len(candidatos)} candidatos, teto de {teto} pares por produto)"
            )
    if not escolhidos:
        return pd.DataFrame(columns=["id_a", "id_b", "score", "faixa"])
    return (
        pd.DataFrame(escolhidos)
        .sort_values(["id_a", "id_b"])
        .reset_index(drop=True)[["id_a", "id_b", "score", "faixa"]]
    )


def selecionar_negativos_tamanho(
    produtos_treino: pd.DataFrame, cfg: ConfigTreinoPxp
) -> pd.DataFrame:
    """Negativos certos: pares com tamanho reconhecível e **diferente** nos dois lados.

    Candidatos do top-`k` TF-IDF no treino (entre lojas ou, com `incluir_mesma_loja`, entre todos),
    um por par não ordenado. Amostragem por faixa de cosseno com a seed da config, das faixas mais
    difíceis para as mais fáceis e com teto de pares por produto, para os mais difíceis terem
    prioridade e nenhum produto dominar. Falha com `ValueError` nomeando a faixa se faltar
    candidato (não reduz em silêncio). Tamanho igual ou ausente nunca entra.
    """
    universo = produtos_treino[["id_produto", "descricao", "loja"]]
    if cfg["incluir_mesma_loja"]:
        ranking = ranquear_vizinhos(universo, cfg["k"])
    else:
        ranking = ranquear_entre_lojas(universo, "tfidf", cfg["k"])
    tamanho = dict(
        zip(universo["id_produto"], universo["descricao"].map(tokens_numericos), strict=True)
    )
    diferente = np.array(
        [
            bool(tamanho[a]) and bool(tamanho[b]) and tamanho[a] != tamanho[b]
            for a, b in zip(ranking["id_produto"], ranking["id_candidato"], strict=True)
        ],
        dtype=bool,
    )
    ranking = ranking[diferente]
    pares = (
        pd.DataFrame(
            {
                "id_a": [
                    min(a, b)
                    for a, b in zip(ranking["id_produto"], ranking["id_candidato"], strict=True)
                ],
                "id_b": [
                    max(a, b)
                    for a, b in zip(ranking["id_produto"], ranking["id_candidato"], strict=True)
                ],
                "score": ranking["score"].to_numpy(),
            }
        )
        .sort_values(["id_a", "id_b"])
        .drop_duplicates(["id_a", "id_b"])
        .reset_index(drop=True)
    )
    return _amostrar_por_faixa(
        pares,
        cfg["faixas_cosseno"],
        cfg["n_negativos_por_faixa"],
        cfg["teto_negativos_por_produto"],
        cfg["seed"],
    )


def _dados_do_produto(produtos_treino: pd.DataFrame) -> pd.DataFrame:
    return produtos_treino.set_index("id_produto")[["descricao", "und_val", "und_med"]]


def gerar_negativos_tamanho(produtos_treino: pd.DataFrame, cfg: ConfigTreinoPxp) -> pd.DataFrame:
    """Os negativos por tamanho no formato dos pares de treino (`origem = neg_tamanho`)."""
    selecao = selecionar_negativos_tamanho(produtos_treino, cfg)
    base = _dados_do_produto(produtos_treino)
    pares = selecao[["id_a", "id_b"]].copy()
    for lado in ("a", "b"):
        for coluna in ("descricao", "und_val", "und_med"):
            pares[f"{coluna}_{lado}"] = pares[f"id_{lado}"].map(base[coluna])
    pares["id_par"] = [
        _hash_curto(f"{a}|{b}") for a, b in zip(pares["id_a"], pares["id_b"], strict=True)
    ]
    pares["tipo_par"] = "produto_produto"
    pares["origem"] = ORIGEM_NEGATIVO_TAMANHO
    pares["rotulo"] = "nao_match"
    return pares[COLUNAS_PARES_TREINO_PXP].reset_index(drop=True)


def gerar_positivos_perturbados(
    produtos_treino: pd.DataFrame, cfg: ConfigTreinoPxp
) -> pd.DataFrame:
    """Positivos por construção: um produto contra uma versão perturbada dele mesmo.

    Cada positivo usa um produto diferente. Só entram produtos para os quais ao menos uma
    perturbação de peso positivo se aplica; pedir mais positivos que produtos elegíveis levanta
    `ValueError`. O lado B é sintético (`sint_<hash>`), com a unidade do produto original, e a
    perturbação preserva o conjunto de tamanhos. A ordem de varredura é a dos ids, então o
    resultado não depende da ordem das linhas.
    """
    rng = np.random.default_rng(cfg["seed"])
    tipos = [t for t in TIPOS_PERTURBACAO if cfg["pesos_perturbacao"].get(t, 0) > 0]
    funcoes = {
        "unidade": lambda t: perturbar_unidade(t),
        "ordem": lambda t: perturbar_ordem(t, rng),
        "abreviacao": lambda t: perturbar_abreviacao(t, cfg["abreviacoes"], rng),
        "ruido": lambda t: perturbar_ruido_tipografico(t, rng),
    }
    base = _dados_do_produto(produtos_treino).sort_index()
    elegiveis: list[tuple[str, dict[str, str]]] = []
    for id_produto, descricao in base["descricao"].items():
        opcoes = {}
        for tipo in tipos:
            novo = funcoes[tipo](descricao)
            if novo is not None and novo != descricao:
                opcoes[tipo] = novo
        if opcoes:
            elegiveis.append((str(id_produto), opcoes))
    n = cfg["n_positivos"]
    if n > len(elegiveis):
        raise ValueError(f"apenas {len(elegiveis)} produtos elegíveis para {n} positivos")
    linhas = []
    for posicao in sorted(int(i) for i in rng.choice(len(elegiveis), size=n, replace=False)):
        id_a, opcoes = elegiveis[posicao]
        disponiveis = list(opcoes)
        pesos = np.array([cfg["pesos_perturbacao"][t] for t in disponiveis], dtype=float)
        tipo = disponiveis[int(rng.choice(len(disponiveis), p=pesos / pesos.sum()))]
        id_b = _PREFIXO_SINTETICO + _hash_curto(f"{id_a}|{tipo}|{opcoes[tipo]}")
        linhas.append(
            {
                "id_par": _hash_curto(f"{id_a}|{id_b}"),
                "id_a": id_a,
                "descricao_a": base.at[id_a, "descricao"],
                "und_val_a": base.at[id_a, "und_val"],
                "und_med_a": base.at[id_a, "und_med"],
                "id_b": id_b,
                "descricao_b": opcoes[tipo],
                "und_val_b": base.at[id_a, "und_val"],
                "und_med_b": base.at[id_a, "und_med"],
                "tipo_par": "produto_produto",
                "origem": f"pos_{tipo}",
                "rotulo": "match",
            }
        )
    return pd.DataFrame(linhas, columns=COLUNAS_PARES_TREINO_PXP)


def montar_pares_treino_auto(produtos_treino: pd.DataFrame, cfg: ConfigTreinoPxp) -> pd.DataFrame:
    """Negativos por tamanho e positivos por perturbação, juntos e em ordem determinística."""
    pares = pd.concat(
        [
            gerar_negativos_tamanho(produtos_treino, cfg),
            gerar_positivos_perturbados(produtos_treino, cfg),
        ],
        ignore_index=True,
    )
    return pares.sort_values(["origem", "id_a", "id_b"]).reset_index(drop=True)


def verificar_pares_treino_auto(
    pares: pd.DataFrame, produtos_treino: pd.DataFrame, mesma_loja_permitida: bool = False
) -> None:
    """Barreira crítica: o que torna os rótulos automáticos certos por construção.

    `AssertionError` explícito (vale com `python -O`) se: as colunas não forem as do contrato (nem
    sobrar coluna da ALTA); houver `id_par` repetido; origem e rótulo forem incoerentes; um id
    não for do treino; um negativo tiver tamanho igual ou ausente (ou for da mesma loja, quando a
    config não permite); ou um positivo mudar o conjunto de tamanhos.
    """
    if list(pares.columns) != COLUNAS_PARES_TREINO_PXP:
        extras = sorted(set(pares.columns) - set(COLUNAS_PARES_TREINO_PXP))
        raise AssertionError(f"colunas fora do contrato dos pares de treino; sobram {extras}")
    repetidos = sorted(set(pares.loc[pares["id_par"].duplicated(), "id_par"]))
    if repetidos:
        raise AssertionError(f"id_par duplicado nos pares de treino: {repetidos[:10]}")
    negativo = pares["origem"] == ORIGEM_NEGATIVO_TAMANHO
    positivo = pares["origem"].isin(ORIGENS_POSITIVAS)
    desconhecidas = sorted(set(pares.loc[~(negativo | positivo), "origem"]))
    if desconhecidas:
        raise AssertionError(f"origem desconhecida nos pares de treino: {desconhecidas}")
    incoerentes = pares[
        (negativo & (pares["rotulo"] != "nao_match")) | (positivo & (pares["rotulo"] != "match"))
    ]
    if len(incoerentes):
        raise AssertionError(
            f"rotulo incoerente com a origem em: {sorted(incoerentes['id_par'])[:10]}"
        )
    ids = set(produtos_treino["id_produto"])
    fora = sorted((set(pares["id_a"]) - ids) | (set(pares.loc[negativo, "id_b"]) - ids))
    if fora:
        raise AssertionError(f"ids fora dos produtos de treino: {fora[:10]}")
    sinteticos = pares.loc[positivo, "id_b"]
    reais_no_lado_b = sorted(
        i for i in sinteticos if not i.startswith(_PREFIXO_SINTETICO) or i in ids
    )
    if reais_no_lado_b:
        raise AssertionError(f"lado B de positivo não é sintético: {reais_no_lado_b[:10]}")

    loja = produtos_treino.set_index("id_produto")["loja"]
    texto = produtos_treino.set_index("id_produto")["descricao"]
    for linha in pares.itertuples(index=False):
        tamanho_a = tokens_numericos(linha.descricao_a)
        tamanho_b = tokens_numericos(linha.descricao_b)
        if linha.origem == ORIGEM_NEGATIVO_TAMANHO:
            if not (tamanho_a and tamanho_b and tamanho_a != tamanho_b):
                raise AssertionError(f"negativo com tamanho igual ou ausente: {linha.id_par}")
            if not mesma_loja_permitida and loja[linha.id_a] == loja[linha.id_b]:
                raise AssertionError(f"negativo entre produtos da mesma loja: {linha.id_par}")
            if texto[linha.id_b] != linha.descricao_b:
                raise AssertionError(f"texto do lado B diferente do treino: {linha.id_par}")
        else:
            if tamanho_a != tamanho_b:
                raise AssertionError(f"positivo muda o conjunto de tamanhos: {linha.id_par}")
            if linha.descricao_a == linha.descricao_b:
                raise AssertionError(f"positivo idêntico ao original: {linha.id_par}")
        if texto[linha.id_a] != linha.descricao_a:
            raise AssertionError(f"texto do lado A diferente do treino: {linha.id_par}")


def gerar_pares_treino_auto_pxp(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    caminho_config: Path = CONFIG_PARES_TREINO_PXP,
) -> pd.DataFrame:
    """Parte A dos pares de treino: negativos por tamanho e positivos por perturbação.

    Só usa `produtos_treino_pxp.parquet` (nada do teste, do pool ou da validação chega aqui).
    Calcula e verifica tudo antes de gravar `pares_treino_auto_pxp.parquet`: se algo falha
    (faixa sem candidatos, positivos demais, barreira crítica), nada é escrito. É regenerável.
    A anotação B2 e os pares da TAIL entram no `treino_pxp.parquet` em `gerar_treino_pxp`.
    """
    cfg = carregar_config_treino_pxp(caminho_config)
    arquivo_treino = diretorio_processados / "produtos_treino_pxp.parquet"
    if not arquivo_treino.exists():
        raise FileNotFoundError(
            f"{arquivo_treino} não existe: rode a partição (gerar_conjuntos_pxp) antes "
            "dos pares de treino"
        )
    treino = pd.read_parquet(arquivo_treino)
    pares = montar_pares_treino_auto(treino, cfg)
    verificar_pares_treino_auto(pares, treino, cfg["incluir_mesma_loja"])
    destino = diretorio_processados / ARQUIVO_PARES_TREINO_AUTO_PXP
    pares.to_parquet(destino, index=False)
    logger.info(
        "Pares de treino automáticos (%d) gravados em %s:\n%s",
        len(pares),
        destino,
        pares["origem"].value_counts().to_string(),
    )
    return pares


# ── Montagem do treino produto × produto (parte A + anotação B2 + TAIL; ADR-0015) ───────────

ORIGEM_B2_AUTOR = "autor_b2"
ORIGENS_TAIL_POSITIVAS = ("tail_variante", "tail_nf")
ORIGENS_TAIL = (*ORIGENS_TAIL_POSITIVAS, "tail_negativo")
ORIGENS_TREINO_PXP = (ORIGEM_NEGATIVO_TAMANHO, *ORIGENS_POSITIVAS, ORIGEM_B2_AUTOR, *ORIGENS_TAIL)
_PREFIXO_TAIL = "tail_"
ARQUIVO_TREINO_PXP = "treino_pxp.parquet"
ARQUIVO_PARES_TAIL_PXP = "pares_tail_pxp.parquet"
ARQUIVO_RESUMO_TREINO_PXP = "treino_pxp_resumo.csv"
_ORIGENS_DA_PARTE_A = (ORIGEM_NEGATIVO_TAMANHO, *ORIGENS_POSITIVAS)


def ingerir_anotacao_b2(
    planilha: pd.DataFrame, pares_b2: pd.DataFrame, produtos_treino: pd.DataFrame
) -> pd.DataFrame:
    """Transforma a anotação do autor na planilha do B2 em pares de treino (`origem = autor_b2`).

    Só `match` e `nao_match` entram: `incerto` e o que ainda está pendente ficam de fora. Como a
    planilha foi embaralhada com seed, qualquer subconjunto anotado é uma amostra sem viés de
    estrato, então a anotação parcial já serve. Valida a forma (rótulo fora do domínio, linha
    apagada ou par fora do B2 levantam `ValueError` com os ids) e usa o texto e a unidade do
    treino, nunca os da planilha. Planilha sem anotação devolve um quadro vazio com as colunas.
    """
    validar_anotacao_b2(planilha, pares_b2)
    rotulo = planilha["rotulo"].map(_entrada)
    anotada = planilha.loc[rotulo.isin(["match", "nao_match"]), ["id_a", "id_b"]].assign(
        rotulo=rotulo[rotulo.isin(["match", "nao_match"])]
    )
    if anotada.empty:
        return pd.DataFrame(columns=COLUNAS_PARES_TREINO_PXP)
    fora = sorted(
        (set(anotada["id_a"]) | set(anotada["id_b"])) - set(produtos_treino["id_produto"])
    )
    if fora:
        raise ValueError(f"pares do B2 com produtos fora do treino: {fora[:10]}")
    pares = pd.DataFrame(
        {
            "id_a": [min(a, b) for a, b in zip(anotada["id_a"], anotada["id_b"], strict=True)],
            "id_b": [max(a, b) for a, b in zip(anotada["id_a"], anotada["id_b"], strict=True)],
            "rotulo": anotada["rotulo"].to_numpy(),
        }
    )
    base = _dados_do_produto(produtos_treino)
    for lado in ("a", "b"):
        for coluna in ("descricao", "und_val", "und_med"):
            pares[f"{coluna}_{lado}"] = pares[f"id_{lado}"].map(base[coluna])
    pares["id_par"] = [
        _hash_curto(f"{a}|{b}") for a, b in zip(pares["id_a"], pares["id_b"], strict=True)
    ]
    pares["tipo_par"] = "produto_produto"
    pares["origem"] = ORIGEM_B2_AUTOR
    return pares[COLUNAS_PARES_TREINO_PXP].sort_values(["id_a", "id_b"]).reset_index(drop=True)


def montar_treino_pxp(
    produtos_treino: pd.DataFrame,
    auto: pd.DataFrame,
    b2: pd.DataFrame | None = None,
    tail: pd.DataFrame | None = None,
    mesma_loja_permitida: bool = False,
) -> pd.DataFrame:
    """Junta a parte A, a anotação B2 e a TAIL (as duas últimas opcionais) e verifica o conjunto.

    A ordem é determinística (por origem e `id_par`) e não depende da ordem das linhas de cada
    fonte. `mesma_loja_permitida` vem da config da parte A.
    """
    fontes = [f for f in (auto, b2, tail) if f is not None and not f.empty]
    treino = (
        pd.concat(fontes, ignore_index=True)
        .sort_values(["origem", "id_par"])
        .reset_index(drop=True)
    )
    verificar_treino_pxp(treino, produtos_treino, mesma_loja_permitida)
    return treino


def verificar_treino_pxp(
    treino: pd.DataFrame, produtos_treino: pd.DataFrame, mesma_loja_permitida: bool = False
) -> None:
    """Barreira crítica da montagem, `AssertionError` explícito (vale com `python -O`).

    Valida as colunas (sem coluna da ALTA), `id_par` único entre fontes, origem conhecida, rótulo
    só `match` ou `nao_match` e coerente com a origem; a parte A com `verificar_pares_treino_auto`;
    a B2 com ids reais do treino, lojas diferentes, texto do treino e o mesmo tamanho nos dois
    lados; e a TAIL com ids `tail_...` que nunca são de produto real e positivos que preservam o
    tamanho.
    """
    if list(treino.columns) != COLUNAS_PARES_TREINO_PXP:
        extras = sorted(set(treino.columns) - set(COLUNAS_PARES_TREINO_PXP))
        raise AssertionError(f"colunas fora do contrato do treino; sobram {extras}")
    repetidos = sorted(set(treino.loc[treino["id_par"].duplicated(), "id_par"]))
    if repetidos:
        raise AssertionError(f"id_par duplicado no treino: {repetidos[:10]}")
    desconhecidas = sorted(set(treino["origem"]) - set(ORIGENS_TREINO_PXP))
    if desconhecidas:
        raise AssertionError(f"origem desconhecida no treino: {desconhecidas}")
    invalidos = sorted(set(treino["rotulo"]) - {"match", "nao_match"})
    if invalidos:
        raise AssertionError(f"rotulo fora do domínio (match, nao_match) no treino: {invalidos}")
    deve_ser_match = treino["origem"].isin((*ORIGENS_POSITIVAS, *ORIGENS_TAIL_POSITIVAS))
    deve_ser_nao_match = treino["origem"].isin((ORIGEM_NEGATIVO_TAMANHO, "tail_negativo"))
    incoerentes = treino[
        (deve_ser_match & (treino["rotulo"] != "match"))
        | (deve_ser_nao_match & (treino["rotulo"] != "nao_match"))
    ]
    if len(incoerentes):
        raise AssertionError(
            f"rotulo incoerente com a origem em: {sorted(incoerentes['id_par'])[:10]}"
        )

    parte_a = treino[treino["origem"].isin(_ORIGENS_DA_PARTE_A)]
    if len(parte_a):
        verificar_pares_treino_auto(parte_a, produtos_treino, mesma_loja_permitida)

    ids = set(produtos_treino["id_produto"])
    loja = produtos_treino.set_index("id_produto")["loja"]
    texto = produtos_treino.set_index("id_produto")["descricao"]
    b2 = treino[treino["origem"] == ORIGEM_B2_AUTOR]
    fora = sorted((set(b2["id_a"]) | set(b2["id_b"])) - ids)
    if fora:
        raise AssertionError(f"B2 com ids fora dos produtos de treino: {fora[:10]}")
    for linha in b2.itertuples(index=False):
        tamanho_a, tamanho_b = (
            tokens_numericos(linha.descricao_a),
            tokens_numericos(linha.descricao_b),
        )
        if not (tamanho_a and tamanho_a == tamanho_b):
            raise AssertionError(f"B2 com tamanho diferente ou ausente: {linha.id_par}")
        if loja[linha.id_a] == loja[linha.id_b]:
            raise AssertionError(f"B2 entre produtos da mesma loja: {linha.id_par}")
        if texto[linha.id_a] != linha.descricao_a or texto[linha.id_b] != linha.descricao_b:
            raise AssertionError(f"texto do B2 diferente do treino: {linha.id_par}")

    for linha in treino[treino["origem"].isin(ORIGENS_TAIL)].itertuples(index=False):
        if (
            not (linha.id_a.startswith(_PREFIXO_TAIL) and linha.id_b.startswith(_PREFIXO_TAIL))
            or linha.id_a in ids
            or linha.id_b in ids
        ):
            raise AssertionError(
                f"par da TAIL com id sem prefixo tail_ ou igual a produto real: {linha.id_par}"
            )
        if linha.origem in ORIGENS_TAIL_POSITIVAS:
            if tokens_numericos(linha.descricao_a) != tokens_numericos(linha.descricao_b):
                raise AssertionError(
                    f"positivo da TAIL muda o conjunto de tamanhos: {linha.id_par}"
                )
            if linha.descricao_a == linha.descricao_b:
                raise AssertionError(f"positivo da TAIL idêntico ao original: {linha.id_par}")


def gerar_treino_pxp(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    diretorio_metricas: Path = RESULTADOS_METRICAS,
    caminho_config_treino: Path = CONFIG_PARES_TREINO_PXP,
) -> pd.DataFrame:
    """Grava `treino_pxp.parquet`: parte A + a anotação B2 que já existir + a TAIL, se houver.

    A parte A (`pares_treino_auto_pxp.parquet`) é obrigatória. A B2 entra com o que o autor já
    anotou em `anotacoes_treino_b2_pxp.csv` (só leitura: nunca escreve na planilha). A TAIL entra
    de `pares_tail_pxp.parquet`, quando o P5 o entregar. Tudo é calculado e verificado antes de
    gravar; se algo falha, nada é escrito. Regenerável; o resumo por origem e rótulo vai para
    `resultados/metricas/treino_pxp_resumo.csv`.
    """
    cfg = carregar_config_treino_pxp(caminho_config_treino)
    arquivo_treino = diretorio_processados / "produtos_treino_pxp.parquet"
    arquivo_auto = diretorio_processados / ARQUIVO_PARES_TREINO_AUTO_PXP
    for arquivo in (arquivo_treino, arquivo_auto):
        if not arquivo.exists():
            raise FileNotFoundError(
                f"{arquivo} não existe: gere os pares automáticos antes do treino"
            )
    produtos_treino = pd.read_parquet(arquivo_treino)
    auto = pd.read_parquet(arquivo_auto)

    planilha_b2 = diretorio_processados / ARQUIVO_PLANILHA_B2_PXP
    pares_b2 = diretorio_processados / ARQUIVO_PARES_B2_PXP
    b2 = None
    if planilha_b2.exists():
        if not pares_b2.exists():
            raise ValueError(
                f"{planilha_b2} existe sem {pares_b2.name}: pares do B2 não congelados"
            )
        planilha = pd.read_csv(planilha_b2, sep=";", dtype=str, keep_default_na=False)
        b2 = ingerir_anotacao_b2(
            planilha,
            pd.read_csv(pares_b2, dtype={"id_a": str, "id_b": str}),
            produtos_treino,
        )
        rotulos = planilha["rotulo"].map(_entrada)
        logger.info(
            "B2: %d de %d pares anotados entram no treino (%d incerto, %d pendentes).",
            len(b2),
            len(planilha),
            int((rotulos == INCERTO).sum()),
            int((rotulos == "").sum()),
        )
    else:
        logger.info("Planilha do B2 ainda não existe: o treino não tem a fonte autor_b2.")
    arquivo_tail = diretorio_processados / ARQUIVO_PARES_TAIL_PXP
    tail = pd.read_parquet(arquivo_tail) if arquivo_tail.exists() else None
    if tail is None:
        logger.info("%s ainda não existe: o treino não tem a fonte TAIL.", ARQUIVO_PARES_TAIL_PXP)

    treino = montar_treino_pxp(produtos_treino, auto, b2, tail, cfg["incluir_mesma_loja"])
    resumo = treino.groupby(["origem", "rotulo"]).size().reset_index(name="n_pares")
    diretorio_processados.mkdir(parents=True, exist_ok=True)
    diretorio_metricas.mkdir(parents=True, exist_ok=True)
    treino.to_parquet(diretorio_processados / ARQUIVO_TREINO_PXP, index=False)
    resumo.to_csv(diretorio_metricas / ARQUIVO_RESUMO_TREINO_PXP, index=False)
    logger.info(
        "Treino p×p (%d pares) gravado em %s:\n%s",
        len(treino),
        diretorio_processados / ARQUIVO_TREINO_PXP,
        resumo.to_string(index=False),
    )
    return treino


def particionar_por_produto_canonico() -> None:
    """Particiona treino/validação/teste por produto canônico, antes de qualquer geração.

    Pendente e só para a fatia secundária (produto × dicionário, RF6). A partição da fatia
    principal (produto × produto) está pronta: `gerar_conjuntos_pxp`, por componente conexo.

    [CRÍTICO] validar com assert que nenhum produto do teste aparece no treino.
    """
    raise NotImplementedError(
        "Implementar conforme specs/001-construcao-dataset-ground-truth/requirements.md"
    )


# ── Adjudicação dos `incerto` do teste (protocolo §3.5; decisão do autor em 2026-11-16) ──────
#
# Os pares `incerto` da primeira passada vão para uma planilha SEPARADA, com o mesmo contrato de
# 15 colunas da planilha do teste (o anotador HTML abre sem mudança). A primeira passada nunca é
# alterada: o reteste e o Kappa comparam contra o que o autor marcou de fato. A fonte de cada
# decisão vai no prefixo da observação; quem continuar `incerto` fica fora do teste final.

ARQUIVO_PLANILHA_ADJUDICACAO_PXP = "anotacoes_teste_pxp_adjudicacao.csv"
ORIGEM_ADJUDICACAO = "teste_adjudicacao"
# `autor:` é um desvio do protocolo §3.5 (que prevê só dicionário ou pesquisadores do ALTA): o
# autor decidiu alguns `incerto` pelo próprio julgamento (2026-11-16). Fica registrado como fonte
# própria para o teste poder ser reportado com e sem esses pares (ADR-0018, rascunho).
PREFIXOS_FONTE_ADJUDICACAO = ("dicionario:", "alta:", "autor:")
_FONTE_POR_PREFIXO = {
    "dicionario:": "dicionario",
    "alta:": "alta",
    "autor:": "autor_adjudicacao",
}
FONTE_PRIMEIRA_PASSADA = "autor_primeira_passada"


def _exigir_primeira_passada_completa(primeira: pd.DataFrame) -> pd.Series:
    rotulo = primeira["rotulo"].map(_entrada)
    vazios = sorted(primeira.loc[rotulo == "", "id_par"])
    if vazios:
        raise ValueError(
            f"{len(vazios)} pares sem rotulo na primeira passada, por exemplo: {vazios[:10]}"
        )
    return rotulo


def montar_planilha_adjudicacao_pxp(primeira: pd.DataFrame) -> pd.DataFrame:
    """Planilha com só os pares `incerto` da primeira passada, na ordem dela, sem decisão.

    Mesmo contrato de colunas da planilha do teste; `rotulo`, `observacao`, `timestamp_anotacao`
    e `reteste` saem vazios e `origem` vira `teste_adjudicacao`. Não altera `primeira`. Falha se a
    primeira passada estiver incompleta (nomeando os pares) ou se não houver nenhum `incerto`.
    """
    rotulo = _exigir_primeira_passada_completa(primeira)
    incertos = primeira[rotulo == _ROTULO_INCERTO]
    if incertos.empty:
        raise ValueError("nenhum par `incerto` na primeira passada: nada a adjudicar")
    planilha = incertos.assign(
        origem=ORIGEM_ADJUDICACAO, rotulo="", observacao="", timestamp_anotacao="", reteste=""
    )[COLUNAS_PLANILHA_TESTE_PXP]
    assert not set(_PROIBIDAS_NA_PLANILHA_TESTE) & set(planilha.columns), "ADR-0011 violado"
    return planilha.reset_index(drop=True)


def _fonte_da_decisao(observacao: object) -> str | None:
    """Fonte (`dicionario`, `alta` ou `autor_adjudicacao`) se a observação tem o prefixo e texto.

    Devolve None se não começa por um dos prefixos (sensível a maiúscula) ou se não há texto
    depois dele.
    """
    texto = _entrada(observacao)
    for prefixo in PREFIXOS_FONTE_ADJUDICACAO:
        if texto.startswith(prefixo) and texto[len(prefixo) :].strip():
            return _FONTE_POR_PREFIXO[prefixo]
    return None


def validar_adjudicacao_pxp(
    adjudicacao: pd.DataFrame, primeira: pd.DataFrame, completa: bool = False
) -> None:
    """Valida a forma da planilha de adjudicação; nunca o mérito da decisão.

    Falha, nomeando os ids, se faltar coluna, houver coluna proibida, `id_par` repetido, rótulo
    fora de {match, nao_match, incerto}, par que não era `incerto` na primeira passada, par
    `incerto` apagado, ou decisão (`match`/`nao_match`) sem fonte válida no prefixo da observação.
    Rótulo vazio é "ainda não decidido" e só é erro com `completa=True`; `incerto` mantido não
    exige fonte (continua fora do teste final).
    """
    faltando = [c for c in COLUNAS_PLANILHA_TESTE_PXP if c not in adjudicacao.columns]
    if faltando:
        raise ValueError(f"colunas ausentes na planilha de adjudicação: {faltando}")
    proibidas = [c for c in _PROIBIDAS_NA_PLANILHA_TESTE if c in adjudicacao.columns]
    if proibidas:
        raise ValueError(f"colunas proibidas na planilha de adjudicação: {proibidas}")
    repetidos = sorted(set(adjudicacao.loc[adjudicacao["id_par"].duplicated(), "id_par"]))
    if repetidos:
        raise ValueError(f"id_par duplicado na planilha de adjudicação: {repetidos}")

    rotulo = adjudicacao["rotulo"].map(_entrada)
    invalidos = sorted(adjudicacao.loc[~rotulo.isin(["", *ROTULOS_TESTE]), "id_par"])
    if invalidos:
        raise ValueError(f"rotulo fora do domínio {ROTULOS_TESTE} em: {invalidos}")

    incertos = set(primeira.loc[primeira["rotulo"].map(_entrada) == _ROTULO_INCERTO, "id_par"])
    intrusos = sorted(set(adjudicacao["id_par"]) - incertos)
    if intrusos:
        raise ValueError(f"pares que não eram incerto na primeira passada: {intrusos}")
    apagados = sorted(incertos - set(adjudicacao["id_par"]))
    if apagados:
        raise ValueError(f"faltam pares incerto na planilha de adjudicação: {apagados}")
    if completa:
        vazios = sorted(adjudicacao.loc[rotulo == "", "id_par"])
        if vazios:
            raise ValueError(f"{len(vazios)} pares sem rotulo na adjudicação: {vazios[:10]}")

    decidido = rotulo.isin(["match", "nao_match"])
    sem_fonte = sorted(
        adjudicacao.loc[
            decidido & adjudicacao["observacao"].map(_fonte_da_decisao).isna(), "id_par"
        ]
    )
    if sem_fonte:
        raise ValueError(
            "decisão sem fonte válida (a observação deve começar por 'dicionario:', 'alta:' "
            f"ou 'autor:' e trazer o texto da consulta ou do raciocínio): {sem_fonte}"
        )


def compor_rotulos_finais_teste_pxp(
    primeira: pd.DataFrame, adjudicacao: pd.DataFrame
) -> pd.DataFrame:
    """Rótulo final de cada par do teste: primeira passada, ou a adjudicação para os `incerto`.

    Pares `match`/`nao_match` da primeira passada mantêm o rótulo (`fonte_rotulo =
    autor_primeira_passada`); os `incerto` resolvidos recebem o da adjudicação (`dicionario` ou
    `alta`); os que continuam `incerto` ficam **fora** (não entram no teste final). O reteste não
    participa. Exige primeira passada e adjudicação completas. Não altera as entradas.
    """
    rotulo = _exigir_primeira_passada_completa(primeira)
    validar_adjudicacao_pxp(adjudicacao, primeira, completa=True)
    decisao = adjudicacao.set_index("id_par")
    base = primeira[["id_par", "id_a", "id_b"]].assign(rotulo=rotulo.to_numpy())
    final: list[str] = []
    fonte: list[str | None] = []
    for linha in base.itertuples(index=False):
        if linha.rotulo != _ROTULO_INCERTO:
            final.append(linha.rotulo)
            fonte.append(FONTE_PRIMEIRA_PASSADA)
            continue
        adj = _entrada(decisao.loc[linha.id_par, "rotulo"])
        final.append(adj)
        fonte.append(
            _fonte_da_decisao(decisao.loc[linha.id_par, "observacao"]) if adj != "incerto" else None
        )
    base = base.assign(rotulo_final=final, fonte_rotulo=fonte)
    resolvidos = base[base["rotulo_final"].isin(["match", "nao_match"])]
    return resolvidos[["id_par", "id_a", "id_b", "rotulo_final", "fonte_rotulo"]].reset_index(
        drop=True
    )


def gerar_planilha_adjudicacao_pxp(diretorio_processados: Path = DADOS_PROCESSADOS) -> Path:
    """Gera `anotacoes_teste_pxp_adjudicacao.csv` a partir da primeira passada, uma única vez.

    Nunca altera `anotacoes_teste_pxp.csv` e nunca reescreve a planilha de adjudicação: se ela já
    existe, lê como o autor a deixou, valida a forma (decisão sem fonte, par apagado ou rótulo
    inválido levantam `ValueError`) e registra quantos pares já foram decididos.
    """
    primeira = _ler_planilha_teste(
        diretorio_processados,
        ARQUIVO_PLANILHA_TESTE_PXP,
        "gere e anote o teste (primeira passada) antes de adjudicar",
    )
    destino = diretorio_processados / ARQUIVO_PLANILHA_ADJUDICACAO_PXP
    if destino.exists():
        adjudicacao = pd.read_csv(destino, sep=";", dtype=str, keep_default_na=False)
        validar_adjudicacao_pxp(adjudicacao, primeira)
        rotulo = adjudicacao["rotulo"].map(_entrada)
        logger.info(
            "Planilha de adjudicação já existe (%s): %d decididos (match ou nao_match), "
            "%d mantidos incerto, %d pendentes; não reescrita.",
            destino,
            int(rotulo.isin(["match", "nao_match"]).sum()),
            int((rotulo == _ROTULO_INCERTO).sum()),
            int((rotulo == "").sum()),
        )
        return destino
    planilha = montar_planilha_adjudicacao_pxp(primeira)
    validar_adjudicacao_pxp(planilha, primeira)
    caminho = gravar_planilha_teste_pxp(
        planilha, diretorio_processados, ARQUIVO_PLANILHA_ADJUDICACAO_PXP
    )
    logger.info("Planilha de adjudicação (%d pares incerto) gravada em %s.", len(planilha), caminho)
    return caminho


# ── teste_pxp.parquet: o teste final (primeira passada + adjudicação; ADR-0018) ──────────────

ARQUIVO_TESTE_PXP = "teste_pxp.parquet"
ARQUIVO_RESUMO_TESTE_PXP = "teste_pxp_resumo.csv"
ARQUIVO_COMPONENTES_PXP = "componentes_pxp.parquet"
COLUNAS_TESTE_PXP = [
    "id_par",
    "id_a",
    "descricao_a",
    "und_val_a",
    "und_med_a",
    "id_b",
    "descricao_b",
    "und_val_b",
    "und_med_b",
    "tipo_par",
    "origem",
    "rotulo",
    "fonte_rotulo",
    "estrato",
    "prob_inclusao",
]
FONTES_ROTULO_TESTE = (FONTE_PRIMEIRA_PASSADA, "dicionario", "alta", "autor_adjudicacao")


def montar_teste_pxp(
    primeira: pd.DataFrame,
    adjudicacao: pd.DataFrame,
    pares_teste: pd.DataFrame,
    universo: pd.DataFrame,
) -> pd.DataFrame:
    """Teste final: rótulos de `compor_rotulos_finais_teste_pxp` + texto do universo + sorteio.

    O texto e a unidade vêm do UNIVERSO, nunca da planilha. `estrato` e `prob_inclusao` vêm de
    `pares_teste` (`pares_teste_pxp.csv`) e servem para ponderar o teste estratificado (spec 004).
    Os `incerto` não resolvidos ficam fora. Ordenado por `id_par`. Falha com `ValueError` se a
    adjudicação estiver incompleta, se algum par da planilha não tiver estrato no sorteio ou se
    algum produto não estiver no universo. Não altera as entradas.
    """
    final = compor_rotulos_finais_teste_pxp(primeira, adjudicacao)
    sorteio = pares_teste.assign(id_par=_ids_de_pares(pares_teste)).set_index("id_par")
    sem_estrato = sorted(set(primeira["id_par"]) - set(sorteio.index))
    if sem_estrato:
        raise ValueError(f"pares do teste sem estrato em pares_teste: {sem_estrato[:10]}")
    ids = set(primeira["id_a"]) | set(primeira["id_b"])
    fora = sorted(ids - set(universo["id_produto"]))
    if fora:
        raise ValueError(f"produtos do teste fora do universo: {fora[:10]}")
    base = universo.set_index("id_produto")[["descricao", "und_val", "und_med"]]
    teste = final[["id_par", "id_a", "id_b"]].copy()
    for lado in ("a", "b"):
        for coluna in ("descricao", "und_val", "und_med"):
            teste[f"{coluna}_{lado}"] = teste[f"id_{lado}"].map(base[coluna])
    teste["tipo_par"] = "produto_produto"
    teste["origem"] = "teste"
    teste["rotulo"] = final["rotulo_final"].to_numpy()
    teste["fonte_rotulo"] = final["fonte_rotulo"].to_numpy()
    teste["estrato"] = teste["id_par"].map(sorteio["estrato"])
    teste["prob_inclusao"] = teste["id_par"].map(sorteio["prob_inclusao"]).astype(float)
    return teste[COLUNAS_TESTE_PXP].sort_values("id_par").reset_index(drop=True)


def verificar_teste_pxp(
    teste: pd.DataFrame, universo: pd.DataFrame, componentes: pd.DataFrame
) -> None:
    """Barreira crítica do teste final, `AssertionError` explícito (vale com `python -O`).

    Sem coluna do matcher ALTA (ADR-0011); colunas do contrato; `id_par` único; rótulo só `match`
    ou `nao_match`; fonte conhecida; cada produto em no máximo um par; texto igual ao do universo;
    `prob_inclusao` em (0, 1]; e todo produto na partição de teste (ADR-0004).
    """
    proibidas = sorted(set(COLUNAS_MATCHER_ALTA) & set(teste.columns))
    if proibidas:
        raise AssertionError(f"ADR-0011 violado: colunas do matcher ALTA no teste: {proibidas}")
    if list(teste.columns) != COLUNAS_TESTE_PXP:
        extras = sorted(set(teste.columns) - set(COLUNAS_TESTE_PXP))
        raise AssertionError(f"colunas fora do contrato do teste; sobram {extras}")
    repetidos = sorted(set(teste.loc[teste["id_par"].duplicated(), "id_par"]))
    if repetidos:
        raise AssertionError(f"id_par duplicado no teste: {repetidos[:10]}")
    invalidos = sorted(set(teste["rotulo"]) - {"match", "nao_match"})
    if invalidos:
        raise AssertionError(f"rotulo fora do domínio (match, nao_match) no teste: {invalidos}")
    desconhecidas = sorted(set(teste["fonte_rotulo"]) - set(FONTES_ROTULO_TESTE))
    if desconhecidas:
        raise AssertionError(f"fonte_rotulo desconhecida no teste: {desconhecidas}")
    contagem = Counter([*teste["id_a"], *teste["id_b"]])
    em_varios = sorted(i for i, n in contagem.items() if n > 1)
    if em_varios:
        raise AssertionError(f"produto em mais de um par do teste: {em_varios[:10]}")
    texto = universo.set_index("id_produto")["descricao"]
    for linha in teste.itertuples(index=False):
        if texto.get(linha.id_a) != linha.descricao_a or texto.get(linha.id_b) != linha.descricao_b:
            raise AssertionError(f"texto do teste diferente do universo: {linha.id_par}")
    prob = teste["prob_inclusao"]
    if prob.isna().any() or ((prob <= 0) | (prob > 1)).any():
        raise AssertionError("prob_inclusao fora de (0, 1] ou ausente no teste")
    if teste["estrato"].map(_entrada).eq("").any():
        raise AssertionError("estrato ausente em pares do teste")
    particao = componentes.set_index("id_produto")["particao"]
    for produto in sorted(contagem):
        if particao.get(produto) != "teste":
            raise AssertionError(
                f"produto do teste fora da partição de teste (ADR-0004): {produto} "
                f"({particao.get(produto)!r})"
            )


def resumir_teste_pxp(teste: pd.DataFrame, pares_teste: pd.DataFrame) -> pd.DataFrame:
    """Por estrato: sorteados, `incerto` excluídos, finais, `match`, `nao_match` e adjudicados.

    As exclusões mudam as contagens por estrato e a ponderação por `prob_inclusao` precisa delas.
    """
    sorteados = pares_teste["estrato"].value_counts()
    final = teste["estrato"].value_counts()
    linhas = []
    for estrato in sorted(sorteados.index):
        do_estrato = teste[teste["estrato"] == estrato]
        linhas.append(
            {
                "estrato": estrato,
                "n_sorteados": int(sorteados[estrato]),
                "n_incerto_excluido": int(sorteados[estrato] - final.get(estrato, 0)),
                "n_final": len(do_estrato),
                "n_match": int((do_estrato["rotulo"] == "match").sum()),
                "n_nao_match": int((do_estrato["rotulo"] == "nao_match").sum()),
                "n_autor_adjudicacao": int(
                    (do_estrato["fonte_rotulo"] == "autor_adjudicacao").sum()
                ),
            }
        )
    return pd.DataFrame(linhas)


def gerar_teste_pxp(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    diretorio_metricas: Path = RESULTADOS_METRICAS,
) -> pd.DataFrame:
    """Grava `teste_pxp.parquet` e `teste_pxp_resumo.csv` a partir das duas planilhas do autor.

    Lê a primeira passada e a adjudicação (nunca as altera), o sorteio, o universo e a partição.
    Tudo ou nada: nada é gravado se qualquer verificação falhar. Regenerável e determinístico.
    """
    primeira = _ler_planilha_teste(
        diretorio_processados, ARQUIVO_PLANILHA_TESTE_PXP, "primeira passada ausente"
    )
    adjudicacao = _ler_planilha_teste(
        diretorio_processados,
        ARQUIVO_PLANILHA_ADJUDICACAO_PXP,
        "gere e preencha a adjudicação (--adjudicacao) antes de compor o teste",
    )
    arquivo_componentes = diretorio_processados / ARQUIVO_COMPONENTES_PXP
    if not arquivo_componentes.exists():
        raise FileNotFoundError(f"{arquivo_componentes} não existe: gere a partição antes")
    pares_teste = pd.read_csv(diretorio_processados / "pares_teste_pxp.csv", dtype=str)
    pares_teste["prob_inclusao"] = pares_teste["prob_inclusao"].astype(float)
    produtos = pd.read_parquet(diretorio_processados / "produtos_limpos.parquet")
    universo = deduplicar_por_texto_e_loja(produtos)
    componentes = pd.read_parquet(arquivo_componentes)

    teste = montar_teste_pxp(primeira, adjudicacao, pares_teste, universo)
    verificar_teste_pxp(teste, universo, componentes)
    resumo = resumir_teste_pxp(teste, pares_teste)

    diretorio_processados.mkdir(parents=True, exist_ok=True)
    diretorio_metricas.mkdir(parents=True, exist_ok=True)
    teste.to_parquet(diretorio_processados / ARQUIVO_TESTE_PXP, index=False)
    resumo.to_csv(diretorio_metricas / ARQUIVO_RESUMO_TESTE_PXP, index=False)
    logger.info(
        "Teste final (%d pares) gravado em %s:\n%s",
        len(teste),
        diretorio_processados / ARQUIVO_TESTE_PXP,
        resumo.to_string(index=False),
    )
    return teste


# ── Pares da TAIL para o treino produto × produto, bloco P5a (ADR-0013; ADR-0015; RF8) ────────
#
# Só uso LOCAL (a autorização escrita da TAIL não existe, ADR-0013): nada daqui é versionado. As
# decisões D1 a D6 do autor (2026-11-16) estão em `configs/pares_tail_pxp.yaml`. Este bloco lê as
# fontes (conferidas por SHA-256), monta os positivos e aplica os filtros e as barreiras de dados;
# os negativos e a orquestração são o bloco P5b.

ARQUIVOS_TAIL = (
    "old_attack_dataset.csv",
    "attack.csv",
    "itens_nf_normalizados.csv",
    "octaprice_mercadolivre_1.json",
    "octaprice_mercadolivre_2.json",
    "pairs_to_label.csv",
)
MANIFEST_TAIL = "MANIFEST.sha256"
COLUNAS_PARES_TAIL = ["titulo_a", "titulo_b", "fonte", "tipo_variacao"]
_FALLBACK_LLM = "Fallback_Erro_LLM"
_COLUNAS_FONTES_TAIL = {
    "old_attack_dataset.csv": ["original", "attacked"],
    "attack.csv": ["id", "original", "tipo_variacao", "attacked"],
    "itens_nf_normalizados.csv": ["title", "normalized"],
    "pairs_to_label.csv": ["title_a", "title_b", "candidate_label", "similarity_score", "label"],
}


class ConfigTailPxp(TypedDict):
    seed: int
    incluir_sem_tamanho: bool
    limiar_quase_duplicata: float
    max_pares_por_grupo_nf: int
    razao_negativos: float
    k: int
    faixas_cosseno: list[float]
    peso_negativos_por_faixa: dict[str, float]
    teto_negativos_por_produto: int


def carregar_config_tail_pxp(caminho: Path) -> ConfigTailPxp:
    """Lê `configs/pares_tail_pxp.yaml` e valida as decisões D1 a D6 do autor.

    `incluir_sem_tamanho` deve ser booleano (D1); `limiar_quase_duplicata` em (0, 1] (D2); o teto de
    pares por grupo de nota fiscal ≥ 1 (D4); a razão de negativos > 0 (D5); os pesos por faixa de
    cosseno devem cobrir exatamente as faixas, sem peso negativo e com soma positiva.
    """
    cfg: dict[str, Any] = yaml.safe_load(caminho.read_text(encoding="utf-8"))

    def falhar(chave: str, motivo: str) -> ValueError:
        return ValueError(f"{chave} inválido em {caminho}: {motivo} (valor: {cfg.get(chave)!r})")

    if not isinstance(cfg.get("incluir_sem_tamanho"), bool):
        raise falhar("incluir_sem_tamanho", "esperado true ou false")
    limiar = cfg.get("limiar_quase_duplicata")
    if isinstance(limiar, bool) or not isinstance(limiar, int | float) or not 0 < limiar <= 1:
        raise falhar("limiar_quase_duplicata", "esperado número em (0, 1]")
    teto = cfg.get("max_pares_por_grupo_nf")
    if isinstance(teto, bool) or not isinstance(teto, int) or teto < 1:
        raise falhar("max_pares_por_grupo_nf", "esperado inteiro ≥ 1")
    razao = cfg.get("razao_negativos")
    if isinstance(razao, bool) or not isinstance(razao, int | float) or razao <= 0:
        raise falhar("razao_negativos", "esperado número > 0")
    k = cfg.get("k")
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise falhar("k", "esperado inteiro ≥ 1")
    teto_neg = cfg.get("teto_negativos_por_produto")
    if isinstance(teto_neg, bool) or not isinstance(teto_neg, int) or teto_neg < 1:
        raise falhar("teto_negativos_por_produto", "esperado inteiro ≥ 1")
    faixas = [float(f) for f in cfg["faixas_cosseno"]]
    _validar_faixas(faixas)
    pesos = cfg.get("peso_negativos_por_faixa")
    esperados = set(_rotulos_das_faixas(faixas))
    if not isinstance(pesos, dict) or set(pesos) != esperados:
        raise falhar(
            "peso_negativos_por_faixa", f"as chaves devem ser exatamente {sorted(esperados)}"
        )
    if any(isinstance(v, bool) or not isinstance(v, int | float) or v < 0 for v in pesos.values()):
        raise falhar("peso_negativos_por_faixa", "pesos devem ser números ≥ 0")
    if sum(pesos.values()) <= 0:
        raise falhar("peso_negativos_por_faixa", "a soma dos pesos deve ser positiva")
    return ConfigTailPxp(
        seed=int(cfg["seed"]),
        incluir_sem_tamanho=cfg["incluir_sem_tamanho"],
        limiar_quase_duplicata=float(limiar),
        max_pares_por_grupo_nf=teto,
        razao_negativos=float(razao),
        k=k,
        faixas_cosseno=faixas,
        peso_negativos_por_faixa={r: float(v) for r, v in pesos.items()},
        teto_negativos_por_produto=teto_neg,
    )


def titulo_do_slug(url: str) -> str:
    """Título de um anúncio do Mercado Livre a partir do slug da URL (o octaprice só traz a URL).

    Cobre os formatos medidos em 18.084 URLs: `produto.mercadolivre.com.br/MLB-<id>-<slug>-_JM`
    (10.279), `www.mercadolivre.com.br/<slug>/p/MLB<id>` (7.804) e `<slug>/up/MLBU<id>` (1).
    Ignora query e fragmento. Formato desconhecido levanta `ValueError` nomeando a url.
    """
    partes = urlsplit(url)
    slug = None
    if partes.netloc.endswith("mercadolivre.com.br"):
        casou = re.fullmatch(r"/MLB-\d+-(.+?)-?_JM", partes.path) or re.fullmatch(
            r"/([^/]+)/(?:p/MLB|up/MLBU)\d+", partes.path
        )
        slug = casou.group(1) if casou else None
    titulo = " ".join(slug.replace("-", " ").split()) if slug else ""
    if not titulo:
        raise ValueError(f"url de anúncio em formato desconhecido: {url!r}")
    return titulo


def normalizar_titulo_tail(texto: object) -> str:
    """Minúsculas, sem acento nem pontuação e com espaço único (compara títulos entre fontes)."""
    bruto = "" if texto is None or pd.isna(texto) else str(texto)
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", bruto) if not unicodedata.combining(c)
    )
    return " ".join(re.sub(r"[^a-z0-9]+", " ", sem_acento.casefold()).split())


def _verificar_manifest_tail(diretorio: Path) -> None:
    if not diretorio.is_dir():
        raise FileNotFoundError(
            f"diretório da TAIL não existe: {diretorio} (copie os artefatos do clone para "
            "dados/brutos/tail e gere o MANIFEST.sha256)"
        )
    manifest = diretorio / MANIFEST_TAIL
    if not manifest.exists():
        raise FileNotFoundError(f"{manifest} não existe: sem o MANIFEST.sha256 não há conferência")
    esperados: dict[str, str] = {}
    for linha in manifest.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            soma, nome = linha.split(maxsplit=1)
            esperados[nome.strip().lstrip("*")] = soma
    for nome in ARQUIVOS_TAIL:
        if not (diretorio / nome).exists():
            raise FileNotFoundError(f"{diretorio / nome} não existe (listado no {MANIFEST_TAIL})")
        if nome not in esperados:
            raise ValueError(f"{nome} não consta no {MANIFEST_TAIL} de {diretorio}")
        if hashlib.sha256((diretorio / nome).read_bytes()).hexdigest() != esperados[nome]:
            raise ValueError(f"SHA-256 de {nome} difere do {MANIFEST_TAIL}: arquivo alterado")


def ler_fontes_tail(diretorio_tail: Path = DADOS_BRUTOS_TAIL) -> dict[str, pd.DataFrame]:
    """Lê as cinco fontes da cópia curada da TAIL, conferindo o SHA-256 de cada arquivo.

    Devolve `old_attack`, `attack`, `itens_nf`, `octaprice` (só a URL distinta, **nunca** o texto
    das avaliações) e `benchmark` (rótulo com `strip()`, como a spec manda; o arquivo nunca é
    editado). Falha se faltar o diretório, o manifesto ou um arquivo, ou se algum hash divergir.
    """
    _verificar_manifest_tail(diretorio_tail)

    def csv(nome: str) -> pd.DataFrame:
        quadro = pd.read_csv(
            diretorio_tail / nome, dtype=str, keep_default_na=False, encoding="utf-8-sig"
        )
        if list(quadro.columns) != _COLUNAS_FONTES_TAIL[nome]:
            raise ValueError(
                f"colunas de {nome} diferentes do esperado {_COLUNAS_FONTES_TAIL[nome]}: "
                f"{list(quadro.columns)}"
            )
        return quadro

    benchmark = csv("pairs_to_label.csv")
    benchmark["label"] = benchmark["label"].str.strip()
    urls: set[str] = set()
    for nome in ("octaprice_mercadolivre_1.json", "octaprice_mercadolivre_2.json"):
        avaliacoes = json.loads((diretorio_tail / nome).read_text(encoding="utf-8"))
        urls.update(str(a["product_url"]) for a in avaliacoes)
    return {
        "old_attack": csv("old_attack_dataset.csv"),
        "attack": csv("attack.csv"),
        "itens_nf": csv("itens_nf_normalizados.csv"),
        "octaprice": pd.DataFrame({"product_url": sorted(urls)}),
        "benchmark": benchmark,
    }


def titulos_do_benchmark(benchmark: pd.DataFrame) -> list[str]:
    """Títulos do benchmark (os dois lados), normalizados, sem repetição e ordenados."""
    brutos = pd.concat([benchmark["title_a"], benchmark["title_b"]])
    return sorted({t for t in brutos.map(normalizar_titulo_tail) if t})


def construir_pares_variante(old_attack: pd.DataFrame, attack: pd.DataFrame) -> pd.DataFrame:
    """Pares (original, variante) do `old_attack_dataset.csv` e do `attack.csv`.

    Descarta variante vazia, variante igual ao original depois de normalizar e as linhas
    `Fallback_Erro_LLM` (falha do LLM). Um par presente nas duas fontes fica uma vez, com a fonte
    `old_attack`. O resultado não depende da ordem das linhas de entrada.
    """
    old = pd.DataFrame(
        {
            "titulo_a": old_attack["original"],
            "titulo_b": old_attack["attacked"],
            "fonte": "old_attack",
            "tipo_variacao": None,
        }
    )
    tipado = attack[attack["tipo_variacao"] != _FALLBACK_LLM]
    novo = pd.DataFrame(
        {
            "titulo_a": tipado["original"],
            "titulo_b": tipado["attacked"],
            "fonte": "attack",
            "tipo_variacao": tipado["tipo_variacao"],
        }
    )
    pares = pd.concat([old, novo], ignore_index=True)
    a = pares["titulo_a"].map(normalizar_titulo_tail)
    b = pares["titulo_b"].map(normalizar_titulo_tail)
    pares = pares[(b != "") & (a != b)].assign(_prioridade=lambda d: d["fonte"] != "old_attack")
    pares = (
        pares.sort_values(
            ["_prioridade", "titulo_a", "titulo_b", "tipo_variacao"], na_position="first"
        )
        .drop_duplicates(["titulo_a", "titulo_b"])
        .sort_values(["titulo_a", "titulo_b"])
    )
    return pares[COLUNAS_PARES_TAIL].reset_index(drop=True)


def construir_pares_nf(itens_nf: pd.DataFrame) -> pd.DataFrame:
    """Todos os pares de títulos distintos dentro de cada grupo `normalized` das notas fiscais."""
    linhas: list[tuple[str, str]] = []
    for _, titulos in itens_nf.groupby("normalized", sort=True)["title"]:
        unicos = sorted(set(titulos))
        linhas.extend(
            (unicos[i], unicos[j]) for i in range(len(unicos)) for j in range(i + 1, len(unicos))
        )
    pares = pd.DataFrame(linhas, columns=["titulo_a", "titulo_b"]).assign(fonte="nf")
    return pares.sort_values(["titulo_a", "titulo_b"]).reset_index(drop=True)


def filtrar_positivos_por_tamanho(pares: pd.DataFrame, incluir_sem_tamanho: bool) -> pd.DataFrame:
    """Mantém só positivos cujo conjunto de tamanhos é o mesmo nos dois lados (D1).

    Tamanho diferente, ou perdido só na variante, é descartado sempre (a variante corrompeu o
    tamanho). Sem tamanho em nenhum dos lados não é verificável: só entra com
    `incluir_sem_tamanho`. Preserva colunas e índice.
    """
    tamanho_a = pares["titulo_a"].map(tokens_numericos)
    tamanho_b = pares["titulo_b"].map(tokens_numericos)
    verificado = (tamanho_a.map(bool)) & (tamanho_a == tamanho_b)
    if incluir_sem_tamanho:
        verificado = verificado | (~tamanho_a.map(bool) & ~tamanho_b.map(bool))
    return pares[verificado]


def agrupar_titulos_tail(pares: pd.DataFrame) -> pd.Series:
    """Grupo de cada título: original, variantes e positivos ligados formam um só (union-find).

    O id do grupo é o hash do menor título dele, então não depende da ordem das linhas.
    """
    titulos = sorted(set(pares["titulo_a"]) | set(pares["titulo_b"]))
    posicao = {t: i for i, t in enumerate(titulos)}
    ligacoes = coo_matrix(
        (
            np.ones(len(pares)),
            (pares["titulo_a"].map(posicao).to_numpy(), pares["titulo_b"].map(posicao).to_numpy()),
        ),
        shape=(len(titulos), len(titulos)),
    )
    _, rotulos = connected_components(ligacoes, directed=False)
    menor: dict[int, str] = {}
    for titulo, componente in zip(titulos, rotulos, strict=True):
        menor.setdefault(int(componente), titulo)  # `titulos` está ordenado: o 1º é o menor
    grupos = [_hash_curto(menor[int(c)]) for c in rotulos]
    return pd.Series(grupos, index=titulos, name="grupo")


def excluir_grupos_quase_duplicatas(
    grupos: pd.Series, titulos_benchmark: list[str], limiar: float
) -> tuple[pd.Series, pd.DataFrame]:
    """Exclui o grupo **inteiro** se algum título dele for idêntico ou quase-duplicata do benchmark.

    Idêntico: igual depois de `normalizar_titulo_tail`. Quase-duplicata: cosseno TF-IDF de palavras
    (vocabulário do conjunto TAIL + benchmark) ≥ `limiar` com algum título do benchmark (D2; o
    limiar é fixado antes de ver as contagens). Devolve os grupos mantidos e as exclusões, com o
    título do benchmark que as causou. Os títulos do benchmark são proibidos no treino e na
    validação (ADR-0013). `ValueError` se o limiar estiver fora de (0, 1].
    """
    if not 0 < limiar <= 1:
        raise ValueError(f"limiar fora de (0, 1]: {limiar!r}")
    colunas = ["grupo", "titulo", "motivo", "titulo_benchmark"]
    if not titulos_benchmark:
        return grupos, pd.DataFrame(columns=colunas)
    bench = sorted(set(titulos_benchmark))
    bench_norm = [normalizar_titulo_tail(t) for t in bench]
    por_norm: dict[str, str] = {}
    for original, norm in zip(bench, bench_norm, strict=True):
        por_norm.setdefault(norm, original)
    titulos = sorted(grupos.index)
    norm_tail = [normalizar_titulo_tail(t) for t in titulos]
    vetor = TfidfVectorizer(lowercase=False, token_pattern=r"\S+")
    matriz = vetor.fit_transform([*norm_tail, *bench_norm])
    tail_m, bench_m = matriz[: len(titulos)], matriz[len(titulos) :].T.tocsc()
    maximo = np.zeros(len(titulos))
    melhor = np.zeros(len(titulos), dtype=int)
    for inicio in range(0, len(titulos), 2000):  # em lotes: a matriz densa inteira não cabe
        bloco = (tail_m[inicio : inicio + 2000] @ bench_m).toarray()
        maximo[inicio : inicio + 2000] = bloco.max(axis=1)
        melhor[inicio : inicio + 2000] = bloco.argmax(axis=1)
    linhas = []
    for i, titulo in enumerate(titulos):
        if norm_tail[i] in por_norm:
            linhas.append((grupos[titulo], titulo, "identico", por_norm[norm_tail[i]]))
        elif maximo[i] >= limiar - _TOLERANCIA_COSSENO:
            linhas.append((grupos[titulo], titulo, "quase_duplicata", bench[int(melhor[i])]))
    exclusoes = pd.DataFrame(linhas, columns=colunas)
    return grupos[~grupos.isin(set(exclusoes["grupo"]))], exclusoes


def limitar_pares_por_grupo(pares: pd.DataFrame, teto: int, seed: int) -> pd.DataFrame:
    """No máximo `teto` pares por grupo, sorteados com a seed (D4); grupos menores ficam como estão.

    O sorteio de cada grupo usa a seed e o id do grupo, então não depende da ordem das linhas nem
    dos outros grupos. Devolve ordenado por grupo e título.
    """
    if teto < 1:
        raise ValueError(f"teto deve ser ≥ 1: {teto!r}")
    mantidos = []
    for grupo, bloco in pares.groupby("grupo", sort=True):
        bloco = bloco.sort_values(["titulo_a", "titulo_b"]).reset_index(drop=True)
        if len(bloco) > teto:
            rng = np.random.default_rng([seed, int(_hash_curto(str(grupo)), 16)])
            bloco = bloco.iloc[sorted(rng.choice(len(bloco), size=teto, replace=False))]
        mantidos.append(bloco)
    if not mantidos:
        return pares.iloc[0:0]
    return pd.concat(mantidos, ignore_index=True)


# ── Pares da TAIL, bloco P5b: negativos, montagem, barreira e geração (D1 a D6 do autor) ──────
#
# D1 vale para as variantes E para as notas fiscais (decisão do autor, 2026-11-16): par sem
# tamanho reconhecível fica fora, salvo `incluir_sem_tamanho`. Só uso LOCAL: nada é versionado.

ARQUIVO_RESUMO_PARES_TAIL_PXP = "pares_tail_pxp_resumo.csv"
_ORIGEM_TAIL_POR_FONTE = {"old_attack": "tail_variante", "attack": "tail_variante", "nf": "tail_nf"}
_GRUPO_OCTAPRICE = "octaprice|"


def _id_tail(titulo: str) -> str:
    return _PREFIXO_TAIL + _hash_curto(titulo)


def _alocar_por_peso(n_total: int, pesos: dict[str, float], rotulos: list[str]) -> dict[str, int]:
    """Divide `n_total` entre as faixas pelo peso (maiores restos; empate: faixa mais difícil)."""
    soma = sum(pesos.values())
    exato = {r: n_total * pesos[r] / soma for r in rotulos}
    cotas = {r: int(np.floor(v)) for r, v in exato.items()}
    sobra = n_total - sum(cotas.values())
    ordem = sorted(rotulos, key=lambda r: (exato[r] - cotas[r], rotulos.index(r)), reverse=True)
    for rotulo in ordem[:sobra]:
        cotas[rotulo] += 1
    return cotas


def selecionar_negativos_tail(
    titulos: pd.DataFrame, cfg: ConfigTailPxp, n_total: int
) -> pd.DataFrame:
    """Negativos certos da TAIL: tamanho conhecido e **diferente**, de **grupos diferentes** (D5).

    `titulos` traz `titulo` e `grupo`. Candidatos do top-`k` TF-IDF entre todos os títulos, um por
    par não ordenado; `n_total` pares repartidos entre as faixas de cosseno pelo peso da config,
    das mais difíceis para as mais fáceis, com teto de pares por título e a seed da config. Falha
    com `ValueError` nomeando a faixa se faltar candidato. Devolve `titulo_a` < `titulo_b`,
    `score` e `faixa`.
    """
    base = titulos.drop_duplicates("titulo").sort_values("titulo").reset_index(drop=True)
    ids = [_hash_curto(t) for t in base["titulo"]]
    universo = pd.DataFrame({"id_produto": ids, "descricao": base["titulo"]})
    titulo_de = dict(zip(ids, base["titulo"], strict=True))
    grupo_de = dict(zip(ids, base["grupo"], strict=True))
    tamanho_de = {i: tokens_numericos(t) for i, t in titulo_de.items()}
    ranking = ranquear_vizinhos(universo, cfg["k"])
    a, b = ranking["id_produto"].to_numpy(), ranking["id_candidato"].to_numpy()
    valido = np.array(
        [
            bool(tamanho_de[x])
            and bool(tamanho_de[y])
            and tamanho_de[x] != tamanho_de[y]
            and grupo_de[x] != grupo_de[y]
            for x, y in zip(a, b, strict=True)
        ],
        dtype=bool,
    )
    pares = (
        pd.DataFrame(
            {
                "id_a": np.minimum(a[valido], b[valido]),
                "id_b": np.maximum(a[valido], b[valido]),
                "score": ranking["score"].to_numpy()[valido],
            }
        )
        .sort_values(["id_a", "id_b"])
        .drop_duplicates(["id_a", "id_b"])
        .reset_index(drop=True)
    )
    rotulos = _rotulos_das_faixas(cfg["faixas_cosseno"])
    alocacao = _alocar_por_peso(n_total, cfg["peso_negativos_por_faixa"], rotulos)
    escolhidos = _amostrar_por_faixa(
        pares, cfg["faixas_cosseno"], alocacao, cfg["teto_negativos_por_produto"], cfg["seed"]
    )
    nomes_a = escolhidos["id_a"].map(titulo_de)
    nomes_b = escolhidos["id_b"].map(titulo_de)
    saida = pd.DataFrame(
        {
            "titulo_a": np.minimum(nomes_a, nomes_b),
            "titulo_b": np.maximum(nomes_a, nomes_b),
            "score": escolhidos["score"].to_numpy(),
            "faixa": escolhidos["faixa"].to_numpy(),
        }
    )
    return saida.sort_values(["titulo_a", "titulo_b"]).reset_index(drop=True)


def _formatar_pares_tail(pares: pd.DataFrame, origem: pd.Series, rotulo: str) -> pd.DataFrame:
    """Pares de títulos no formato de treino: ids `tail_<hash>`, `a < b` pelo id, sem unidade."""
    id_a = pares["titulo_a"].map(_id_tail)
    id_b = pares["titulo_b"].map(_id_tail)
    troca = (id_a > id_b).to_numpy()
    lado_a = np.where(troca, pares["titulo_b"], pares["titulo_a"])
    lado_b = np.where(troca, pares["titulo_a"], pares["titulo_b"])
    saida = pd.DataFrame({"descricao_a": lado_a, "descricao_b": lado_b})
    saida["id_a"] = saida["descricao_a"].map(_id_tail)
    saida["id_b"] = saida["descricao_b"].map(_id_tail)
    saida["id_par"] = [
        _hash_curto(f"{x}|{y}") for x, y in zip(saida["id_a"], saida["id_b"], strict=True)
    ]
    saida["und_val_a"] = np.nan
    saida["und_val_b"] = np.nan
    saida["und_med_a"] = None
    saida["und_med_b"] = None
    saida["tipo_par"] = "produto_produto"
    saida["origem"] = origem.to_numpy()
    saida["rotulo"] = rotulo
    return saida[COLUNAS_PARES_TREINO_PXP]


def montar_pares_tail_pxp(
    fontes: dict[str, pd.DataFrame], cfg: ConfigTailPxp
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pares de treino da TAIL: positivos das variantes e das notas fiscais, mais negativos.

    Passos: pares de variante e de nota fiscal; filtro de tamanho nos dois (D1); grupos por
    união-busca; exclusão do grupo inteiro que bata com o benchmark (D2), também para os títulos do
    octaprice; teto por grupo só nas notas fiscais (D4); negativos só de tamanho diferente, entre
    grupos diferentes, na razão da config (D5). Devolve os pares (`COLUNAS_PARES_TREINO_PXP`) e um
    resumo `etapa`, `n`. Determinístico e independente da ordem das linhas das fontes.
    """
    variante = filtrar_positivos_por_tamanho(
        construir_pares_variante(fontes["old_attack"], fontes["attack"]), cfg["incluir_sem_tamanho"]
    )
    nota = filtrar_positivos_por_tamanho(
        construir_pares_nf(fontes["itens_nf"]), cfg["incluir_sem_tamanho"]
    )
    positivos = pd.concat([variante, nota], ignore_index=True)
    grupos = agrupar_titulos_tail(positivos[["titulo_a", "titulo_b"]])
    titulos_octaprice = sorted(
        {titulo_do_slug(u) for u in fontes["octaprice"]["product_url"]} - set(grupos.index)
    )
    do_octaprice = pd.Series(
        [_hash_curto(_GRUPO_OCTAPRICE + t) for t in titulos_octaprice],
        index=titulos_octaprice,
        name="grupo",
    )
    benchmark = titulos_do_benchmark(fontes["benchmark"])
    mantidos, exclusoes = excluir_grupos_quase_duplicatas(
        pd.concat([grupos, do_octaprice]), benchmark, cfg["limiar_quase_duplicata"]
    )
    excluidos_octaprice = exclusoes[exclusoes["titulo"].isin(set(titulos_octaprice))]
    excluidos_positivos = exclusoes.drop(excluidos_octaprice.index)

    grupo_do_par = positivos["titulo_a"].map(mantidos)
    positivos = positivos.assign(grupo=grupo_do_par)[grupo_do_par.notna()]
    de_variante = positivos[positivos["fonte"] != "nf"]
    de_nota = limitar_pares_por_grupo(
        positivos[positivos["fonte"] == "nf"], cfg["max_pares_por_grupo_nf"], cfg["seed"]
    )
    todos = pd.concat([de_variante, de_nota], ignore_index=True)
    n_negativos = round(cfg["razao_negativos"] * len(todos))
    pool = pd.concat([mantidos.rename("grupo")], axis=0).rename_axis("titulo").reset_index()
    negativos = selecionar_negativos_tail(pool, cfg, n_negativos)

    pares = pd.concat(
        [
            _formatar_pares_tail(todos, todos["fonte"].map(_ORIGEM_TAIL_POR_FONTE), "match"),
            _formatar_pares_tail(
                negativos, pd.Series("tail_negativo", index=negativos.index), "nao_match"
            ),
        ],
        ignore_index=True,
    )
    pares = pares.sort_values(["origem", "id_par"]).reset_index(drop=True)
    resumo = pd.DataFrame(
        {
            "etapa": [
                "variante_apos_filtro_tamanho",
                "nf_apos_filtro_tamanho",
                "grupos_excluidos_benchmark",
                "titulos_octaprice_excluidos_benchmark",
                "positivos_variante",
                "positivos_nf",
                "negativos",
            ],
            "n": [
                len(variante),
                len(nota),
                int(excluidos_positivos["grupo"].nunique()),
                len(excluidos_octaprice),
                len(de_variante),
                len(de_nota),
                len(negativos),
            ],
        }
    )
    return pares, resumo


def verificar_pares_tail_pxp(pares: pd.DataFrame, titulos_benchmark: list[str]) -> None:
    """Barreira crítica dos pares da TAIL, `AssertionError` explícito (vale com `python -O`).

    Colunas do contrato de treino; `id_par` único; ids `tail_...`; origem conhecida; rótulo
    coerente com a origem; nenhum título do benchmark (normalizado) em nenhum lado (ADR-0013);
    positivos que preservam o tamanho e nunca são idênticos; negativos com tamanho conhecido e
    diferente.
    """
    if pares.empty:
        raise AssertionError("nenhum par da TAIL gerado")
    if list(pares.columns) != COLUNAS_PARES_TREINO_PXP:
        extras = sorted(set(pares.columns) - set(COLUNAS_PARES_TREINO_PXP))
        raise AssertionError(f"colunas fora do contrato do treino; sobram {extras}")
    repetidos = sorted(set(pares.loc[pares["id_par"].duplicated(), "id_par"]))
    if repetidos:
        raise AssertionError(f"id_par duplicado nos pares da TAIL: {repetidos[:10]}")
    sem_prefixo = pares[
        ~pares["id_a"].str.startswith(_PREFIXO_TAIL) | ~pares["id_b"].str.startswith(_PREFIXO_TAIL)
    ]
    if len(sem_prefixo):
        raise AssertionError(f"id sem prefixo tail_: {sorted(sem_prefixo['id_par'])[:10]}")
    desconhecidas = sorted(set(pares["origem"]) - set(ORIGENS_TAIL))
    if desconhecidas:
        raise AssertionError(f"origem fora das origens da TAIL: {desconhecidas}")
    positivo = pares["origem"].isin(ORIGENS_TAIL_POSITIVAS)
    incoerentes = pares[
        (positivo & (pares["rotulo"] != "match")) | (~positivo & (pares["rotulo"] != "nao_match"))
    ]
    if len(incoerentes):
        raise AssertionError(
            f"rotulo incoerente com a origem em: {sorted(incoerentes['id_par'])[:10]}"
        )
    proibidos = {normalizar_titulo_tail(t) for t in titulos_benchmark}
    for linha in pares.itertuples(index=False):
        for texto in (linha.descricao_a, linha.descricao_b):
            if normalizar_titulo_tail(texto) in proibidos:
                raise AssertionError(
                    f"título do benchmark da TAIL no treino (ADR-0013): {linha.id_par}"
                )
    for linha in pares.itertuples(index=False):
        a, b = tokens_numericos(linha.descricao_a), tokens_numericos(linha.descricao_b)
        if linha.origem in ORIGENS_TAIL_POSITIVAS:
            if a != b:
                raise AssertionError(
                    f"positivo da TAIL muda o conjunto de tamanhos: {linha.id_par}"
                )
            if linha.descricao_a == linha.descricao_b:
                raise AssertionError(f"positivo da TAIL idêntico ao original: {linha.id_par}")
        elif not (a and b and a != b):
            raise AssertionError(
                f"negativo da TAIL sem tamanho diferente nos dois lados: {linha.id_par}"
            )


def gerar_pares_tail_pxp(
    diretorio_processados: Path = DADOS_PROCESSADOS,
    diretorio_tail: Path = DADOS_BRUTOS_TAIL,
    caminho_config: Path = CONFIG_PARES_TAIL_PXP,
    diretorio_metricas: Path = RESULTADOS_METRICAS,
) -> pd.DataFrame:
    """Grava `pares_tail_pxp.parquet` e `pares_tail_pxp_resumo.csv` a partir da cópia da TAIL.

    Lê as fontes conferindo o SHA-256 (`ler_fontes_tail`), monta e verifica os pares. Tudo ou nada:
    nada é gravado se qualquer etapa falhar. Determinístico e regenerável. Só uso local.
    """
    fontes = ler_fontes_tail(diretorio_tail)
    cfg = carregar_config_tail_pxp(caminho_config)
    pares, resumo = montar_pares_tail_pxp(fontes, cfg)
    verificar_pares_tail_pxp(pares, titulos_do_benchmark(fontes["benchmark"]))
    diretorio_processados.mkdir(parents=True, exist_ok=True)
    diretorio_metricas.mkdir(parents=True, exist_ok=True)
    pares.to_parquet(diretorio_processados / ARQUIVO_PARES_TAIL_PXP, index=False)
    resumo.to_csv(diretorio_metricas / ARQUIVO_RESUMO_PARES_TAIL_PXP, index=False)
    logger.info(
        "Pares da TAIL (%d) gravados em %s:\n%s",
        len(pares),
        diretorio_processados / ARQUIVO_PARES_TAIL_PXP,
        resumo.to_string(index=False),
    )
    return pares


def _argumentos(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Construção do dataset e ground truth (spec 001). Sem flag, roda as etapas "
        "automáticas; o reteste só roda com a flag explícita."
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "--reteste",
        action="store_true",
        help="gera a planilha do reteste (ADR-0005) e nada mais; use ≥ 7 dias depois da 1ª passada",
    )
    grupo.add_argument(
        "--adjudicacao",
        action="store_true",
        help="gera a planilha de adjudicação dos `incerto` do teste (protocolo §3.5) e nada mais",
    )
    grupo.add_argument(
        "--teste",
        action="store_true",
        help="compõe teste_pxp.parquet (primeira passada + adjudicação) e o resumo por estrato",
    )
    grupo.add_argument(
        "--kappa-reteste",
        action="store_true",
        help="calcula o Kappa do reteste e grava resultados/metricas/kappa_reteste_pxp.csv",
    )
    parser.add_argument(
        "--aceitar-intervalo-curto",
        action="store_true",
        help="com --kappa-reteste: calcula mesmo com < 7 dias e registra o desvio do ADR-0005",
    )
    args = parser.parse_args(list(argv))
    if args.aceitar_intervalo_curto and not args.kappa_reteste:
        parser.error("--aceitar-intervalo-curto só vale junto com --kappa-reteste")
    return args


def main(argv: Sequence[str] = ()) -> None:
    args = _argumentos(argv)
    if args.reteste:
        gerar_planilha_reteste_pxp(DADOS_PROCESSADOS, CONFIG_BLOCAGEM_PXP)
        return
    if args.adjudicacao:
        gerar_planilha_adjudicacao_pxp(DADOS_PROCESSADOS)
        return
    if args.teste:
        gerar_teste_pxp(DADOS_PROCESSADOS, RESULTADOS_METRICAS)
        return
    if args.kappa_reteste:
        gerar_kappa_reteste_pxp(
            DADOS_PROCESSADOS,
            RESULTADOS_METRICAS,
            aceitar_intervalo_curto=args.aceitar_intervalo_curto,
        )
        return
    executar_blocagem(
        DADOS_PROCESSADOS,
        RESULTADOS_METRICAS,
        CONFIG_BLOCAGEM,
        diretorio_latex_tabelas=LATEX_TABELAS,
    )
    executar_blocagem_pxp(
        DADOS_PROCESSADOS,
        RESULTADOS_METRICAS,
        CONFIG_BLOCAGEM_PXP,
        diretorio_latex_tabelas=LATEX_TABELAS,
    )
    if (DADOS_PROCESSADOS / "produtos_treino_pxp.parquet").exists():
        gerar_pares_treino_auto_pxp(DADOS_PROCESSADOS, CONFIG_PARES_TREINO_PXP)
    else:
        logger.info("produtos_treino_pxp.parquet ainda não existe: pares de treino não gerados.")
    if DADOS_BRUTOS_TAIL.exists():
        gerar_pares_tail_pxp(
            DADOS_PROCESSADOS, DADOS_BRUTOS_TAIL, CONFIG_PARES_TAIL_PXP, RESULTADOS_METRICAS
        )
    else:
        logger.info("%s não existe: pares da TAIL não gerados.", DADOS_BRUTOS_TAIL)
    if (DADOS_PROCESSADOS / ARQUIVO_PARES_TREINO_AUTO_PXP).exists():
        gerar_treino_pxp(DADOS_PROCESSADOS, RESULTADOS_METRICAS, CONFIG_PARES_TREINO_PXP)
    else:
        logger.info("%s ainda não existe: treino_pxp não montado.", ARQUIVO_PARES_TREINO_AUTO_PXP)
    logger.info(
        "Pendentes (spec 001): partição produto × dicionário (RF6) e o benchmark externo da TAIL "
        "(RF9). O teste final se compõe com `--teste`; a anotação B2 entra sozinha a cada execução."
    )


if __name__ == "__main__":
    main(sys.argv[1:])
