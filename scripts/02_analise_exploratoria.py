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

Saídas:
    resultados/metricas/estatisticas_descritivas.csv    (tarefa 1.1.1)
    resultados/metricas/distribuicoes_categoricas.csv   (tarefa 1.1.1)
    resultados/metricas/taxonomia_ruido.csv              (tarefa 1.1.2)
    resultados/metricas/distribuicao_match_score.csv     (tarefa 1.1.3, ADR-0010)
    latex/tcc_artigo/tabelas/tab_heterogeneidade_exemplos.tex (tarefa 1.1.4)
    resultados/figuras/distribuicao_source.png           (tarefa 1.1.5)

Status: tarefa 1.1 (spec 001) implementada. Falta 1.1.7 — leitura e
interpretação dos números pelo autor (docs/plano_desenvolvimento.md).

Uso:
    uv run python scripts/02_analise_exploratoria.py
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
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
    numero_estabelecimentos: int
    taxa_sobreposicao_lojas: float
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
LATEX_FIGURAS = Path("latex/tcc_artigo/figuras")


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


_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]+(?:[.,][0-9]+)?")


def tokenizar(texto: str, normalizar: bool = False) -> list[str]:
    """Tokeniza uma descrição, preservando números decimais (`1,35`, `0.9`) como um único token.

    `normalizar=True` aplica `normalizar_para_comparacao` antes de tokenizar
    (uppercase, sem acento) — usado para vocabulário/n-gramas comparáveis
    entre lojas; `normalizar=False` preserva o texto original, para exibir
    exemplos reais ao leitor.
    """
    texto_para_tokenizar = normalizar_para_comparacao(texto) if normalizar else texto
    return _TOKEN_RE.findall(texto_para_tokenizar)


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


class ComparacaoComprimentos(TypedDict):
    """Estatísticas descritivas de comprimento, bruto vs. dicionário (spec 001, EDA textual)."""

    caracteres_bruto: dict[str, float]
    caracteres_dicionario: dict[str, float]
    tokens_bruto: dict[str, float]
    tokens_dicionario: dict[str, float]


def comparar_comprimentos(
    df_produtos: pd.DataFrame, df_dicionario: pd.DataFrame
) -> ComparacaoComprimentos:
    """Compara o comprimento (caracteres e tokens) das descrições brutas com o dicionário.

    Evidencia a diferença de granularidade descritiva entre a base de PDV e
    o dicionário canônico (`main.tex`, "Variação de granularidade descritiva
    entre lojas").
    """
    caracteres_bruto = df_produtos["description"].str.len()
    caracteres_dicionario = df_dicionario["desc_alim"].str.len()
    tokens_bruto = df_produtos["description"].map(lambda texto: len(tokenizar(texto)))
    tokens_dicionario = df_dicionario["desc_alim"].map(lambda texto: len(tokenizar(texto)))
    return {
        "caracteres_bruto": caracteres_bruto.describe().to_dict(),
        "caracteres_dicionario": caracteres_dicionario.describe().to_dict(),
        "tokens_bruto": tokens_bruto.describe().to_dict(),
        "tokens_dicionario": tokens_dicionario.describe().to_dict(),
    }


_STOPWORDS_NGRAMAS = {"DE", "DA", "DO", "DOS", "DAS", "E", "COM", "EM", "C"}


def _marcas_de_ruido(descricao: str) -> list[str]:
    marcas = []
    if tem_unidade_colada(descricao):
        marcas.append("unidade colada")
    if esta_em_caixa_alta(descricao):
        marcas.append("caixa alta")
    if esta_sem_acentuacao(descricao):
        marcas.append("sem acentuação")
    if tem_abreviatura(descricao):
        marcas.append("abreviatura")
    return marcas


def _contem_subsequencia(tokens: list[str], ngrama: tuple[str, ...]) -> bool:
    tamanho = len(ngrama)
    return any(tuple(tokens[i : i + tamanho]) == ngrama for i in range(len(tokens) - tamanho + 1))


