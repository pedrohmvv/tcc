"""
test_transformacao_b2_pxp.py — Camada 2: pares do treino que o autor anota (opção B2), em memória
(spec 001, design-treino-pxp §8; pendência A5).

A B2 seleciona, entre os produtos de treino, os pares de lojas diferentes com **mesmo tamanho** e
cosseno TF-IDF ≥ corte, e os entrega ao autor numa planilha de cartão por par (a mesma do teste,
para usar a mesma ferramenta). Os textos da fixture foram escritos para este teste e os cossenos
que importam foram medidos com o mesmo vetorizador do script: 1,00; 0,77; 0,79; 0,63; 0,43; 0,41 e
0,76.
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
    ("p02", "suco uva integral tial 1l", "loja_b"),  # idêntico a p01 (cos 1,00)
    ("p03", "suco uva integral tial 1l tipo 1", "loja_a"),  # mesma loja de p01; cos 0,77 com p02
    ("p04", "arroz branco tio joao 5kg", "loja_a"),
    ("p05", "arroz tio joao branco 5kg", "loja_b"),  # inversão: vetor idêntico (1,00)
    ("p06", "arroz integral camil 1kg", "loja_c"),  # 0,43 e 0,41 com os feijões
    ("p07", "sabao em po omo 1kg", "loja_c"),
    ("p08", "sabao em po omo lavagem perfeita 1kg", "loja_a"),  # 0,79 com p07
    ("p09", "feijao carioca camil 1kg", "loja_a"),
    ("p10", "feijao preto camil 1kg", "loja_b"),  # 0,63 com p09
    ("p11", "biscoito maria bauducco 200g", "loja_b"),
    ("p12", "macarrao espaguete adria 500g", "loja_b"),
    ("p13", "feijao carioca camil 500g", "loja_c"),  # 0,76 com p09, mas 500g × 1kg
    ("p14", "sal cisne", "loja_c"),
    ("p15", "sal cisne refinado", "loja_a"),  # 0,78 com p14, mas nenhum dos dois tem tamanho
]
COLUNAS_PLANILHA = [
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
    "observacao",
    "timestamp_anotacao",
    "reteste",
]
PROIBIDAS = ["score", "cosseno", "estrato", "prob_inclusao", "codg_item", "desc_ref"]
K = 20


@pytest.fixture
def treino() -> pd.DataFrame:
    df = pd.DataFrame(TEXTOS, columns=["id_produto", "descricao", "loja"])
    df["texto_normalizado"] = df["descricao"]
    df["und_val"] = 1.0
    df["und_med"] = "KG"
    return df


def _pares(df: pd.DataFrame) -> set[tuple[str, str]]:
    return set(zip(df["id_a"], df["id_b"], strict=True))


# ── selecionar_pares_b2 ──────────────────────────────────────────────────────


def test_com_corte_05_entram_so_pares_entre_lojas_de_mesmo_tamanho(treino):
    pares = construcao.selecionar_pares_b2(treino, K, 0.5)

    assert _pares(pares) == {
        ("p01", "p02"),
        ("p02", "p03"),
        ("p04", "p05"),
        ("p07", "p08"),
        ("p09", "p10"),
    }


@pytest.mark.parametrize(("corte", "n_pares"), [(0.4, 7), (0.5, 5), (0.7, 4), (0.9, 2)])
def test_corte_maior_nunca_aumenta_o_numero_de_pares(treino, corte, n_pares):
    assert len(construcao.selecionar_pares_b2(treino, K, corte)) == n_pares


def test_par_de_tamanho_diferente_nunca_entra_mesmo_com_cosseno_alto(treino):
    """p09 × p13 tem cosseno 0,76, mas 1kg × 500g: pelo protocolo já é não-match, sem anotar."""
    pares = construcao.selecionar_pares_b2(treino, K, 0.3)

    assert ("p09", "p13") not in _pares(pares)


def test_par_sem_tamanho_nos_dois_lados_nunca_entra(treino):
    pares = construcao.selecionar_pares_b2(treino, K, 0.3)

    assert ("p14", "p15") not in _pares(pares)


def test_par_da_mesma_loja_nunca_entra(treino):
    pares = construcao.selecionar_pares_b2(treino, K, 0.3)

    assert ("p01", "p03") not in _pares(pares)


def test_pares_saem_unicos_em_ordem_canonica_com_o_score_acima_do_corte(treino):
    pares = construcao.selecionar_pares_b2(treino, K, 0.5)

    assert list(pares.columns) == ["id_a", "id_b", "score"]
    assert (pares["id_a"] < pares["id_b"]).all()
    assert not pares.duplicated(["id_a", "id_b"]).any()
    assert list(zip(pares["id_a"], pares["id_b"], strict=True)) == sorted(_pares(pares))
    assert (pares["score"] >= 0.5).all()
    assert (pares["score"] <= 1.0 + 1e-9).all()


def test_selecao_nao_depende_da_ordem_das_linhas(treino):
    esperado = construcao.selecionar_pares_b2(treino, K, 0.5)

    embaralhado = construcao.selecionar_pares_b2(
        treino.sample(frac=1, random_state=9).reset_index(drop=True), K, 0.5
    )

    pd.testing.assert_frame_equal(esperado, embaralhado)


def test_selecao_sem_nenhum_par_levanta_erro(treino):
    so_dois = treino[treino["id_produto"].isin(["p06", "p09"])]  # cosseno 0,43: abaixo do corte

    with pytest.raises(ValueError, match="nenhum par"):
        construcao.selecionar_pares_b2(so_dois, K, 0.5)


@pytest.mark.parametrize("corte", [0.0, -0.2, 1.01])
def test_corte_de_cosseno_fora_de_zero_a_um_levanta_erro(treino, corte):
    with pytest.raises(ValueError, match="cosseno"):
        construcao.selecionar_pares_b2(treino, K, corte)


# ── montar_planilha_b2 ───────────────────────────────────────────────────────


def _planilha(treino, seed: int = 42) -> pd.DataFrame:
    return construcao.montar_planilha_b2(
        construcao.selecionar_pares_b2(treino, K, 0.4), treino, seed
    )


def test_planilha_tem_as_colunas_da_planilha_do_teste_para_a_mesma_ferramenta(treino):
    planilha = _planilha(treino)

    assert list(planilha.columns) == COLUNAS_PLANILHA
    assert list(planilha.columns) == construcao.COLUNAS_PLANILHA_TESTE_PXP
    assert len(planilha) == 7
    assert planilha["id_par"].is_unique


def test_planilha_sai_sem_rotulo_com_origem_treino_b2_e_sem_score(treino):
    planilha = _planilha(treino)

    assert set(planilha["origem"]) == {"treino_b2"}
    assert set(planilha["tipo_par"]) == {"produto_produto"}
    for coluna in ["rotulo", "observacao", "timestamp_anotacao", "reteste"]:
        assert (planilha[coluna].fillna("") == "").all(), coluna
    assert not set(PROIBIDAS) & set(planilha.columns)


def test_planilha_traz_o_texto_do_universo_de_cada_lado(treino):
    planilha = _planilha(treino)
    descricao = treino.set_index("id_produto")["descricao"]

    assert (planilha["descricao_a"] == planilha["id_a"].map(descricao)).all()
    assert (planilha["descricao_b"] == planilha["id_b"].map(descricao)).all()


def test_ordem_da_planilha_depende_da_seed_e_nao_da_ordem_de_entrada(treino):
    pares = construcao.selecionar_pares_b2(treino, K, 0.4)
    embaralhado = pares.sample(frac=1, random_state=2).reset_index(drop=True)

    assert construcao.montar_planilha_b2(pares, treino, 7).equals(
        construcao.montar_planilha_b2(embaralhado, treino, 7)
    )
    assert list(_planilha(treino, 7)["id_par"]) != list(_planilha(treino, 8)["id_par"])


def test_id_par_e_o_mesmo_hash_da_planilha_do_teste(treino):
    planilha = _planilha(treino).set_index(["id_a", "id_b"])

    assert planilha.loc[("p01", "p02"), "id_par"] == construcao._hash_curto("p01|p02")


def test_produto_fora_do_treino_levanta_erro_com_o_id(treino):
    pares = construcao.selecionar_pares_b2(treino, K, 0.4)

    with pytest.raises(ValueError, match="p01"):
        construcao.montar_planilha_b2(pares, treino[treino["id_produto"] != "p01"], 42)


# ── validar_anotacao_b2 ──────────────────────────────────────────────────────


def _validar(planilha, treino, **kwargs):
    construcao.validar_anotacao_b2(
        planilha, construcao.selecionar_pares_b2(treino, K, 0.4), **kwargs
    )


def test_planilha_recem_montada_e_valida_enquanto_incompleta(treino):
    _validar(_planilha(treino), treino)


@pytest.mark.parametrize("rotulo", ["match", "nao_match", "incerto"])
def test_rotulos_do_dominio_sao_aceitos(treino, rotulo):
    _validar(_planilha(treino).assign(rotulo=rotulo), treino, completa=True)


def test_rotulo_fora_do_dominio_levanta_erro_com_o_id_do_par(treino):
    planilha = _planilha(treino)
    planilha.loc[2, "rotulo"] = "talvez"

    with pytest.raises(ValueError, match=planilha.loc[2, "id_par"]):
        _validar(planilha, treino)


def test_exigir_completa_falha_com_rotulo_vazio_e_nomeia_o_par(treino):
    planilha = _planilha(treino).assign(rotulo="nao_match")
    planilha.loc[3, "rotulo"] = ""

    with pytest.raises(ValueError, match=planilha.loc[3, "id_par"]):
        _validar(planilha, treino, completa=True)


def test_par_apagado_levanta_erro(treino):
    with pytest.raises(ValueError, match="faltam"):
        _validar(_planilha(treino).iloc[1:], treino)


def test_par_que_nao_e_do_b2_levanta_erro(treino):
    planilha = _planilha(treino)
    planilha.loc[0, "id_b"] = "zzz"

    with pytest.raises(ValueError, match="fora"):
        _validar(planilha, treino)


def test_id_par_duplicado_levanta_erro(treino):
    planilha = _planilha(treino)
    planilha.loc[1, "id_par"] = planilha.loc[0, "id_par"]

    with pytest.raises(ValueError, match="duplicado"):
        _validar(planilha, treino)


def test_coluna_proibida_levanta_erro(treino):
    with pytest.raises(ValueError, match="score"):
        _validar(_planilha(treino).assign(score=0.9), treino)


def test_planilha_vazia_levanta_erro(treino):
    with pytest.raises(ValueError, match="vazia"):
        _validar(_planilha(treino).iloc[0:0], treino)


# ── gravar_planilha_b2 ───────────────────────────────────────────────────────


def test_grava_com_nome_versionavel_e_separador_ponto_e_virgula(treino, tmp_path):
    caminho = construcao.gravar_planilha_b2(_planilha(treino), tmp_path)

    assert caminho.name == "anotacoes_treino_b2_pxp.csv"
    assert pd.read_csv(caminho, sep=";", dtype=str).shape[1] == len(COLUNAS_PLANILHA)


def test_nunca_sobrescreve_a_planilha_onde_o_autor_anota(treino, tmp_path):
    construcao.gravar_planilha_b2(_planilha(treino), tmp_path)

    with pytest.raises(FileExistsError):
        construcao.gravar_planilha_b2(_planilha(treino), tmp_path)
