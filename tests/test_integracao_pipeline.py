"""
test_integracao_pipeline.py — Camada 3: integração leve do pipeline (tmp_path).

Ver AGENTS.md, seção 3, camada 3: "um teste de pipeline em tmp_path que
verifica a passagem de artefatos 01→06".

Scripts 01 (validação + limpeza, ADR-0012) e 02 (EDA sobre a base limpa)
implementados; 03-06 são esqueletos que levantam NotImplementedError
apontando para a spec correspondente.
"""

import importlib.util
import os
from pathlib import Path

import pandas as pd
import pytest

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
