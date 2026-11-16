"""
test_unitario_tail_pxp.py — Camada 1: config dos pares da TAIL (`configs/pares_tail_pxp.yaml`).

As decisões D1 a D6 do autor (2026-11-16) viram chaves versionadas, para nenhuma ficar só na
conversa: tamanho ausente fora por padrão, limiar de quase-duplicata fixado antes de ver as
contagens, teto por grupo de nota fiscal, razão de negativos.
"""

import importlib.util
import os
from pathlib import Path

import pytest
import yaml

_ROOT = os.path.join(os.path.dirname(__file__), "..")


def _load(filename: str):
    path = os.path.join(_ROOT, "scripts", filename)
    spec = importlib.util.spec_from_file_location(filename, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


construcao = _load("03_construcao_dataset.py")

PESOS = {
    "[0.00, 0.30)": 1,
    "[0.30, 0.50)": 1,
    "[0.50, 0.70)": 1,
    "[0.70, 1.00]": 1,
}
CONFIG_VALIDA = {
    "seed": 42,
    "incluir_sem_tamanho": False,
    "limiar_quase_duplicata": 0.9,
    "max_pares_por_grupo_nf": 10,
    "razao_negativos": 1.0,
    "k": 20,
    "faixas_cosseno": [0.0, 0.3, 0.5, 0.7, 1.0],
    "peso_negativos_por_faixa": PESOS,
    "teto_negativos_por_produto": 3,
}


def _gravar(tmp_path: Path, **alteracoes: object) -> Path:
    caminho = tmp_path / "pares_tail_pxp.yaml"
    caminho.write_text(yaml.safe_dump({**CONFIG_VALIDA, **alteracoes}), encoding="utf-8")
    return caminho


def test_config_tail_valida_carrega_os_parametros(tmp_path):
    cfg = construcao.carregar_config_tail_pxp(_gravar(tmp_path))

    assert cfg["seed"] == 42
    assert cfg["incluir_sem_tamanho"] is False
    assert cfg["limiar_quase_duplicata"] == 0.9
    assert cfg["max_pares_por_grupo_nf"] == 10
    assert cfg["razao_negativos"] == 1.0
    assert cfg["faixas_cosseno"] == [0.0, 0.3, 0.5, 0.7, 1.0]
    assert cfg["peso_negativos_por_faixa"] == PESOS


def test_config_tail_versionada_traz_as_decisoes_d1_a_d6_do_autor():
    cfg = construcao.carregar_config_tail_pxp(Path(_ROOT) / "configs" / "pares_tail_pxp.yaml")

    assert cfg["incluir_sem_tamanho"] is False  # D1
    assert cfg["limiar_quase_duplicata"] == 0.9  # D2
    assert cfg["max_pares_por_grupo_nf"] == 10  # D4 (19 grupos x 10 = 190 pares de NF)
    assert cfg["razao_negativos"] == 1.0  # D5
    assert cfg["seed"] == 42


@pytest.mark.parametrize("valor", ["false", "nao", 0, 1, None])
def test_config_tail_exige_booleano_em_incluir_sem_tamanho(tmp_path, valor):
    with pytest.raises(ValueError, match="incluir_sem_tamanho"):
        construcao.carregar_config_tail_pxp(_gravar(tmp_path, incluir_sem_tamanho=valor))


@pytest.mark.parametrize("valor", [0.0, -0.1, 1.01])
def test_config_tail_rejeita_limiar_fora_de_zero_a_um(tmp_path, valor):
    with pytest.raises(ValueError, match="limiar_quase_duplicata"):
        construcao.carregar_config_tail_pxp(_gravar(tmp_path, limiar_quase_duplicata=valor))


@pytest.mark.parametrize("valor", [0, -1])
def test_config_tail_rejeita_teto_de_grupo_menor_que_um(tmp_path, valor):
    with pytest.raises(ValueError, match="max_pares_por_grupo_nf"):
        construcao.carregar_config_tail_pxp(_gravar(tmp_path, max_pares_por_grupo_nf=valor))


@pytest.mark.parametrize("valor", [0, -0.5])
def test_config_tail_rejeita_razao_de_negativos_nao_positiva(tmp_path, valor):
    with pytest.raises(ValueError, match="razao_negativos"):
        construcao.carregar_config_tail_pxp(_gravar(tmp_path, razao_negativos=valor))


def test_config_tail_rejeita_pesos_com_faixas_diferentes_das_faixas_de_cosseno(tmp_path):
    pesos = {**PESOS}
    pesos.pop("[0.70, 1.00]")

    with pytest.raises(ValueError, match="peso_negativos_por_faixa"):
        construcao.carregar_config_tail_pxp(_gravar(tmp_path, peso_negativos_por_faixa=pesos))


def test_config_tail_rejeita_pesos_negativos_ou_todos_zero(tmp_path):
    with pytest.raises(ValueError, match="peso_negativos_por_faixa"):
        construcao.carregar_config_tail_pxp(
            _gravar(tmp_path, peso_negativos_por_faixa={**PESOS, "[0.00, 0.30)": -1})
        )
    with pytest.raises(ValueError, match="peso_negativos_por_faixa"):
        construcao.carregar_config_tail_pxp(
            _gravar(tmp_path, peso_negativos_por_faixa={k: 0 for k in PESOS})
        )


def test_config_tail_invalida_informa_o_caminho_do_yaml(tmp_path):
    caminho = _gravar(tmp_path, limiar_quase_duplicata=2)

    with pytest.raises(ValueError, match="pares_tail_pxp.yaml"):
        construcao.carregar_config_tail_pxp(caminho)
