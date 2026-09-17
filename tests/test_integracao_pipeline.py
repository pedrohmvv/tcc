"""
test_integracao_pipeline.py — Camada 3: integração leve do pipeline (tmp_path).

Ver AGENTS.md, seção 3, camada 3: "um teste de pipeline em tmp_path que
verifica a passagem de artefatos 01→06".

Hoje só o script 01 está implementado (validação de brutos); os demais
(02-06) são esqueletos que levantam NotImplementedError apontando para a
spec correspondente (specs/001 a 004). Os testes abaixo cobrem o que já
existe e documentam, via xfail explícito, o que falta.
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


@pytest.mark.xfail(
    reason="scripts/02_analise_exploratoria.py é esqueleto — spec 001 ainda não implementada",
    raises=NotImplementedError,
    strict=True,
)
def test_script_02_eda_ainda_nao_implementado() -> None:
    analise_exploratoria.main()