def contar_ngramas(
    df_produtos: pd.DataFrame, n: int, top_k: int = 10, seed: int = SEED
) -> list[dict[str, object]]:
    """Top-k n-gramas (tokens normalizados, sem stopwords mínimas) na base bruta.

    Cada linha traz uma descrição real que contém o n-grama (amostra
    determinística via `seed`) e quais detectores de ruído já existentes
    (spec 001, 1.1.2) disparam nessa descrição — não inventa exemplo novo,
    reaproveita os detectores já testados.
    """
    tokens_por_descricao = df_produtos["description"].map(
        lambda texto: [
            token for token in tokenizar(texto, normalizar=True) if token not in _STOPWORDS_NGRAMAS
        ]
    )
    contador: Counter[tuple[str, ...]] = Counter()
    for tokens in tokens_por_descricao:
        for i in range(len(tokens) - n + 1):
            contador[tuple(tokens[i : i + n])] += 1

    resultado: list[dict[str, object]] = []
    for ngrama, contagem in contador.most_common(top_k):
        mascara = tokens_por_descricao.map(
            lambda tokens, ng=ngrama: _contem_subsequencia(tokens, ng)
        )
        candidatos = df_produtos.loc[mascara, "description"]
        exemplo = str(candidatos.sample(1, random_state=seed).iloc[0]) if len(candidatos) else ""
        resultado.append(
            {
                "ngrama": " ".join(ngrama),
                "contagem": contagem,
                "exemplo": exemplo,
                "marca_ruido": ", ".join(_marcas_de_ruido(exemplo)) if exemplo else "-",
            }
        )
    return resultado


def _bloco_tabela_ngramas(titulo: str, label: str, linhas: list[dict[str, object]]) -> str:
    corpo = "\n".join(
        f"{escapar_latex(str(linha['ngrama']))} & {linha['contagem']} & "
        f"{escapar_latex(str(linha['marca_ruido']))} & {escapar_latex(str(linha['exemplo']))} \\\\"
        for linha in linhas
    )
    return (
        "\\begin{table}[htbp]\n"
        "\\centering\n"
        f"\\caption{{{titulo}}}\n"
        f"\\label{{{label}}}\n"
        "\\small\n"
        "\\resizebox{\\textwidth}{!}{%\n"
        "\\begin{tabular}{lrll}\n"
        "\\toprule\n"
        "N-grama & Contagem & Ruído & Exemplo real \\\\\n"
        "\\midrule\n"
        f"{corpo}\n"
        "\\bottomrule\n"
        "\\end{tabular}%\n"
        "}\n"
        "\\vspace{2mm}\n"
        "\\fonte{Elaborado pelo autor a partir de dados do projeto ALTA}\n"
        "\\end{table}\n"
    )


def gerar_tabela_ngramas_tex(
    unigramas: list[dict[str, object]],
    bigramas: list[dict[str, object]],
    trigramas: list[dict[str, object]],
    caminho: Path,
) -> None:
    """Escreve as três tabelas de n-gramas mais frequentes (EDA textual, item 2)."""
    conteudo = (
        "% Gerado automaticamente por scripts/02_analise_exploratoria.py — não editar à mão.\n"
        + _bloco_tabela_ngramas("Unigramas mais frequentes", "tab:ngramas-unigramas", unigramas)
        + "\n"
        + _bloco_tabela_ngramas("Bigramas mais frequentes", "tab:ngramas-bigramas", bigramas)
        + "\n"
        + _bloco_tabela_ngramas("Trigramas mais frequentes", "tab:ngramas-trigramas", trigramas)
    )
    caminho.write_text(conteudo, encoding="utf-8")


class Vocabulario(TypedDict):
    """Métricas de vocabulário e dispersão lexical (spec 001, EDA textual, item 4)."""

    tipos_brutos: int
    tipos_normalizados: int
    hapax: int
    dis_legomena: int
    tokens_exclusivos_uma_loja: int
    tokens_exclusivos_uma_loja_freq_min2: int
    vocabulario_dicionario: int
    tokens_dicionario_presentes_na_base: int
    fracao_cobertura_dicionario: float
    fracao_oov_bruto: float


