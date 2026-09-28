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
import re
import unicodedata
from pathlib import Path
from typing import TypedDict

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402


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
LATEX_TABELAS = Path("latex/tcc_artigo/tabelas")


def extrair_estado(location: str) -> str:
    """Extrai a sigla do estado do campo `location` (formato "UF, Cidade, Loja")."""
    if "," not in location:
        raise ValueError(f"location sem o formato esperado 'UF, Cidade, Loja': {location!r}")
    return location.split(",", 1)[0].strip()


# ── Taxonomia de ruído de PDV (spec 001, tarefa 1.1.2) ──────────────────────
#
# Quatro dimensões vêm de docs/protocolo_anotacao.md §3.2 (casos de MATCH):
# abreviação, inversão de ordem, unidade, tipografia. "Inversão de ordem" só
# é detectável comparando um par de descrições do mesmo produto (requer
# blocagem — tarefa 1.2) e por isso fica fora desta caracterização de
# descrição única; as outras três são heurísticas de regex validadas contra
# amostra real da base (ver diário de pesquisa).

_UNIDADE_COLADA_RE = re.compile(r"\d(?:ml|gr|kg|un|g|l)\b", re.IGNORECASE)
_CARACTERES_ACENTUADOS = set("áàâãéèêíìóòôõúùçÁÀÂÃÉÈÊÍÌÓÒÔÕÚÙÇ")
_ABREVIATURA_RE = re.compile(r"\b[A-Za-z]{1,3}/|\b[A-Za-z]{2,}\.")


def tem_unidade_colada(description: str) -> bool:
    """Detecta quantidade colada à unidade sem espaço (ex.: "92G", "660ml")."""
    return bool(_UNIDADE_COLADA_RE.search(description))


def esta_em_caixa_alta(description: str) -> bool:
    """Descrição inteiramente em maiúsculas — convenção de PDV que varia por loja."""
    letras = [c for c in description if c.isalpha()]
    return bool(letras) and all(c.isupper() for c in letras)


def esta_sem_acentuacao(description: str) -> bool:
    """Descrição sem nenhum caractere acentuado — indício de normalização/ruído de PDV."""
    tem_letra = any(c.isalpha() for c in description)
    tem_acento = any(c in _CARACTERES_ACENTUADOS for c in description)
    return tem_letra and not tem_acento


