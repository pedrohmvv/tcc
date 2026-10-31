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
    (arquivo de anotação manual, produzido fora do pipeline — ver
     docs/protocolo_anotacao.md)

Saídas (ver spec 001):
    dados/processados/anotacoes_amostra_cega.csv   (planilha SEM candidatos; nunca sobrescrita)
    resultados/metricas/recall_blocagem.csv        (só depois de a planilha estar toda anotada)
    latex/tcc_artigo/tabelas/tab_recall_blocagem.tex  (idem; gerada a partir do recall)
    dados/processados/candidatos_blocagem.parquet  (só com `metodo` e `k` congelados no YAML)
    dados/processados/{treino,validacao,teste}.parquet   (pendente)

Nenhuma saída em dados/processados/ contém codg_item/desc_ref/match_score (ADR-0011).

Status: blocagem produto × dicionário (1.2a) implementada; partição pendente (spec 001).
A blocagem produto × produto (1.2b) fica para depois.

[CRÍTICO] Nenhuma chamada ao Dataset Generator deve tocar os produtos
reservados ao teste — o particionamento por produto canônico precisa
ocorrer ANTES de qualquer geração/augmentation, com checagem explícita
(assert), não apenas por convenção (ADR-0004).

Uso:
    uv run python scripts/03_construcao_dataset.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import logging
from pathlib import Path
from types import ModuleType
from typing import Any, TypedDict

import numpy as np
import pandas as pd
import yaml
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DADOS_PROCESSADOS = Path("dados/processados")
RESULTADOS_METRICAS = Path("resultados/metricas")
LATEX_TABELAS = Path("latex/tcc_artigo/tabelas")
CONFIG_BLOCAGEM = Path("configs/blocagem.yaml")

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


def _montar_ranking(lotes: list[dict[str, np.ndarray]]) -> pd.DataFrame:
    if not lotes:
        return pd.DataFrame(columns=COLUNAS_RANKING)
    return pd.DataFrame(
        {col: np.concatenate([lote[col] for lote in lotes]) for col in COLUNAS_RANKING}
    )


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


def particionar_por_produto_canonico() -> None:
    """Particiona treino/validação/teste por produto canônico, antes de qualquer geração.

    [CRÍTICO] validar com assert que nenhum produto do teste aparece no treino.
    """
    raise NotImplementedError(
        "Implementar conforme specs/001-construcao-dataset-ground-truth/requirements.md"
    )


def main() -> None:
    executar_blocagem(
        DADOS_PROCESSADOS,
        RESULTADOS_METRICAS,
        CONFIG_BLOCAGEM,
        diretorio_latex_tabelas=LATEX_TABELAS,
    )
    logger.info("Partição por produto canônico ainda não implementada — ver spec 001.")


if __name__ == "__main__":
    main()
