"""
test_transformacao_fixtures_dominio.py — Camada 2: transformação em memória.

Usa as fixtures de domínio de tests/conftest.py, sem I/O de disco. Serve hoje
como guarda de regressão do schema das fixtures; deve ganhar testes reais de
transformação (blocagem, normalização de unidade/marca) conforme as specs
001/002 forem implementadas em scripts/03_construcao_dataset.py e
scripts/04_baselines.py.

Ver AGENTS.md, seção 3, camada 2.
"""

import pandas as pd


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
