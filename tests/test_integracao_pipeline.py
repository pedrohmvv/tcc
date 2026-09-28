"""
test_integracao_pipeline.py — Camada 3: integração leve do pipeline (tmp_path).

Ver AGENTS.md, seção 3, camada 3: "um teste de pipeline em tmp_path que
verifica a passagem de artefatos 01→06".

Scripts 01 e 02 já implementados (validação de brutos e contagens
básicas da EDA, spec 001 tarefa 1.1.1); 03-06 são esqueletos que
levantam NotImplementedError apontando para a spec correspondente.
"""

import importlib.util
import os
from pathlib import Path

import pandas as pd
import pytest

_ROOT = os.path.join(os.path.dirname(__file__), "..")


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
    """02_analise_exploratoria.py deve ler os brutos e escrever as métricas de 1.1.1."""
    dados_brutos = tmp_path / "dados" / "brutos"
    dados_brutos.mkdir(parents=True)
    resultados_metricas = tmp_path / "resultados" / "metricas"
    resultados_figuras = tmp_path / "resultados" / "figuras"
    latex_tabelas = tmp_path / "latex" / "tcc_artigo" / "tabelas"

    produtos_brutos_variados_exemplo.to_csv(
        dados_brutos / "todos_mercados_2026-01-01.csv", index=False
    )
    dicionario_canonico_exemplo.to_csv(
        dados_brutos / "dicionario_canonico.csv", sep=";", index=False
    )

    contagens = analise_exploratoria.estatisticas_descritivas(
        dados_brutos,
        diretorio_saida=resultados_metricas,
        diretorio_latex_tabelas=latex_tabelas,
        diretorio_figuras=resultados_figuras,
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

    conteudo_tabela = (latex_tabelas / "tab_heterogeneidade_exemplos.tex").read_text(
        encoding="utf-8"
    )
    assert "ARROZ BRANCO" in conteudo_tabela

    caminho_figura = resultados_figuras / "distribuicao_source.png"
    assert caminho_figura.exists()
    assert caminho_figura.stat().st_size > 0


def test_gerar_tabela_heterogeneidade_tex_escreve_arquivo_com_exemplo_real(
    tmp_path: Path,
) -> None:
    exemplos = [
        {
            "supermercado_a": "Arroz Branco Tio Joao 1kg",
            "supermercado_b": "ARROZ BRANCO TIO JOAO 1KG",
            "canonico": "ARROZ BRANCO",
        }
    ]
    caminho_tex = tmp_path / "tab_heterogeneidade_exemplos.tex"

    analise_exploratoria.gerar_tabela_heterogeneidade_tex(exemplos, caminho_tex)

    conteudo = caminho_tex.read_text(encoding="utf-8")
    assert "Arroz Branco Tio Joao 1kg" in conteudo
    assert "ARROZ BRANCO TIO JOAO 1KG" in conteudo
    assert r"\label{tab:heterogeneidade}" in conteudo
    assert "% Gerado automaticamente" in conteudo