def normalizar_para_comparacao(texto: str) -> str:
    """Uppercase e remove acentos — comparação tolerante à variação de PDV."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.upper().strip()


def tem_abreviatura(description: str) -> bool:
    """Detecta marcas de abreviação/truncamento ("C/", "S/", "aprox.", "und.")."""
    return bool(_ABREVIATURA_RE.search(description))


class RuidoPDV(TypedDict):
    """Contagem de descrições por tipo de ruído de PDV (spec 001, tarefa 1.1.2)."""

    unidade_colada: int
    caixa_alta: int
    sem_acentuacao: int
    abreviatura: int


class DistribuicaoMatchScore(TypedDict):
    """Distribuição descritiva de `match_score` (spec 001, tarefa 1.1.3).

    ADR-0010: `match_score` só é lido aqui, e só para esta caracterização
    descritiva do estado atual do matching heurístico do ALTA — nunca como
    rótulo de anotação, supervisão distante ou treino.
    """

    contagem: int
    media: float
    desvio_padrao: float
    minimo: float
    maximo: float
    p25: float
    mediana: float
    p75: float


def caracterizar_match_score(df_produtos: pd.DataFrame) -> DistribuicaoMatchScore:
    """Caracteriza a distribuição de `match_score` (ADR-0010: contexto, nunca rótulo)."""
    serie = df_produtos["match_score"]
    return {
        "contagem": int(serie.count()),
        "media": float(serie.mean()),
        "desvio_padrao": float(serie.std()),
        "minimo": float(serie.min()),
        "maximo": float(serie.max()),
        "p25": float(serie.quantile(0.25)),
        "mediana": float(serie.quantile(0.5)),
        "p75": float(serie.quantile(0.75)),
    }


_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escapar_latex(texto: str) -> str:
    """Escapa caracteres especiais do LaTeX (`AGENTS.md` §4: preservar escapes)."""
    return "".join(_LATEX_ESCAPES.get(caractere, caractere) for caractere in texto)


def selecionar_exemplos_heterogeneidade(
    df_produtos: pd.DataFrame,
    df_dicionario: pd.DataFrame,
    n_exemplos: int = 3,
    seed: int = SEED,
) -> list[dict[str, str]]:
    """Seleciona pares reais (loja A, loja B) por entrada canônica (spec 001, 1.1.4).

    Heurística de correspondência pela frase canônica completa normalizada
    (não só o primeiro token — "ARROZ" sozinho colidiria "ARROZ BRANCO" com
    "ARROZ INTEGRAL") — não é a blocagem da tarefa 1.2, serve só para
    ilustrar a heterogeneidade com dados reais em vez de exemplos
    inventados (D1 conflito 3, D6). Requer candidatos de pelo menos duas
    fontes (`source`) distintas para cada entrada, para que o par ilustre
    de fato a variação entre lojas.
    """
    descricoes_normalizadas = df_produtos["description"].map(normalizar_para_comparacao)
    exemplos: list[dict[str, str]] = []
    for _, linha_dicionario in df_dicionario.iterrows():
        canonico = str(linha_dicionario["desc_alim"])
        frase_canonica = normalizar_para_comparacao(canonico)
        # Ancorado ao início: descrições de PDV tipicamente abrem com o nome
        # do produto, o que evita falso positivo de produto correlato que só
        # cita a entrada canônica de passagem (ex.: um tempero para arroz).
        padrao = re.compile(rf"^{re.escape(frase_canonica)}\b")
        mascara = descricoes_normalizadas.map(lambda texto: bool(padrao.match(texto)))
        candidatos = df_produtos[mascara]
        fontes_distintas = sorted(candidatos["source"].unique())
        if len(fontes_distintas) < 2:
            continue

        fonte_a, fonte_b = fontes_distintas[0], fontes_distintas[1]
        descricao_a = (
            candidatos[candidatos["source"] == fonte_a]["description"]
            .sample(1, random_state=seed)
            .iloc[0]
        )
        descricao_b = (
            candidatos[candidatos["source"] == fonte_b]["description"]
            .sample(1, random_state=seed)
            .iloc[0]
        )
        exemplos.append(
            {"supermercado_a": descricao_a, "supermercado_b": descricao_b, "canonico": canonico}
        )
        if len(exemplos) >= n_exemplos:
            break
    return exemplos


def gerar_figura_distribuicao_source(contagens: ContagensBasicas, caminho: Path) -> None:
    """Gera o gráfico de barras de registros por fonte/rede (spec 001, tarefa 1.1.5)."""
    distribuicao = contagens["distribuicao_source"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(list(distribuicao.keys()), list(distribuicao.values()))
    ax.set_xlabel("Fonte (rede)")
    ax.set_ylabel("Registros")
    ax.set_title("Distribuição de registros por fonte")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(caminho)
    plt.close(fig)


def gerar_tabela_heterogeneidade_tex(exemplos: list[dict[str, str]], caminho: Path) -> None:
    """Escreve a tabela LaTeX de exemplos de heterogeneidade (tarefa 1.1.4).

    Substitui a versão escrita à mão (D1 conflito 3, D6) — mesma estrutura
    de colunas/legenda/label consumida por `main.tex` via `\\input`.
    """
    linhas_tabela = "\n".join(
        f"{escapar_latex(exemplo['supermercado_a'])} & "
        f"{escapar_latex(exemplo['supermercado_b'])} & "
        f"{escapar_latex(exemplo['canonico'])} \\\\"
        for exemplo in exemplos
    )
    conteudo = (
        "% Gerado automaticamente por scripts/02_analise_exploratoria.py — não editar à mão.\n"
        "\\begin{table}[htbp]\n"
        "\\centering\n"
        "\\caption{Exemplos de heterogeneidade nas descrições de produtos}\n"
        "\\label{tab:heterogeneidade}\n"
        "\\small\n"
        "\\resizebox{\\textwidth}{!}{%\n"
        "\\begin{tabular}{lll}\n"
        "\\toprule\n"
        "\\textbf{Supermercado A} & \\textbf{Supermercado B} & "
        "\\textbf{Canônico (Dicionário)} \\\\\n"
        "\\midrule\n"
        f"{linhas_tabela}\n"
        "\\bottomrule\n"
        "\\end{tabular}%\n"
        "}\n"
        "\\vspace{2mm}\n"
        "\\fonte{Elaborado pelo autor a partir de dados do projeto ALTA}\n"
        "\\end{table}\n"
    )
    caminho.write_text(conteudo, encoding="utf-8")


def caracterizar_ruido_pdv(df_produtos: pd.DataFrame) -> RuidoPDV:
    """Conta, por dimensão de ruído, quantas descrições brutas exibem o padrão."""
    descricoes = df_produtos["description"]
    return {
        "unidade_colada": int(descricoes.map(tem_unidade_colada).sum()),
        "caixa_alta": int(descricoes.map(esta_em_caixa_alta).sum()),
        "sem_acentuacao": int(descricoes.map(esta_sem_acentuacao).sum()),
        "abreviatura": int(descricoes.map(tem_abreviatura).sum()),
    }


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


def _salvar_match_score(distribuicao: DistribuicaoMatchScore, caminho: Path) -> None:
    linhas = [
        {"metrica": "contagem", "valor": distribuicao["contagem"]},
        {"metrica": "media", "valor": distribuicao["media"]},
        {"metrica": "desvio_padrao", "valor": distribuicao["desvio_padrao"]},
        {"metrica": "minimo", "valor": distribuicao["minimo"]},
        {"metrica": "maximo", "valor": distribuicao["maximo"]},
        {"metrica": "p25", "valor": distribuicao["p25"]},
        {"metrica": "mediana", "valor": distribuicao["mediana"]},
        {"metrica": "p75", "valor": distribuicao["p75"]},
    ]
    pd.DataFrame(linhas).to_csv(caminho, index=False)


def _salvar_ruido_pdv(ruido: RuidoPDV, total_registros: int, caminho: Path) -> None:
    contagens_por_categoria: list[tuple[str, int]] = [
        ("unidade_colada", ruido["unidade_colada"]),
        ("caixa_alta", ruido["caixa_alta"]),
        ("sem_acentuacao", ruido["sem_acentuacao"]),
        ("abreviatura", ruido["abreviatura"]),
    ]
    linhas = [
        {"categoria": categoria, "contagem": contagem, "fracao": contagem / total_registros}
        for categoria, contagem in contagens_por_categoria
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
    diretorio_brutos: Path,
    diretorio_saida: Path = RESULTADOS_METRICAS,
    diretorio_latex_tabelas: Path = LATEX_TABELAS,
    diretorio_figuras: Path = RESULTADOS_FIGURAS,
) -> ContagensBasicas:
    """Calcula e persiste as estatísticas descritivas da spec 001 (tarefas 1.1.1-1.1.4).

    Ver specs/001-construcao-dataset-ground-truth/requirements.md.
    """
    df_produtos = carregar_produtos(diretorio_brutos)
    df_dicionario = carregar_dicionario(diretorio_brutos)
    contagens = calcular_contagens_basicas(df_produtos, df_dicionario)
    ruido = caracterizar_ruido_pdv(df_produtos)
    distribuicao_match_score = caracterizar_match_score(df_produtos)
    exemplos_heterogeneidade = selecionar_exemplos_heterogeneidade(df_produtos, df_dicionario)

    diretorio_saida.mkdir(parents=True, exist_ok=True)
    _salvar_contagens_escalares(contagens, diretorio_saida / "estatisticas_descritivas.csv")
    _salvar_distribuicoes(contagens, diretorio_saida / "distribuicoes_categoricas.csv")
    _salvar_ruido_pdv(ruido, contagens["total_registros"], diretorio_saida / "taxonomia_ruido.csv")
    _salvar_match_score(distribuicao_match_score, diretorio_saida / "distribuicao_match_score.csv")

    diretorio_latex_tabelas.mkdir(parents=True, exist_ok=True)
    gerar_tabela_heterogeneidade_tex(
        exemplos_heterogeneidade, diretorio_latex_tabelas / "tab_heterogeneidade_exemplos.tex"
    )

    diretorio_figuras.mkdir(parents=True, exist_ok=True)
    gerar_figura_distribuicao_source(contagens, diretorio_figuras / "distribuicao_source.png")

    logger.info(
        "EDA (1.1.1-1.1.4): %d registros, %d entradas no dicionário, %d exemplos de "
        "heterogeneidade. Estatísticas em %s, tabela em %s",
        contagens["total_registros"],
        contagens["total_entradas_dicionario"],
        len(exemplos_heterogeneidade),
        diretorio_saida,
        diretorio_latex_tabelas,
    )
    return contagens


def main() -> None:
    estatisticas_descritivas(DADOS_BRUTOS, RESULTADOS_METRICAS, LATEX_TABELAS, RESULTADOS_FIGURAS)


if __name__ == "__main__":
    main()
