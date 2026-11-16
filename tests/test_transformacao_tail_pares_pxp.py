"""
test_transformacao_tail_pares_pxp.py — Camada 2: pares da TAIL no formato do treino, bloco P5b
(ADR-0013; ADR-0015; spec 001 RF8; decisões D1 a D6 do autor em 2026-11-16, com o D1 valendo para
as variantes E para as notas fiscais).

Fontes sintéticas (`fontes_tail_exemplo`, conftest). Config com uma única faixa de cosseno, para os
testes não dependerem de valores numéricos de similaridade.
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


def _cfg(**alteracoes: object) -> dict:
    base = {
        "seed": 42,
        "incluir_sem_tamanho": False,
        "limiar_quase_duplicata": 0.9,
        "max_pares_por_grupo_nf": 2,
        "razao_negativos": 0.5,
        "k": 20,
        "faixas_cosseno": [0.0, 1.0],
        "peso_negativos_por_faixa": {"[0.00, 1.00]": 1.0},
        "teto_negativos_por_produto": 3,
    }
    return {**base, **alteracoes}


def _montar(fontes: dict, **alteracoes: object) -> tuple[pd.DataFrame, pd.DataFrame]:
    return construcao.montar_pares_tail_pxp(fontes, _cfg(**alteracoes))


def _titulos(pares: pd.DataFrame) -> set[str]:
    return set(pares["descricao_a"]) | set(pares["descricao_b"])


# ── contrato do conjunto ─────────────────────────────────────────────────────


def test_pares_da_tail_tem_o_formato_dos_pares_de_treino(fontes_tail_exemplo):
    pares, _ = _montar(fontes_tail_exemplo)

    assert list(pares.columns) == construcao.COLUNAS_PARES_TREINO_PXP
    assert set(pares["origem"]) <= set(construcao.ORIGENS_TAIL)
    assert set(pares["tipo_par"]) == {"produto_produto"}


def test_rotulo_segue_a_origem(fontes_tail_exemplo):
    pares, _ = _montar(fontes_tail_exemplo)

    positivos = pares[pares["origem"].isin(construcao.ORIGENS_TAIL_POSITIVAS)]
    negativos = pares[pares["origem"] == "tail_negativo"]
    assert set(positivos["rotulo"]) == {"match"}
    assert set(negativos["rotulo"]) == {"nao_match"}


def test_ids_dos_dois_lados_tem_prefixo_tail_e_o_id_do_par_e_unico(fontes_tail_exemplo):
    pares, _ = _montar(fontes_tail_exemplo)

    assert pares["id_a"].str.startswith("tail_").all()
    assert pares["id_b"].str.startswith("tail_").all()
    assert (pares["id_a"] != pares["id_b"]).all()
    assert pares["id_par"].is_unique


def test_titulo_igual_recebe_sempre_o_mesmo_id(fontes_tail_exemplo):
    pares, _ = _montar(fontes_tail_exemplo)
    ids = pd.concat(
        [
            pares[["id_a", "descricao_a"]].set_axis(["id", "d"], axis=1),
            pares[["id_b", "descricao_b"]].set_axis(["id", "d"], axis=1),
        ]
    )

    assert ids.groupby("d")["id"].nunique().max() == 1
    assert ids.groupby("id")["d"].nunique().max() == 1


def test_a_tail_nao_traz_unidade_estruturada(fontes_tail_exemplo):
    pares, _ = _montar(fontes_tail_exemplo)

    assert pares["und_val_a"].isna().all() and pares["und_val_b"].isna().all()
    assert pares["und_med_a"].isna().all() and pares["und_med_b"].isna().all()


# ── positivos: D1 (tamanho), grupos, benchmark (D2) e teto (D4) ──────────────


def test_positivos_preservam_o_conjunto_de_tamanhos_e_nunca_sao_iguais(fontes_tail_exemplo):
    pares, _ = _montar(fontes_tail_exemplo)
    positivos = pares[pares["origem"].isin(construcao.ORIGENS_TAIL_POSITIVAS)]

    for linha in positivos.itertuples(index=False):
        assert construcao.tokens_numericos(linha.descricao_a) == construcao.tokens_numericos(
            linha.descricao_b
        )
        assert linha.descricao_a != linha.descricao_b


def test_variante_que_corrompe_o_tamanho_ou_vem_do_fallback_do_llm_fica_fora(fontes_tail_exemplo):
    pares, _ = _montar(fontes_tail_exemplo)

    assert "Biscoito Maria Bauducco 200" not in _titulos(pares)
    assert "lixo do llm" not in _titulos(pares)


def test_d1_sem_tamanho_fica_fora_nas_variantes_e_tambem_nas_notas_fiscais(fontes_tail_exemplo):
    pares, _ = _montar(fontes_tail_exemplo)
    titulos = _titulos(pares)

    assert "Pao Forma Wickbold" not in titulos  # variante sem tamanho
    assert not any(t.startswith("Pao Sem Tamanho") for t in titulos)  # nota fiscal sem tamanho


def test_d1_ligado_inclui_os_pares_sem_tamanho_das_variantes_e_das_notas_fiscais(
    fontes_tail_exemplo,
):
    pares, _ = _montar(fontes_tail_exemplo, incluir_sem_tamanho=True)
    titulos = _titulos(pares)

    assert "Pao Forma Wickbold" in titulos
    assert any(t.startswith("Pao Sem Tamanho") for t in titulos)


def test_grupo_com_titulo_do_benchmark_e_excluido_inteiro_dos_positivos_e_dos_negativos(
    fontes_tail_exemplo,
):
    pares, _ = _montar(fontes_tail_exemplo)
    titulos = {construcao.normalizar_titulo_tail(t) for t in _titulos(pares)}

    assert "shampoo exemplo antiqueda 100ml" not in titulos
    assert "shampoo exemplo antiqueda 0 1l" not in titulos  # a variante do mesmo grupo
    for proibido in construcao.titulos_do_benchmark(fontes_tail_exemplo["benchmark"]):
        assert proibido not in titulos


def test_titulo_do_octaprice_igual_ao_do_benchmark_nunca_vira_negativo(fontes_tail_exemplo):
    pares, _ = _montar(fontes_tail_exemplo)

    assert "suco laranja tial 1l" not in {
        construcao.normalizar_titulo_tail(t) for t in _titulos(pares)
    }


def test_teto_por_grupo_vale_para_as_notas_fiscais_e_nao_para_as_variantes(fontes_tail_exemplo):
    pares, _ = _montar(fontes_tail_exemplo, max_pares_por_grupo_nf=2)

    assert (pares["origem"] == "tail_nf").sum() == 2  # 10 pares do grupo, teto 2
    assert (pares["origem"] == "tail_variante").sum() == 8  # nenhum corte nas variantes


def test_octaprice_so_aparece_como_negativo(fontes_tail_exemplo):
    pares, _ = _montar(fontes_tail_exemplo)
    positivos = pares[pares["origem"].isin(construcao.ORIGENS_TAIL_POSITIVAS)]
    octaprice = {"suco uva tial 500ml", "arroz tio joao 1kg", "macarrao espaguete adria 1kg"}

    assert not octaprice & {construcao.normalizar_titulo_tail(t) for t in _titulos(positivos)}


# ── negativos: D5 (só tamanho diferente, razão 1:1 configurável) ─────────────


def test_negativos_tem_tamanho_conhecido_e_diferente_nos_dois_lados(fontes_tail_exemplo):
    pares, _ = _montar(fontes_tail_exemplo)
    negativos = pares[pares["origem"] == "tail_negativo"]

    assert len(negativos) > 0
    for linha in negativos.itertuples(index=False):
        a = construcao.tokens_numericos(linha.descricao_a)
        b = construcao.tokens_numericos(linha.descricao_b)
        assert a and b and a != b


def test_numero_de_negativos_segue_a_razao_da_config(fontes_tail_exemplo):
    pares, _ = _montar(fontes_tail_exemplo, razao_negativos=0.5)
    n_positivos = pares["origem"].isin(construcao.ORIGENS_TAIL_POSITIVAS).sum()

    assert n_positivos == 10
    assert (pares["origem"] == "tail_negativo").sum() == 5


def test_razao_maior_que_o_disponivel_falha_nomeando_a_faixa_e_nao_reduz_em_silencio(
    fontes_tail_exemplo,
):
    with pytest.raises(ValueError, match="faixa"):
        _montar(fontes_tail_exemplo, razao_negativos=50.0)


# ── propriedades gerais ──────────────────────────────────────────────────────


def test_resultado_e_deterministico_e_nao_depende_da_ordem_das_linhas(fontes_tail_exemplo):
    um, _ = _montar(fontes_tail_exemplo)
    invertido = {
        nome: quadro.iloc[::-1].reset_index(drop=True)
        for nome, quadro in fontes_tail_exemplo.items()
    }
    outro, _ = _montar(invertido)

    assert um.reset_index(drop=True).equals(outro.reset_index(drop=True))


def test_montar_nao_altera_as_fontes(fontes_tail_exemplo):
    antes = {n: q.copy(deep=True) for n, q in fontes_tail_exemplo.items()}

    _montar(fontes_tail_exemplo)

    for nome, quadro in antes.items():
        assert fontes_tail_exemplo[nome].equals(quadro), nome


def test_resumo_reporta_cada_etapa_e_as_exclusoes(fontes_tail_exemplo):
    _, resumo = _montar(fontes_tail_exemplo)

    por_etapa = dict(zip(resumo["etapa"], resumo["n"], strict=True))
    assert list(resumo.columns) == ["etapa", "n"]
    assert por_etapa["positivos_variante"] == 8
    assert por_etapa["positivos_nf"] == 2
    assert por_etapa["grupos_excluidos_benchmark"] == 1
    assert por_etapa["negativos"] == 5


# ── selecionar_negativos_tail (regra de grupo, teto e faixa) ─────────────────


@pytest.fixture
def pool() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "titulo": [
                "suco uva tial 1l",
                "suco uva tial 500ml",  # mesmo grupo do anterior, tamanho diferente
                "suco uva tial 2l",
                "suco laranja tial 300ml",
                "suco uva integral 1l",
                "suco uva natural 250ml",
            ],
            "grupo": ["g1", "g1", "g2", "g3", "g4", "g5"],
        }
    )


def test_negativo_nunca_junta_dois_titulos_do_mesmo_grupo(pool):
    pares = construcao.selecionar_negativos_tail(pool, _cfg(), n_total=6)

    assert ("suco uva tial 1l", "suco uva tial 500ml") not in set(
        zip(pares["titulo_a"], pares["titulo_b"], strict=True)
    )
    grupo = dict(zip(pool["titulo"], pool["grupo"], strict=True))
    assert all(
        grupo[a] != grupo[b] for a, b in zip(pares["titulo_a"], pares["titulo_b"], strict=True)
    )


def test_negativo_exige_tamanho_conhecido_e_diferente(pool):
    pares = construcao.selecionar_negativos_tail(pool, _cfg(), n_total=6)

    for a, b in zip(pares["titulo_a"], pares["titulo_b"], strict=True):
        ta, tb = construcao.tokens_numericos(a), construcao.tokens_numericos(b)
        assert ta and tb and ta != tb


def test_selecao_tem_as_colunas_e_um_par_unico_por_combinacao(pool):
    pares = construcao.selecionar_negativos_tail(pool, _cfg(), n_total=6)

    assert list(pares.columns) == ["titulo_a", "titulo_b", "score", "faixa"]
    assert (pares["titulo_a"] < pares["titulo_b"]).all()
    assert not pares.duplicated(["titulo_a", "titulo_b"]).any()
    assert len(pares) == 6


def test_teto_de_negativos_por_titulo_e_respeitado(pool):
    pares = construcao.selecionar_negativos_tail(
        pool, _cfg(teto_negativos_por_produto=1), n_total=3
    )

    uso = pd.concat([pares["titulo_a"], pares["titulo_b"]]).value_counts()
    assert uso.max() == 1


def test_pedir_mais_negativos_do_que_existem_falha_nomeando_a_faixa(pool):
    with pytest.raises(ValueError, match="faixa"):
        construcao.selecionar_negativos_tail(pool, _cfg(), n_total=500)


def test_selecao_e_deterministica_por_seed(pool):
    um = construcao.selecionar_negativos_tail(pool, _cfg(), n_total=5)
    dois = construcao.selecionar_negativos_tail(pool, _cfg(), n_total=5)

    assert um.equals(dois)


# ── verificar_pares_tail_pxp (barreira crítica final) ────────────────────────


def _validos(fontes: dict) -> pd.DataFrame:
    return _montar(fontes)[0]


def _benchmark(fontes: dict) -> list[str]:
    return construcao.titulos_do_benchmark(fontes["benchmark"])


def test_conjunto_valido_passa_pela_barreira(fontes_tail_exemplo):
    construcao.verificar_pares_tail_pxp(
        _validos(fontes_tail_exemplo), _benchmark(fontes_tail_exemplo)
    )


def test_barreira_recusa_colunas_diferentes_das_de_treino(fontes_tail_exemplo):
    pares = _validos(fontes_tail_exemplo).assign(codg_item="x")

    with pytest.raises(AssertionError, match="colunas"):
        construcao.verificar_pares_tail_pxp(pares, _benchmark(fontes_tail_exemplo))


def test_barreira_recusa_id_sem_prefixo_tail(fontes_tail_exemplo):
    pares = _validos(fontes_tail_exemplo)
    pares.loc[0, "id_a"] = "p001"

    with pytest.raises(AssertionError, match="tail_"):
        construcao.verificar_pares_tail_pxp(pares, _benchmark(fontes_tail_exemplo))


def test_barreira_recusa_positivo_que_muda_o_tamanho(fontes_tail_exemplo):
    pares = _validos(fontes_tail_exemplo)
    linha = pares.index[pares["origem"] == "tail_variante"][0]
    pares.loc[linha, "descricao_b"] = "Suco Uva Tial 500ml"

    with pytest.raises(AssertionError, match="tamanho"):
        construcao.verificar_pares_tail_pxp(pares, _benchmark(fontes_tail_exemplo))


def test_barreira_recusa_negativo_com_tamanho_igual(fontes_tail_exemplo):
    pares = _validos(fontes_tail_exemplo)
    linha = pares.index[pares["origem"] == "tail_negativo"][0]
    pares.loc[linha, "descricao_b"] = pares.loc[linha, "descricao_a"] + " x"

    with pytest.raises(AssertionError, match="tamanho"):
        construcao.verificar_pares_tail_pxp(pares, _benchmark(fontes_tail_exemplo))


def test_barreira_recusa_titulo_do_benchmark_em_qualquer_lado(fontes_tail_exemplo):
    pares = _validos(fontes_tail_exemplo)
    pares.loc[0, "descricao_a"] = "SUCO LARANJA TIAL 1L."

    with pytest.raises(AssertionError, match="benchmark"):
        construcao.verificar_pares_tail_pxp(pares, _benchmark(fontes_tail_exemplo))


def test_barreira_recusa_rotulo_incoerente_com_a_origem(fontes_tail_exemplo):
    pares = _validos(fontes_tail_exemplo)
    linha = pares.index[pares["origem"] == "tail_negativo"][0]
    pares.loc[linha, "rotulo"] = "match"

    with pytest.raises(AssertionError, match="rotulo"):
        construcao.verificar_pares_tail_pxp(pares, _benchmark(fontes_tail_exemplo))


def test_barreira_recusa_id_de_par_duplicado(fontes_tail_exemplo):
    pares = _validos(fontes_tail_exemplo)
    pares.loc[1, "id_par"] = pares.loc[0, "id_par"]

    with pytest.raises(AssertionError, match="id_par"):
        construcao.verificar_pares_tail_pxp(pares, _benchmark(fontes_tail_exemplo))