def medir_vocabulario(df_produtos: pd.DataFrame, df_dicionario: pd.DataFrame) -> Vocabulario:
    """Mede tamanho de vocabulário, hapax/dis legomena, dispersão entre lojas e cobertura canônica.

    Sustenta o argumento de baixo recurso/especificidade de domínio: quanto
    do vocabulário é raro (hapax), exclusivo de uma única loja, ou fora do
    vocabulário do dicionário canônico (OOV).
    """
    tokens_brutos_por_descricao = df_produtos["description"].map(
        lambda texto: tokenizar(texto, normalizar=False)
    )
    tokens_normalizados_por_descricao = df_produtos["description"].map(
        lambda texto: tokenizar(texto, normalizar=True)
    )

    vocab_bruto: set[str] = set()
    for tokens in tokens_brutos_por_descricao:
        vocab_bruto.update(tokens)

    vocab_normalizado: Counter[str] = Counter()
    for tokens in tokens_normalizados_por_descricao:
        vocab_normalizado.update(tokens)

    hapax = sum(1 for frequencia in vocab_normalizado.values() if frequencia == 1)
    dis_legomena = sum(1 for frequencia in vocab_normalizado.values() if frequencia == 2)

    pares_token_fonte = (
        df_produtos.assign(_token=tokens_normalizados_por_descricao)[["source", "_token"]]
        .explode("_token")
        .dropna()
    )
    fontes_por_token = pares_token_fonte.groupby("_token")["source"].nunique()
    tokens_exclusivos = fontes_por_token[fontes_por_token == 1].index
    tokens_freq_min2 = {token for token, freq in vocab_normalizado.items() if freq >= 2}
    exclusivos_freq_min2 = sum(1 for token in tokens_exclusivos if token in tokens_freq_min2)

    vocab_dicionario: set[str] = set()
    for entrada in df_dicionario["desc_alim"]:
        vocab_dicionario.update(tokenizar(str(entrada), normalizar=True))

    presentes_na_base = vocab_dicionario & set(vocab_normalizado)
    fracao_cobertura = len(presentes_na_base) / len(vocab_dicionario) if vocab_dicionario else 0.0
    fracao_oov = 1 - (len(presentes_na_base) / len(vocab_normalizado)) if vocab_normalizado else 0.0

    return {
        "tipos_brutos": len(vocab_bruto),
        "tipos_normalizados": len(vocab_normalizado),
        "hapax": hapax,
        "dis_legomena": dis_legomena,
        "tokens_exclusivos_uma_loja": len(tokens_exclusivos),
        "tokens_exclusivos_uma_loja_freq_min2": exclusivos_freq_min2,
        "vocabulario_dicionario": len(vocab_dicionario),
        "tokens_dicionario_presentes_na_base": len(presentes_na_base),
        "fracao_cobertura_dicionario": fracao_cobertura,
        "fracao_oov_bruto": fracao_oov,
    }


def calcular_jaccard_entre_lojas(df_produtos: pd.DataFrame) -> pd.DataFrame:
    """Matriz de similaridade de Jaccard do vocabulário normalizado entre lojas (`source`).

    Mede a dispersão lexical entre lojas (spec 001, EDA textual, item 4):
    quanto menor a similaridade, mais cada rede usa um vocabulário próprio.
    """
    tokens_normalizados = df_produtos["description"].map(
        lambda texto: set(tokenizar(texto, normalizar=True))
    )
    vocab_por_loja = (
        df_produtos.assign(_tokens=tokens_normalizados)
        .groupby("source")["_tokens"]
        .apply(lambda grupos: set().union(*grupos))
    )
    fontes = sorted(vocab_por_loja.index)
    matriz = pd.DataFrame(index=fontes, columns=fontes, dtype=float)
    for fonte_a in fontes:
        for fonte_b in fontes:
            uniao = vocab_por_loja[fonte_a] | vocab_por_loja[fonte_b]
            intersecao = vocab_por_loja[fonte_a] & vocab_por_loja[fonte_b]
            matriz.loc[fonte_a, fonte_b] = len(intersecao) / len(uniao) if uniao else 0.0
    return matriz


