"""
test_transformacao_teste_pxp.py — Camada 2: composição do `teste_pxp.parquet`, em memória (spec 001
RF4/RF5; ADR-0004; ADR-0018; decisão do autor em 2026-11-16).

O teste final junta a primeira passada com a adjudicação dos `incerto` (`compor_rotulos_finais_
teste_pxp`), traz o texto e a unidade do UNIVERSO (nunca da planilha), e leva `estrato` e
`prob_inclusao` do sorteio (`pares_teste_pxp.csv`), necessários para ponderar o teste
estratificado (spec 004). Formato: as 12 colunas de `validacao_pxp.parquet` mais `fonte_rotulo`,
`estrato` e `prob_inclusao`. Os `incerto` não resolvidos ficam fora e isso é reportado por estrato.

Produtos e pares sintéticos, escritos para o teste; nenhum rótulo é de dado real.
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

COLUNAS_TESTE = [
    "id_par",
    "id_a",
    "descricao_a",
    "und_val_a",
    "und_med_a",
    "id_b",
    "descricao_b",
    "und_val_b",
    "und_med_b",
    "tipo_par",
    "origem",
    "rotulo",
    "fonte_rotulo",
    "estrato",
    "prob_inclusao",
]
CICLO = ["match", "nao_match", "incerto", "match"]  # 12 pares → 3 `incerto`
ESTRATOS = [("[0.90, 1.00]", 0.25), ("[0.70, 0.90)", 0.5), ("digito_divergente", 0.1)]


@pytest.fixture
def cenario() -> dict:
    produtos, pares = [], []
    for n in range(12):
        a, b = f"a{n:03d}", f"b{n:03d}"
        produtos.append((a, f"t{a}", f"SUCO {n} 1L", "X", 1.0, "L"))
        produtos.append((b, f"t{b}", f"SUCO {n}X 1L", "Y", 1.0, "L"))
        estrato, prob = ESTRATOS[n % 3]
        pares.append((a, b, estrato, prob))
    universo = pd.DataFrame(
        produtos, columns=["id_produto", "id_texto", "descricao", "loja", "und_val", "und_med"]
    )
    universo["texto_normalizado"] = universo["descricao"].str.lower()
    pares_df = pd.DataFrame(pares, columns=["id_a", "id_b", "estrato", "prob_inclusao"])
    primeira = construcao.montar_planilha_teste_pxp(pares_df, universo, 42)
    primeira = primeira.assign(
        rotulo=[CICLO[i % len(CICLO)] for i in range(len(primeira))],
        timestamp_anotacao="2026-11-16T10:00:00-03:00",
    )
    adjudicacao = construcao.montar_planilha_adjudicacao_pxp(primeira)
    adjudicacao = adjudicacao.assign(
        rotulo=["match", "nao_match", "incerto"],
        observacao=["dicionario: ok", "autor: julgamento próprio", "faltam informações"],
    )
    componentes = pd.DataFrame(
        {"id_produto": universo["id_produto"], "componente": universo["id_produto"]}
    ).assign(particao="teste")
    return {
        "primeira": primeira,
        "adjudicacao": adjudicacao,
        "pares": pares_df,
        "universo": universo,
        "componentes": componentes,
    }


def _montar(c: dict) -> pd.DataFrame:
    return construcao.montar_teste_pxp(c["primeira"], c["adjudicacao"], c["pares"], c["universo"])


# ── montar_teste_pxp ─────────────────────────────────────────────────────────


def test_teste_tem_as_15_colunas_do_contrato_na_ordem(cenario):
    assert list(_montar(cenario).columns) == COLUNAS_TESTE


def test_teste_so_tem_match_e_nao_match_e_deixa_fora_o_incerto_nao_resolvido(cenario):
    teste = _montar(cenario)
    mantido = cenario["adjudicacao"].query("rotulo == 'incerto'")["id_par"]

    assert set(teste["rotulo"]) <= {"match", "nao_match"}
    assert not set(mantido) & set(teste["id_par"])
    assert len(teste) == 12 - 1


def test_teste_registra_a_fonte_de_cada_rotulo(cenario):
    teste = _montar(cenario).set_index("id_par")
    adj = cenario["adjudicacao"].set_index("id_par")

    por_fonte = teste["fonte_rotulo"].value_counts().to_dict()
    assert por_fonte == {"autor_primeira_passada": 9, "dicionario": 1, "autor_adjudicacao": 1}
    assert teste.loc[adj.index[0], "rotulo"] == "match"
    assert teste.loc[adj.index[1], "fonte_rotulo"] == "autor_adjudicacao"


def test_estrato_e_prob_inclusao_vem_do_sorteio_e_nao_da_planilha(cenario):
    teste = _montar(cenario)
    pares = cenario["pares"]
    esperado = pares.set_index(["id_a", "id_b"])

    for linha in teste.itertuples(index=False):
        sorteio = esperado.loc[(linha.id_a, linha.id_b)]
        assert linha.estrato == sorteio["estrato"]
        assert linha.prob_inclusao == pytest.approx(sorteio["prob_inclusao"])


def test_texto_e_unidade_vem_do_universo_mesmo_com_planilha_adulterada(cenario):
    cenario["primeira"].loc[:, "descricao_a"] = "TEXTO ADULTERADO"
    universo = cenario["universo"].set_index("id_produto")

    teste = _montar(cenario)

    assert (teste["descricao_a"] == teste["id_a"].map(universo["descricao"])).all()
    assert (teste["descricao_b"] == teste["id_b"].map(universo["descricao"])).all()
    assert set(teste["und_med_a"]) == {"L"}


def test_origem_e_tipo_de_par_sao_fixos(cenario):
    teste = _montar(cenario)

    assert set(teste["origem"]) == {"teste"}
    assert set(teste["tipo_par"]) == {"produto_produto"}


def test_teste_e_ordenado_por_id_par_e_nao_depende_da_ordem_da_planilha(cenario):
    um = _montar(cenario)
    cenario["primeira"] = cenario["primeira"].iloc[::-1].reset_index(drop=True)
    outro = _montar(cenario)

    assert list(um["id_par"]) == sorted(um["id_par"])
    assert um.reset_index(drop=True).equals(outro.reset_index(drop=True))


def test_montar_nao_altera_as_entradas(cenario):
    antes = {k: v.copy(deep=True) for k, v in cenario.items()}

    _montar(cenario)

    for nome, quadro in antes.items():
        assert cenario[nome].equals(quadro), nome


def test_adjudicacao_incompleta_falha_e_nao_devolve_teste(cenario):
    cenario["adjudicacao"].loc[0, "rotulo"] = ""

    with pytest.raises(ValueError, match="sem rotulo"):
        _montar(cenario)


def test_par_do_teste_sem_estrato_no_sorteio_falha_nomeando_o_par(cenario):
    cenario["pares"] = cenario["pares"].iloc[1:]

    with pytest.raises(ValueError, match="estrato"):
        _montar(cenario)


def test_produto_fora_do_universo_falha_nomeando_o_id(cenario):
    cenario["universo"] = cenario["universo"][cenario["universo"]["id_produto"] != "a000"]

    with pytest.raises(ValueError, match="a000"):
        _montar(cenario)


# ── verificar_teste_pxp (barreiras críticas) ─────────────────────────────────


def _verificar(c: dict, teste: pd.DataFrame | None = None, componentes=None) -> None:
    teste = _montar(c) if teste is None else teste
    construcao.verificar_teste_pxp(
        teste, c["universo"], c["componentes"] if componentes is None else componentes
    )


def test_teste_valido_passa_pelas_barreiras(cenario):
    _verificar(cenario)


def test_produto_do_teste_fora_da_particao_teste_falha_nomeando_o_produto(cenario):
    teste = _montar(cenario)
    componentes = cenario["componentes"].copy()
    componentes.loc[componentes["id_produto"] == teste.iloc[0]["id_a"], "particao"] = "treino"

    with pytest.raises(AssertionError, match=teste.iloc[0]["id_a"]):
        _verificar(cenario, teste, componentes)


def test_produto_em_dois_pares_falha(cenario):
    teste = _montar(cenario)
    teste.loc[1, "id_a"] = teste.loc[0, "id_a"]

    with pytest.raises(AssertionError, match="mais de um par"):
        _verificar(cenario, teste)


@pytest.mark.parametrize("coluna", ["codg_item", "desc_ref", "match_score"])
def test_coluna_do_matcher_alta_falha(cenario, coluna):
    teste = _montar(cenario).assign(**{coluna: "x"})

    with pytest.raises(AssertionError, match="ADR-0011"):
        _verificar(cenario, teste)


def test_rotulo_fora_de_match_e_nao_match_falha(cenario):
    teste = _montar(cenario)
    teste.loc[0, "rotulo"] = "incerto"

    with pytest.raises(AssertionError, match="rotulo"):
        _verificar(cenario, teste)


def test_fonte_de_rotulo_desconhecida_falha(cenario):
    teste = _montar(cenario)
    teste.loc[0, "fonte_rotulo"] = "llm"

    with pytest.raises(AssertionError, match="fonte_rotulo"):
        _verificar(cenario, teste)


def test_texto_diferente_do_universo_falha(cenario):
    teste = _montar(cenario)
    teste.loc[0, "descricao_a"] = "OUTRO TEXTO"

    with pytest.raises(AssertionError, match="texto"):
        _verificar(cenario, teste)


@pytest.mark.parametrize("valor", [0.0, -0.1, 1.5, float("nan")])
def test_prob_inclusao_fora_de_zero_a_um_falha(cenario, valor):
    teste = _montar(cenario)
    teste.loc[0, "prob_inclusao"] = valor

    with pytest.raises(AssertionError, match="prob_inclusao"):
        _verificar(cenario, teste)


# ── resumir_teste_pxp (as exclusões por estrato têm de ser reportadas) ───────


def test_resumo_por_estrato_conta_sorteados_excluidos_e_finais(cenario):
    teste = _montar(cenario)

    resumo = construcao.resumir_teste_pxp(teste, cenario["pares"]).set_index("estrato")

    assert list(construcao.resumir_teste_pxp(teste, cenario["pares"]).columns) == [
        "estrato",
        "n_sorteados",
        "n_incerto_excluido",
        "n_final",
        "n_match",
        "n_nao_match",
        "n_autor_adjudicacao",
    ]
    assert resumo["n_sorteados"].sum() == 12
    assert resumo["n_incerto_excluido"].sum() == 1
    assert resumo["n_final"].sum() == len(teste)
    assert (resumo["n_sorteados"] == resumo["n_final"] + resumo["n_incerto_excluido"]).all()
    assert (resumo["n_final"] == resumo["n_match"] + resumo["n_nao_match"]).all()
    assert resumo["n_autor_adjudicacao"].sum() == 1
