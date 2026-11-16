"""
test_transformacao_treino_pxp.py — Camada 2: montagem do `treino_pxp.parquet`, em memória (spec 001,
RF2 reescrita pelo ADR-0015; design-treino-pxp §5, §8 e §10).

O treino junta até três fontes no mesmo formato de pares: a parte A (negativos por tamanho e
positivos por perturbação), a anotação B2 do autor (só `match` e `nao_match`; `incerto` e pendente
ficam de fora) e os pares da TAIL (lado sintético `tail_...`). A verificação final é a barreira
crítica da montagem. Os textos e rótulos são sintéticos, escritos para o teste.
"""

import importlib.util
import os

import numpy as np
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
    ("n01", "leite integral italac 1l", "loja_a"),
    ("n02", "leite integral italac 500ml", "loja_b"),
    ("n03", "leite integral italac 200ml", "loja_c"),
    ("n04", "arroz branco tio joao 5kg", "loja_a"),
    ("n05", "arroz branco tio joao 1kg", "loja_b"),
    ("n06", "feijao carioca camil 1kg", "loja_a"),
    ("n07", "feijao carioca camil 500g", "loja_c"),
    ("n08", "leite desnatado piracanjuba 500ml", "loja_b"),
    ("n09", "cafe pilao tradicional 500g", "loja_a"),
    ("n10", "cafe pilao extra forte 250g", "loja_b"),
    ("n11", "oleo de soja liza 900ml", "loja_c"),
    ("n12", "oleo de soja liza 0,9l", "loja_a"),
    ("n13", "sal cisne", "loja_a"),
    ("n14", "sal cisne refinado 1kg", "loja_b"),
    ("n15", "biscoito maria bauducco 200g", "loja_c"),
    ("n16", "biscoito maria bauducco 200g", "loja_a"),
    ("n17", "agua mineral indaia 1,5l", "loja_a"),
    ("n18", "agua mineral crystal 500ml", "loja_c"),
    ("p01", "suco uva integral tial 1l", "loja_a"),
    ("p02", "suco uva integral tial 1l", "loja_b"),
    ("p03", "suco uva integral tial 1l tipo 1", "loja_a"),
    ("p04", "arroz branco tio joao 5kg", "loja_a"),
    ("p05", "arroz tio joao branco 5kg", "loja_b"),
    ("p06", "arroz integral camil 1kg", "loja_c"),
    ("p07", "sabao em po omo 1kg", "loja_c"),
    ("p08", "sabao em po omo lavagem perfeita 1kg", "loja_a"),
    ("p09", "feijao carioca camil 1kg", "loja_a"),
    ("p10", "feijao preto camil 1kg", "loja_b"),
    ("p11", "biscoito maria bauducco 200g", "loja_b"),
    ("p12", "macarrao espaguete adria 500g", "loja_b"),
    ("p13", "feijao carioca camil 500g", "loja_c"),
    ("p14", "sal cisne", "loja_c"),
    ("p15", "sal cisne refinado", "loja_a"),
]
CFG_AUTO = {
    "seed": 42,
    "k": 20,
    "incluir_mesma_loja": False,
    "faixas_cosseno": [0.0, 0.5, 1.0],
    "n_negativos_por_faixa": {"[0.00, 0.50)": 2, "[0.50, 1.00]": 2},
    "teto_negativos_por_produto": 3,
    "n_positivos": 4,
    "pesos_perturbacao": {"unidade": 1, "ordem": 0, "abreviacao": 0, "ruido": 0},
    "abreviacoes": {"leite": ["lt"]},
}
COLUNAS_PARES = construcao.COLUNAS_PARES_TREINO_PXP


@pytest.fixture
def treino() -> pd.DataFrame:
    df = pd.DataFrame(TEXTOS, columns=["id_produto", "descricao", "loja"])
    df["texto_normalizado"] = df["descricao"]
    df["und_val"] = [float(i + 1) for i in range(len(df))]
    df["und_med"] = "KG"
    df["componente"] = df["id_produto"]
    return df


@pytest.fixture
def auto(treino) -> pd.DataFrame:
    return construcao.montar_pares_treino_auto(treino, CFG_AUTO)


@pytest.fixture
def pares_b2(treino) -> pd.DataFrame:
    return construcao.selecionar_pares_b2(treino, 20, 0.4)


def _planilha_anotada(treino, pares_b2, rotulos: list[str]) -> pd.DataFrame:
    planilha = construcao.montar_planilha_b2(pares_b2, treino, 42)
    planilha.loc[: len(rotulos) - 1, "rotulo"] = rotulos
    return planilha


ROTULOS_PARCIAIS = ["match"] * 3 + ["nao_match"] * 2 + ["incerto"]  # o resto fica pendente