def gerar_tabela_vocabulario_tex(vocabulario: Vocabulario, caminho: Path) -> None:
    """Escreve a tabela LaTeX de métricas de vocabulário (EDA textual, item 4)."""
    linhas_por_metrica: list[tuple[str, str]] = [
        ("Tipos (bruto, sensível a caixa/acento)", "tipos_brutos"),
        ("Tipos (normalizado)", "tipos_normalizados"),
        ("Hapax legomena (frequência 1)", "hapax"),
        ("Dis legomena (frequência 2)", "dis_legomena"),
        ("Tokens exclusivos de uma loja", "tokens_exclusivos_uma_loja"),
        ("— idem, com frequência ≥ 2", "tokens_exclusivos_uma_loja_freq_min2"),
        ("Vocabulário do dicionário canônico", "vocabulario_dicionario"),
        ("— presente na base bruta", "tokens_dicionario_presentes_na_base"),
    ]
    linhas_tabela = "\n".join(
        f"{rotulo} & {vocabulario[chave]} \\\\"  # type: ignore[literal-required]
        for rotulo, chave in linhas_por_metrica
    )
    cobertura_pct = vocabulario["fracao_cobertura_dicionario"] * 100
    oov_pct = vocabulario["fracao_oov_bruto"] * 100
    linha_cobertura = f"Cobertura do dicionário na base (\\%) & {cobertura_pct:.1f} \\\\"
    linha_oov = f"Tokens brutos fora do dicionário (OOV, \\%) & {oov_pct:.1f} \\\\"
    conteudo = (
        "% Gerado automaticamente por scripts/02_analise_exploratoria.py — não editar à mão.\n"
        "\\begin{table}[htbp]\n"
        "\\centering\n"
        "\\caption{Vocabulário e dispersão lexical entre lojas}\n"
        "\\label{tab:vocabulario}\n"
        "\\small\n"
        "\\begin{tabular}{lr}\n"
        "\\toprule\n"
        "Métrica & Valor \\\\\n"
        "\\midrule\n"
        f"{linhas_tabela}\n"
        f"{linha_cobertura}\n"
        f"{linha_oov}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\vspace{2mm}\n"
        "\\fonte{Elaborado pelo autor a partir de dados do projeto ALTA}\n"
        "\\end{table}\n"
    )
    caminho.write_text(conteudo, encoding="utf-8")


def gerar_figura_jaccard(matriz: pd.DataFrame, caminho: Path) -> None:
    """Gera o heatmap de similaridade de Jaccard do vocabulário entre lojas."""
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(matriz.to_numpy(), cmap="viridis", vmin=0, vmax=1)
    ax.set_xticks(range(len(matriz.columns)))
    ax.set_xticklabels(matriz.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(matriz.index)))
    ax.set_yticklabels(matriz.index)
    for i in range(len(matriz.index)):
        for j in range(len(matriz.columns)):
            ax.text(
                j,
                i,
                f"{matriz.iloc[i, j]:.2f}",
                ha="center",
                va="center",
                color="white" if matriz.iloc[i, j] < 0.5 else "black",
                fontsize=8,
            )
    ax.set_title("Similaridade de Jaccard do vocabulário entre lojas")
    fig.colorbar(im, ax=ax, label="Jaccard")
    fig.tight_layout()
    fig.savefig(caminho)
    plt.close(fig)


def gerar_figura_jaccard_tex(caminho: Path, nome_arquivo_png: str) -> None:
    """Escreve o wrapper LaTeX da figura de Jaccard entre lojas."""
    conteudo = (
        "% Gerado automaticamente por scripts/02_analise_exploratoria.py — não editar à mão.\n"
        "\\begin{figure}[htbp]\n"
        "\\centering\n"
        "\\caption{Similaridade de Jaccard do vocabulário entre lojas}\n"
        "\\label{fig:jaccard-lojas}\n"
        f"\\includegraphics[width=0.8\\textwidth]{{{nome_arquivo_png}}}\n"
        "\\vspace{2mm}\n"
        "\\fonte{Elaborado pelo autor a partir de dados do projeto ALTA}\n"
        "\\end{figure}\n"
    )
    caminho.write_text(conteudo, encoding="utf-8")


def detectar_inversoes_de_ordem(df_produtos: pd.DataFrame) -> dict[str, object]:
    """Taxa de grupos com o mesmo multiconjunto de tokens em ordem diferente entre lojas.

    Fecha a lacuna deixada em aberto na tarefa 1.1.2: a inversão de ordem só
    é observável comparando um par de descrições do mesmo produto, o que
    não exige a blocagem da tarefa 1.2 — basta agrupar pelo multiconjunto
    de tokens normalizados. Descrições idênticas repetidas em lojas
    diferentes (mesma ordem) não contam como inversão.
    """
    tokens_por_descricao = df_produtos["description"].map(
        lambda texto: tokenizar(texto, normalizar=True)
    )
    chave_multiconjunto = tokens_por_descricao.map(lambda tokens: " ".join(sorted(tokens)))
    ordem_original = tokens_por_descricao.map(lambda tokens: " ".join(tokens))

    agrupado = (
        df_produtos.assign(_chave=chave_multiconjunto, _ordem=ordem_original)
        .groupby("_chave")
        .agg(n_ordens_distintas=("_ordem", "nunique"), n_fontes_distintas=("source", "nunique"))
    )

    grupos_com_inversao = agrupado[
        (agrupado["n_ordens_distintas"] > 1) & (agrupado["n_fontes_distintas"] > 1)
    ]
    total_grupos = len(agrupado)
    taxa = len(grupos_com_inversao) / total_grupos if total_grupos else 0.0
    return {
        "grupos_totais": total_grupos,
        "grupos_com_inversao_entre_lojas": len(grupos_com_inversao),
        "taxa_inversao_entre_lojas": taxa,
    }


