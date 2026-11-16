"""
test_transformacao_particao_pxp.py — Camada 2: componentes conexos em memória (spec 001, RF1 "1b",
CA-1b-06; tasks-1b T11; design-1b C9).

A unidade de partição é o componente de um grafo cujas arestas são os pares de produtos com cosseno
TF-IDF de palavras ≥ τ, inclusive da mesma loja, mais as arestas dos pares do teste. Os textos da
fixture foram escritos para este teste e os cossenos que importam foram medidos com o mesmo
vetorizador do script: 1,00 (idênticos), 0,76 (quase idêntico), 0,79, 0,63 e 0,41.
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


construcao = _load("03_construcao_dataset.py")

TEXTOS = [
    ("p01", "suco uva integral tial 1l", "loja_a"),
    ("p02", "suco uva integral tial 1l", "loja_b"),  # idêntico a p01, outra loja (cos 1,00)
    ("p03", "suco uva integral tial 1l tipo 1", "loja_a"),  # mesma loja de p01 (cos 0,76)
    ("p04", "arroz branco tio joao 5kg", "loja_a"),
    ("p05", "arroz tio joao branco 5kg", "loja_b"),  # inversão de tokens: vetor idêntico (1,00)
    ("p06", "arroz integral camil 1kg", "loja_c"),  # só 0,41 com os feijões
    ("p07", "sabao em po omo 1kg", "loja_c"),
    ("p08", "sabao em po omo lavagem perfeita 1kg", "loja_a"),  # cos 0,79 com p07
    ("p09", "feijao carioca camil 1kg", "loja_a"),
    ("p10", "feijao preto camil 1kg", "loja_b"),  # cos 0,63 com p09
    ("p11", "biscoito maria bauducco 200g", "loja_b"),
    ("p12", "macarrao espaguete adria 500g", "loja_b"),
]


@pytest.fixture
def universo() -> pd.DataFrame:
    df = pd.DataFrame(TEXTOS, columns=["id_produto", "descricao", "loja"])
    df["texto_normalizado"] = df["descricao"].str.lower()
    return df


def _grupos(componentes: pd.Series) -> set[frozenset[str]]:
    return {frozenset(g.index) for _, g in componentes.groupby(componentes)}


def _g(*ids: str) -> frozenset[str]:
    return frozenset(ids)


def _arestas(*pares: tuple[str, str]) -> pd.DataFrame:
    return pd.DataFrame(pares, columns=["id_a", "id_b"])


def test_com_tau_07_os_componentes_sao_os_esperados(universo):
    componentes = construcao.componentes_conexos(universo, 0.7)

    assert _grupos(componentes) == {
        _g("p01", "p02", "p03"),
        _g("p04", "p05"),
        _g("p07", "p08"),
        _g("p06"),
        _g("p09"),
        _g("p10"),
        _g("p11"),
        _g("p12"),
    }


def test_texto_identico_entre_lojas_liga_os_produtos(universo):
    componentes = construcao.componentes_conexos(universo, 0.7)

    assert componentes["p01"] == componentes["p02"]


def test_quase_duplicata_da_mesma_loja_tambem_liga(universo):
    """O critério vale entre todos os produtos, inclusive da mesma loja (p01 e p03: loja_a)."""
    componentes = construcao.componentes_conexos(universo, 0.7)

    assert componentes["p01"] == componentes["p03"]


def test_produto_sem_parecido_fica_sozinho(universo):
    componentes = construcao.componentes_conexos(universo, 0.7)

    assert (componentes == componentes["p11"]).sum() == 1


def test_retorno_cobre_o_universo_com_indice_id_produto_ordenado(universo):
    componentes = construcao.componentes_conexos(universo, 0.7)

    assert componentes.name == "componente"
    assert componentes.index.name == "id_produto"
    assert list(componentes.index) == sorted(universo["id_produto"])


def test_o_rotulo_do_componente_e_o_menor_id_dele(universo):
    componentes = construcao.componentes_conexos(universo, 0.7)

    assert componentes["p03"] == "p01"
    assert componentes["p05"] == "p04"
    assert componentes["p08"] == "p07"
    assert componentes["p12"] == "p12"


def test_resultado_nao_depende_da_ordem_das_linhas(universo):
    esperado = construcao.componentes_conexos(universo, 0.7)

    embaralhado = construcao.componentes_conexos(
        universo.sample(frac=1, random_state=5).reset_index(drop=True), 0.7
    )

    pd.testing.assert_series_equal(esperado, embaralhado)


@pytest.mark.parametrize(("tau", "n_componentes"), [(0.4, 6), (0.6, 7), (0.7, 8), (1.0, 10)])
def test_tau_menor_junta_mais_e_tau_maior_separa(universo, tau, n_componentes):
    """0,41 liga o arroz aos feijões (0,4), 0,63 liga os feijões entre si (0,6); τ = 1 só liga
    vetores idênticos (p01=p02 e p04=p05), então a tolerância de ponto flutuante importa."""
    componentes = construcao.componentes_conexos(universo, tau)

    assert componentes.nunique() == n_componentes


def test_arestas_extra_ligam_componentes_que_nao_se_ligariam(universo):
    teste = _arestas(("p06", "p11"))

    componentes = construcao.componentes_conexos(universo, 0.7, teste)

    assert _g("p06", "p11") in _grupos(componentes)
    assert componentes.nunique() == 7


def test_aresta_extra_entre_dois_componentes_os_funde_e_o_rotulo_vira_o_menor_id(universo):
    componentes = construcao.componentes_conexos(universo, 0.7, _arestas(("p03", "p05")))

    assert _g("p01", "p02", "p03", "p04", "p05") in _grupos(componentes)
    assert componentes["p05"] == "p01"


def test_sem_arestas_extra_ou_com_arestas_vazias_o_resultado_e_o_mesmo(universo):
    base = construcao.componentes_conexos(universo, 0.7)

    pd.testing.assert_series_equal(construcao.componentes_conexos(universo, 0.7, None), base)
    pd.testing.assert_series_equal(construcao.componentes_conexos(universo, 0.7, _arestas()), base)


def test_aresta_com_id_fora_do_universo_levanta_erro_com_o_id(universo):
    with pytest.raises(ValueError, match="zzz"):
        construcao.componentes_conexos(universo, 0.7, _arestas(("p01", "zzz")))


def test_id_produto_duplicado_levanta_erro(universo):
    duplicado = pd.concat([universo, universo.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicado"):
        construcao.componentes_conexos(duplicado, 0.7)


@pytest.mark.parametrize("tau", [0.0, -0.2, 1.01])
def test_tau_fora_de_zero_a_um_levanta_erro(universo, tau):
    with pytest.raises(ValueError, match="tau"):
        construcao.componentes_conexos(universo, tau)


def test_universo_de_um_produto_e_um_componente(universo):
    componentes = construcao.componentes_conexos(universo.iloc[[0]], 0.7)

    assert list(componentes) == ["p01"]