@pytest.fixture
def b2(treino, pares_b2) -> pd.DataFrame:
    planilha = _planilha_anotada(treino, pares_b2, ROTULOS_PARCIAIS)
    return construcao.ingerir_anotacao_b2(planilha, pares_b2, treino)


def _pares_tail(n: int = 3) -> pd.DataFrame:
    linhas = []
    for i in range(n):
        original, variante = f"Shampoo Acme Brilho {i} 300ml", f"Shampo Acme Brilho {i} 300ml"
        id_a = "tail_" + construcao._hash_curto(original)
        id_b = "tail_" + construcao._hash_curto(variante)
        linhas.append(
            {
                "id_par": construcao._hash_curto(f"{id_a}|{id_b}"),
                "id_a": id_a,
                "descricao_a": original,
                "und_val_a": np.nan,
                "und_med_a": None,
                "id_b": id_b,
                "descricao_b": variante,
                "und_val_b": np.nan,
                "und_med_b": None,
                "tipo_par": "produto_produto",
                "origem": "tail_variante",
                "rotulo": "match",
            }
        )
    return pd.DataFrame(linhas, columns=COLUNAS_PARES)


@pytest.fixture
def tail() -> pd.DataFrame:
    return _pares_tail()


@pytest.fixture
def completo(treino, auto, b2, tail) -> pd.DataFrame:
    return construcao.montar_treino_pxp(treino, auto, b2, tail)


# ── ingerir_anotacao_b2 ──────────────────────────────────────────────────────


def test_ingestao_traz_so_match_e_nao_match_com_origem_autor_b2(b2):
    assert list(b2.columns) == COLUNAS_PARES
    assert len(b2) == 5
    assert b2["rotulo"].value_counts().to_dict() == {"match": 3, "nao_match": 2}
    assert set(b2["origem"]) == {"autor_b2"}
    assert set(b2["tipo_par"]) == {"produto_produto"}


def test_ingestao_deixa_de_fora_o_incerto_e_o_que_ainda_esta_pendente(treino, pares_b2):
    planilha = _planilha_anotada(treino, pares_b2, ROTULOS_PARCIAIS)

    b2 = construcao.ingerir_anotacao_b2(planilha, pares_b2, treino)

    anotados = planilha.loc[planilha["rotulo"].isin(["match", "nao_match"])]
    assert set(zip(b2["id_a"], b2["id_b"], strict=True)) == set(
        zip(anotados["id_a"], anotados["id_b"], strict=True)
    )


def test_ingestao_usa_texto_e_unidade_do_treino_e_o_hash_do_par(treino, b2):
    base = treino.set_index("id_produto")

    assert (b2["id_a"] < b2["id_b"]).all()
    assert (b2["descricao_a"] == b2["id_a"].map(base["descricao"])).all()
    assert (b2["und_val_b"] == b2["id_b"].map(base["und_val"])).all()
    assert (
        b2["id_par"]
        == [construcao._hash_curto(f"{a}|{b}") for a, b in zip(b2["id_a"], b2["id_b"], strict=True)]
    ).all()


def test_ingestao_de_planilha_sem_nenhuma_anotacao_devolve_vazio_com_as_colunas(treino, pares_b2):
    planilha = construcao.montar_planilha_b2(pares_b2, treino, 42)

    b2 = construcao.ingerir_anotacao_b2(planilha, pares_b2, treino)

    assert b2.empty and list(b2.columns) == COLUNAS_PARES


def test_ingestao_com_rotulo_invalido_levanta_erro(treino, pares_b2):
    planilha = _planilha_anotada(treino, pares_b2, ["match", "talvez"])

    with pytest.raises(ValueError, match=planilha.loc[1, "id_par"]):
        construcao.ingerir_anotacao_b2(planilha, pares_b2, treino)


def test_ingestao_com_linha_apagada_levanta_erro(treino, pares_b2):
    planilha = _planilha_anotada(treino, pares_b2, ROTULOS_PARCIAIS).iloc[1:]

    with pytest.raises(ValueError, match="faltam"):
        construcao.ingerir_anotacao_b2(planilha, pares_b2, treino)


def test_ingestao_com_par_fora_do_treino_levanta_erro_com_o_id(treino, pares_b2):
    planilha = _planilha_anotada(treino, pares_b2, ROTULOS_PARCIAIS)
    sai = planilha.loc[0, "id_a"]

    with pytest.raises(ValueError, match=sai):
        construcao.ingerir_anotacao_b2(planilha, pares_b2, treino[treino["id_produto"] != sai])


# ── montar_treino_pxp ────────────────────────────────────────────────────────