def gerar_tabela_comprimentos_tex(comparacao: ComparacaoComprimentos, caminho: Path) -> None:
    """Escreve a tabela LaTeX de comprimento de descrições (EDA textual, item 1)."""
    linhas_por_metrica = [
        ("Média", "mean"),
        ("Desvio-padrão", "std"),
        ("Mediana", "50%"),
        ("Mínimo", "min"),
        ("Máximo", "max"),
    ]
    linhas_tabela = "\n".join(
        f"{rotulo} & {comparacao['caracteres_bruto'][chave]:.1f} & "
        f"{comparacao['caracteres_dicionario'][chave]:.1f} & "
        f"{comparacao['tokens_bruto'][chave]:.1f} & "
        f"{comparacao['tokens_dicionario'][chave]:.1f} \\\\"
        for rotulo, chave in linhas_por_metrica
    )
    conteudo = (
        "% Gerado automaticamente por scripts/02_analise_exploratoria.py — não editar à mão.\n"
        "\\begin{table}[htbp]\n"
        "\\centering\n"
        "\\caption{Comprimento das descrições: base bruta vs. dicionário canônico}\n"
        "\\label{tab:comprimento-descricoes}\n"
        "\\small\n"
        "\\begin{tabular}{lrrrr}\n"
        "\\toprule\n"
        " & \\multicolumn{2}{c}{Caracteres} & \\multicolumn{2}{c}{Tokens} \\\\\n"
        "Estatística & Bruto & Dicionário & Bruto & Dicionário \\\\\n"
        "\\midrule\n"
        f"{linhas_tabela}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\vspace{2mm}\n"
        "\\fonte{Elaborado pelo autor a partir de dados do projeto ALTA}\n"
        "\\end{table}\n"
    )
    caminho.write_text(conteudo, encoding="utf-8")


def gerar_figura_comprimentos(
    df_produtos: pd.DataFrame, df_dicionario: pd.DataFrame, caminho: Path
) -> None:
    """Gera histogramas sobrepostos de comprimento (caracteres/tokens), bruto vs. dicionário."""
    caracteres_bruto = df_produtos["description"].str.len()
    caracteres_dicionario = df_dicionario["desc_alim"].str.len()
    tokens_bruto = df_produtos["description"].map(lambda texto: len(tokenizar(texto)))
    tokens_dicionario = df_dicionario["desc_alim"].map(lambda texto: len(tokenizar(texto)))

    fig, (ax_caracteres, ax_tokens) = plt.subplots(1, 2, figsize=(10, 4))

    ax_caracteres.hist(caracteres_bruto, bins=20, alpha=0.6, density=True, label="Bruto")
    ax_caracteres.hist(caracteres_dicionario, bins=20, alpha=0.6, density=True, label="Dicionário")
    ax_caracteres.set_xlabel("Caracteres")
    ax_caracteres.set_ylabel("Densidade")
    ax_caracteres.legend()

    ax_tokens.hist(tokens_bruto, bins=15, alpha=0.6, density=True, label="Bruto")
    ax_tokens.hist(tokens_dicionario, bins=15, alpha=0.6, density=True, label="Dicionário")
    ax_tokens.set_xlabel("Tokens")
    ax_tokens.legend()

    fig.suptitle("Comprimento das descrições: base bruta vs. dicionário canônico")
    fig.tight_layout()
    fig.savefig(caminho)
    plt.close(fig)


