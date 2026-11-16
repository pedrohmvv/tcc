"""
test_transformacao_adjudicacao_pxp.py — Camada 2: adjudicação dos `incerto` do teste produto ×
produto, em memória (protocolo §3.5; ADR-0005; decisão do autor em 2026-11-16, formato A).

Os pares `incerto` da primeira passada vão para uma planilha SEPARADA (`anotacoes_teste_pxp_
adjudicacao.csv`), com o mesmo contrato de 15 colunas da planilha do teste (o anotador HTML abre
sem mudança). A primeira passada nunca é alterada: o reteste e o Kappa comparam contra o que o
autor marcou de fato. A fonte da decisão vai no prefixo da observação (`dicionario:` ou `alta:`),
conferido pelo validador. Quem continuar `incerto` fica fora do teste final.

Os produtos e pares são sintéticos, escritos para o teste; nenhum rótulo é de dado real.
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

CICLO = ["match", "nao_match", "incerto", "match"]  # 12 pares → 3 `incerto`
N_PARES = 12


@pytest.fixture
def primeira() -> pd.DataFrame:
    """Planilha do teste com a primeira passada completa (rótulo, observação, timestamp)."""
    produtos, pares = [], []
    for n in range(N_PARES):
        a, b = f"a{n:03d}", f"b{n:03d}"
        produtos.append((a, f"t{a}", f"SUCO {n} 1L", "X", 1.0, "L"))
        produtos.append((b, f"t{b}", f"SUCO {n}X 1L", "Y", 1.0, "L"))
        pares.append((a, b, "[0.90, 1.00]", 0.05))
    universo = pd.DataFrame(
        produtos, columns=["id_produto", "id_texto", "descricao", "loja", "und_val", "und_med"]
    )
    universo["texto_normalizado"] = universo["descricao"].str.lower()
    pares_df = pd.DataFrame(pares, columns=["id_a", "id_b", "estrato", "prob_inclusao"])
    planilha = construcao.montar_planilha_teste_pxp(pares_df, universo, 42)
    return planilha.assign(
        rotulo=[CICLO[i % len(CICLO)] for i in range(len(planilha))],
        observacao=[f"1a {i}" for i in range(len(planilha))],
        timestamp_anotacao=[f"2026-11-16T10:{i:02d}:00-03:00" for i in range(len(planilha))],
    )


def _incertos(primeira: pd.DataFrame) -> list[str]:
    return list(primeira.loc[primeira["rotulo"] == "incerto", "id_par"])


# ── montar_planilha_adjudicacao_pxp ──────────────────────────────────────────


def test_planilha_so_tem_os_pares_incerto_da_primeira_passada_na_mesma_ordem(primeira):
    planilha = construcao.montar_planilha_adjudicacao_pxp(primeira)

    assert list(planilha["id_par"]) == _incertos(primeira)
    assert len(planilha) == 3


def test_planilha_tem_o_contrato_de_15_colunas_do_teste(primeira):
    planilha = construcao.montar_planilha_adjudicacao_pxp(primeira)

    assert list(planilha.columns) == construcao.COLUNAS_PLANILHA_TESTE_PXP


def test_planilha_sai_sem_rotulo_observacao_nem_timestamp_e_com_origem_propria(primeira):
    planilha = construcao.montar_planilha_adjudicacao_pxp(primeira)

    for coluna in ["rotulo", "observacao", "timestamp_anotacao", "reteste"]:
        assert (planilha[coluna].fillna("") == "").all(), coluna
    assert set(planilha["origem"]) == {"teste_adjudicacao"}
    assert set(planilha["tipo_par"]) == {"produto_produto"}


def test_planilha_traz_o_texto_e_os_ids_da_primeira_passada(primeira):
    planilha = construcao.montar_planilha_adjudicacao_pxp(primeira).set_index("id_par")
    original = primeira.set_index("id_par")
    colunas = ["id_a", "descricao_a", "und_val_a", "und_med_a", "id_b", "descricao_b"]

    assert planilha[colunas].equals(original.loc[planilha.index, colunas])


def test_planilha_nao_altera_a_primeira_passada(primeira):
    antes = primeira.copy(deep=True)

    construcao.montar_planilha_adjudicacao_pxp(primeira)

    assert primeira.equals(antes)


def test_planilha_sem_nenhum_incerto_falha_em_vez_de_gerar_arquivo_vazio(primeira):
    sem = primeira.assign(rotulo="match")

    with pytest.raises(ValueError, match="incerto"):
        construcao.montar_planilha_adjudicacao_pxp(sem)


def test_planilha_com_primeira_passada_incompleta_falha_nomeando_o_par(primeira):
    pendente = primeira.loc[0, "id_par"]
    primeira.loc[0, "rotulo"] = ""

    with pytest.raises(ValueError, match=pendente):
        construcao.montar_planilha_adjudicacao_pxp(primeira)


# ── validar_adjudicacao_pxp ──────────────────────────────────────────────────


def _adjudicada(primeira: pd.DataFrame, rotulos: list[str], obs: list[str]) -> pd.DataFrame:
    planilha = construcao.montar_planilha_adjudicacao_pxp(primeira)
    return planilha.assign(rotulo=rotulos, observacao=obs)


def test_validacao_aceita_planilha_em_branco_quando_nao_exige_completa(primeira):
    planilha = construcao.montar_planilha_adjudicacao_pxp(primeira)

    construcao.validar_adjudicacao_pxp(planilha, primeira)


def test_validacao_exige_todos_os_pares_decididos_quando_completa(primeira):
    planilha = construcao.montar_planilha_adjudicacao_pxp(primeira)

    with pytest.raises(ValueError, match="sem rotulo"):
        construcao.validar_adjudicacao_pxp(planilha, primeira, completa=True)


def test_validacao_aceita_match_e_nao_match_com_fonte_e_incerto_mantido(primeira):
    planilha = _adjudicada(
        primeira,
        ["match", "nao_match", "incerto"],
        ["dicionario: categoria confere", "alta: marca confirmada", "continua sem informação"],
    )

    construcao.validar_adjudicacao_pxp(planilha, primeira, completa=True)


@pytest.mark.parametrize("obs", ["", "porque sim", "dicionário: acento", "ALTA: maiúscula"])
def test_resolvido_sem_fonte_valida_no_prefixo_falha_nomeando_o_par(primeira, obs):
    ids = _incertos(primeira)
    planilha = _adjudicada(primeira, ["match", "incerto", "incerto"], [obs, "", ""])

    with pytest.raises(ValueError, match=ids[0]):
        construcao.validar_adjudicacao_pxp(planilha, primeira)


def test_resolvido_com_prefixo_mas_sem_texto_depois_falha(primeira):
    planilha = _adjudicada(primeira, ["nao_match", "incerto", "incerto"], ["alta:", "", ""])

    with pytest.raises(ValueError, match="fonte"):
        construcao.validar_adjudicacao_pxp(planilha, primeira)


def test_rotulo_fora_do_dominio_falha(primeira):
    planilha = _adjudicada(primeira, ["talvez", "", ""], ["", "", ""])

    with pytest.raises(ValueError, match="dom"):
        construcao.validar_adjudicacao_pxp(planilha, primeira)


def test_par_que_nao_era_incerto_na_primeira_passada_falha(primeira):
    planilha = construcao.montar_planilha_adjudicacao_pxp(primeira)
    intruso = primeira[primeira["rotulo"] == "match"].iloc[[0]].assign(rotulo="")
    planilha = pd.concat([planilha, intruso], ignore_index=True)

    with pytest.raises(ValueError, match=intruso.iloc[0]["id_par"]):
        construcao.validar_adjudicacao_pxp(planilha, primeira)


def test_par_incerto_apagado_da_planilha_falha(primeira):
    planilha = construcao.montar_planilha_adjudicacao_pxp(primeira).iloc[1:]

    with pytest.raises(ValueError, match="faltam"):
        construcao.validar_adjudicacao_pxp(planilha, primeira)


def test_id_par_duplicado_falha(primeira):
    planilha = construcao.montar_planilha_adjudicacao_pxp(primeira)
    planilha = pd.concat([planilha, planilha.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicado"):
        construcao.validar_adjudicacao_pxp(planilha, primeira)


def test_coluna_proibida_ou_ausente_falha(primeira):
    planilha = construcao.montar_planilha_adjudicacao_pxp(primeira)

    with pytest.raises(ValueError, match="proibidas"):
        construcao.validar_adjudicacao_pxp(planilha.assign(estrato="x"), primeira)
    with pytest.raises(ValueError, match="ausentes"):
        construcao.validar_adjudicacao_pxp(planilha.drop(columns=["rotulo"]), primeira)


# ── compor_rotulos_finais_teste_pxp ──────────────────────────────────────────


def test_rotulo_final_mantem_a_primeira_passada_e_aplica_a_adjudicacao(primeira):
    ids = _incertos(primeira)
    planilha = _adjudicada(
        primeira,
        ["match", "nao_match", "incerto"],
        ["dicionario: ok", "alta: ok", ""],
    )

    final = construcao.compor_rotulos_finais_teste_pxp(primeira, planilha).set_index("id_par")

    assert final.loc[ids[0], "rotulo_final"] == "match"
    assert final.loc[ids[0], "fonte_rotulo"] == "dicionario"
    assert final.loc[ids[1], "rotulo_final"] == "nao_match"
    assert final.loc[ids[1], "fonte_rotulo"] == "alta"
    outros = primeira[primeira["rotulo"] != "incerto"].set_index("id_par")
    assert (final.loc[outros.index, "rotulo_final"] == outros["rotulo"]).all()
    assert set(final.loc[outros.index, "fonte_rotulo"]) == {"autor_primeira_passada"}


def test_incerto_nao_resolvido_fica_fora_do_teste_final(primeira):
    ids = _incertos(primeira)
    planilha = _adjudicada(primeira, ["match", "incerto", "incerto"], ["dicionario: ok", "", ""])

    final = construcao.compor_rotulos_finais_teste_pxp(primeira, planilha)

    assert ids[1] not in set(final["id_par"])
    assert ids[2] not in set(final["id_par"])
    assert len(final) == N_PARES - 2
    assert set(final["rotulo_final"]) <= {"match", "nao_match"}


def test_composicao_tem_colunas_exatas_e_nao_traz_colunas_proibidas(primeira):
    planilha = _adjudicada(primeira, ["match", "match", "match"], ["alta: a", "alta: b", "alta: c"])

    final = construcao.compor_rotulos_finais_teste_pxp(primeira, planilha)

    assert list(final.columns) == ["id_par", "id_a", "id_b", "rotulo_final", "fonte_rotulo"]
    assert final["id_par"].is_unique


def test_composicao_exige_adjudicacao_completa(primeira):
    planilha = construcao.montar_planilha_adjudicacao_pxp(primeira)

    with pytest.raises(ValueError, match="sem rotulo"):
        construcao.compor_rotulos_finais_teste_pxp(primeira, planilha)


def test_composicao_nao_altera_as_entradas(primeira):
    planilha = _adjudicada(primeira, ["match", "nao_match", "incerto"], ["alta: a", "alta: b", ""])
    antes_p, antes_a = primeira.copy(deep=True), planilha.copy(deep=True)

    construcao.compor_rotulos_finais_teste_pxp(primeira, planilha)

    assert primeira.equals(antes_p)
    assert planilha.equals(antes_a)


# ── Terceira fonte `autor:` (decisão do autor em 2026-11-16, caminho 1) ──────────────────────────
# Desvio do protocolo §3.5 (que prevê só dicionário ou pesquisadores do ALTA): o autor decidiu
# alguns `incerto` pelo próprio julgamento, sem consultar nenhuma fonte. Precisa ficar registrado
# como tal, para o teste poder ser reportado com e sem esses pares.


def test_os_prefixos_aceitos_sao_dicionario_alta_e_autor():
    assert construcao.PREFIXOS_FONTE_ADJUDICACAO == ("dicionario:", "alta:", "autor:")


def test_decisao_com_prefixo_autor_e_aceita_pelo_validador(primeira):
    planilha = _adjudicada(
        primeira,
        ["nao_match", "match", "incerto"],
        ["autor: marcas diferentes no texto", "autor: mesma linha e tamanho", ""],
    )

    construcao.validar_adjudicacao_pxp(planilha, primeira, completa=True)


def test_rotulo_final_registra_autor_adjudicacao_como_fonte_propria(primeira):
    ids = _incertos(primeira)
    planilha = _adjudicada(
        primeira,
        ["nao_match", "match", "incerto"],
        ["autor: marcas diferentes", "dicionario: ok", ""],
    )

    final = construcao.compor_rotulos_finais_teste_pxp(primeira, planilha).set_index("id_par")

    assert final.loc[ids[0], "rotulo_final"] == "nao_match"
    assert final.loc[ids[0], "fonte_rotulo"] == "autor_adjudicacao"
    assert final.loc[ids[1], "fonte_rotulo"] == "dicionario"


def test_as_quatro_fontes_ficam_distinguiveis_no_teste_final(primeira):
    planilha = _adjudicada(
        primeira,
        ["match", "nao_match", "match"],
        ["dicionario: ok", "alta: ok", "autor: julgamento próprio"],
    )

    final = construcao.compor_rotulos_finais_teste_pxp(primeira, planilha)

    assert set(final["fonte_rotulo"]) == {
        "autor_primeira_passada",
        "dicionario",
        "alta",
        "autor_adjudicacao",
    }
    assert (final["fonte_rotulo"] == "autor_adjudicacao").sum() == 1


def test_autor_sem_texto_depois_do_prefixo_falha(primeira):
    planilha = _adjudicada(primeira, ["nao_match", "incerto", "incerto"], ["autor:", "", ""])

    with pytest.raises(ValueError, match="fonte"):
        construcao.validar_adjudicacao_pxp(planilha, primeira)


def test_prefixo_autor_e_sensivel_a_maiuscula(primeira):
    planilha = _adjudicada(primeira, ["nao_match", "incerto", "incerto"], ["Autor: x", "", ""])

    with pytest.raises(ValueError, match="fonte"):
        construcao.validar_adjudicacao_pxp(planilha, primeira)


def test_a_mensagem_de_fonte_invalida_lista_as_tres_fontes_aceitas(primeira):
    planilha = _adjudicada(primeira, ["nao_match", "incerto", "incerto"], ["sem prefixo", "", ""])

    with pytest.raises(ValueError) as erro:
        construcao.validar_adjudicacao_pxp(planilha, primeira)

    for prefixo in ("dicionario:", "alta:", "autor:"):
        assert prefixo in str(erro.value)


def test_incerto_mantido_nao_precisa_de_prefixo_nem_vira_autor(primeira):
    ids = _incertos(primeira)
    planilha = _adjudicada(
        primeira,
        ["incerto", "incerto", "match"],
        ["faltam informações", "", "autor: ok"],
    )

    final = construcao.compor_rotulos_finais_teste_pxp(primeira, planilha)

    assert ids[0] not in set(final["id_par"])
    assert ids[1] not in set(final["id_par"])
    assert len(final) == N_PARES - 2
