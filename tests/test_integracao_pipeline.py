"""
test_integracao_pipeline.py — Camada 3: integração leve do pipeline (tmp_path).

Ver AGENTS.md, seção 3, camada 3: "um teste de pipeline em tmp_path que
verifica a passagem de artefatos 01→06".

Scripts 01 (validação + limpeza, ADR-0012) e 02 (EDA sobre a base limpa)
implementados; 03-06 são esqueletos que levantam NotImplementedError
apontando para a spec correspondente.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pandas as pd
import pytest
import yaml

_ROOT = os.path.join(os.path.dirname(__file__), "..")

_CONFIG_EDA_SEM_CONFIRMADOS = (
    "seed: 42\nn_candidatos_heterogeneidade: 20\nheterogeneidade_confirmados: []\n"
)


def _load(filename: str):
    path = os.path.join(_ROOT, "scripts", filename)
    spec = importlib.util.spec_from_file_location(filename, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


coleta_dados = _load("01_coleta_dados.py")
analise_exploratoria = _load("02_analise_exploratoria.py")


def test_script_01_valida_brutos_reais_em_tmp_path(
    tmp_path: Path,
    produtos_brutos_exemplo: pd.DataFrame,
    dicionario_canonico_exemplo: pd.DataFrame,
) -> None:
    """01_coleta_dados.py deve validar um par de brutos com schema correto, em tmp_path."""
    dados_brutos = tmp_path / "dados" / "brutos"
    dados_brutos.mkdir(parents=True)

    produtos_brutos_exemplo.to_csv(dados_brutos / "todos_mercados_2026-01-01.csv", index=False)
    dicionario_canonico_exemplo.to_csv(
        dados_brutos / "dicionario_canonico.csv", sep=";", index=False
    )

    caminho_mercados = coleta_dados.localizar_arquivo_mercados(dados_brutos)
    df_produtos = coleta_dados.validar_produtos_coletados(caminho_mercados)
    df_dicionario = coleta_dados.validar_dicionario_canonico(
        dados_brutos / "dicionario_canonico.csv"
    )

    assert len(df_produtos) == len(produtos_brutos_exemplo)
    assert len(df_dicionario) == len(dicionario_canonico_exemplo)


def test_script_02_eda_gera_estatisticas_descritivas_em_tmp_path(
    tmp_path: Path,
    produtos_brutos_variados_exemplo: pd.DataFrame,
    dicionario_canonico_exemplo: pd.DataFrame,
) -> None:
    """02 descreve a base limpa gravada pelo 01, não os brutos (ADR-0012)."""
    dados_brutos = tmp_path / "dados" / "brutos"
    dados_brutos.mkdir(parents=True)
    dados_processados = tmp_path / "dados" / "processados"
    resultados_metricas = tmp_path / "resultados" / "metricas"
    resultados_figuras = tmp_path / "resultados" / "figuras"
    latex_tabelas = tmp_path / "latex" / "tcc_artigo" / "tabelas"
    latex_figuras = tmp_path / "latex" / "tcc_artigo" / "figuras"

    # Uma duplicata exata nos brutos: a EDA só pode contá-la se ler a base errada.
    pd.concat(
        [produtos_brutos_variados_exemplo, produtos_brutos_variados_exemplo.iloc[[0]]],
        ignore_index=True,
    ).to_csv(dados_brutos / "todos_mercados_2026-01-01.csv", index=False)
    dicionario_canonico_exemplo.to_csv(
        dados_brutos / "dicionario_canonico.csv", sep=";", index=False
    )
    coleta_dados.executar_limpeza(dados_brutos, dados_processados)
    config_eda = tmp_path / "eda.yaml"
    config_eda.write_text(_CONFIG_EDA_SEM_CONFIRMADOS, encoding="utf-8")

    contagens = analise_exploratoria.estatisticas_descritivas(
        dados_processados,
        diretorio_brutos=dados_brutos,
        caminho_config=config_eda,
        diretorio_saida=resultados_metricas,
        diretorio_latex_tabelas=latex_tabelas,
        diretorio_figuras=resultados_figuras,
        diretorio_latex_figuras=latex_figuras,
    )

    assert contagens["total_registros"] == 4
    assert contagens["total_entradas_dicionario"] == 2

    df_escalares = pd.read_csv(resultados_metricas / "estatisticas_descritivas.csv")
    linha = df_escalares.set_index("metrica")["valor"]
    assert int(linha["total_registros"]) == 4
    assert int(linha["total_entradas_dicionario"]) == 2
    assert int(linha["numero_estabelecimentos"]) == 3
    assert float(linha["taxa_sobreposicao_lojas"]) == pytest.approx(1 / 3)

    df_distribuicoes = pd.read_csv(resultados_metricas / "distribuicoes_categoricas.csv")
    assert set(df_distribuicoes["dimensao"]) == {"source", "location", "estado"}

    df_ruido = pd.read_csv(resultados_metricas / "taxonomia_ruido.csv")
    linha_ruido = df_ruido.set_index("categoria")["contagem"]
    assert int(linha_ruido["unidade_colada"]) == 4
    assert int(linha_ruido["sem_acentuacao"]) == 3

    df_match_score = pd.read_csv(resultados_metricas / "distribuicao_match_score.csv")
    linha_match_score = df_match_score.set_index("metrica")["valor"]
    assert int(linha_match_score["contagem"]) == 4
    assert float(linha_match_score["media"]) == pytest.approx(0.79)

    # Sem pares confirmados pelo autor, a tabela de heterogeneidade não é regenerada.
    assert (resultados_metricas / "candidatos_heterogeneidade.csv").exists()
    assert not (latex_tabelas / "tab_heterogeneidade_exemplos.tex").exists()

    caminho_figura = resultados_figuras / "distribuicao_source.png"
    assert caminho_figura.exists()
    assert caminho_figura.stat().st_size > 0

    df_comprimentos = pd.read_csv(resultados_metricas / "comprimento_descricoes.csv")
    assert set(df_comprimentos["serie"]) == {
        "caracteres_bruto",
        "caracteres_dicionario",
        "tokens_bruto",
        "tokens_dicionario",
    }

    assert (latex_tabelas / "tab_comprimento_descricoes.tex").exists()
    assert (latex_figuras / "fig_comprimento_descricoes.png").exists()
    assert (latex_figuras / "fig_comprimento_descricoes.tex").exists()

    df_ngramas = pd.read_csv(resultados_metricas / "ngramas.csv")
    assert set(df_ngramas["n"]) == {1, 2, 3}
    assert (latex_tabelas / "tab_ngramas.tex").exists()

    df_vocabulario = pd.read_csv(resultados_metricas / "vocabulario.csv")
    linha_vocabulario = df_vocabulario.set_index("metrica")["valor"]
    assert int(linha_vocabulario["tipos_normalizados"]) == 16
    assert (latex_tabelas / "tab_vocabulario.tex").exists()

    df_jaccard = pd.read_csv(resultados_metricas / "jaccard_lojas.csv", index_col=0)
    assert float(df_jaccard.loc["diniz_api", "guedes_api"]) == pytest.approx(1.0)
    assert (latex_figuras / "fig_jaccard_lojas.png").exists()
    assert (latex_figuras / "fig_jaccard_lojas.tex").exists()

    df_inversoes = pd.read_csv(resultados_metricas / "inversoes_ordem.csv")
    linha_inversoes = df_inversoes.set_index("metrica")["valor"]
    assert int(linha_inversoes["grupos_com_inversao_entre_lojas"]) == 0

    df_formas_unidade = pd.read_csv(resultados_metricas / "formas_unidade.csv")
    por_forma = df_formas_unidade.set_index("forma")["contagem"]
    assert int(por_forma["l"]) == 2
    assert int(por_forma["kg"]) == 2
    assert (latex_tabelas / "tab_formas_unidade.tex").exists()

    df_exemplos_ruido = pd.read_csv(resultados_metricas / "exemplos_ruido.csv")
    assert set(df_exemplos_ruido["tipo"]) <= {"abreviação", "tipografia", "unidade", "inversão"}
    assert (latex_tabelas / "tab_exemplos_ruido.tex").exists()


def test_gerar_tabela_comprimentos_tex_escreve_arquivo_com_estatisticas(
    tmp_path: Path,
    produtos_brutos_variados_exemplo: pd.DataFrame,
    dicionario_canonico_exemplo: pd.DataFrame,
) -> None:
    comparacao = analise_exploratoria.comparar_comprimentos(
        produtos_brutos_variados_exemplo, dicionario_canonico_exemplo
    )
    caminho_tex = tmp_path / "tab_comprimento_descricoes.tex"

    analise_exploratoria.gerar_tabela_comprimentos_tex(comparacao, caminho_tex)

    conteudo = caminho_tex.read_text(encoding="utf-8")
    assert r"\label{tab:comprimento-descricoes}" in conteudo
    assert "bruta" not in conteudo.lower()  # descreve a base limpa (ADR-0012)
    assert "29.5" in conteudo
    assert "12.0" in conteudo


def test_gerar_figura_comprimentos_escreve_arquivo_png(
    tmp_path: Path,
    produtos_brutos_variados_exemplo: pd.DataFrame,
    dicionario_canonico_exemplo: pd.DataFrame,
) -> None:
    caminho_png = tmp_path / "fig_comprimento_descricoes.png"

    analise_exploratoria.gerar_figura_comprimentos(
        produtos_brutos_variados_exemplo, dicionario_canonico_exemplo, caminho_png
    )
    caminho_tex = tmp_path / "fig_comprimento_descricoes.tex"
    analise_exploratoria.gerar_figura_comprimentos_tex(caminho_tex, caminho_png.name)

    assert "bruta" not in caminho_tex.read_text(encoding="utf-8").lower()  # ADR-0012
    assert caminho_png.exists()
    assert caminho_png.stat().st_size > 0


def test_gerar_tabela_ngramas_tex_escreve_tres_blocos(tmp_path: Path) -> None:
    linhas = [
        {
            "ngrama": "ARROZ",
            "contagem": 120,
            "marca_ruido": "sem acentuação",
            "exemplo": "Arroz Branco 1kg",
        }
    ]
    caminho_tex = tmp_path / "tab_ngramas.tex"

    analise_exploratoria.gerar_tabela_ngramas_tex(linhas, linhas, linhas, caminho_tex)

    conteudo = caminho_tex.read_text(encoding="utf-8")
    assert r"\label{tab:ngramas-unigramas}" in conteudo
    assert r"\label{tab:ngramas-bigramas}" in conteudo
    assert r"\label{tab:ngramas-trigramas}" in conteudo
    assert "ARROZ" in conteudo
    assert "Arroz Branco 1kg" in conteudo


def test_gerar_tabela_vocabulario_tex_escreve_arquivo_com_metricas(
    tmp_path: Path,
    produtos_brutos_variados_exemplo: pd.DataFrame,
    dicionario_canonico_exemplo: pd.DataFrame,
) -> None:
    vocabulario = analise_exploratoria.medir_vocabulario(
        produtos_brutos_variados_exemplo, dicionario_canonico_exemplo
    )
    caminho_tex = tmp_path / "tab_vocabulario.tex"

    analise_exploratoria.gerar_tabela_vocabulario_tex(vocabulario, caminho_tex)

    conteudo = caminho_tex.read_text(encoding="utf-8")
    assert r"\label{tab:vocabulario}" in conteudo
    assert "base bruta" not in conteudo  # descreve a base limpa (ADR-0012)
    assert "18" in conteudo
    assert "0.75" in conteudo or "75.0" in conteudo


def test_gerar_figura_jaccard_escreve_arquivo_png(
    tmp_path: Path, produtos_brutos_variados_exemplo: pd.DataFrame
) -> None:
    matriz = analise_exploratoria.calcular_jaccard_entre_lojas(produtos_brutos_variados_exemplo)
    caminho_png = tmp_path / "fig_jaccard_lojas.png"

    analise_exploratoria.gerar_figura_jaccard(matriz, caminho_png)

    assert caminho_png.exists()
    assert caminho_png.stat().st_size > 0


def test_gerar_tabela_formas_unidade_tex_escreve_arquivo(tmp_path: Path) -> None:
    formas = [{"unidade_canonica": "grama", "forma": "GR", "contagem": 1131}]
    caminho_tex = tmp_path / "tab_formas_unidade.tex"

    analise_exploratoria.gerar_tabela_formas_unidade_tex(formas, caminho_tex)

    conteudo = caminho_tex.read_text(encoding="utf-8")
    assert r"\label{tab:formas-unidade}" in conteudo
    assert "grama" in conteudo
    assert "1131" in conteudo


def test_gerar_tabela_exemplos_ruido_tex_escreve_arquivo(tmp_path: Path) -> None:
    exemplos = [
        {"tipo": "abreviação", "descricao_a": "Canjica C/ Pacoca 200g", "descricao_b": ""},
        {
            "tipo": "inversão",
            "descricao_a": "Suco Uva Del Valle 1,5L",
            "descricao_b": "Suco Del Valle Uva 1,5l",
        },
    ]
    caminho_tex = tmp_path / "tab_exemplos_ruido.tex"

    analise_exploratoria.gerar_tabela_exemplos_ruido_tex(exemplos, caminho_tex)

    conteudo = caminho_tex.read_text(encoding="utf-8")
    assert r"\label{tab:exemplos-ruido}" in conteudo
    assert "Canjica C/ Pacoca 200g" in conteudo
    assert "Suco Uva Del Valle 1,5L" in conteudo
    assert "Suco Del Valle Uva 1,5l" in conteudo


def test_gerar_tabela_heterogeneidade_tex_escreve_arquivo_com_exemplo_real(
    tmp_path: Path,
) -> None:
    exemplos = [
        {
            "supermercado_a": "Vinho Chileno Cono Sur Carmenere 750ml",
            "supermercado_b": "VH CHI CONO SUR 1551 CARMENERE 750ML",
        }
    ]
    caminho_tex = tmp_path / "tab_heterogeneidade_exemplos.tex"

    analise_exploratoria.gerar_tabela_heterogeneidade_tex(exemplos, caminho_tex)

    conteudo = caminho_tex.read_text(encoding="utf-8")
    assert "Vinho Chileno Cono Sur Carmenere 750ml" in conteudo
    assert "VH CHI CONO SUR 1551 CARMENERE 750ML" in conteudo
    assert r"\begin{tabular}{ll}" in conteudo
    assert "Canônico" not in conteudo
    assert r"\label{tab:heterogeneidade}" in conteudo
    assert "% Gerado automaticamente" in conteudo


def test_script_01_limpeza_grava_base_limpa_sem_colunas_alta_em_tmp_path(
    tmp_path: Path,
    produtos_brutos_variados_exemplo: pd.DataFrame,
    dicionario_canonico_exemplo: pd.DataFrame,
) -> None:
    """01_coleta_dados.py: limpeza grava parquet + relatório em processados (ADR-0012)."""
    dados_brutos = tmp_path / "dados" / "brutos"
    dados_brutos.mkdir(parents=True)
    dados_processados = tmp_path / "dados" / "processados"
    brutos = pd.concat(
        [produtos_brutos_variados_exemplo, produtos_brutos_variados_exemplo.iloc[[0]]],
        ignore_index=True,
    ).assign(codg_item=6300113.0, desc_ref="ARROZ BRANCO")
    brutos.to_csv(dados_brutos / "todos_mercados_2026-01-01.csv", index=False)
    dicionario_canonico_exemplo.assign(**{"Unnamed: 3": None}).to_csv(
        dados_brutos / "dicionario_canonico.csv", sep=";", index=False
    )

    relatorio = coleta_dados.executar_limpeza(dados_brutos, dados_processados)

    produtos = pd.read_parquet(dados_processados / "produtos_limpos.parquet")
    dicionario = pd.read_parquet(dados_processados / "dicionario_limpo.parquet")
    assert relatorio["duplicatas_exatas_removidas"] == 1
    assert len(produtos) == len(produtos_brutos_variados_exemplo)
    assert not {"codg_item", "desc_ref", "match_score"} & set(produtos.columns)
    assert "Unnamed: 3" not in dicionario.columns
    rastreio = (dados_processados / "relatorio_limpeza.json").read_text(encoding="utf-8")
    assert "sha256_brutos" in rastreio


# ── Script 03: blocagem produto × dicionário (spec 001, RF1 "1a") ───────────

construcao_dataset = _load("03_construcao_dataset.py")

_PRODUTOS_BLOCAGEM = [
    "Arroz Branco Tio Joao 1kg",
    "Arroz Integral Camil 1kg",
    "Feijao Carioca Kicaldo 1kg",
    "Leite Integral Italac 1L",
    "Agua Mineral Sem Gas Indaia 5l",
    "Leite Desnatado Italac 1L",
    "ARROZ BRANCO TIO JOAO 1KG",  # duplicata por texto normalizado do primeiro
]
_ENTRADA_POR_PALAVRA = {
    "ARROZ": "ARROZ BRANCO",
    "FEIJAO": "FEIJAO CARIOCA",
    "LEITE": "LEITE INTEGRAL",
    "AGUA": "AGUA MINERAL",
}


def _preparar_base_limpa(tmp_path: Path, metodo=None, k=None) -> tuple[Path, Path, Path]:
    processados = tmp_path / "dados" / "processados"
    processados.mkdir(parents=True)
    pd.DataFrame(
        {
            "product_id": range(1, len(_PRODUTOS_BLOCAGEM) + 1),
            "description": _PRODUTOS_BLOCAGEM,
            "und_val": 1.0,
            "und_med": "KG",
            "source": "a_api",
            "texto_repetido_na_loja": False,
            "preco_invalido": False,
        }
    ).to_parquet(processados / "produtos_limpos.parquet", index=False)
    pd.DataFrame(
        {
            "desc_alim": [
                "ARROZ BRANCO",
                "ARROZ INTEGRAL",
                "FEIJAO CARIOCA",
                "LEITE INTEGRAL",
                "LEITE DESNATADO",
                "AGUA MINERAL",
            ],
            "codg_item1": [1, 2, 3, 4, 5, 6],
            "cod_padrao": [99] * 6,
        }
    ).to_parquet(processados / "dicionario_limpo.parquet", index=False)
    config = tmp_path / "blocagem.yaml"
    config.write_text(
        "seed: 42\nn_amostra: 4\nks: [1, 5, 10, 20, 50, 100]\nmetodos: [tfidf, bm25]\n"
        f"metodo: {metodo or 'null'}\nk: {k or 'null'}\n",
        encoding="utf-8",
    )
    return processados, tmp_path / "resultados" / "metricas", config


def _anotar(planilha: Path) -> None:
    df = pd.read_csv(planilha, sep=";", dtype=str, keep_default_na=False)
    df["entrada_indicada"] = [
        next(v for p, v in _ENTRADA_POR_PALAVRA.items() if p in d.upper()) for d in df["descricao"]
    ]
    df.to_csv(planilha, sep=";", index=False)


def test_carregar_config_le_o_yaml_versionado(tmp_path: Path) -> None:
    _, _, config = _preparar_base_limpa(tmp_path)
    cfg = construcao_dataset.carregar_config(config)
    assert cfg["seed"] == 42
    assert cfg["ks"] == [1, 5, 10, 20, 50, 100]
    assert cfg["metodo"] is None and cfg["k"] is None


def test_carregar_config_rejeita_metodo_fora_de_tfidf_bm25(tmp_path: Path) -> None:
    _, _, config = _preparar_base_limpa(tmp_path, metodo="levenshtein", k=10)
    with pytest.raises(ValueError, match="metodo"):
        construcao_dataset.carregar_config(config)


def test_carregar_config_rejeita_k_fora_da_varredura(tmp_path: Path) -> None:
    _, _, config = _preparar_base_limpa(tmp_path, metodo="bm25", k=7)
    with pytest.raises(ValueError, match="k"):
        construcao_dataset.carregar_config(config)


def test_script_03_gera_planilha_cega_sem_candidatos_e_aguarda_anotacao(tmp_path: Path) -> None:
    processados, metricas, config = _preparar_base_limpa(tmp_path)

    construcao_dataset.executar_blocagem(
        processados, metricas, config, diretorio_latex_tabelas=tmp_path / "tabelas"
    )

    planilha = pd.read_csv(
        processados / "anotacoes_amostra_cega.csv", sep=";", dtype=str, keep_default_na=False
    )
    assert len(planilha) == 4
    assert not {"codg_item", "desc_ref", "match_score", "score", "desc_alim"} & set(
        planilha.columns
    )
    assert (planilha["entrada_indicada"] == "").all()
    assert not (metricas / "recall_blocagem.csv").exists()
    assert not (tmp_path / "tabelas" / "tab_recall_blocagem.tex").exists()
    assert not (processados / "candidatos_blocagem.parquet").exists()


def test_script_03_nao_sobrescreve_planilha_ja_anotada(tmp_path: Path) -> None:
    processados, metricas, config = _preparar_base_limpa(tmp_path)
    construcao_dataset.executar_blocagem(
        processados, metricas, config, diretorio_latex_tabelas=tmp_path / "tabelas"
    )
    _anotar(processados / "anotacoes_amostra_cega.csv")
    antes = (processados / "anotacoes_amostra_cega.csv").read_text(encoding="utf-8")

    construcao_dataset.executar_blocagem(
        processados, metricas, config, diretorio_latex_tabelas=tmp_path / "tabelas"
    )

    assert (processados / "anotacoes_amostra_cega.csv").read_text(encoding="utf-8") == antes


def test_script_03_com_planilha_anotada_grava_recall_por_metodo_e_k(tmp_path: Path) -> None:
    processados, metricas, config = _preparar_base_limpa(tmp_path)
    construcao_dataset.executar_blocagem(
        processados, metricas, config, diretorio_latex_tabelas=tmp_path / "tabelas"
    )
    _anotar(processados / "anotacoes_amostra_cega.csv")

    construcao_dataset.executar_blocagem(
        processados, metricas, config, diretorio_latex_tabelas=tmp_path / "tabelas"
    )

    recall = pd.read_csv(metricas / "recall_blocagem.csv")
    assert len(recall) == 2 * 6
    assert set(recall["metodo"]) == {"tfidf", "bm25"}
    assert set(recall["k"]) == {1, 5, 10, 20, 50, 100}
    assert recall["recall"].between(0, 1).all()
    assert (recall[recall["k"] == 100]["recall"] == 1.0).all()
    tabela = (tmp_path / "tabelas" / "tab_recall_blocagem.tex").read_text(encoding="utf-8")
    assert "TF-IDF" in tabela and "BM25" in tabela
    assert r"\label{tab:recall-blocagem}" in tabela


def test_script_03_com_metodo_e_k_congelados_grava_candidatos_sem_colunas_alta(
    tmp_path: Path,
) -> None:
    processados, metricas, config = _preparar_base_limpa(tmp_path, metodo="bm25", k=5)

    construcao_dataset.executar_blocagem(
        processados, metricas, config, diretorio_latex_tabelas=tmp_path / "tabelas"
    )

    candidatos = pd.read_parquet(processados / "candidatos_blocagem.parquet")
    assert not {"codg_item", "desc_ref", "match_score"} & set(candidatos.columns)
    assert set(candidatos["metodo"]) == {"bm25"}
    assert candidatos["rank"].max() <= 5
    assert candidatos["id_produto"].nunique() == 6  # 7 registros, 6 textos normalizados distintos


# ── Script 02: pares de mesmo SKU para a Tabela de heterogeneidade (ADR-0014) ──


def _brutos_com_par_mesmo_sku(produtos_brutos_variados_exemplo: pd.DataFrame) -> pd.DataFrame:
    extra = pd.DataFrame(
        [
            {
                "product_id": 20,
                "description": "Vinho Chileno Cono Sur Carmenere 750ml",
                "unit": "UN",
                "price": 39.9,
                "location": "CE, Fortaleza, Centro",
                "source": "diniz_api",
                "collected_at": "2026-09-10 12:40:00",
                "match_score": 0.5,
            },
            {
                "product_id": 21,
                "description": "VH CHI CONO SUR 1551 CARMENERE 750ML",
                "unit": "UN",
                "price": 41.5,
                "location": "PI, Teresina, Centro",
                "source": "guedes_api",
                "collected_at": "2026-09-10 12:41:00",
                "match_score": 0.4,
            },
        ]
    )
    return pd.concat([produtos_brutos_variados_exemplo, extra], ignore_index=True)


def _rodar_eda_com_par_mesmo_sku(
    tmp_path: Path,
    produtos_brutos_variados_exemplo: pd.DataFrame,
    dicionario_canonico_exemplo: pd.DataFrame,
    config_texto: str,
) -> tuple[Path, Path]:
    dados_brutos = tmp_path / "dados" / "brutos"
    dados_brutos.mkdir(parents=True, exist_ok=True)
    dados_processados = tmp_path / "dados" / "processados"
    resultados_metricas = tmp_path / "resultados" / "metricas"
    latex_tabelas = tmp_path / "latex" / "tcc_artigo" / "tabelas"
    _brutos_com_par_mesmo_sku(produtos_brutos_variados_exemplo).to_csv(
        dados_brutos / "todos_mercados_2026-01-01.csv", index=False
    )
    dicionario_canonico_exemplo.to_csv(
        dados_brutos / "dicionario_canonico.csv", sep=";", index=False
    )
    coleta_dados.executar_limpeza(dados_brutos, dados_processados)
    config = tmp_path / "eda.yaml"
    config.write_text(config_texto, encoding="utf-8")
    analise_exploratoria.estatisticas_descritivas(
        dados_processados,
        diretorio_brutos=dados_brutos,
        diretorio_saida=resultados_metricas,
        diretorio_latex_tabelas=latex_tabelas,
        diretorio_figuras=tmp_path / "resultados" / "figuras",
        diretorio_latex_figuras=tmp_path / "latex" / "tcc_artigo" / "figuras",
        caminho_config=config,
    )
    return resultados_metricas, latex_tabelas


def test_carregar_config_eda_le_o_yaml(tmp_path: Path) -> None:
    config = tmp_path / "eda.yaml"
    config.write_text(
        "seed: 7\nn_candidatos_heterogeneidade: 5\nheterogeneidade_confirmados: ['aaaaaaaaaaaa']\n",
        encoding="utf-8",
    )
    cfg = analise_exploratoria.carregar_config_eda(config)
    assert cfg["seed"] == 7
    assert cfg["n_candidatos_heterogeneidade"] == 5
    assert cfg["heterogeneidade_confirmados"] == ["aaaaaaaaaaaa"]


def test_carregar_config_eda_rejeita_confirmados_que_nao_e_lista(tmp_path: Path) -> None:
    config = tmp_path / "eda.yaml"
    config.write_text(
        "seed: 7\nn_candidatos_heterogeneidade: 5\nheterogeneidade_confirmados: aaaa\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="heterogeneidade_confirmados"):
        analise_exploratoria.carregar_config_eda(config)


def test_script_02_sem_confirmados_grava_candidatos_e_nao_gera_a_tabela(
    tmp_path: Path,
    produtos_brutos_variados_exemplo: pd.DataFrame,
    dicionario_canonico_exemplo: pd.DataFrame,
) -> None:
    metricas, tabelas = _rodar_eda_com_par_mesmo_sku(
        tmp_path,
        produtos_brutos_variados_exemplo,
        dicionario_canonico_exemplo,
        _CONFIG_EDA_SEM_CONFIRMADOS,
    )

    candidatos = pd.read_csv(metricas / "candidatos_heterogeneidade.csv")
    assert list(candidatos["supermercado_a"]) == ["Vinho Chileno Cono Sur Carmenere 750ml"]
    assert not (tabelas / "tab_heterogeneidade_exemplos.tex").exists()


def test_script_02_com_par_confirmado_gera_a_tabela_so_com_ele(
    tmp_path: Path,
    produtos_brutos_variados_exemplo: pd.DataFrame,
    dicionario_canonico_exemplo: pd.DataFrame,
) -> None:
    metricas, _ = _rodar_eda_com_par_mesmo_sku(
        tmp_path,
        produtos_brutos_variados_exemplo,
        dicionario_canonico_exemplo,
        _CONFIG_EDA_SEM_CONFIRMADOS,
    )
    id_par = pd.read_csv(metricas / "candidatos_heterogeneidade.csv").iloc[0]["id_par"]

    _, tabelas = _rodar_eda_com_par_mesmo_sku(
        tmp_path,
        produtos_brutos_variados_exemplo,
        dicionario_canonico_exemplo,
        f"seed: 42\nn_candidatos_heterogeneidade: 20\nheterogeneidade_confirmados: ['{id_par}']\n",
    )

    conteudo = (tabelas / "tab_heterogeneidade_exemplos.tex").read_text(encoding="utf-8")
    assert "Vinho Chileno Cono Sur Carmenere 750ml" in conteudo
    assert "VH CHI CONO SUR 1551 CARMENERE 750ML" in conteudo
    assert "Canônico" not in conteudo


# ── 1.2b: executar_blocagem_pxp (pool cego em lotes; spec 001, RF1 "1b") ──────
# A "anotação" aqui é mecânica e só simula o autor sobre a fixture; nenhum rótulo é de dado real.


def _preparar_base_pxp(
    tmp_path: Path, produtos: pd.DataFrame, **alteracoes: object
) -> tuple[Path, Path, Path, Path]:
    processados = tmp_path / "processados"
    processados.mkdir(parents=True)
    produtos.drop(columns=["grupo_sku"]).to_parquet(processados / "produtos_limpos.parquet")
    config = tmp_path / "blocagem_pxp.yaml"
    parametros = {
        "seed": 42,
        "lote_ancoras": 5,
        "alvo_ancoras_com_positivo": 3,
        "max_ancoras": 10,
        "profundidade_pool": 100,
        "ngramas": [3, 5],
        "ks": [1, 5, 10, 20, 50, 100],
        "metodo": None,
        "k": None,
        "tau_particao": 0.7,
        "n_teste": 300,
        "fracao_digito_divergente": 0.2,
        **alteracoes,
    }
    config.write_text(yaml.safe_dump(parametros), encoding="utf-8")
    return processados, tmp_path / "metricas", config, tmp_path / "tabelas"


def _rodar_pxp(processados: Path, metricas: Path, config: Path, tabelas: Path) -> None:
    construcao_dataset.executar_blocagem_pxp(
        processados, metricas, config, diretorio_latex_tabelas=tabelas
    )


def _anotar_lote(caminho: Path, n_ancoras_com_match: int, concluir: bool = True) -> None:
    planilha = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False)
    if concluir:
        planilha["ancora_concluida"] = "sim"
    for ancora in list(dict.fromkeys(planilha["id_ancora"]))[:n_ancoras_com_match]:
        primeira = planilha.index[planilha["id_ancora"] == ancora][0]
        planilha.loc[primeira, "rotulo"] = "match"
    planilha.to_csv(caminho, sep=";", index=False)


def _ids_do_lote(processados: Path, numero: int) -> list[str]:
    manifesto = processados / "pool_cego" / f"ancoras_lote_{numero:02d}.csv"
    return list(pd.read_csv(manifesto, sep=";", dtype=str)["id_ancora"])


def _permutacao(produtos: pd.DataFrame, seed: int = 42) -> list[str]:
    universo = construcao_dataset.deduplicar_por_texto_e_loja(produtos.drop(columns=["grupo_sku"]))
    return list(construcao_dataset.sortear_ancoras(universo, seed)["id_produto"])


def test_pxp_gera_o_lote_1_com_as_primeiras_ancoras_da_permutacao_e_aguarda_anotacao(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_entre_lojas_exemplo
    )

    _rodar_pxp(processados, metricas, config, tabelas)

    planilha = pd.read_csv(
        processados / "pool_cego" / "lote_01.csv", sep=";", dtype=str, keep_default_na=False
    )
    assert list(planilha.columns) == construcao_dataset.COLUNAS_PLANILHA_POOL
    assert not {"codg_item", "desc_ref", "match_score", "metodo", "rank", "score"} & set(
        planilha.columns
    )
    assert (planilha["rotulo"] == "").all()
    assert _ids_do_lote(processados, 1) == _permutacao(produtos_entre_lojas_exemplo)[:5]
    assert not (processados / "pool_cego" / "lote_02.csv").exists()
    assert not (metricas / "recall_blocagem_pxp.csv").exists()
    assert not (tabelas / "tab_recall_blocagem_pxp.tex").exists()


def test_pxp_rodar_de_novo_sem_anotacao_nao_reescreve_nem_avanca(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_entre_lojas_exemplo
    )
    _rodar_pxp(processados, metricas, config, tabelas)
    lote_1 = processados / "pool_cego" / "lote_01.csv"
    antes = lote_1.read_bytes()

    _rodar_pxp(processados, metricas, config, tabelas)

    assert lote_1.read_bytes() == antes
    assert not (processados / "pool_cego" / "lote_02.csv").exists()


def test_pxp_lote_parcialmente_concluido_aguarda_sem_gerar_o_proximo(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_entre_lojas_exemplo
    )
    _rodar_pxp(processados, metricas, config, tabelas)
    _anotar_lote(processados / "pool_cego" / "lote_01.csv", 1, concluir=False)

    _rodar_pxp(processados, metricas, config, tabelas)

    assert not (processados / "pool_cego" / "lote_02.csv").exists()
    assert not (metricas / "recall_blocagem_pxp.csv").exists()


def test_pxp_abaixo_do_alvo_gera_o_lote_2_com_as_ancoras_seguintes_e_sem_recall(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_entre_lojas_exemplo
    )
    _rodar_pxp(processados, metricas, config, tabelas)
    _anotar_lote(processados / "pool_cego" / "lote_01.csv", 1)

    _rodar_pxp(processados, metricas, config, tabelas)

    assert _ids_do_lote(processados, 2) == _permutacao(produtos_entre_lojas_exemplo)[5:10]
    assert not (metricas / "recall_blocagem_pxp.csv").exists()  # o recall só sai depois da parada


def test_pxp_ao_atingir_o_alvo_grava_recall_e_tabela_e_para(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_entre_lojas_exemplo
    )
    _rodar_pxp(processados, metricas, config, tabelas)
    _anotar_lote(processados / "pool_cego" / "lote_01.csv", 3)

    _rodar_pxp(processados, metricas, config, tabelas)

    recall = pd.read_csv(metricas / "recall_blocagem_pxp.csv")
    assert list(recall.columns) == construcao_dataset.COLUNAS_RECALL_PXP
    assert len(recall) == 2 * 6
    assert set(recall["n_ancoras_sorteadas"]) == {5}
    assert set(recall["n_ancoras_com_positivo"]) == {3}
    assert "tab:recall-blocagem-pxp" in (tabelas / "tab_recall_blocagem_pxp.tex").read_text(
        encoding="utf-8"
    )
    assert not (processados / "pool_cego" / "lote_02.csv").exists()


def test_pxp_ao_atingir_o_teto_sem_o_alvo_grava_recall_indefinido_e_para(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_entre_lojas_exemplo
    )
    for numero in (1, 2):
        _rodar_pxp(processados, metricas, config, tabelas)
        _anotar_lote(processados / "pool_cego" / f"lote_{numero:02d}.csv", 0)

    _rodar_pxp(processados, metricas, config, tabelas)

    recall = pd.read_csv(metricas / "recall_blocagem_pxp.csv")
    assert set(recall["n_ancoras_sorteadas"]) == {10}
    assert set(recall["n_positivos"]) == {0}
    assert recall["recall"].isna().all()
    assert "--" in (tabelas / "tab_recall_blocagem_pxp.tex").read_text(encoding="utf-8")
    assert not (processados / "pool_cego" / "lote_03.csv").exists()


def test_pxp_mesma_config_e_mesmas_anotacoes_dao_arquivos_identicos(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    saidas = []
    for nome in ("a", "b"):
        processados, metricas, config, tabelas = _preparar_base_pxp(
            tmp_path / nome, produtos_entre_lojas_exemplo
        )
        _rodar_pxp(processados, metricas, config, tabelas)
        _anotar_lote(processados / "pool_cego" / "lote_01.csv", 3)
        _rodar_pxp(processados, metricas, config, tabelas)
        saidas.append(
            [
                (processados / "pool_cego" / "lote_01.csv").read_bytes(),
                (processados / "pool_cego" / "ancoras_lote_01.csv").read_bytes(),
                (metricas / "recall_blocagem_pxp.csv").read_bytes(),
                (tabelas / "tab_recall_blocagem_pxp.tex").read_bytes(),
            ]
        )

    assert saidas[0] == saidas[1]


def test_pxp_linha_apagada_da_planilha_levanta_erro_em_vez_de_virar_nao_match(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_entre_lojas_exemplo
    )
    _rodar_pxp(processados, metricas, config, tabelas)
    lote_1 = processados / "pool_cego" / "lote_01.csv"
    planilha = pd.read_csv(lote_1, sep=";", dtype=str, keep_default_na=False)
    planilha.iloc[1:].to_csv(lote_1, sep=";", index=False)

    with pytest.raises(ValueError, match="faltam"):
        _rodar_pxp(processados, metricas, config, tabelas)


def test_pxp_planilha_sem_manifesto_das_ancoras_levanta_erro(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_entre_lojas_exemplo
    )
    _rodar_pxp(processados, metricas, config, tabelas)
    (processados / "pool_cego" / "ancoras_lote_01.csv").unlink()

    with pytest.raises(ValueError, match="ancoras_lote_01.csv"):
        _rodar_pxp(processados, metricas, config, tabelas)


def test_pxp_ancoras_gravadas_fora_da_permutacao_da_seed_levantam_erro(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_entre_lojas_exemplo
    )
    _rodar_pxp(processados, metricas, config, tabelas)

    with pytest.raises(ValueError, match="permutação"):
        _rodar_pxp(processados, metricas, _com_seed(config, 7), tabelas)  # outra seed


def _com_seed(config: Path, seed: int) -> Path:
    parametros = yaml.safe_load(config.read_text(encoding="utf-8"))
    parametros["seed"] = seed
    novo = config.with_name(f"seed_{seed}.yaml")
    novo.write_text(yaml.safe_dump(parametros), encoding="utf-8")
    return novo


def test_pxp_ks_acima_da_profundidade_do_pool_levanta_erro(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_entre_lojas_exemplo, profundidade_pool=10, ks=[1, 5, 10, 20]
    )

    with pytest.raises(ValueError, match="profundidade_pool"):
        _rodar_pxp(processados, metricas, config, tabelas)


# ── 1.2b T9: gravar_taxas_positivos_por_faixa_pxp (calibração do teste, só no pool) ───────────


def _pool_anotado_ate_o_alvo(tmp_path: Path, produtos: pd.DataFrame, **alteracoes: object):
    processados, metricas, config, tabelas = _preparar_base_pxp(tmp_path, produtos, **alteracoes)
    _rodar_pxp(processados, metricas, config, tabelas)
    _anotar_lote(processados / "pool_cego" / "lote_01.csv", 3)
    _rodar_pxp(processados, metricas, config, tabelas)
    return processados, metricas, config


def test_taxas_por_faixa_gravam_csv_com_o_total_dos_pares_do_topk_das_ancoras(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config = _pool_anotado_ate_o_alvo(
        tmp_path, produtos_entre_lojas_exemplo, metodo="tfidf", k=5
    )

    construcao_dataset.gravar_taxas_positivos_por_faixa_pxp(processados, metricas, config)

    taxas = pd.read_csv(metricas / "taxas_positivos_por_faixa_pxp.csv")
    assert list(taxas.columns) == [
        "faixa",
        "n_pares",
        "n_match",
        "n_incerto",
        "taxa_match",
        "n_digito_divergente",
        "n_match_digito_divergente",
    ]
    universo = construcao_dataset.deduplicar_por_texto_e_loja(
        produtos_entre_lojas_exemplo.drop(columns=["grupo_sku"])
    )
    ancoras = _ids_do_lote(processados, 1)
    topk = construcao_dataset.ranquear_entre_lojas(universo, "tfidf", 5, ids_ancoras=ancoras)
    planilha = pd.read_csv(
        processados / "pool_cego" / "lote_01.csv", sep=";", dtype=str, keep_default_na=False
    )
    no_topk = set(zip(topk["id_produto"], topk["id_candidato"], strict=True))
    matches_no_topk = sum(
        1
        for a, c, r in zip(
            planilha["id_ancora"], planilha["id_candidato"], planilha["rotulo"], strict=True
        )
        if r == "match" and (a, c) in no_topk
    )
    total = taxas.set_index("faixa").loc["total"]
    assert total["n_pares"] == len(topk)
    assert total["n_match"] == matches_no_topk


def test_taxas_por_faixa_nao_tocam_o_pool_e_sao_deterministicas(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config = _pool_anotado_ate_o_alvo(
        tmp_path, produtos_entre_lojas_exemplo, metodo="tfidf", k=5
    )
    lote = processados / "pool_cego" / "lote_01.csv"
    antes = lote.read_bytes()

    construcao_dataset.gravar_taxas_positivos_por_faixa_pxp(processados, metricas, config)
    primeira = (metricas / "taxas_positivos_por_faixa_pxp.csv").read_bytes()
    construcao_dataset.gravar_taxas_positivos_por_faixa_pxp(processados, metricas, config)

    assert lote.read_bytes() == antes
    assert (metricas / "taxas_positivos_por_faixa_pxp.csv").read_bytes() == primeira


def test_taxas_por_faixa_exigem_metodo_e_k_congelados(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config = _pool_anotado_ate_o_alvo(tmp_path, produtos_entre_lojas_exemplo)

    with pytest.raises(ValueError, match="congel"):
        construcao_dataset.gravar_taxas_positivos_por_faixa_pxp(processados, metricas, config)


def test_taxas_por_faixa_com_lote_nao_concluido_levantam_erro(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_entre_lojas_exemplo, metodo="tfidf", k=5
    )
    _rodar_pxp(processados, metricas, config, tabelas)
    _anotar_lote(processados / "pool_cego" / "lote_01.csv", 1, concluir=False)

    with pytest.raises(ValueError, match="lote 1"):
        construcao_dataset.gravar_taxas_positivos_por_faixa_pxp(processados, metricas, config)


# ── 1.2b T10: gerar_pares_teste_pxp (sorteio do teste produto × produto) ─────────────────────

ALOCACAO_PEQUENA = {"texto_identico": 1, "digito_divergente": 1, "[0.00, 1.00]": 3}


def _config_teste(tmp_path: Path, produtos: pd.DataFrame, **alteracoes: object):
    parametros = {
        "metodo": "tfidf",
        "k": 5,
        "n_teste": 5,
        "faixas": [0.0, 1.0],
        "score_minimo_digito_divergente": 0.5,
        "n_por_estrato": ALOCACAO_PEQUENA,
        **alteracoes,
    }
    return _preparar_base_pxp(tmp_path, produtos, **parametros)


def test_gerar_pares_teste_grava_o_csv_sem_rotulo_com_os_estratos_alocados(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, config, _ = _config_teste(tmp_path, produtos_entre_lojas_exemplo)

    pares = construcao_dataset.gerar_pares_teste_pxp(processados, config)

    gravado = pd.read_csv(processados / "pares_teste_pxp.csv")
    assert list(gravado.columns) == ["id_a", "id_b", "estrato", "prob_inclusao"]
    assert gravado["estrato"].value_counts().to_dict() == ALOCACAO_PEQUENA
    assert len(pares) == len(gravado) == 5
    assert not {"rotulo", "codg_item", "desc_ref", "match_score"} & set(gravado.columns)


def test_gerar_pares_teste_e_deterministico_entre_execucoes_independentes(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    primeiro, _, config1, _ = _config_teste(tmp_path / "a", produtos_entre_lojas_exemplo)
    segundo, _, config2, _ = _config_teste(tmp_path / "b", produtos_entre_lojas_exemplo)

    construcao_dataset.gerar_pares_teste_pxp(primeiro, config1)
    construcao_dataset.gerar_pares_teste_pxp(segundo, config2)

    assert (primeiro / "pares_teste_pxp.csv").read_bytes() == (
        segundo / "pares_teste_pxp.csv"
    ).read_bytes()


def test_gerar_pares_teste_nunca_sobrescreve_um_teste_existente(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, config, _ = _config_teste(tmp_path, produtos_entre_lojas_exemplo)
    construcao_dataset.gerar_pares_teste_pxp(processados, config)
    antes = (processados / "pares_teste_pxp.csv").read_bytes()

    with pytest.raises(FileExistsError, match="pares_teste_pxp.csv"):
        construcao_dataset.gerar_pares_teste_pxp(processados, config)

    assert (processados / "pares_teste_pxp.csv").read_bytes() == antes


def test_gerar_pares_teste_com_metodo_ou_k_nulos_falha_sem_gravar(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, config, _ = _config_teste(
        tmp_path, produtos_entre_lojas_exemplo, metodo=None, k=None
    )

    with pytest.raises(ValueError, match="congel"):
        construcao_dataset.gerar_pares_teste_pxp(processados, config)

    assert not (processados / "pares_teste_pxp.csv").exists()


# ── 1.2b T10b: gerar_planilha_teste_pxp (planilha onde o autor anota o teste) ─────────────────

ARQUIVO_PLANILHA_TESTE = "anotacoes_teste_pxp.csv"


def _planilha_teste_gerada(tmp_path: Path, produtos: pd.DataFrame) -> tuple[Path, Path, Path]:
    processados, _, config, _ = _config_teste(tmp_path, produtos)
    construcao_dataset.gerar_pares_teste_pxp(processados, config)
    caminho = construcao_dataset.gerar_planilha_teste_pxp(processados, config)
    return processados, config, caminho


def test_gerar_planilha_teste_grava_um_par_por_linha_sem_rotulo_nem_estrato(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, caminho = _planilha_teste_gerada(tmp_path, produtos_entre_lojas_exemplo)

    planilha = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False)
    pares = pd.read_csv(processados / "pares_teste_pxp.csv")
    assert caminho == processados / ARQUIVO_PLANILHA_TESTE
    assert list(planilha.columns) == construcao_dataset.COLUNAS_PLANILHA_TESTE_PXP
    assert set(zip(planilha["id_a"], planilha["id_b"], strict=True)) == set(
        zip(pares["id_a"], pares["id_b"], strict=True)
    )
    assert (planilha["rotulo"] == "").all()
    assert not {"estrato", "prob_inclusao", "codg_item", "desc_ref", "match_score"} & set(
        planilha.columns
    )


def test_gerar_planilha_teste_rodar_de_novo_preserva_a_anotacao_parcial(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, config, caminho = _planilha_teste_gerada(tmp_path, produtos_entre_lojas_exemplo)
    planilha = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False)
    planilha.loc[0, "rotulo"] = "nao_match"
    planilha.loc[1, "rotulo"] = "match"
    planilha.to_csv(caminho, sep=";", index=False)
    antes = caminho.read_bytes()

    de_novo = construcao_dataset.gerar_planilha_teste_pxp(processados, config)

    assert de_novo == caminho
    assert caminho.read_bytes() == antes


def test_gerar_planilha_teste_e_deterministica_entre_execucoes_independentes(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    _, _, primeiro = _planilha_teste_gerada(tmp_path / "a", produtos_entre_lojas_exemplo)
    _, _, segundo = _planilha_teste_gerada(tmp_path / "b", produtos_entre_lojas_exemplo)

    assert primeiro.read_bytes() == segundo.read_bytes()


def test_gerar_planilha_teste_sem_os_pares_sorteados_falha_com_mensagem_clara(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, config, _ = _config_teste(tmp_path, produtos_entre_lojas_exemplo)

    with pytest.raises(FileNotFoundError, match="pares_teste_pxp.csv"):
        construcao_dataset.gerar_planilha_teste_pxp(processados, config)

    assert not (processados / ARQUIVO_PLANILHA_TESTE).exists()


def test_gerar_planilha_teste_com_linha_apagada_levanta_erro_em_vez_de_seguir(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, config, caminho = _planilha_teste_gerada(tmp_path, produtos_entre_lojas_exemplo)
    planilha = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False)
    planilha.iloc[1:].to_csv(caminho, sep=";", index=False)

    with pytest.raises(ValueError, match="faltam"):
        construcao_dataset.gerar_planilha_teste_pxp(processados, config)


# ── 1.2b T11: gerar_particao_pxp (componentes, partição e vazamento residual) ─────────────────
# O pool "anotado" aqui é mecânico (a primeira linha de cada âncora vira `match`): só simula o
# autor sobre a fixture; nenhum rótulo é de dado real.

PARAMETROS_PARTICAO = {
    "metodo": "tfidf",
    "k": 5,
    "n_teste": 5,
    "faixas": [0.0, 1.0],
    "score_minimo_digito_divergente": 0.5,
    "n_por_estrato": ALOCACAO_PEQUENA,
}
COLUNAS_COMPONENTES = ["id_produto", "componente", "particao"]
COLUNAS_RESUMO_PARTICAO = [
    "particao",
    "n_componentes",
    "n_produtos",
    "fracao_base",
    "maior_componente",
]
COLUNAS_VAZAMENTO = [
    "tau",
    "n_positivos_pool",
    "n_positivos_separados",
    "vazamento_residual",
    "n_pares_validacao",
    "n_match_validacao",
    "n_incerto_validacao",
]


def _base_para_particao(
    tmp_path: Path, produtos: pd.DataFrame, parametros: dict[str, object] | None = None
) -> tuple[Path, Path, Path]:
    """Pool concluído e teste sorteado, sem partição nem conjuntos gerados ainda.

    Segue a ordem real do autor: o pool para com método e k ainda nulos (nada além do recall é
    gerado), o congelamento é gravado no YAML depois e só então o teste é sorteado.
    """
    parametros = dict(PARAMETROS_PARTICAO if parametros is None else parametros)
    congelado = {chave: parametros.pop(chave) for chave in ("metodo", "k")}
    processados, metricas, config = _pool_anotado_ate_o_alvo(
        tmp_path, produtos, **{**parametros, "metodo": None, "k": None}
    )
    gravado = yaml.safe_load(config.read_text(encoding="utf-8"))
    config.write_text(yaml.safe_dump({**gravado, **congelado}), encoding="utf-8")
    construcao_dataset.gerar_pares_teste_pxp(processados, config)
    return processados, metricas, config


def _lote_anotado(processados: Path) -> pd.DataFrame:
    return pd.read_csv(
        processados / "pool_cego" / "lote_01.csv", sep=";", dtype=str, keep_default_na=False
    )


def test_particao_grava_componentes_resumo_e_vazamento_com_as_colunas_do_contrato(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config = _base_para_particao(tmp_path, produtos_entre_lojas_exemplo)

    particao = construcao_dataset.gerar_particao_pxp(processados, metricas, config)

    gravada = pd.read_parquet(processados / "componentes_pxp.parquet")
    resumo = pd.read_csv(metricas / "particao_pxp.csv")
    vazamento = pd.read_csv(metricas / "vazamento_residual_pxp.csv")
    assert list(gravada.columns) == COLUNAS_COMPONENTES
    assert gravada.reset_index(drop=True).equals(particao.reset_index(drop=True))
    assert list(resumo.columns) == COLUNAS_RESUMO_PARTICAO
    assert list(resumo["particao"]) == list(construcao_dataset.PARTICOES)
    assert list(vazamento.columns) == COLUNAS_VAZAMENTO
    assert len(vazamento) == 1
    assert vazamento.loc[0, "tau"] == 0.7


def test_particao_cobre_o_universo_e_respeita_teste_pool_e_componente(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config = _base_para_particao(tmp_path, produtos_entre_lojas_exemplo)

    particao = construcao_dataset.gerar_particao_pxp(processados, metricas, config)

    universo = construcao_dataset.deduplicar_por_texto_e_loja(
        produtos_entre_lojas_exemplo.drop(columns=["grupo_sku"])
    )
    por_produto = dict(zip(particao["id_produto"], particao["particao"], strict=True))
    pares = pd.read_csv(processados / "pares_teste_pxp.csv", dtype=str)
    lote = _lote_anotado(processados)
    pool = set(lote["id_ancora"]) | set(lote["id_candidato"]) | set(_ids_do_lote(processados, 1))
    assert sorted(particao["id_produto"]) == sorted(universo["id_produto"])
    assert particao["id_produto"].is_unique
    assert {por_produto[i] for i in [*pares["id_a"], *pares["id_b"]]} == {"teste"}
    assert "treino" not in {por_produto[i] for i in pool}
    assert (particao.groupby("componente")["particao"].nunique() == 1).all()
    assert not {"codg_item", "desc_ref", "match_score"} & set(particao.columns)


def test_particao_calcula_vazamento_e_pares_de_validacao_como_se_confere_a_mao(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config = _base_para_particao(tmp_path, produtos_entre_lojas_exemplo)

    particao = construcao_dataset.gerar_particao_pxp(processados, metricas, config)

    vazamento = pd.read_csv(metricas / "vazamento_residual_pxp.csv").iloc[0]
    lote = _lote_anotado(processados)
    componente = dict(zip(particao["id_produto"], particao["componente"], strict=True))
    por_produto = dict(zip(particao["id_produto"], particao["particao"], strict=True))
    positivos = lote[lote["rotulo"] == "match"]
    separados = sum(
        componente[a] != componente[c]
        for a, c in zip(positivos["id_ancora"], positivos["id_candidato"], strict=True)
    )
    na_validacao = lote[
        [
            por_produto[a] == por_produto[c] == "validacao"
            for a, c in zip(lote["id_ancora"], lote["id_candidato"], strict=True)
        ]
    ]
    assert vazamento["n_positivos_pool"] == len(positivos)
    assert vazamento["n_positivos_separados"] == separados
    assert vazamento["vazamento_residual"] == pytest.approx(separados / len(positivos))
    assert vazamento["n_pares_validacao"] == len(na_validacao)
    assert vazamento["n_match_validacao"] == int((na_validacao["rotulo"] == "match").sum())
    assert vazamento["n_incerto_validacao"] == int((na_validacao["rotulo"] == "incerto").sum())


def test_particao_e_deterministica_e_pode_ser_regenerada_sem_mudar_nada(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    pa, ma, ca = _base_para_particao(tmp_path / "a", produtos_entre_lojas_exemplo)
    pb, mb, cb = _base_para_particao(tmp_path / "b", produtos_entre_lojas_exemplo)

    construcao_dataset.gerar_particao_pxp(pa, ma, ca)
    construcao_dataset.gerar_particao_pxp(pb, mb, cb)
    antes = (ma / "particao_pxp.csv").read_bytes(), (ma / "vazamento_residual_pxp.csv").read_bytes()
    construcao_dataset.gerar_particao_pxp(pa, ma, ca)

    assert pd.read_parquet(pa / "componentes_pxp.parquet").equals(
        pd.read_parquet(pb / "componentes_pxp.parquet")
    )
    assert (ma / "particao_pxp.csv").read_bytes() == (mb / "particao_pxp.csv").read_bytes()
    assert (ma / "vazamento_residual_pxp.csv").read_bytes() == (
        mb / "vazamento_residual_pxp.csv"
    ).read_bytes()
    assert antes == (
        (ma / "particao_pxp.csv").read_bytes(),
        (ma / "vazamento_residual_pxp.csv").read_bytes(),
    )


def test_particao_sem_os_pares_do_teste_falha_sem_gravar(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config = _pool_anotado_ate_o_alvo(
        tmp_path, produtos_entre_lojas_exemplo, **{**PARAMETROS_PARTICAO, "metodo": None, "k": None}
    )  # método e k nulos: o pool para e o teste ainda não é sorteado

    with pytest.raises(FileNotFoundError, match="pares_teste_pxp.csv"):
        construcao_dataset.gerar_particao_pxp(processados, metricas, config)

    assert not (processados / "componentes_pxp.parquet").exists()
    assert not (metricas / "particao_pxp.csv").exists()


def test_particao_com_pool_nao_concluido_falha_sem_gravar(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_entre_lojas_exemplo, **PARAMETROS_PARTICAO
    )
    _rodar_pxp(processados, metricas, config, tabelas)  # gera o lote 1, que ninguém anotou
    construcao_dataset.gerar_pares_teste_pxp(processados, config)

    with pytest.raises(ValueError, match="concluíd"):
        construcao_dataset.gerar_particao_pxp(processados, metricas, config)

    assert not (processados / "componentes_pxp.parquet").exists()
    assert not (metricas / "vazamento_residual_pxp.csv").exists()


def test_particao_sem_nenhum_lote_do_pool_falha_sem_gravar(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, _ = _preparar_base_pxp(
        tmp_path, produtos_entre_lojas_exemplo, **PARAMETROS_PARTICAO
    )
    construcao_dataset.gerar_pares_teste_pxp(processados, config)

    with pytest.raises(ValueError, match="pool"):
        construcao_dataset.gerar_particao_pxp(processados, metricas, config)

    assert not (processados / "componentes_pxp.parquet").exists()


# ── 1.2b T12: gerar_conjuntos_pxp e a fiação das etapas 3 a 5 em executar_blocagem_pxp ────────

# Na fixture de 17 produtos o pool cobre quase tudo (os n-gramas de caracteres ligam qualquer
# produto a qualquer outro) e o treino fica vazio. Estes 24 produtos têm vocabulário próprio, e o
# pool menos profundo deixa parte deles de fora, para o treino ter o que mostrar.
_EXTRAS_CONJUNTOS = [
    ("Detergente Ype Neutro 500ml", "loja_a"),
    ("DETERG YPE NEUTRO 500ML", "loja_b"),
    ("Shampoo Seda Cachos 325ml", "loja_b"),
    ("SHAMP SEDA CACHOS 325ML", "loja_c"),
    ("Papel Higienico Neve 12un", "loja_a"),
    ("PAP HIG NEVE 12UN", "loja_c"),
    ("Molho Tomate Quero 340g", "loja_c"),
    ("MOLHO DE TOMATE QUERO 340G", "loja_a"),
    ("Achocolatado Nescau 400g", "loja_a"),
    ("ACHOC NESCAU 400G", "loja_b"),
    ("Refrigerante Guarana Antarctica 2l", "loja_b"),
    ("REFRIG GUARANA ANTARCTICA 2L", "loja_c"),
    ("Margarina Qualy 500g", "loja_c"),
    ("MARGARINA QUALY CREMOSA 500G", "loja_a"),
    ("Farinha Trigo Dona Benta 1kg", "loja_a"),
    ("FARINHA DE TRIGO DONA BENTA 1KG", "loja_b"),
    ("Creme Dental Colgate 90g", "loja_b"),
    ("CR DENTAL COLGATE 90G", "loja_c"),
    ("Amaciante Comfort 2l", "loja_c"),
    ("AMAC COMFORT 2L", "loja_a"),
    ("Cerveja Brahma Lata 350ml", "loja_a"),
    ("CERV BRAHMA LATA 350ML", "loja_b"),
    ("Queijo Mussarela Fatiado 150g", "loja_b"),
    ("MUSSARELA FATIADA 150G", "loja_c"),
]
PARAMETROS_CONJUNTOS = {**PARAMETROS_PARTICAO, "profundidade_pool": 5, "ks": [1, 5]}


@pytest.fixture
def produtos_para_conjuntos(produtos_entre_lojas_exemplo: pd.DataFrame) -> pd.DataFrame:
    n = len(produtos_entre_lojas_exemplo)
    extras = pd.DataFrame(
        {
            "product_id": range(n + 1, n + 1 + len(_EXTRAS_CONJUNTOS)),
            "description": [d for d, _ in _EXTRAS_CONJUNTOS],
            "source": [loja for _, loja in _EXTRAS_CONJUNTOS],
            "und_val": 1.0,
            "und_med": "KG",
            "grupo_sku": "extra",
        }
    )
    return pd.concat([produtos_entre_lojas_exemplo, extras], ignore_index=True)


ARQUIVOS_PXP_APOS_A_PARADA = [
    "pares_teste_pxp.csv",
    "anotacoes_teste_pxp.csv",
    "componentes_pxp.parquet",
    "validacao_pxp.parquet",
    "produtos_treino_pxp.parquet",
]
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


def test_conjuntos_gravam_validacao_e_produtos_de_treino_e_respeitam_a_particao(
    tmp_path: Path, produtos_para_conjuntos: pd.DataFrame
) -> None:
    processados, metricas, config = _base_para_particao(
        tmp_path, produtos_para_conjuntos, PARAMETROS_CONJUNTOS
    )

    validacao, treino = construcao_dataset.gerar_conjuntos_pxp(processados, metricas, config)

    particao = pd.read_parquet(processados / "componentes_pxp.parquet")
    por_particao = {
        nome: set(particao.loc[particao["particao"] == nome, "id_produto"])
        for nome in construcao_dataset.PARTICOES
    }
    gravada = pd.read_parquet(processados / "validacao_pxp.parquet")
    assert list(gravada.columns) == COLUNAS_VALIDACAO_PXP
    assert gravada.reset_index(drop=True).equals(validacao.reset_index(drop=True))
    assert pd.read_parquet(processados / "produtos_treino_pxp.parquet").equals(treino)
    assert (validacao["id_a"] < validacao["id_b"]).all()
    assert validacao["rotulo"].isin(["match", "nao_match"]).all()
    assert set(validacao["id_a"]) | set(validacao["id_b"]) <= por_particao["validacao"]
    assert set(treino["id_produto"]) == por_particao["treino"]


def test_conjuntos_contam_os_match_da_validacao_como_se_confere_a_mao(
    tmp_path: Path, produtos_para_conjuntos: pd.DataFrame
) -> None:
    processados, metricas, config = _base_para_particao(
        tmp_path, produtos_para_conjuntos, PARAMETROS_CONJUNTOS
    )

    validacao, _ = construcao_dataset.gerar_conjuntos_pxp(processados, metricas, config)

    particao = pd.read_parquet(processados / "componentes_pxp.parquet")
    na_validacao = set(particao.loc[particao["particao"] == "validacao", "id_produto"])
    lote = _lote_anotado(processados)
    esperados = {
        frozenset((a, c))
        for a, c, r in zip(lote["id_ancora"], lote["id_candidato"], lote["rotulo"], strict=True)
        if r == "match" and a in na_validacao and c in na_validacao
    }
    obtidos = {
        frozenset((a, b))
        for a, b in zip(
            validacao.loc[validacao["rotulo"] == "match", "id_a"],
            validacao.loc[validacao["rotulo"] == "match", "id_b"],
            strict=True,
        )
    }
    assert obtidos == esperados


def test_produtos_de_treino_nao_tem_nenhum_produto_do_teste_nem_do_pool(
    tmp_path: Path, produtos_para_conjuntos: pd.DataFrame
) -> None:
    """[CRÍTICO] ADR-0004: nada do teste ou da validação alimenta a geração de pares de treino."""
    processados, metricas, config = _base_para_particao(
        tmp_path, produtos_para_conjuntos, PARAMETROS_CONJUNTOS
    )

    _, treino = construcao_dataset.gerar_conjuntos_pxp(processados, metricas, config)

    pares = pd.read_csv(processados / "pares_teste_pxp.csv", dtype=str)
    lote = _lote_anotado(processados)
    proibidos = (
        set(pares["id_a"])
        | set(pares["id_b"])
        | set(lote["id_ancora"])
        | set(lote["id_candidato"])
        | set(_ids_do_lote(processados, 1))
    )
    assert not set(treino["id_produto"]) & proibidos
    assert not {"codg_item", "desc_ref", "match_score"} & set(treino.columns)


def test_conjuntos_sao_deterministicos_e_regeneraveis(
    tmp_path: Path, produtos_para_conjuntos: pd.DataFrame
) -> None:
    pa, ma, ca = _base_para_particao(tmp_path / "a", produtos_para_conjuntos, PARAMETROS_CONJUNTOS)
    pb, mb, cb = _base_para_particao(tmp_path / "b", produtos_para_conjuntos, PARAMETROS_CONJUNTOS)

    construcao_dataset.gerar_conjuntos_pxp(pa, ma, ca)
    construcao_dataset.gerar_conjuntos_pxp(pb, mb, cb)
    antes = pd.read_parquet(pa / "validacao_pxp.parquet")
    construcao_dataset.gerar_conjuntos_pxp(pa, ma, ca)

    for arquivo in ["validacao_pxp.parquet", "produtos_treino_pxp.parquet"]:
        assert pd.read_parquet(pa / arquivo).equals(pd.read_parquet(pb / arquivo))
    assert pd.read_parquet(pa / "validacao_pxp.parquet").equals(antes)


def test_conjuntos_sao_tudo_ou_nada_se_a_validacao_falha_nada_e_gravado(
    tmp_path: Path, produtos_para_conjuntos: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    processados, metricas, config = _base_para_particao(
        tmp_path, produtos_para_conjuntos, PARAMETROS_CONJUNTOS
    )

    def falha(*args: object, **kwargs: object) -> None:
        raise ValueError("par com rótulos conflitantes")

    monkeypatch.setattr(construcao_dataset, "montar_validacao_pxp", falha)

    with pytest.raises(ValueError, match="conflitantes"):
        construcao_dataset.gerar_conjuntos_pxp(processados, metricas, config)

    assert not (processados / "componentes_pxp.parquet").exists()
    assert not (processados / "validacao_pxp.parquet").exists()
    assert not (processados / "produtos_treino_pxp.parquet").exists()
    assert not (metricas / "particao_pxp.csv").exists()


def test_conjuntos_com_pool_nao_concluido_falham_sem_gravar_nada(
    tmp_path: Path, produtos_para_conjuntos: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_para_conjuntos, **PARAMETROS_CONJUNTOS
    )
    _rodar_pxp(processados, metricas, config, tabelas)  # lote 1 sem anotação
    construcao_dataset.gerar_pares_teste_pxp(processados, config)

    with pytest.raises(ValueError, match="concluíd"):
        construcao_dataset.gerar_conjuntos_pxp(processados, metricas, config)

    assert not (processados / "validacao_pxp.parquet").exists()
    assert not (processados / "produtos_treino_pxp.parquet").exists()


# ── fiação: executar_blocagem_pxp depois da parada do pool ────────────────────────────────────


def _pool_parado(tmp_path: Path, produtos: pd.DataFrame, **extra: object):
    """Gera o lote 1, anota 3 âncoras com `match` (o alvo) e roda de novo: o pool para."""
    parametros = {**PARAMETROS_CONJUNTOS, **extra}
    processados, metricas, config, tabelas = _preparar_base_pxp(tmp_path, produtos, **parametros)
    _rodar_pxp(processados, metricas, config, tabelas)
    _anotar_lote(processados / "pool_cego" / "lote_01.csv", 3)
    _rodar_pxp(processados, metricas, config, tabelas)
    return processados, metricas, config, tabelas


def test_executar_apos_a_parada_sorteia_o_teste_gera_a_planilha_e_particiona(
    tmp_path: Path, produtos_para_conjuntos: pd.DataFrame
) -> None:
    processados, metricas, _, _ = _pool_parado(tmp_path, produtos_para_conjuntos)

    for arquivo in ARQUIVOS_PXP_APOS_A_PARADA:
        assert (processados / arquivo).exists(), arquivo
    assert (metricas / "recall_blocagem_pxp.csv").exists()
    assert (metricas / "particao_pxp.csv").exists()
    assert (metricas / "vazamento_residual_pxp.csv").exists()


@pytest.mark.parametrize(
    "extra",
    [
        pytest.param({"metodo": None, "k": None}, id="metodo_e_k_nao_congelados"),
        pytest.param(
            {"faixas": None, "n_por_estrato": None, "score_minimo_digito_divergente": None},
            id="alocacao_do_teste_nao_definida",
        ),
    ],
)
def test_executar_sem_congelamento_ou_alocacao_para_depois_do_recall_sem_erro(
    tmp_path: Path, produtos_para_conjuntos: pd.DataFrame, extra: dict[str, object]
) -> None:
    processados, metricas, _, _ = _pool_parado(tmp_path, produtos_para_conjuntos, **extra)

    assert (metricas / "recall_blocagem_pxp.csv").exists()
    for arquivo in ARQUIVOS_PXP_APOS_A_PARADA:
        assert not (processados / arquivo).exists(), arquivo


def test_executar_so_sorteia_o_teste_depois_da_parada_do_pool(
    tmp_path: Path, produtos_para_conjuntos: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _preparar_base_pxp(
        tmp_path, produtos_para_conjuntos, **PARAMETROS_CONJUNTOS
    )

    _rodar_pxp(processados, metricas, config, tabelas)  # só gera o lote 1

    for arquivo in ARQUIVOS_PXP_APOS_A_PARADA:
        assert not (processados / arquivo).exists(), arquivo


def test_executar_de_novo_nao_reescreve_o_teste_nem_a_planilha_que_o_autor_anotou(
    tmp_path: Path, produtos_para_conjuntos: pd.DataFrame
) -> None:
    processados, metricas, config, tabelas = _pool_parado(tmp_path, produtos_para_conjuntos)
    planilha = processados / "anotacoes_teste_pxp.csv"
    anotada = pd.read_csv(planilha, sep=";", dtype=str, keep_default_na=False)
    anotada.loc[0, "rotulo"] = "match"
    anotada.to_csv(planilha, sep=";", index=False)
    antes = {a: (processados / a).read_bytes() for a in ["pares_teste_pxp.csv", planilha.name]}

    _rodar_pxp(processados, metricas, config, tabelas)

    assert {a: (processados / a).read_bytes() for a in antes} == antes


def test_executar_e_deterministico_entre_execucoes_independentes(
    tmp_path: Path, produtos_para_conjuntos: pd.DataFrame
) -> None:
    pa, ma, _, _ = _pool_parado(tmp_path / "a", produtos_para_conjuntos)
    pb, mb, _, _ = _pool_parado(tmp_path / "b", produtos_para_conjuntos)

    for arquivo in ["pares_teste_pxp.csv", "anotacoes_teste_pxp.csv"]:
        assert (pa / arquivo).read_bytes() == (pb / arquivo).read_bytes(), arquivo
    for arquivo in ["particao_pxp.csv", "vazamento_residual_pxp.csv"]:
        assert (ma / arquivo).read_bytes() == (mb / arquivo).read_bytes(), arquivo
    for arquivo in [
        "componentes_pxp.parquet",
        "validacao_pxp.parquet",
        "produtos_treino_pxp.parquet",
    ]:
        assert pd.read_parquet(pa / arquivo).equals(pd.read_parquet(pb / arquivo)), arquivo


def _registrar_etapas_do_main(monkeypatch: pytest.MonkeyPatch, processados: Path) -> list[tuple]:
    chamadas: list[tuple] = []
    monkeypatch.setattr(construcao_dataset, "DADOS_PROCESSADOS", processados)
    monkeypatch.setattr(
        construcao_dataset, "executar_blocagem", lambda *a, **k: chamadas.append(("1a", a, k))
    )
    monkeypatch.setattr(
        construcao_dataset, "executar_blocagem_pxp", lambda *a, **k: chamadas.append(("1b", a, k))
    )
    monkeypatch.setattr(
        construcao_dataset,
        "gerar_pares_treino_auto_pxp",
        lambda *a, **k: chamadas.append(("treino_auto", a, k)),
    )
    monkeypatch.setattr(
        construcao_dataset, "gerar_treino_pxp", lambda *a, **k: chamadas.append(("treino", a, k))
    )
    # A TAIL só roda se `dados/brutos/tail` existir; aqui aponta para um lugar que não existe.
    monkeypatch.setattr(construcao_dataset, "DADOS_BRUTOS_TAIL", processados / "sem_tail")
    monkeypatch.setattr(
        construcao_dataset,
        "gerar_pares_tail_pxp",
        lambda *a, **k: chamadas.append(("tail", a, k)),
        raising=False,
    )
    return chamadas


def test_main_roda_a_blocagem_1a_e_depois_a_1b(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    chamadas = _registrar_etapas_do_main(monkeypatch, tmp_path)

    construcao_dataset.main()

    assert [nome for nome, _, _ in chamadas][:2] == ["1a", "1b"]
    assert chamadas[1][2]["diretorio_latex_tabelas"] == construcao_dataset.LATEX_TABELAS


def test_main_so_gera_os_pares_de_treino_se_ja_existem_os_produtos_de_treino(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    chamadas = _registrar_etapas_do_main(monkeypatch, tmp_path)

    construcao_dataset.main()  # sem produtos_treino_pxp.parquet: a etapa só avisa

    assert "treino_auto" not in [nome for nome, _, _ in chamadas]


def test_main_gera_os_pares_de_treino_depois_da_1b_quando_ha_produtos_de_treino(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "produtos_treino_pxp.parquet").write_bytes(b"")
    chamadas = _registrar_etapas_do_main(monkeypatch, tmp_path)

    construcao_dataset.main()

    assert [nome for nome, _, _ in chamadas] == ["1a", "1b", "treino_auto"]
    assert chamadas[2][1] == (tmp_path, construcao_dataset.CONFIG_PARES_TREINO_PXP)


# ── 1.2b B2: gerar_planilha_b2_pxp (pares do treino que o autor anota; design-treino-pxp §8) ───

ARQUIVO_PARES_B2 = "pares_b2_pxp.csv"
ARQUIVO_PLANILHA_B2 = "anotacoes_treino_b2_pxp.csv"
_TREINO_B2 = [
    ("p01", "suco uva integral tial 1l", "loja_a"),
    ("p02", "suco uva integral tial 1l", "loja_b"),
    ("p04", "arroz branco tio joao 5kg", "loja_a"),
    ("p05", "arroz tio joao branco 5kg", "loja_b"),
    ("p06", "arroz integral camil 1kg", "loja_c"),
    ("p09", "feijao carioca camil 1kg", "loja_a"),
    ("p10", "feijao preto camil 1kg", "loja_b"),
    ("p13", "feijao carioca camil 500g", "loja_c"),
]
# cossenos medidos: p01-p02 1,00; p04-p05 1,00; p09-p10 0,63; p09-p13 0,76 (mas 1kg × 500g)
_PARES_B2_ESPERADOS = {("p01", "p02"), ("p04", "p05"), ("p09", "p10")}


def _base_b2(tmp_path: Path, produtos: pd.DataFrame, **extra: object) -> tuple[Path, Path]:
    """Config válida (método e k congelados) e um `produtos_treino_pxp.parquet` feito à mão."""
    processados, _, config, _ = _preparar_base_pxp(
        tmp_path, produtos, **{"metodo": "tfidf", "k": 20, "b2_cosseno_minimo": 0.5, **extra}
    )
    treino = pd.DataFrame(_TREINO_B2, columns=["id_produto", "descricao", "loja"])
    treino["texto_normalizado"] = treino["descricao"]
    treino["und_val"] = 1.0
    treino["und_med"] = "KG"
    treino["componente"] = treino["id_produto"]
    treino.to_parquet(processados / "produtos_treino_pxp.parquet", index=False)
    return processados, config


def test_b2_gera_os_pares_congelados_e_a_planilha_sem_rotulo(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, config = _base_b2(tmp_path, produtos_entre_lojas_exemplo)

    caminho = construcao_dataset.gerar_planilha_b2_pxp(processados, config)

    pares = pd.read_csv(processados / ARQUIVO_PARES_B2, dtype={"id_a": str, "id_b": str})
    planilha = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False)
    assert caminho == processados / ARQUIVO_PLANILHA_B2
    assert list(pares.columns) == ["id_a", "id_b", "score"]
    assert set(zip(pares["id_a"], pares["id_b"], strict=True)) == _PARES_B2_ESPERADOS
    assert set(zip(planilha["id_a"], planilha["id_b"], strict=True)) == _PARES_B2_ESPERADOS
    assert list(planilha.columns) == construcao_dataset.COLUNAS_PLANILHA_TESTE_PXP
    assert set(planilha["origem"]) == {"treino_b2"}
    assert (planilha["rotulo"] == "").all()
    assert "score" not in planilha.columns


def test_b2_rodar_de_novo_preserva_a_anotacao_parcial_e_os_pares_congelados(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, config = _base_b2(tmp_path, produtos_entre_lojas_exemplo)
    caminho = construcao_dataset.gerar_planilha_b2_pxp(processados, config)
    planilha = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False)
    planilha.loc[0, "rotulo"] = "match"
    planilha.to_csv(caminho, sep=";", index=False)
    antes = {a: (processados / a).read_bytes() for a in [ARQUIVO_PARES_B2, ARQUIVO_PLANILHA_B2]}

    construcao_dataset.gerar_planilha_b2_pxp(processados, config)

    assert {a: (processados / a).read_bytes() for a in antes} == antes


def test_b2_e_deterministica_entre_execucoes_independentes(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    pa, ca = _base_b2(tmp_path / "a", produtos_entre_lojas_exemplo)
    pb, cb = _base_b2(tmp_path / "b", produtos_entre_lojas_exemplo)

    construcao_dataset.gerar_planilha_b2_pxp(pa, ca)
    construcao_dataset.gerar_planilha_b2_pxp(pb, cb)

    for arquivo in [ARQUIVO_PARES_B2, ARQUIVO_PLANILHA_B2]:
        assert (pa / arquivo).read_bytes() == (pb / arquivo).read_bytes(), arquivo


def test_b2_sem_os_produtos_de_treino_falha_sem_gravar(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, config = _base_b2(tmp_path, produtos_entre_lojas_exemplo)
    (processados / "produtos_treino_pxp.parquet").unlink()

    with pytest.raises(FileNotFoundError, match="produtos_treino_pxp.parquet"):
        construcao_dataset.gerar_planilha_b2_pxp(processados, config)

    assert not (processados / ARQUIVO_PARES_B2).exists()
    assert not (processados / ARQUIVO_PLANILHA_B2).exists()


def test_b2_sem_corte_de_cosseno_no_yaml_falha_sem_gravar(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, config = _base_b2(tmp_path, produtos_entre_lojas_exemplo, b2_cosseno_minimo=None)

    with pytest.raises(ValueError, match="b2_cosseno_minimo"):
        construcao_dataset.gerar_planilha_b2_pxp(processados, config)

    assert not (processados / ARQUIVO_PLANILHA_B2).exists()


def test_b2_sem_metodo_e_k_congelados_falha_sem_gravar(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, config = _base_b2(tmp_path, produtos_entre_lojas_exemplo, metodo=None, k=None)

    with pytest.raises(ValueError, match="congel"):
        construcao_dataset.gerar_planilha_b2_pxp(processados, config)

    assert not (processados / ARQUIVO_PLANILHA_B2).exists()


def test_executar_depois_da_parada_gera_a_planilha_b2_so_com_produtos_de_treino(
    tmp_path: Path, produtos_para_conjuntos: pd.DataFrame
) -> None:
    processados, _, _, _ = _pool_parado(tmp_path, produtos_para_conjuntos, b2_cosseno_minimo=0.5)

    planilha = pd.read_csv(
        processados / ARQUIVO_PLANILHA_B2, sep=";", dtype=str, keep_default_na=False
    )
    particao = pd.read_parquet(processados / "componentes_pxp.parquet")
    por_produto = dict(zip(particao["id_produto"], particao["particao"], strict=True))
    textos = {
        frozenset((a, b))
        for a, b in zip(planilha["descricao_a"], planilha["descricao_b"], strict=True)
    }
    assert {por_produto[i] for i in [*planilha["id_a"], *planilha["id_b"]]} == {"treino"}
    assert textos == {
        frozenset(("CR DENTAL COLGATE 90G", "Creme Dental Colgate 90g")),
        frozenset(("Amaciante Comfort 2l", "AMAC COMFORT 2L")),
    }


def test_executar_sem_corte_de_cosseno_no_yaml_nao_gera_a_planilha_b2(
    tmp_path: Path, produtos_para_conjuntos: pd.DataFrame
) -> None:
    processados, _, _, _ = _pool_parado(tmp_path, produtos_para_conjuntos)

    assert (processados / "produtos_treino_pxp.parquet").exists()
    assert not (processados / ARQUIVO_PARES_B2).exists()
    assert not (processados / ARQUIVO_PLANILHA_B2).exists()


# ── Parte A dos pares de treino: gerar_pares_treino_auto_pxp (design-treino-pxp §5, ADR-0015) ──

ARQUIVO_PARES_TREINO_AUTO = "pares_treino_auto_pxp.parquet"
_TREINO_AUTO = [
    ("n01", "leite integral italac 1l", "loja_a"),
    ("n02", "leite integral italac 500ml", "loja_b"),
    ("n03", "leite integral italac 200ml", "loja_c"),
    ("n04", "arroz branco tio joao 5kg", "loja_a"),
    ("n05", "arroz branco tio joao 1kg", "loja_b"),
    ("n06", "feijao carioca camil 1kg", "loja_a"),
    ("n07", "feijao carioca camil 500g", "loja_c"),
    ("n08", "leite desnatado piracanjuba 500ml", "loja_b"),
    ("n09", "cafe pilao tradicional 500g", "loja_a"),
    ("n10", "cafe pilao extra forte 250g", "loja_b"),
    ("n11", "oleo de soja liza 900ml", "loja_c"),
    ("n12", "oleo de soja liza 0,9l", "loja_a"),
    ("n13", "sal cisne", "loja_a"),
    ("n14", "sal cisne refinado 1kg", "loja_b"),
    ("n15", "biscoito maria bauducco 200g", "loja_c"),
    ("n16", "biscoito maria bauducco 200g", "loja_a"),
    ("n17", "agua mineral indaia 1,5l", "loja_a"),
    ("n18", "agua mineral crystal 500ml", "loja_c"),
]
_CONFIG_TREINO_AUTO = {
    "seed": 42,
    "k": 20,
    "incluir_mesma_loja": False,
    "faixas_cosseno": [0.0, 0.3, 0.5, 0.7, 1.0],
    "n_negativos_por_faixa": {
        "[0.00, 0.30)": 2,
        "[0.30, 0.50)": 2,
        "[0.50, 0.70)": 3,
        "[0.70, 1.00]": 2,
    },
    "teto_negativos_por_produto": 3,
    "n_positivos": 6,
    "pesos_perturbacao": {"unidade": 1, "ordem": 1, "abreviacao": 1, "ruido": 1},
    "abreviacoes": {"leite": ["lt"], "integral": ["int"], "biscoito": ["bisc"]},
}


def _base_treino_auto(tmp_path: Path, **alteracoes: object) -> tuple[Path, Path, pd.DataFrame]:
    processados = tmp_path / "processados"
    processados.mkdir(parents=True)
    treino = pd.DataFrame(_TREINO_AUTO, columns=["id_produto", "descricao", "loja"])
    treino["texto_normalizado"] = treino["descricao"]
    treino["und_val"] = [float(i + 1) for i in range(len(treino))]
    treino["und_med"] = "KG"
    treino["componente"] = treino["id_produto"]
    treino.to_parquet(processados / "produtos_treino_pxp.parquet", index=False)
    config = tmp_path / "pares_treino_pxp.yaml"
    config.write_text(yaml.safe_dump({**_CONFIG_TREINO_AUTO, **alteracoes}), encoding="utf-8")
    return processados, config, treino


def test_pares_treino_auto_gravam_o_parquet_com_as_contagens_e_origens_da_config(
    tmp_path: Path,
) -> None:
    processados, config, treino = _base_treino_auto(tmp_path)

    pares = construcao_dataset.gerar_pares_treino_auto_pxp(processados, config)

    gravado = pd.read_parquet(processados / ARQUIVO_PARES_TREINO_AUTO)
    assert gravado.reset_index(drop=True).equals(pares.reset_index(drop=True))
    assert list(gravado.columns) == construcao_dataset.COLUNAS_PARES_TREINO_PXP
    assert (gravado["origem"] == "neg_tamanho").sum() == 9
    assert gravado["origem"].str.startswith("pos_").sum() == 6
    assert set(gravado["rotulo"]) == {"match", "nao_match"}
    construcao_dataset.verificar_pares_treino_auto(gravado, treino)  # confere de forma independente


def test_pares_treino_auto_so_usam_produtos_de_treino_e_nenhuma_coluna_da_alta(
    tmp_path: Path,
) -> None:
    processados, config, treino = _base_treino_auto(tmp_path)

    pares = construcao_dataset.gerar_pares_treino_auto_pxp(processados, config)

    ids_reais = set(treino["id_produto"])
    assert set(pares["id_a"]) <= ids_reais
    reais_b = pares.loc[~pares["id_b"].str.startswith("sint_"), "id_b"]
    assert set(reais_b) <= ids_reais
    assert not {"codg_item", "desc_ref", "match_score"} & set(pares.columns)


def test_pares_treino_auto_sao_deterministicos_e_regeneraveis(tmp_path: Path) -> None:
    pa, ca, _ = _base_treino_auto(tmp_path / "a")
    pb, cb, _ = _base_treino_auto(tmp_path / "b")

    construcao_dataset.gerar_pares_treino_auto_pxp(pa, ca)
    construcao_dataset.gerar_pares_treino_auto_pxp(pb, cb)
    antes = pd.read_parquet(pa / ARQUIVO_PARES_TREINO_AUTO)
    construcao_dataset.gerar_pares_treino_auto_pxp(pa, ca)

    assert antes.equals(pd.read_parquet(pb / ARQUIVO_PARES_TREINO_AUTO))
    assert antes.equals(pd.read_parquet(pa / ARQUIVO_PARES_TREINO_AUTO))


def test_pares_treino_auto_sem_os_produtos_de_treino_falham_sem_gravar(tmp_path: Path) -> None:
    processados, config, _ = _base_treino_auto(tmp_path)
    (processados / "produtos_treino_pxp.parquet").unlink()

    with pytest.raises(FileNotFoundError, match="produtos_treino_pxp.parquet"):
        construcao_dataset.gerar_pares_treino_auto_pxp(processados, config)

    assert not (processados / ARQUIVO_PARES_TREINO_AUTO).exists()


def test_pares_treino_auto_com_faixa_insuficiente_falham_sem_gravar(tmp_path: Path) -> None:
    alocacao = {**_CONFIG_TREINO_AUTO["n_negativos_por_faixa"], "[0.70, 1.00]": 3}
    processados, config, _ = _base_treino_auto(tmp_path, n_negativos_por_faixa=alocacao)

    with pytest.raises(ValueError, match=r"\[0.70, 1.00\]"):
        construcao_dataset.gerar_pares_treino_auto_pxp(processados, config)

    assert not (processados / ARQUIVO_PARES_TREINO_AUTO).exists()


def test_pares_treino_auto_sao_tudo_ou_nada_se_a_verificacao_falha_nada_e_gravado(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    processados, config, _ = _base_treino_auto(tmp_path)

    def barra(*args: object, **kwargs: object) -> None:
        raise AssertionError("negativo com tamanho igual")

    monkeypatch.setattr(construcao_dataset, "verificar_pares_treino_auto", barra)

    with pytest.raises(AssertionError, match="tamanho igual"):
        construcao_dataset.gerar_pares_treino_auto_pxp(processados, config)

    assert not (processados / ARQUIVO_PARES_TREINO_AUTO).exists()


def test_main_monta_o_treino_depois_da_parte_a_quando_ha_os_pares_automaticos(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "produtos_treino_pxp.parquet").write_bytes(b"")
    (tmp_path / "pares_treino_auto_pxp.parquet").write_bytes(b"")
    chamadas = _registrar_etapas_do_main(monkeypatch, tmp_path)

    construcao_dataset.main()

    assert [nome for nome, _, _ in chamadas] == ["1a", "1b", "treino_auto", "treino"]
    assert chamadas[3][1] == (
        tmp_path,
        construcao_dataset.RESULTADOS_METRICAS,
        construcao_dataset.CONFIG_PARES_TREINO_PXP,
    )


# ── treino_pxp.parquet: gerar_treino_pxp (parte A + anotação B2 + TAIL; ADR-0015) ─────────────

ARQUIVO_TREINO_PXP = "treino_pxp.parquet"
_TREINO_B2_COMPLETO = [
    ("p01", "suco uva integral tial 1l", "loja_a"),
    ("p02", "suco uva integral tial 1l", "loja_b"),
    ("p03", "suco uva integral tial 1l tipo 1", "loja_a"),
    ("p04", "arroz branco tio joao 5kg", "loja_a"),
    ("p05", "arroz tio joao branco 5kg", "loja_b"),
    ("p06", "arroz integral camil 1kg", "loja_c"),
    ("p07", "sabao em po omo 1kg", "loja_c"),
    ("p08", "sabao em po omo lavagem perfeita 1kg", "loja_a"),
    ("p09", "feijao carioca camil 1kg", "loja_a"),
    ("p10", "feijao preto camil 1kg", "loja_b"),
    ("p11", "biscoito maria bauducco 200g", "loja_b"),
    ("p12", "macarrao espaguete adria 500g", "loja_b"),
    ("p13", "feijao carioca camil 500g", "loja_c"),
    ("p14", "sal cisne", "loja_c"),
    ("p15", "sal cisne refinado", "loja_a"),
]
_CONFIG_TREINO_COMPLETO = {
    "seed": 42,
    "k": 20,
    "incluir_mesma_loja": False,
    "faixas_cosseno": [0.0, 0.5, 1.0],
    "n_negativos_por_faixa": {"[0.00, 0.50)": 2, "[0.50, 1.00]": 2},
    "teto_negativos_por_produto": 3,
    "n_positivos": 4,
    "pesos_perturbacao": {"unidade": 1, "ordem": 0, "abreviacao": 0, "ruido": 0},
    "abreviacoes": {"leite": ["lt"]},
}
_CONFIG_BLOCAGEM_B2 = {
    "seed": 42,
    "lote_ancoras": 5,
    "alvo_ancoras_com_positivo": 3,
    "max_ancoras": 10,
    "profundidade_pool": 100,
    "ngramas": [3, 5],
    "ks": [1, 5, 10, 20, 50, 100],
    "metodo": "tfidf",
    "k": 20,
    "tau_particao": 0.7,
    "n_teste": 300,
    "fracao_digito_divergente": 0.2,
    "b2_cosseno_minimo": 0.4,
}


def _base_treino_completo(
    tmp_path: Path, com_b2: bool = True, rotulos: list[str] | None = None
) -> tuple[Path, Path, Path]:
    """Parte A gerada e, se pedido, a planilha da B2 gerada e anotada (parcialmente) pelo autor."""
    processados, config_auto, _ = _base_treino_auto(
        tmp_path, **{k: v for k, v in _CONFIG_TREINO_COMPLETO.items()}
    )
    treino = pd.DataFrame(
        _TREINO_AUTO + _TREINO_B2_COMPLETO, columns=["id_produto", "descricao", "loja"]
    )
    treino["texto_normalizado"] = treino["descricao"]
    treino["und_val"] = [float(i + 1) for i in range(len(treino))]
    treino["und_med"] = "KG"
    treino["componente"] = treino["id_produto"]
    treino.to_parquet(processados / "produtos_treino_pxp.parquet", index=False)
    construcao_dataset.gerar_pares_treino_auto_pxp(processados, config_auto)
    metricas = tmp_path / "metricas"
    if com_b2:
        blocagem = tmp_path / "blocagem_pxp.yaml"
        blocagem.write_text(yaml.safe_dump(_CONFIG_BLOCAGEM_B2), encoding="utf-8")
        caminho = construcao_dataset.gerar_planilha_b2_pxp(processados, blocagem)
        planilha = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False)
        anotados = (
            rotulos if rotulos is not None else ["match"] * 3 + ["nao_match"] * 2 + ["incerto"]
        )
        planilha.loc[: len(anotados) - 1, "rotulo"] = anotados
        planilha.to_csv(caminho, sep=";", index=False)
    return processados, metricas, config_auto


def _tail_em_disco(processados: Path) -> pd.DataFrame:
    linhas = []
    for i in range(3):
        original, variante = f"Shampoo Acme Brilho {i} 300ml", f"Shampo Acme Brilho {i} 300ml"
        id_a = "tail_" + construcao_dataset._hash_curto(original)
        id_b = "tail_" + construcao_dataset._hash_curto(variante)
        linhas.append(
            (
                construcao_dataset._hash_curto(f"{id_a}|{id_b}"),
                id_a,
                original,
                None,
                None,
                id_b,
                variante,
                None,
                None,
                "produto_produto",
                "tail_variante",
                "match",
            )
        )
    tail = pd.DataFrame(linhas, columns=construcao_dataset.COLUNAS_PARES_TREINO_PXP)
    tail.to_parquet(processados / "pares_tail_pxp.parquet", index=False)
    return tail


def test_treino_pxp_junta_a_parte_a_e_a_anotacao_parcial_da_b2(tmp_path: Path) -> None:
    processados, metricas, config = _base_treino_completo(tmp_path)

    treino = construcao_dataset.gerar_treino_pxp(processados, metricas, config)

    gravado = pd.read_parquet(processados / ARQUIVO_TREINO_PXP)
    contagem = gravado["origem"].value_counts().to_dict()
    assert gravado.reset_index(drop=True).equals(treino.reset_index(drop=True))
    assert list(gravado.columns) == construcao_dataset.COLUNAS_PARES_TREINO_PXP
    assert (
        contagem["autor_b2"] == 5
    )  # 3 match + 2 nao_match; o incerto e os pendentes ficam de fora
    assert contagem["neg_tamanho"] == 4 and contagem["pos_unidade"] == 4
    assert gravado["id_par"].is_unique and set(gravado["rotulo"]) == {"match", "nao_match"}


def test_treino_pxp_grava_o_resumo_por_origem_e_rotulo(tmp_path: Path) -> None:
    processados, metricas, config = _base_treino_completo(tmp_path)

    treino = construcao_dataset.gerar_treino_pxp(processados, metricas, config)

    resumo = pd.read_csv(metricas / "treino_pxp_resumo.csv")
    assert list(resumo.columns) == ["origem", "rotulo", "n_pares"]
    assert resumo["n_pares"].sum() == len(treino)
    b2 = resumo[resumo["origem"] == "autor_b2"].set_index("rotulo")["n_pares"].to_dict()
    assert b2 == {"match": 3, "nao_match": 2}


def test_treino_pxp_sem_a_planilha_da_b2_so_tem_a_parte_a(tmp_path: Path) -> None:
    processados, metricas, config = _base_treino_completo(tmp_path, com_b2=False)

    treino = construcao_dataset.gerar_treino_pxp(processados, metricas, config)

    assert "autor_b2" not in set(treino["origem"])
    assert len(treino) == len(pd.read_parquet(processados / "pares_treino_auto_pxp.parquet"))


def test_treino_pxp_com_a_planilha_da_b2_ainda_sem_anotacao_so_tem_a_parte_a(
    tmp_path: Path,
) -> None:
    processados, metricas, config = _base_treino_completo(tmp_path, rotulos=[])

    treino = construcao_dataset.gerar_treino_pxp(processados, metricas, config)

    assert "autor_b2" not in set(treino["origem"])


def test_treino_pxp_inclui_os_pares_da_tail_quando_existem(tmp_path: Path) -> None:
    processados, metricas, config = _base_treino_completo(tmp_path)
    tail = _tail_em_disco(processados)

    treino = construcao_dataset.gerar_treino_pxp(processados, metricas, config)

    assert (treino["origem"] == "tail_variante").sum() == len(tail) == 3


def test_treino_pxp_sem_os_pares_automaticos_falha_sem_gravar(tmp_path: Path) -> None:
    processados, metricas, config = _base_treino_completo(tmp_path)
    (processados / "pares_treino_auto_pxp.parquet").unlink()

    with pytest.raises(FileNotFoundError, match="pares_treino_auto_pxp.parquet"):
        construcao_dataset.gerar_treino_pxp(processados, metricas, config)

    assert not (processados / ARQUIVO_TREINO_PXP).exists()


def test_treino_pxp_com_rotulo_invalido_na_b2_falha_sem_gravar(tmp_path: Path) -> None:
    processados, metricas, config = _base_treino_completo(tmp_path, rotulos=["match", "talvez"])

    with pytest.raises(ValueError, match="rotulo"):
        construcao_dataset.gerar_treino_pxp(processados, metricas, config)

    assert not (processados / ARQUIVO_TREINO_PXP).exists()
    assert not (metricas / "treino_pxp_resumo.csv").exists()


def test_treino_pxp_e_deterministico_e_nunca_altera_a_planilha_do_autor(tmp_path: Path) -> None:
    pa, ma, ca = _base_treino_completo(tmp_path / "a")
    pb, mb, cb = _base_treino_completo(tmp_path / "b")
    planilha = pa / ARQUIVO_PLANILHA_B2
    antes = planilha.read_bytes()

    construcao_dataset.gerar_treino_pxp(pa, ma, ca)
    construcao_dataset.gerar_treino_pxp(pb, mb, cb)
    primeiro = pd.read_parquet(pa / ARQUIVO_TREINO_PXP)
    construcao_dataset.gerar_treino_pxp(pa, ma, ca)

    assert planilha.read_bytes() == antes
    assert primeiro.equals(pd.read_parquet(pb / ARQUIVO_TREINO_PXP))
    assert primeiro.equals(pd.read_parquet(pa / ARQUIVO_TREINO_PXP))


# ── T10c: reteste do teste (gerar_planilha_reteste_pxp, gerar_kappa_reteste_pxp, --reteste) ────
# A "anotação" aqui é mecânica e só simula o autor sobre a fixture; nenhum rótulo é de dado real.
# O reteste nunca roda no `main()` sem a flag: a planilha só nasce quando o autor pede.

ARQUIVO_PLANILHA_RETESTE = "anotacoes_teste_pxp_reteste.csv"
ARQUIVO_KAPPA_RETESTE = "kappa_reteste_pxp.csv"
_ROTULOS_PRIMEIRA = ["match", "nao_match", "incerto", "match", "nao_match"]


def _teste_anotado(
    tmp_path: Path, produtos: pd.DataFrame, n_reteste: int | None = 3, completa: bool = True
) -> tuple[Path, Path, Path, Path]:
    """Teste de 5 pares com a primeira passada gravada (rótulo e timestamp mecânicos)."""
    extra: dict[str, object] = {}
    if n_reteste is not None:
        extra = {"n_reteste": n_reteste, "seed_reteste": 43}
    processados, metricas, config, _ = _config_teste(tmp_path, produtos, **extra)
    construcao_dataset.gerar_pares_teste_pxp(processados, config)
    caminho = construcao_dataset.gerar_planilha_teste_pxp(processados, config)
    planilha = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False)
    planilha["rotulo"] = _ROTULOS_PRIMEIRA[: len(planilha)]
    planilha["timestamp_anotacao"] = [
        f"2026-11-16T10:{i:02d}:00-03:00" for i in range(len(planilha))
    ]
    planilha["observacao"] = [f"obs {i}" for i in range(len(planilha))]
    if not completa:
        planilha.loc[2, "rotulo"] = ""
    planilha.to_csv(caminho, sep=";", index=False)
    return processados, metricas, config, caminho


def _ler(caminho: Path) -> pd.DataFrame:
    return pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False)


def test_reteste_grava_a_planilha_cega_com_so_pares_do_teste(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, config, primeira = _teste_anotado(tmp_path, produtos_entre_lojas_exemplo)

    caminho = construcao_dataset.gerar_planilha_reteste_pxp(processados, config)

    reteste = _ler(caminho)
    assert caminho == processados / ARQUIVO_PLANILHA_RETESTE
    assert list(reteste.columns) == construcao_dataset.COLUNAS_PLANILHA_TESTE_PXP
    assert len(reteste) == 3
    assert set(reteste["id_par"]) <= set(_ler(primeira)["id_par"])
    for coluna in ["rotulo", "observacao", "timestamp_anotacao"]:
        assert (reteste[coluna] == "").all(), coluna
    assert set(reteste["reteste"]) == {"sim"}
    assert not {"estrato", "prob_inclusao", "codg_item", "desc_ref", "match_score"} & set(
        reteste.columns
    )


def test_reteste_nunca_altera_a_planilha_da_primeira_passada(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, config, primeira = _teste_anotado(tmp_path, produtos_entre_lojas_exemplo)
    antes = primeira.read_bytes()

    construcao_dataset.gerar_planilha_reteste_pxp(processados, config)

    assert primeira.read_bytes() == antes


def test_reteste_rodar_de_novo_preserva_a_anotacao_parcial(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, config, _ = _teste_anotado(tmp_path, produtos_entre_lojas_exemplo)
    caminho = construcao_dataset.gerar_planilha_reteste_pxp(processados, config)
    reteste = _ler(caminho)
    reteste.loc[0, "rotulo"] = "match"
    reteste.to_csv(caminho, sep=";", index=False)
    antes = caminho.read_bytes()

    de_novo = construcao_dataset.gerar_planilha_reteste_pxp(processados, config)

    assert de_novo == caminho
    assert caminho.read_bytes() == antes


def test_reteste_e_deterministico_entre_execucoes_independentes(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    pa, _, ca, _ = _teste_anotado(tmp_path / "a", produtos_entre_lojas_exemplo)
    pb, _, cb, _ = _teste_anotado(tmp_path / "b", produtos_entre_lojas_exemplo)

    a = construcao_dataset.gerar_planilha_reteste_pxp(pa, ca)
    b = construcao_dataset.gerar_planilha_reteste_pxp(pb, cb)

    assert a.read_bytes() == b.read_bytes()


def test_reteste_com_primeira_passada_incompleta_falha_e_nao_grava(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, config, _ = _teste_anotado(
        tmp_path, produtos_entre_lojas_exemplo, completa=False
    )

    with pytest.raises(ValueError, match="sem rotulo"):
        construcao_dataset.gerar_planilha_reteste_pxp(processados, config)

    assert not (processados / ARQUIVO_PLANILHA_RETESTE).exists()


def test_reteste_sem_as_chaves_no_yaml_falha_e_nao_grava(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, config, _ = _teste_anotado(
        tmp_path, produtos_entre_lojas_exemplo, n_reteste=None
    )

    with pytest.raises(ValueError, match="n_reteste"):
        construcao_dataset.gerar_planilha_reteste_pxp(processados, config)

    assert not (processados / ARQUIVO_PLANILHA_RETESTE).exists()


def test_reteste_sem_a_planilha_do_teste_falha_com_mensagem_clara(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, config, _ = _config_teste(
        tmp_path, produtos_entre_lojas_exemplo, n_reteste=3, seed_reteste=43
    )

    with pytest.raises(FileNotFoundError, match="anotacoes_teste_pxp.csv"):
        construcao_dataset.gerar_planilha_reteste_pxp(processados, config)


def _reteste_anotado(
    tmp_path: Path, produtos: pd.DataFrame, primeiro_timestamp: str, rotulos: list[str]
) -> tuple[Path, Path, Path]:
    """Reteste de todos os 5 pares (n_reteste=5), já anotado mecanicamente."""
    processados, metricas, config, _ = _teste_anotado(tmp_path, produtos, n_reteste=5)
    caminho = construcao_dataset.gerar_planilha_reteste_pxp(processados, config)
    primeira = _ler(processados / "anotacoes_teste_pxp.csv").set_index("id_par")["rotulo"]
    reteste = _ler(caminho)
    ordem_original = {"match": 0, "nao_match": 1, "incerto": 2}
    reteste["rotulo"] = [rotulos[ordem_original[primeira[i]]] for i in reteste["id_par"]]
    reteste["timestamp_anotacao"] = [primeiro_timestamp] * len(reteste)
    reteste.to_csv(caminho, sep=";", index=False)
    return processados, metricas, caminho


def test_kappa_do_reteste_so_aguarda_enquanto_o_reteste_nao_foi_anotado(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, config, _ = _teste_anotado(
        tmp_path, produtos_entre_lojas_exemplo, n_reteste=5
    )
    construcao_dataset.gerar_planilha_reteste_pxp(processados, config)

    resultado = construcao_dataset.gerar_kappa_reteste_pxp(processados, metricas)

    assert resultado is None
    assert not (metricas / ARQUIVO_KAPPA_RETESTE).exists()


def test_kappa_do_reteste_depois_de_7_dias_grava_o_csv_por_tipo_de_par(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, _ = _reteste_anotado(
        tmp_path,
        produtos_entre_lojas_exemplo,
        "2026-11-23T12:00:00-03:00",
        ["match", "nao_match", "incerto"],  # concordância total com a primeira passada
    )

    resultado = construcao_dataset.gerar_kappa_reteste_pxp(processados, metricas)

    gravado = pd.read_csv(metricas / ARQUIVO_KAPPA_RETESTE)
    assert resultado is not None
    assert list(gravado["tipo_par"]) == ["produto_produto"]
    assert gravado.loc[0, "kappa_3_classes"] == pytest.approx(1.0)
    assert gravado.loc[0, "kappa_binario"] == pytest.approx(1.0)
    assert gravado.loc[0, "n_pares"] == 5
    assert gravado.loc[0, "n_binario"] == 4


def test_kappa_do_reteste_com_menos_de_7_dias_falha_e_nao_grava(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, _ = _reteste_anotado(
        tmp_path,
        produtos_entre_lojas_exemplo,
        "2026-11-19T12:00:00-03:00",
        ["match", "nao_match", "incerto"],
    )

    with pytest.raises(ValueError, match="7 dias"):
        construcao_dataset.gerar_kappa_reteste_pxp(processados, metricas)

    assert not (metricas / ARQUIVO_KAPPA_RETESTE).exists()


def test_kappa_do_reteste_sem_a_planilha_do_reteste_falha_com_mensagem_clara(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, _, _ = _teste_anotado(tmp_path, produtos_entre_lojas_exemplo)

    with pytest.raises(FileNotFoundError, match="anotacoes_teste_pxp_reteste.csv"):
        construcao_dataset.gerar_kappa_reteste_pxp(processados, metricas)


def _registrar_reteste_no_main(monkeypatch: pytest.MonkeyPatch, processados: Path) -> list[tuple]:
    chamadas = _registrar_etapas_do_main(monkeypatch, processados)
    monkeypatch.setattr(
        construcao_dataset,
        "gerar_planilha_reteste_pxp",
        lambda *a, **k: chamadas.append(("reteste", a, k)),
    )
    monkeypatch.setattr(
        construcao_dataset,
        "gerar_kappa_reteste_pxp",
        lambda *a, **k: chamadas.append(("kappa_reteste", a, k)),
    )
    return chamadas


def test_main_sem_flag_nunca_gera_o_reteste(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    chamadas = _registrar_reteste_no_main(monkeypatch, tmp_path)

    construcao_dataset.main([])

    nomes = [nome for nome, _, _ in chamadas]
    assert "reteste" not in nomes
    assert "kappa_reteste" not in nomes


def test_main_com_flag_reteste_roda_so_a_planilha_do_reteste(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    chamadas = _registrar_reteste_no_main(monkeypatch, tmp_path)

    construcao_dataset.main(["--reteste"])

    assert [nome for nome, _, _ in chamadas] == ["reteste"]
    assert chamadas[0][1] == (tmp_path, construcao_dataset.CONFIG_BLOCAGEM_PXP)


def test_main_com_flag_kappa_reteste_roda_so_o_kappa(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    chamadas = _registrar_reteste_no_main(monkeypatch, tmp_path)

    construcao_dataset.main(["--kappa-reteste"])

    assert [nome for nome, _, _ in chamadas] == ["kappa_reteste"]
    assert chamadas[0][1] == (tmp_path, construcao_dataset.RESULTADOS_METRICAS)


# ── Kappa do reteste com intervalo menor que 7 dias: só com aceite explícito e com o desvio no CSV
# Decisão do autor (2026-11-16): reteste feito 39 min depois da primeira passada, contra o ADR-0005.


def _reteste_curto(tmp_path: Path, produtos: pd.DataFrame) -> tuple[Path, Path]:
    """Primeira passada às 10:00-10:04 de 16/11 e reteste às 12:00 do mesmo dia (1h56)."""
    processados, metricas, _ = _reteste_anotado(
        tmp_path, produtos, "2026-11-16T12:00:00-03:00", ["match", "nao_match", "incerto"]
    )
    return processados, metricas


def test_kappa_do_reteste_curto_sem_o_aceite_continua_recusando_e_nao_grava(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas = _reteste_curto(tmp_path, produtos_entre_lojas_exemplo)

    with pytest.raises(ValueError, match="7 dias"):
        construcao_dataset.gerar_kappa_reteste_pxp(processados, metricas)

    assert not (metricas / ARQUIVO_KAPPA_RETESTE).exists()


def test_kappa_do_reteste_curto_com_o_aceite_grava_o_desvio_no_proprio_csv(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas = _reteste_curto(tmp_path, produtos_entre_lojas_exemplo)

    construcao_dataset.gerar_kappa_reteste_pxp(processados, metricas, aceitar_intervalo_curto=True)

    gravado = pd.read_csv(metricas / ARQUIVO_KAPPA_RETESTE)
    assert gravado.loc[0, "kappa_3_classes"] == pytest.approx(1.0)
    assert gravado.loc[0, "intervalo_horas"] == pytest.approx(1 + 56 / 60, abs=0.01)
    assert bool(gravado.loc[0, "intervalo_minimo_cumprido"]) is False


def test_kappa_do_reteste_valido_grava_o_intervalo_e_marca_o_minimo_como_cumprido(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas, _ = _reteste_anotado(
        tmp_path,
        produtos_entre_lojas_exemplo,
        "2026-11-23T12:00:00-03:00",
        ["match", "nao_match", "incerto"],
    )

    construcao_dataset.gerar_kappa_reteste_pxp(processados, metricas)

    gravado = pd.read_csv(metricas / ARQUIVO_KAPPA_RETESTE)
    assert gravado.loc[0, "intervalo_horas"] > 7 * 24
    assert bool(gravado.loc[0, "intervalo_minimo_cumprido"]) is True


def test_main_kappa_reteste_com_aceite_repassa_o_aceite(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    chamadas = _registrar_reteste_no_main(monkeypatch, tmp_path)

    construcao_dataset.main(["--kappa-reteste", "--aceitar-intervalo-curto"])

    assert [nome for nome, _, _ in chamadas] == ["kappa_reteste"]
    assert chamadas[0][2] == {"aceitar_intervalo_curto": True}


def test_main_kappa_reteste_sem_o_aceite_nao_o_repassa(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    chamadas = _registrar_reteste_no_main(monkeypatch, tmp_path)

    construcao_dataset.main(["--kappa-reteste"])

    assert chamadas[0][2] == {"aceitar_intervalo_curto": False}


def test_aceitar_intervalo_curto_sozinho_e_um_erro_de_uso(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    chamadas = _registrar_reteste_no_main(monkeypatch, tmp_path)

    with pytest.raises(SystemExit):
        construcao_dataset.main(["--aceitar-intervalo-curto"])

    assert chamadas == []


# ── Adjudicação dos `incerto` do teste (formato A; protocolo §3.5; decisão do autor 2026-11-16) ──

ARQUIVO_ADJUDICACAO = "anotacoes_teste_pxp_adjudicacao.csv"


def test_adjudicacao_grava_so_os_incerto_e_nunca_altera_a_primeira_passada(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, config, primeira = _teste_anotado(tmp_path, produtos_entre_lojas_exemplo)
    antes = primeira.read_bytes()

    caminho = construcao_dataset.gerar_planilha_adjudicacao_pxp(processados)

    adjudicacao = _ler(caminho)
    incertos = _ler(primeira).query("rotulo == 'incerto'")
    assert caminho == processados / ARQUIVO_ADJUDICACAO
    assert list(adjudicacao["id_par"]) == list(incertos["id_par"])
    assert list(adjudicacao.columns) == construcao_dataset.COLUNAS_PLANILHA_TESTE_PXP
    assert (adjudicacao["rotulo"] == "").all()
    assert primeira.read_bytes() == antes


def test_adjudicacao_rodar_de_novo_preserva_o_que_o_autor_decidiu(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, _, _ = _teste_anotado(tmp_path, produtos_entre_lojas_exemplo)
    caminho = construcao_dataset.gerar_planilha_adjudicacao_pxp(processados)
    adjudicacao = _ler(caminho)
    adjudicacao.loc[0, "rotulo"] = "match"
    adjudicacao.loc[0, "observacao"] = "dicionario: categoria confere"
    adjudicacao.to_csv(caminho, sep=";", index=False)
    antes = caminho.read_bytes()

    de_novo = construcao_dataset.gerar_planilha_adjudicacao_pxp(processados)

    assert de_novo == caminho
    assert caminho.read_bytes() == antes


def test_adjudicacao_com_decisao_sem_fonte_falha_ao_rodar_de_novo(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, _, _ = _teste_anotado(tmp_path, produtos_entre_lojas_exemplo)
    caminho = construcao_dataset.gerar_planilha_adjudicacao_pxp(processados)
    adjudicacao = _ler(caminho)
    adjudicacao.loc[0, "rotulo"] = "nao_match"
    adjudicacao.to_csv(caminho, sep=";", index=False)

    with pytest.raises(ValueError, match="fonte"):
        construcao_dataset.gerar_planilha_adjudicacao_pxp(processados)


def test_adjudicacao_sem_a_planilha_do_teste_falha_com_mensagem_clara(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="anotacoes_teste_pxp.csv"):
        construcao_dataset.gerar_planilha_adjudicacao_pxp(tmp_path)

    assert not (tmp_path / ARQUIVO_ADJUDICACAO).exists()


def test_adjudicacao_com_primeira_passada_incompleta_falha_e_nao_grava(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, _, _ = _teste_anotado(tmp_path, produtos_entre_lojas_exemplo, completa=False)

    with pytest.raises(ValueError, match="sem rotulo"):
        construcao_dataset.gerar_planilha_adjudicacao_pxp(processados)

    assert not (processados / ARQUIVO_ADJUDICACAO).exists()


def test_main_com_flag_adjudicacao_roda_so_a_adjudicacao(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    chamadas = _registrar_reteste_no_main(monkeypatch, tmp_path)
    monkeypatch.setattr(
        construcao_dataset,
        "gerar_planilha_adjudicacao_pxp",
        lambda *a, **k: chamadas.append(("adjudicacao", a, k)),
    )

    construcao_dataset.main(["--adjudicacao"])

    assert [nome for nome, _, _ in chamadas] == ["adjudicacao"]
    assert chamadas[0][1] == (tmp_path,)


def test_flag_adjudicacao_nao_combina_com_as_do_reteste() -> None:
    with pytest.raises(SystemExit):
        construcao_dataset.main(["--adjudicacao", "--reteste"])


# ── P5a: ler_fontes_tail (cópia curada em dados/brutos/tail, conferida por SHA-256) ───────────
# Arquivos sintéticos, no formato dos da TAIL (BOM, rótulo com espaço, JSON com texto de avaliação).

_BOM = "\ufeff"
_ARQUIVOS_TAIL = {
    "old_attack_dataset.csv": "original,attacked\nSuco Uva Tial 1L,Suco de Uva Tial 1000ml\n",
    "attack.csv": (
        _BOM + "id,original,tipo_variacao,attacked\n1,Sal Cisne 1kg,Erro_Digitacao,Sal Cizne 1kg\n"
    ),
    "itens_nf_normalizados.csv": (
        "title,normalized\nBisc Maria 200g,BISCOITO MARIA\nBiscoito Maria 200 g,BISCOITO MARIA\n"
    ),
    "pairs_to_label.csv": (
        _BOM + "title_a,title_b,candidate_label,similarity_score,label\n"
        "Oculos Exemplo Vr Box,Oculos Exemplo Vr Box Novo,match,0.9,1\n"
        "Shampoo A,Shampoo B,match,0.8, 0\n"
    ),
}
_AVALIACOES = [
    {
        "date": "2026-01-01",
        "rating": 5,
        "content": "TEXTO PRIVADO DA AVALIACAO",
        "product_url": "https://produto.mercadolivre.com.br/MLB-1-selante-1-litro-_JM",
    },
    {
        "date": "2026-01-02",
        "rating": 4,
        "content": "OUTRO TEXTO",
        "product_url": "https://produto.mercadolivre.com.br/MLB-1-selante-1-litro-_JM",
    },
]


def _diretorio_tail(tmp_path: Path) -> Path:
    tail = tmp_path / "tail"
    tail.mkdir(parents=True)
    for nome, conteudo in _ARQUIVOS_TAIL.items():
        (tail / nome).write_bytes(conteudo.encode("utf-8"))
    (tail / "octaprice_mercadolivre_1.json").write_text(json.dumps(_AVALIACOES), encoding="utf-8")
    (tail / "octaprice_mercadolivre_2.json").write_text(
        json.dumps(
            [
                {
                    "date": "d",
                    "rating": 1,
                    "content": "x",
                    "product_url": "https://www.mercadolivre.com.br/shampoo-coco-354g/p/MLB2",
                }
            ]
        ),
        encoding="utf-8",
    )
    linhas = [
        f"{hashlib.sha256((tail / n).read_bytes()).hexdigest()}  {n}\n"
        for n in sorted(p.name for p in tail.iterdir())
    ]
    (tail / "MANIFEST.sha256").write_text("".join(linhas), encoding="utf-8")
    return tail


def test_ler_fontes_tail_devolve_as_cinco_fontes_com_as_colunas_esperadas(tmp_path: Path) -> None:
    fontes = construcao_dataset.ler_fontes_tail(_diretorio_tail(tmp_path))

    assert set(fontes) == {"old_attack", "attack", "itens_nf", "octaprice", "benchmark"}
    assert list(fontes["old_attack"].columns) == ["original", "attacked"]
    assert list(fontes["attack"].columns) == ["id", "original", "tipo_variacao", "attacked"]
    assert list(fontes["itens_nf"].columns) == ["title", "normalized"]
    assert list(fontes["benchmark"].columns) == [
        "title_a",
        "title_b",
        "candidate_label",
        "similarity_score",
        "label",
    ]


def test_ler_fontes_tail_remove_o_bom_e_normaliza_o_rotulo_do_benchmark_sem_editar_o_arquivo(
    tmp_path: Path,
) -> None:
    tail = _diretorio_tail(tmp_path)
    antes = (tail / "pairs_to_label.csv").read_bytes()

    fontes = construcao_dataset.ler_fontes_tail(tail)

    assert list(fontes["benchmark"]["label"]) == ["1", "0"]  # " 0" virou "0" (strip)
    assert "id" in fontes["attack"].columns  # BOM não ficou no nome da coluna
    assert (tail / "pairs_to_label.csv").read_bytes() == antes


def test_ler_fontes_tail_do_octaprice_guarda_so_a_url_distinta_e_nunca_o_texto_da_avaliacao(
    tmp_path: Path,
) -> None:
    fontes = construcao_dataset.ler_fontes_tail(_diretorio_tail(tmp_path))

    octaprice = fontes["octaprice"]
    assert list(octaprice.columns) == ["product_url"]
    assert list(octaprice["product_url"]) == sorted(set(octaprice["product_url"]))
    assert len(octaprice) == 2
    assert "TEXTO PRIVADO" not in octaprice.to_csv()


def test_ler_fontes_tail_com_arquivo_alterado_falha_nomeando_o_arquivo(tmp_path: Path) -> None:
    tail = _diretorio_tail(tmp_path)
    with (tail / "attack.csv").open("ab") as arquivo:
        arquivo.write(b"2,Arroz,Erro_Digitacao,Aroz\n")

    with pytest.raises(ValueError, match="attack.csv"):
        construcao_dataset.ler_fontes_tail(tail)


def test_ler_fontes_tail_sem_manifest_ou_com_arquivo_ausente_falha(tmp_path: Path) -> None:
    tail = _diretorio_tail(tmp_path)
    (tail / "itens_nf_normalizados.csv").unlink()
    with pytest.raises(FileNotFoundError, match="itens_nf_normalizados.csv"):
        construcao_dataset.ler_fontes_tail(tail)

    sem_manifest = _diretorio_tail(tmp_path / "outro")
    (sem_manifest / "MANIFEST.sha256").unlink()
    with pytest.raises(FileNotFoundError, match="MANIFEST.sha256"):
        construcao_dataset.ler_fontes_tail(sem_manifest)


def test_ler_fontes_tail_de_diretorio_inexistente_falha_com_mensagem_clara(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="tail"):
        construcao_dataset.ler_fontes_tail(tmp_path / "nao_existe")


def test_titulos_do_benchmark_sao_os_dos_dois_lados_normalizados_e_sem_repeticao(
    tmp_path: Path,
) -> None:
    fontes = construcao_dataset.ler_fontes_tail(_diretorio_tail(tmp_path))

    titulos = construcao_dataset.titulos_do_benchmark(fontes["benchmark"])

    assert titulos == [
        "oculos exemplo vr box",
        "oculos exemplo vr box novo",
        "shampoo a",
        "shampoo b",
    ]


def test_adjudicacao_aceita_decisao_com_prefixo_autor_ao_rodar_de_novo(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, _, _, _ = _teste_anotado(tmp_path, produtos_entre_lojas_exemplo)
    caminho = construcao_dataset.gerar_planilha_adjudicacao_pxp(processados)
    adjudicacao = _ler(caminho)
    adjudicacao.loc[0, "rotulo"] = "nao_match"
    adjudicacao.loc[0, "observacao"] = "autor: marcas diferentes no texto"
    adjudicacao.to_csv(caminho, sep=";", index=False)
    antes = caminho.read_bytes()

    de_novo = construcao_dataset.gerar_planilha_adjudicacao_pxp(processados)

    assert de_novo == caminho
    assert caminho.read_bytes() == antes


# ── teste_pxp.parquet: gerar_teste_pxp (primeira passada + adjudicação; ADR-0018) ────────────
# Anotação mecânica sobre a fixture; nenhum rótulo é de dado real.

ARQUIVO_TESTE_PXP = "teste_pxp.parquet"
ARQUIVO_RESUMO_TESTE = "teste_pxp_resumo.csv"


def _teste_fechado(
    tmp_path: Path, produtos: pd.DataFrame, resolver: bool = True
) -> tuple[Path, Path]:
    """Teste de 5 pares com 1 `incerto`; adjudicado como `match` (autor:) ou mantido `incerto`."""
    processados, metricas, _, _ = _teste_anotado(tmp_path, produtos)
    caminho = construcao_dataset.gerar_planilha_adjudicacao_pxp(processados)
    adjudicacao = _ler(caminho)
    adjudicacao["rotulo"] = "match" if resolver else "incerto"
    adjudicacao["observacao"] = "autor: julgamento próprio" if resolver else "faltam informações"
    adjudicacao.to_csv(caminho, sep=";", index=False)
    pares = pd.read_csv(processados / "pares_teste_pxp.csv", dtype=str)
    ids = sorted(set(pares["id_a"]) | set(pares["id_b"]))
    pd.DataFrame({"id_produto": ids, "componente": ids, "particao": "teste"}).to_parquet(
        processados / "componentes_pxp.parquet", index=False
    )
    return processados, metricas


def test_gerar_teste_grava_o_parquet_e_o_resumo_com_o_incerto_resolvido(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas = _teste_fechado(tmp_path, produtos_entre_lojas_exemplo)

    teste = construcao_dataset.gerar_teste_pxp(processados, metricas)

    gravado = pd.read_parquet(processados / ARQUIVO_TESTE_PXP)
    assert len(teste) == 5
    assert gravado.equals(teste)
    assert list(gravado.columns) == [
        *construcao_dataset.COLUNAS_PARES_TREINO_PXP[:-1],
        "rotulo",
        "fonte_rotulo",
        "estrato",
        "prob_inclusao",
    ]
    assert gravado["prob_inclusao"].dtype == float
    resumo = pd.read_csv(metricas / ARQUIVO_RESUMO_TESTE)
    assert resumo["n_sorteados"].sum() == 5
    assert resumo["n_incerto_excluido"].sum() == 0


def test_gerar_teste_com_incerto_mantido_deixa_o_par_fora_e_reporta_a_exclusao(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas = _teste_fechado(tmp_path, produtos_entre_lojas_exemplo, resolver=False)

    teste = construcao_dataset.gerar_teste_pxp(processados, metricas)

    assert len(teste) == 4
    resumo = pd.read_csv(metricas / ARQUIVO_RESUMO_TESTE)
    assert resumo["n_incerto_excluido"].sum() == 1
    assert resumo["n_final"].sum() == 4


def test_gerar_teste_nunca_altera_as_planilhas_do_autor(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas = _teste_fechado(tmp_path, produtos_entre_lojas_exemplo)
    planilhas = [processados / "anotacoes_teste_pxp.csv", processados / ARQUIVO_ADJUDICACAO]
    antes = [p.read_bytes() for p in planilhas]

    construcao_dataset.gerar_teste_pxp(processados, metricas)

    assert [p.read_bytes() for p in planilhas] == antes


def test_gerar_teste_e_deterministico_e_regeneravel(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    pa, ma = _teste_fechado(tmp_path / "a", produtos_entre_lojas_exemplo)
    pb, mb = _teste_fechado(tmp_path / "b", produtos_entre_lojas_exemplo)

    primeiro = construcao_dataset.gerar_teste_pxp(pa, ma)
    de_novo = construcao_dataset.gerar_teste_pxp(pa, ma)
    outro = construcao_dataset.gerar_teste_pxp(pb, mb)

    assert primeiro.equals(de_novo)
    assert primeiro.equals(outro)


def test_gerar_teste_sem_a_adjudicacao_falha_e_nao_grava(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas = _teste_fechado(tmp_path, produtos_entre_lojas_exemplo)
    (processados / ARQUIVO_ADJUDICACAO).unlink()

    with pytest.raises(FileNotFoundError, match="anotacoes_teste_pxp_adjudicacao.csv"):
        construcao_dataset.gerar_teste_pxp(processados, metricas)

    assert not (processados / ARQUIVO_TESTE_PXP).exists()


def test_gerar_teste_com_adjudicacao_incompleta_falha_e_nao_grava(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas = _teste_fechado(tmp_path, produtos_entre_lojas_exemplo)
    adjudicacao = _ler(processados / ARQUIVO_ADJUDICACAO)
    adjudicacao["rotulo"] = ""
    adjudicacao.to_csv(processados / ARQUIVO_ADJUDICACAO, sep=";", index=False)

    with pytest.raises(ValueError, match="sem rotulo"):
        construcao_dataset.gerar_teste_pxp(processados, metricas)

    assert not (processados / ARQUIVO_TESTE_PXP).exists()
    assert not (metricas / ARQUIVO_RESUMO_TESTE).exists()


def test_gerar_teste_com_produto_fora_da_particao_teste_falha_e_nao_grava(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas = _teste_fechado(tmp_path, produtos_entre_lojas_exemplo)
    componentes = pd.read_parquet(processados / "componentes_pxp.parquet")
    componentes.loc[0, "particao"] = "treino"
    componentes.to_parquet(processados / "componentes_pxp.parquet", index=False)

    with pytest.raises(AssertionError, match=componentes.loc[0, "id_produto"]):
        construcao_dataset.gerar_teste_pxp(processados, metricas)

    assert not (processados / ARQUIVO_TESTE_PXP).exists()


def test_gerar_teste_sem_a_particao_falha_com_mensagem_clara(
    tmp_path: Path, produtos_entre_lojas_exemplo: pd.DataFrame
) -> None:
    processados, metricas = _teste_fechado(tmp_path, produtos_entre_lojas_exemplo)
    (processados / "componentes_pxp.parquet").unlink()

    with pytest.raises(FileNotFoundError, match="componentes_pxp.parquet"):
        construcao_dataset.gerar_teste_pxp(processados, metricas)


def test_main_com_flag_teste_roda_so_a_composicao_do_teste(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    chamadas = _registrar_reteste_no_main(monkeypatch, tmp_path)
    monkeypatch.setattr(
        construcao_dataset,
        "gerar_teste_pxp",
        lambda *a, **k: chamadas.append(("teste", a, k)),
        raising=False,
    )

    construcao_dataset.main(["--teste"])

    assert [nome for nome, _, _ in chamadas] == ["teste"]
    assert chamadas[0][1] == (tmp_path, construcao_dataset.RESULTADOS_METRICAS)


def test_flag_teste_nao_combina_com_as_outras() -> None:
    with pytest.raises(SystemExit):
        construcao_dataset.main(["--teste", "--adjudicacao"])


# ── P5b: gerar_pares_tail_pxp (cópia curada → pares_tail_pxp.parquet; ADR-0013; só uso local) ────
# Fontes sintéticas (fixture `fontes_tail_exemplo`), nenhuma do clone da TAIL.

ARQUIVO_PARES_TAIL = "pares_tail_pxp.parquet"
ARQUIVO_RESUMO_TAIL = "pares_tail_pxp_resumo.csv"
_CFG_TAIL = {
    "seed": 42,
    "incluir_sem_tamanho": False,
    "limiar_quase_duplicata": 0.9,
    "max_pares_por_grupo_nf": 2,
    "razao_negativos": 0.5,
    "k": 20,
    "faixas_cosseno": [0.0, 1.0],
    "peso_negativos_por_faixa": {"[0.00, 1.00]": 1.0},
    "teto_negativos_por_produto": 3,
}


def _gravar_tail_exemplo(base: Path, fontes: dict[str, pd.DataFrame]) -> tuple[Path, Path]:
    """Escreve as fontes sintéticas no formato dos arquivos da TAIL, com MANIFEST.sha256."""
    tail = base / "tail"
    tail.mkdir(parents=True)
    bom = "\ufeff"
    (tail / "old_attack_dataset.csv").write_text(
        fontes["old_attack"].to_csv(index=False), encoding="utf-8"
    )
    (tail / "attack.csv").write_text(bom + fontes["attack"].to_csv(index=False), encoding="utf-8")
    (tail / "itens_nf_normalizados.csv").write_text(
        fontes["itens_nf"].to_csv(index=False), encoding="utf-8"
    )
    (tail / "pairs_to_label.csv").write_text(
        bom + fontes["benchmark"].to_csv(index=False), encoding="utf-8"
    )
    urls = list(fontes["octaprice"]["product_url"])
    for numero, parte in enumerate([urls[::2], urls[1::2]], start=1):
        avaliacoes = [{"date": "d", "rating": 5, "content": "x", "product_url": u} for u in parte]
        (tail / f"octaprice_mercadolivre_{numero}.json").write_text(
            json.dumps(avaliacoes), encoding="utf-8"
        )
    linhas = [
        f"{hashlib.sha256((tail / n).read_bytes()).hexdigest()}  {n}\n"
        for n in sorted(p.name for p in tail.iterdir())
    ]
    (tail / "MANIFEST.sha256").write_text("".join(linhas), encoding="utf-8")
    config = base / "pares_tail_pxp.yaml"
    config.write_text(yaml.safe_dump(_CFG_TAIL), encoding="utf-8")
    return tail, config


def _gerar_tail(base: Path, fontes: dict[str, pd.DataFrame]) -> tuple[Path, Path, Path, Path]:
    tail, config = _gravar_tail_exemplo(base, fontes)
    processados, metricas = base / "processados", base / "metricas"
    return processados, metricas, tail, config


def test_gerar_pares_tail_grava_o_parquet_e_o_resumo_no_formato_do_treino(
    tmp_path: Path, fontes_tail_exemplo: dict[str, pd.DataFrame]
) -> None:
    processados, metricas, tail, config = _gerar_tail(tmp_path, fontes_tail_exemplo)

    pares = construcao_dataset.gerar_pares_tail_pxp(processados, tail, config, metricas)

    gravado = pd.read_parquet(processados / ARQUIVO_PARES_TAIL)
    assert gravado.equals(pares)
    assert list(gravado.columns) == construcao_dataset.COLUNAS_PARES_TREINO_PXP
    assert len(gravado) == 15  # 8 variantes + 2 de nota fiscal + 5 negativos
    resumo = pd.read_csv(metricas / ARQUIVO_RESUMO_TAIL)
    assert list(resumo.columns) == ["etapa", "n"]


def test_pares_da_tail_passam_pela_barreira_do_treino(
    tmp_path: Path, fontes_tail_exemplo: dict[str, pd.DataFrame]
) -> None:
    processados, metricas, tail, config = _gerar_tail(tmp_path, fontes_tail_exemplo)
    pares = construcao_dataset.gerar_pares_tail_pxp(processados, tail, config, metricas)
    sem_produtos = pd.DataFrame(columns=["id_produto", "loja", "descricao"])

    construcao_dataset.verificar_treino_pxp(pares, sem_produtos)


def test_gerar_pares_tail_e_deterministico_entre_execucoes_independentes(
    tmp_path: Path, fontes_tail_exemplo: dict[str, pd.DataFrame]
) -> None:
    pa, ma, ta, ca = _gerar_tail(tmp_path / "a", fontes_tail_exemplo)
    pb, mb, tb, cb = _gerar_tail(tmp_path / "b", fontes_tail_exemplo)

    primeiro = construcao_dataset.gerar_pares_tail_pxp(pa, ta, ca, ma)
    segundo = construcao_dataset.gerar_pares_tail_pxp(pb, tb, cb, mb)
    de_novo = construcao_dataset.gerar_pares_tail_pxp(pa, ta, ca, ma)

    assert primeiro.equals(segundo)
    assert primeiro.equals(de_novo)


def test_gerar_pares_tail_com_arquivo_alterado_falha_e_nao_grava(
    tmp_path: Path, fontes_tail_exemplo: dict[str, pd.DataFrame]
) -> None:
    processados, metricas, tail, config = _gerar_tail(tmp_path, fontes_tail_exemplo)
    with (tail / "attack.csv").open("ab") as arquivo:
        arquivo.write(b"9,Arroz,Erro_Digitacao,Aroz\n")

    with pytest.raises(ValueError, match="attack.csv"):
        construcao_dataset.gerar_pares_tail_pxp(processados, tail, config, metricas)

    assert not (processados / ARQUIVO_PARES_TAIL).exists()
    assert not (metricas / ARQUIVO_RESUMO_TAIL).exists()


def test_gerar_pares_tail_e_tudo_ou_nada_se_a_barreira_falhar(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fontes_tail_exemplo: dict[str, pd.DataFrame]
) -> None:
    processados, metricas, tail, config = _gerar_tail(tmp_path, fontes_tail_exemplo)

    def barreira_que_falha(*args: object, **kwargs: object) -> None:
        raise AssertionError("barreira simulada")

    monkeypatch.setattr(
        construcao_dataset, "verificar_pares_tail_pxp", barreira_que_falha, raising=False
    )

    with pytest.raises(AssertionError, match="simulada"):
        construcao_dataset.gerar_pares_tail_pxp(processados, tail, config, metricas)

    assert not (processados / ARQUIVO_PARES_TAIL).exists()
    assert not (metricas / ARQUIVO_RESUMO_TAIL).exists()


def test_gerar_pares_tail_sem_o_diretorio_da_tail_falha_com_mensagem_clara(tmp_path: Path) -> None:
    config = tmp_path / "pares_tail_pxp.yaml"
    config.write_text(yaml.safe_dump(_CFG_TAIL), encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="tail"):
        construcao_dataset.gerar_pares_tail_pxp(
            tmp_path / "processados", tmp_path / "tail", config, tmp_path / "metricas"
        )


def test_main_roda_a_tail_depois_dos_pares_automaticos_e_antes_do_treino(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "produtos_treino_pxp.parquet").write_bytes(b"")
    (tmp_path / "pares_treino_auto_pxp.parquet").write_bytes(b"")
    chamadas = _registrar_etapas_do_main(monkeypatch, tmp_path)
    (tmp_path / "tail").mkdir()
    monkeypatch.setattr(construcao_dataset, "DADOS_BRUTOS_TAIL", tmp_path / "tail")

    construcao_dataset.main([])

    assert [nome for nome, _, _ in chamadas] == ["1a", "1b", "treino_auto", "tail", "treino"]
    assert chamadas[3][1] == (
        tmp_path,
        tmp_path / "tail",
        construcao_dataset.CONFIG_PARES_TAIL_PXP,
        construcao_dataset.RESULTADOS_METRICAS,
    )


def test_main_sem_o_diretorio_da_tail_nao_roda_a_etapa_da_tail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "pares_treino_auto_pxp.parquet").write_bytes(b"")
    chamadas = _registrar_etapas_do_main(monkeypatch, tmp_path)

    construcao_dataset.main([])

    assert "tail" not in [nome for nome, _, _ in chamadas]
