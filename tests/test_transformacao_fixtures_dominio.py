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