def gerar_figura_comprimentos_tex(caminho: Path, nome_arquivo_png: str) -> None:
    """Escreve o wrapper LaTeX (`figure` + `\\includegraphics`) da figura de comprimentos."""
    conteudo = (
        "% Gerado automaticamente por scripts/02_analise_exploratoria.py — não editar à mão.\n"
        "\\begin{figure}[htbp]\n"
        "\\centering\n"
        "\\caption{Comprimento das descrições: base bruta vs. dicionário canônico}\n"
        "\\label{fig:comprimento-descricoes}\n"
        f"\\includegraphics[width=\\textwidth]{{{nome_arquivo_png}}}\n"
        "\\vspace{2mm}\n"
        "\\fonte{Elaborado pelo autor a partir de dados do projeto ALTA}\n"
        "\\end{figure}\n"
    )
    caminho.write_text(conteudo, encoding="utf-8")


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
        "numero_estabelecimentos": df_produtos["location"].nunique(),
        "taxa_sobreposicao_lojas": estimar_sobreposicao_entre_lojas(df_produtos),
        "distribuicao_source": df_produtos["source"].value_counts().to_dict(),
        "distribuicao_location": df_produtos["location"].value_counts().to_dict(),
        "distribuicao_estado": estados.value_counts().to_dict(),
    }


def estimar_sobreposicao_entre_lojas(df_produtos: pd.DataFrame) -> float:
    """Taxa ingênua de sobreposição de produtos entre lojas (`main.tex` §4.7).

    Mede a fração de descrições normalizadas (texto exato, sem blocagem)
    que aparecem em mais de uma fonte (`source`). **Isto subestima a
    sobreposição real de produtos**: o mesmo produto físico raramente tem
    texto idêntico entre lojas — é exatamente o problema de heterogeneidade
    que motiva este TCC. A blocagem da tarefa 1.2 (TF-IDF/BM25) dá uma
    estimativa melhor; este número é só o piso ingênuo exigido pela
    proposta antes da blocagem existir.
    """
    descricoes_normalizadas = df_produtos["description"].map(normalizar_para_comparacao)
    fontes_por_descricao = df_produtos.groupby(descricoes_normalizadas)["source"].nunique()
    if len(fontes_por_descricao) == 0:
        return 0.0
    return float((fontes_por_descricao > 1).sum() / len(fontes_por_descricao))


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
        {"metrica": "numero_estabelecimentos", "valor": contagens["numero_estabelecimentos"]},
        {
            "metrica": "taxa_sobreposicao_lojas",
            "valor": contagens["taxa_sobreposicao_lojas"],
        },
    ]
    pd.DataFrame(linhas).to_csv(caminho, index=False)


def _salvar_inversoes_ordem(resultado: dict[str, object], caminho: Path) -> None:
    linhas = [{"metrica": chave, "valor": valor} for chave, valor in resultado.items()]
    pd.DataFrame(linhas).to_csv(caminho, index=False)


def _salvar_vocabulario(vocabulario: Vocabulario, caminho: Path) -> None:
    linhas = [{"metrica": chave, "valor": valor} for chave, valor in vocabulario.items()]
    pd.DataFrame(linhas).to_csv(caminho, index=False)


def _salvar_ngramas(
    unigramas: list[dict[str, object]],
    bigramas: list[dict[str, object]],
    trigramas: list[dict[str, object]],
    caminho: Path,
) -> None:
    linhas = [
        {"n": n, **linha}
        for n, grupo in ((1, unigramas), (2, bigramas), (3, trigramas))
        for linha in grupo
    ]
    pd.DataFrame(linhas).to_csv(caminho, index=False)


