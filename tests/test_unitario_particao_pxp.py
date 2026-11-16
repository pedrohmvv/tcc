"""
test_unitario_particao_pxp.py — Camada 1: partição treino/validação/teste por componente conexo,
lógica pura sem I/O (spec 001, RF1 "1b", CA-1b-06; tasks-1b T11).

Regra decidida pelo autor em 2026-11-13, com τ = 0,7 mantido: o componente que toca o teste vai
inteiro para o teste; o que toca o pool (e não o teste) vai inteiro para a validação; o restante é
treino. Não há proporção a ajustar. Os ids e componentes são sintéticos, escritos para o teste.
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

COLUNAS_PARTICAO = ["id_produto", "componente", "particao"]
COLUNAS_RESUMO = ["particao", "n_componentes", "n_produtos", "fracao_base", "maior_componente"]


@pytest.fixture
def componentes() -> pd.Series:
    """8 produtos: {p1,p2,p3} em c1, {p4,p5} em c4, {p6} em c6, {p7,p8} em c7."""
    serie = pd.Series(
        {
            "p1": "c1",
            "p2": "c1",
            "p3": "c1",
            "p4": "c4",
            "p5": "c4",
            "p6": "c6",
            "p7": "c7",
            "p8": "c7",
        },
        name="componente",
    )
    serie.index.name = "id_produto"
    return serie


def _por_produto(particao: pd.DataFrame) -> dict[str, str]:
    return dict(zip(particao["id_produto"], particao["particao"], strict=True))


# ── particionar_componentes ──────────────────────────────────────────────────


def test_as_particoes_sao_treino_validacao_e_teste():
    assert construcao.PARTICOES == ("treino", "validacao", "teste")


def test_componente_do_teste_vai_inteiro_para_o_teste_mesmo_com_membros_que_nao_sao_do_teste(
    componentes,
):
    particao = construcao.particionar_componentes(componentes, ["p2"], ["p4"])

    assert {_por_produto(particao)[p] for p in ["p1", "p2", "p3"]} == {"teste"}


def test_componente_do_pool_sem_teste_vai_inteiro_para_a_validacao(componentes):
    particao = construcao.particionar_componentes(componentes, ["p2"], ["p4", "p6"])

    por_produto = _por_produto(particao)
    assert por_produto["p4"] == por_produto["p5"] == "validacao"  # p5 nunca esteve no pool
    assert por_produto["p6"] == "validacao"


def test_componente_sem_teste_nem_pool_vai_para_o_treino(componentes):
    particao = construcao.particionar_componentes(componentes, ["p2"], ["p4", "p6"])

    assert {_por_produto(particao)[p] for p in ["p7", "p8"]} == {"treino"}


def test_componente_com_teste_e_pool_fica_no_teste(componentes):
    """O teste vence: o produto do pool dentro de um componente do teste não vai à validação."""
    particao = construcao.particionar_componentes(componentes, ["p1"], ["p2", "p6"])

    por_produto = _por_produto(particao)
    assert por_produto["p2"] == "teste"
    assert por_produto["p6"] == "validacao"


def test_particao_tem_uma_linha_por_produto_ordenada_com_as_colunas_do_contrato(componentes):
    particao = construcao.particionar_componentes(componentes, ["p2"], ["p4", "p6"])

    assert list(particao.columns) == COLUNAS_PARTICAO
    assert list(particao["id_produto"]) == sorted(componentes.index)
    assert list(particao.index) == list(range(len(componentes)))
    assert set(particao["particao"]) <= set(construcao.PARTICOES)
    assert dict(zip(particao["id_produto"], particao["componente"], strict=True)) == dict(
        componentes
    )


def test_nenhum_componente_fica_em_duas_particoes(componentes):
    particao = construcao.particionar_componentes(componentes, ["p2", "p7"], ["p4", "p6"])

    assert (particao.groupby("componente")["particao"].nunique() == 1).all()


def test_resultado_nao_depende_da_ordem_das_entradas(componentes):
    esperado = construcao.particionar_componentes(componentes, ["p2", "p7"], ["p4", "p6"])

    embaralhado = construcao.particionar_componentes(
        componentes.sample(frac=1, random_state=3), ["p7", "p2"], ["p6", "p4"]
    )

    assert esperado.equals(embaralhado)


@pytest.mark.parametrize(
    ("ids_teste", "ids_pool"), [(["p2", "zzz"], ["p4"]), (["p2"], ["p4", "yyy"])]
)
def test_id_fora_do_universo_levanta_erro_com_o_id(componentes, ids_teste, ids_pool):
    with pytest.raises(ValueError, match="zzz|yyy"):
        construcao.particionar_componentes(componentes, ids_teste, ids_pool)


def test_teste_vazio_levanta_erro(componentes):
    with pytest.raises(ValueError, match="teste"):
        construcao.particionar_componentes(componentes, [], ["p4"])


def test_pool_vazio_levanta_erro_em_vez_de_deixar_a_validacao_sem_nada(componentes):
    with pytest.raises(ValueError, match="pool"):
        construcao.particionar_componentes(componentes, ["p2"], [])


# ── verificar_particao_por_componente (CA-1b-06) ─────────────────────────────


def _valida(componentes) -> pd.DataFrame:
    return construcao.particionar_componentes(componentes, ["p2"], ["p4", "p6"])


def test_particao_valida_passa_na_verificacao(componentes):
    construcao.verificar_particao_por_componente(_valida(componentes))


def test_componente_em_duas_particoes_falha_nomeando_o_componente(componentes):
    particao = _valida(componentes)
    particao.loc[particao["id_produto"] == "p1", "particao"] = "treino"  # c1 era do teste

    with pytest.raises(AssertionError, match="c1"):
        construcao.verificar_particao_por_componente(particao)


def test_particao_fora_do_dominio_falha(componentes):
    particao = _valida(componentes)
    particao.loc[0, "particao"] = "teste_externo"

    with pytest.raises(AssertionError, match="teste_externo"):
        construcao.verificar_particao_por_componente(particao)


# ── vazamento_residual (CA-1b-06) ────────────────────────────────────────────


def _positivos(*pares: tuple[str, str]) -> pd.DataFrame:
    return pd.DataFrame(pares, columns=["id_a", "id_b"])


def test_sem_positivo_separado_o_vazamento_residual_e_zero(componentes):
    positivos = _positivos(("p1", "p2"), ("p4", "p5"))

    assert construcao.vazamento_residual(positivos, componentes) == 0.0


def test_vazamento_residual_e_a_fracao_de_positivos_com_lados_em_componentes_diferentes(
    componentes,
):
    assert construcao.vazamento_residual(
        _positivos(("p1", "p2"), ("p1", "p4")), componentes
    ) == pytest.approx(0.5)
    assert construcao.vazamento_residual(
        _positivos(("p1", "p4"), ("p2", "p6")), componentes
    ) == pytest.approx(1.0)


def test_vazamento_residual_nao_depende_de_qual_lado_e_a_nem_b(componentes):
    assert construcao.vazamento_residual(
        _positivos(("p4", "p1")), componentes
    ) == construcao.vazamento_residual(_positivos(("p1", "p4")), componentes)


def test_positivo_com_id_fora_do_mapa_levanta_erro_com_o_id(componentes):
    with pytest.raises(ValueError, match="zzz"):
        construcao.vazamento_residual(_positivos(("p1", "zzz")), componentes)


def test_sem_positivos_levanta_erro_em_vez_de_dividir_por_zero(componentes):
    with pytest.raises(ValueError, match="positivos"):
        construcao.vazamento_residual(_positivos(), componentes)


# ── resumir_particao (o maior componente é reportado) ────────────────────────


def test_resumo_traz_produtos_componentes_fracao_e_maior_componente_por_particao(componentes):
    particao = construcao.particionar_componentes(componentes, ["p2"], ["p4", "p6"])

    resumo = construcao.resumir_particao(particao).set_index("particao")

    assert list(construcao.resumir_particao(particao).columns) == COLUNAS_RESUMO
    assert list(resumo.index) == list(construcao.PARTICOES)
    assert resumo.loc["teste", ["n_componentes", "n_produtos", "maior_componente"]].tolist() == [
        1,
        3,
        3,
    ]
    assert resumo.loc[
        "validacao", ["n_componentes", "n_produtos", "maior_componente"]
    ].tolist() == [2, 3, 2]
    assert resumo.loc["treino", ["n_componentes", "n_produtos", "maior_componente"]].tolist() == [
        1,
        2,
        2,
    ]
    assert resumo["fracao_base"].tolist() == pytest.approx([2 / 8, 3 / 8, 3 / 8])
    assert resumo["fracao_base"].sum() == pytest.approx(1.0)


def test_particao_vazia_aparece_no_resumo_com_zeros():
    particao = pd.DataFrame(
        {"id_produto": ["a", "b"], "componente": ["c", "d"], "particao": ["treino", "teste"]}
    )

    resumo = construcao.resumir_particao(particao).set_index("particao")

    assert resumo.loc[
        "validacao", ["n_componentes", "n_produtos", "maior_componente"]
    ].tolist() == [
        0,
        0,
        0,
    ]
    assert resumo.loc["validacao", "fracao_base"] == 0.0
