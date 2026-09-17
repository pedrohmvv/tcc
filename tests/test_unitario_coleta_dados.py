"""
test_unitario_coleta_dados.py — Camada 1: testes unitários puros (sem I/O de disco).

Ver AGENTS.md, seção 3, camada 1.
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


coleta = _load("01_coleta_dados.py")


class TestValidarSchemaProdutos:
    def test_schema_completo_nao_levanta_erro(self, produtos_brutos_exemplo: pd.DataFrame) -> None:
        coleta.validar_schema_produtos(produtos_brutos_exemplo)

    def test_schema_incompleto_levanta_value_error(
        self, produtos_brutos_exemplo: pd.DataFrame
    ) -> None:
        df_incompleto = produtos_brutos_exemplo.drop(columns=["price"])
        with pytest.raises(ValueError, match="price"):
            coleta.validar_schema_produtos(df_incompleto)


class TestValidarSchemaDicionario:
    def test_schema_completo_nao_levanta_erro(
        self, dicionario_canonico_exemplo: pd.DataFrame
    ) -> None:
        coleta.validar_schema_dicionario(dicionario_canonico_exemplo)

    def test_schema_incompleto_levanta_value_error(
        self, dicionario_canonico_exemplo: pd.DataFrame
    ) -> None:
        df_incompleto = dicionario_canonico_exemplo.drop(columns=["cod_padrao"])
        with pytest.raises(ValueError, match="cod_padrao"):
            coleta.validar_schema_dicionario(df_incompleto)