def _salvar_comparacao_comprimentos(comparacao: ComparacaoComprimentos, caminho: Path) -> None:
    series: list[tuple[str, dict[str, float]]] = [
        ("caracteres_bruto", comparacao["caracteres_bruto"]),
        ("caracteres_dicionario", comparacao["caracteres_dicionario"]),
        ("tokens_bruto", comparacao["tokens_bruto"]),
        ("tokens_dicionario", comparacao["tokens_dicionario"]),
    ]
    linhas = [
        {"serie": nome_serie, "metrica": metrica, "valor": valor}
        for nome_serie, serie in series
        for metrica, valor in serie.items()
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
    diretorio_latex_figuras: Path = LATEX_FIGURAS,
) -> ContagensBasicas:
    """Calcula e persiste as estatísticas descritivas da spec 001 (EDA, incl. tarefas 1.1.1-1.1.4).

    Ver specs/001-construcao-dataset-ground-truth/requirements.md.
    """
    df_produtos = carregar_produtos(diretorio_brutos)
    df_dicionario = carregar_dicionario(diretorio_brutos)
    contagens = calcular_contagens_basicas(df_produtos, df_dicionario)
    ruido = caracterizar_ruido_pdv(df_produtos)
    distribuicao_match_score = caracterizar_match_score(df_produtos)
    exemplos_heterogeneidade = selecionar_exemplos_heterogeneidade(df_produtos, df_dicionario)
    comparacao_comprimentos = comparar_comprimentos(df_produtos, df_dicionario)
    unigramas = contar_ngramas(df_produtos, n=1, top_k=10)
    bigramas = contar_ngramas(df_produtos, n=2, top_k=10)
    trigramas = contar_ngramas(df_produtos, n=3, top_k=10)
    vocabulario = medir_vocabulario(df_produtos, df_dicionario)
    jaccard_lojas = calcular_jaccard_entre_lojas(df_produtos)
    inversoes_ordem = detectar_inversoes_de_ordem(df_produtos)

    diretorio_saida.mkdir(parents=True, exist_ok=True)
    _salvar_contagens_escalares(contagens, diretorio_saida / "estatisticas_descritivas.csv")
    _salvar_distribuicoes(contagens, diretorio_saida / "distribuicoes_categoricas.csv")
    _salvar_ruido_pdv(ruido, contagens["total_registros"], diretorio_saida / "taxonomia_ruido.csv")
    _salvar_match_score(distribuicao_match_score, diretorio_saida / "distribuicao_match_score.csv")
    _salvar_comparacao_comprimentos(
        comparacao_comprimentos, diretorio_saida / "comprimento_descricoes.csv"
    )
    _salvar_ngramas(unigramas, bigramas, trigramas, diretorio_saida / "ngramas.csv")
    _salvar_vocabulario(vocabulario, diretorio_saida / "vocabulario.csv")
    jaccard_lojas.to_csv(diretorio_saida / "jaccard_lojas.csv")
    _salvar_inversoes_ordem(inversoes_ordem, diretorio_saida / "inversoes_ordem.csv")

    diretorio_latex_tabelas.mkdir(parents=True, exist_ok=True)
    gerar_tabela_heterogeneidade_tex(
        exemplos_heterogeneidade, diretorio_latex_tabelas / "tab_heterogeneidade_exemplos.tex"
    )
    gerar_tabela_comprimentos_tex(
        comparacao_comprimentos, diretorio_latex_tabelas / "tab_comprimento_descricoes.tex"
    )
    gerar_tabela_ngramas_tex(
        unigramas, bigramas, trigramas, diretorio_latex_tabelas / "tab_ngramas.tex"
    )
    gerar_tabela_vocabulario_tex(vocabulario, diretorio_latex_tabelas / "tab_vocabulario.tex")

    diretorio_figuras.mkdir(parents=True, exist_ok=True)
    gerar_figura_distribuicao_source(contagens, diretorio_figuras / "distribuicao_source.png")

    diretorio_latex_figuras.mkdir(parents=True, exist_ok=True)
    gerar_figura_comprimentos(
        df_produtos, df_dicionario, diretorio_latex_figuras / "fig_comprimento_descricoes.png"
    )
    gerar_figura_comprimentos_tex(
        diretorio_latex_figuras / "fig_comprimento_descricoes.tex", "fig_comprimento_descricoes.png"
    )
    gerar_figura_jaccard(jaccard_lojas, diretorio_latex_figuras / "fig_jaccard_lojas.png")
    gerar_figura_jaccard_tex(
        diretorio_latex_figuras / "fig_jaccard_lojas.tex", "fig_jaccard_lojas.png"
    )

    logger.info(
        "EDA: %d registros, %d entradas no dicionário, %d exemplos de heterogeneidade. "
        "Estatísticas em %s, tabelas em %s, figuras em %s",
        contagens["total_registros"],
        contagens["total_entradas_dicionario"],
        len(exemplos_heterogeneidade),
        diretorio_saida,
        diretorio_latex_tabelas,
        diretorio_latex_figuras,
    )
    return contagens


def main() -> None:
    estatisticas_descritivas(
        DADOS_BRUTOS, RESULTADOS_METRICAS, LATEX_TABELAS, RESULTADOS_FIGURAS, LATEX_FIGURAS
    )


if __name__ == "__main__":
    main()
