"""
test_transformacao_fixtures_dominio.py — Camada 2: transformação em memória.

Usa as fixtures de domínio de tests/conftest.py, sem I/O de disco. Serve hoje
como guarda de regressão do schema das fixtures; deve ganhar testes reais de
transformação (blocagem, normalização de unidade/marca) conforme as specs
001/002 forem implementadas em scripts/03_construcao_dataset.py e
scripts/04_baselines.py.

Ver AGENTS.md, seção 3, camada 2.
"""

import importlib.util
import os

import pandas as pd
import pytest

_ROOT = os.path.join(os.path.dirname(__file__), "..")


def _load(filename: str):
    path = os.path.join(_ROOT, "scripts", filename)
    spec = importlib.util.spec_from_file_location(filename, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


eda = _load("02_analise_exploratoria.py")


def test_produtos_brutos_exemplo_tem_colunas_do_schema_alta(
    produtos_brutos_exemplo: pd.DataFrame,
) -> None:
    esperadas = {"product_id", "description", "unit", "price", "source", "collected_at"}
    assert esperadas.issubset(produtos_brutos_exemplo.columns)
    assert len(produtos_brutos_exemplo) >= 1


def test_dicionario_canonico_exemplo_tem_colunas_do_schema_alta(
    dicionario_canonico_exemplo: pd.DataFrame,
) -> None:
    esperadas = {"desc_alim", "codg_item1", "cod_padrao"}
    assert esperadas.issubset(dicionario_canonico_exemplo.columns)
    assert len(dicionario_canonico_exemplo) >= 1


def test_par_match_exemplo_referencia_entrada_existente_no_dicionario(
    par_match_exemplo: tuple[str, str], dicionario_canonico_exemplo: pd.DataFrame
) -> None:
    _, entrada_canonica = par_match_exemplo
    assert entrada_canonica in dicionario_canonico_exemplo["desc_alim"].to_numpy()


def test_par_nao_match_exemplo_referencia_entrada_diferente(
    par_match_exemplo: tuple[str, str], par_nao_match_exemplo: tuple[str, str]
) -> None:
    produto_bruto_match, entrada_match = par_match_exemplo
    produto_bruto_nao_match, entrada_nao_match = par_nao_match_exemplo
    assert produto_bruto_match == produto_bruto_nao_match
    assert entrada_match != entrada_nao_match


def test_calcular_contagens_basicas_reproduz_numeros_da_amostra(
    produtos_brutos_variados_exemplo: pd.DataFrame,
    dicionario_canonico_exemplo: pd.DataFrame,
) -> None:
    contagens = eda.calcular_contagens_basicas(
        produtos_brutos_variados_exemplo, dicionario_canonico_exemplo
    )

    assert contagens["total_registros"] == 4
    assert contagens["total_entradas_dicionario"] == 2
    assert contagens["product_id_distintos"] == 3
    assert contagens["descricoes_distintas"] == 3
    assert contagens["distribuicao_source"] == {
        "ajuba_api": 2,
        "diniz_api": 1,
        "guedes_api": 1,
    }
    assert contagens["distribuicao_estado"] == {"PB": 2, "CE": 1, "PI": 1}
    assert contagens["numero_estabelecimentos"] == 3
    # "Arroz Branco Tio Joao 1kg" é a única descrição normalizada que aparece
    # em mais de uma fonte (diniz_api e guedes_api), de 3 descrições distintas.
    assert contagens["taxa_sobreposicao_lojas"] == pytest.approx(1 / 3)


def test_caracterizar_ruido_pdv_reproduz_contagens_da_amostra(
    produtos_brutos_variados_exemplo: pd.DataFrame,
) -> None:
    ruido = eda.caracterizar_ruido_pdv(produtos_brutos_variados_exemplo)

    assert ruido == {
        "unidade_colada": 4,
        "caixa_alta": 0,
        "sem_acentuacao": 3,
        "abreviatura": 1,
    }


def test_caracterizar_match_score_reproduz_estatisticas_da_amostra(
    produtos_brutos_variados_exemplo: pd.DataFrame,
) -> None:
    distribuicao = eda.caracterizar_match_score(produtos_brutos_variados_exemplo)

    assert distribuicao["contagem"] == 4
    assert distribuicao["media"] == pytest.approx(0.79)
    assert distribuicao["minimo"] == pytest.approx(0.65)
    assert distribuicao["maximo"] == pytest.approx(0.92)
    assert distribuicao["mediana"] == pytest.approx(0.795)


def test_comparar_comprimentos_reproduz_estatisticas_da_amostra(
    produtos_brutos_variados_exemplo: pd.DataFrame,
    dicionario_canonico_exemplo: pd.DataFrame,
) -> None:
    comparacao = eda.comparar_comprimentos(
        produtos_brutos_variados_exemplo, dicionario_canonico_exemplo
    )

    assert comparacao["caracteres_bruto"]["mean"] == pytest.approx(29.5)
    assert comparacao["caracteres_bruto"]["count"] == 4
    assert comparacao["caracteres_dicionario"]["mean"] == pytest.approx(12.0)
    assert comparacao["tokens_bruto"]["mean"] == pytest.approx(6.25)
    assert comparacao["tokens_dicionario"]["mean"] == pytest.approx(2.0)


def test_contar_ngramas_unigrama_reproduz_contagens_da_amostra(
    produtos_brutos_variados_exemplo: pd.DataFrame,
) -> None:
    resultado = eda.contar_ngramas(produtos_brutos_variados_exemplo, n=1, top_k=10)
    por_ngrama = {linha["ngrama"]: linha for linha in resultado}

    assert por_ngrama["AGUA"]["contagem"] == 2
    assert por_ngrama["ARROZ"]["contagem"] == 2
    # "Arroz Branco Tio Joao 1kg" tem unidade colada (1KG) e falta de acentuação (Joao).
    assert "unidade colada" in por_ngrama["ARROZ"]["marca_ruido"]
    assert "sem acentuação" in por_ngrama["ARROZ"]["marca_ruido"]
    assert por_ngrama["ARROZ"]["exemplo"] == "Arroz Branco Tio Joao 1kg"


def test_contar_ngramas_bigrama_reproduz_contagens_da_amostra(
    produtos_brutos_variados_exemplo: pd.DataFrame,
) -> None:
    resultado = eda.contar_ngramas(produtos_brutos_variados_exemplo, n=2, top_k=10)
    por_ngrama = {linha["ngrama"]: linha for linha in resultado}

    assert por_ngrama["AGUA MINERAL"]["contagem"] == 2
    assert por_ngrama["ARROZ BRANCO"]["contagem"] == 2


def test_selecionar_exemplos_heterogeneidade_exige_duas_fontes_distintas(
    produtos_brutos_variados_exemplo: pd.DataFrame,
    dicionario_canonico_exemplo: pd.DataFrame,
) -> None:
    exemplos = eda.selecionar_exemplos_heterogeneidade(
        produtos_brutos_variados_exemplo, dicionario_canonico_exemplo, n_exemplos=5
    )

    # "AGUA MINERAL" só tem candidatos de uma única fonte (ajuba_api) e é
    # descartada; "ARROZ BRANCO" tem candidatos de duas fontes distintas.
    assert len(exemplos) == 1
    assert exemplos[0]["canonico"] == "ARROZ BRANCO"
    assert exemplos[0]["supermercado_a"] == "Arroz Branco Tio Joao 1kg"
    assert exemplos[0]["supermercado_b"] == "Arroz Branco Tio Joao 1kg"