def test_montagem_junta_as_tres_fontes_com_as_origens_esperadas(completo, auto, b2, tail):
    contagem = completo["origem"].value_counts().to_dict()

    assert list(completo.columns) == COLUNAS_PARES
    assert len(completo) == len(auto) + len(b2) + len(tail)
    assert contagem["autor_b2"] == 5 and contagem["tail_variante"] == 3
    assert contagem["neg_tamanho"] == 4 and contagem["pos_unidade"] == 4
    assert completo["id_par"].is_unique
    assert set(completo["rotulo"]) == {"match", "nao_match"}


def test_montagem_sem_b2_nem_tail_so_tem_a_parte_a(treino, auto):
    completo = construcao.montar_treino_pxp(treino, auto)

    assert len(completo) == len(auto)
    assert set(completo["origem"]) == set(auto["origem"])


def test_montagem_sai_em_ordem_deterministica_e_nao_depende_da_ordem_das_fontes(
    treino, auto, b2, tail, completo
):
    de_novo = construcao.montar_treino_pxp(
        treino,
        auto.sample(frac=1, random_state=1).reset_index(drop=True),
        b2.sample(frac=1, random_state=2).reset_index(drop=True),
        tail.sample(frac=1, random_state=3).reset_index(drop=True),
    )

    pd.testing.assert_frame_equal(completo, de_novo)
    assert list(completo["origem"]) == sorted(completo["origem"])


def test_montagem_com_id_par_repetido_entre_fontes_falha(treino, auto, b2):
    repetido = b2.copy()
    repetido.loc[0, "id_par"] = auto.loc[0, "id_par"]

    with pytest.raises(AssertionError, match="duplicado"):
        construcao.montar_treino_pxp(treino, auto, repetido)


# ── verificar_treino_pxp (a barreira crítica da montagem) ────────────────────


def test_treino_completo_passa_na_verificacao(treino, completo):
    construcao.verificar_treino_pxp(completo, treino)


def test_b2_com_tamanho_diferente_falha(treino, completo):
    treino_ruim = completo.copy()
    i = treino_ruim.index[treino_ruim["origem"] == "autor_b2"][0]
    treino_ruim.loc[i, "descricao_b"] = "produto qualquer 7kg"

    with pytest.raises(AssertionError, match="tamanho"):
        construcao.verificar_treino_pxp(treino_ruim, treino)


def test_b2_entre_produtos_da_mesma_loja_falha(treino, completo):
    with pytest.raises(AssertionError, match="loja"):
        construcao.verificar_treino_pxp(completo, treino.assign(loja="loja_a"))


def test_b2_com_id_fora_do_treino_falha_com_o_id(treino, completo):
    ruim = completo.copy()
    i = ruim.index[ruim["origem"] == "autor_b2"][0]
    ruim.loc[i, "id_a"] = "zzz"

    with pytest.raises(AssertionError, match="zzz"):
        construcao.verificar_treino_pxp(ruim, treino)


def test_tail_com_id_de_produto_real_falha(treino, completo):
    ruim = completo.copy()
    i = ruim.index[ruim["origem"] == "tail_variante"][0]
    ruim.loc[i, "id_a"] = "n01"

    with pytest.raises(AssertionError, match="tail"):
        construcao.verificar_treino_pxp(ruim, treino)


def test_tail_sem_o_prefixo_tail_falha(treino, completo):
    ruim = completo.copy()
    i = ruim.index[ruim["origem"] == "tail_variante"][0]
    ruim.loc[i, "id_b"] = "outro_" + ruim.loc[i, "id_b"]

    with pytest.raises(AssertionError, match="tail"):
        construcao.verificar_treino_pxp(ruim, treino)


def test_positivo_da_tail_que_muda_o_tamanho_falha(treino, completo):
    ruim = completo.copy()
    i = ruim.index[ruim["origem"] == "tail_variante"][0]
    ruim.loc[i, "descricao_b"] = "Shampo Acme Brilho 0 900ml"

    with pytest.raises(AssertionError, match="tamanho"):
        construcao.verificar_treino_pxp(ruim, treino)


def test_origem_desconhecida_falha(treino, completo):
    ruim = completo.copy()
    ruim.loc[0, "origem"] = "heuristica_de_marca"

    with pytest.raises(AssertionError, match="origem"):
        construcao.verificar_treino_pxp(ruim, treino)


def test_rotulo_incerto_nunca_entra_no_treino(treino, completo):
    ruim = completo.copy()
    i = ruim.index[ruim["origem"] == "autor_b2"][0]
    ruim.loc[i, "rotulo"] = "incerto"

    with pytest.raises(AssertionError, match="rotulo"):
        construcao.verificar_treino_pxp(ruim, treino)


def test_coluna_do_matcher_alta_falha(treino, completo):
    with pytest.raises(AssertionError, match="codg_item"):
        construcao.verificar_treino_pxp(completo.assign(codg_item="1"), treino)
