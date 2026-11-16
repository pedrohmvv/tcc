"""
test_transformacao_pares_treino_pxp.py — Camada 2: parte A dos pares de treino produto × produto,
em memória (spec 001, RF2 reescrita pelo ADR-0015; design-treino-pxp §5).

Negativos: pares entre lojas com tamanho diferente nos dois lados, amostrados por faixa de cosseno.
Positivos: o texto de um produto perturbado. A verificação final é a barreira crítica: nenhum
negativo com tamanho igual, nenhum positivo que mude o tamanho, nenhum id fora do treino.
Os textos foram escritos para o teste; os cossenos que importam foram medidos com o vetorizador do
script (9 pares de tamanho diferente: 2 em [0, 0,3), 2 em [0,3, 0,5), 3 em [0,5, 0,7) e
2 em [0,7, 1]).
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
    ("n12", "oleo de soja liza 0,9l", "loja_a"),  # 900ml = 0,9l: mesmo tamanho, nunca é negativo
    ("n13", "sal cisne", "loja_a"),  # sem tamanho
    ("n14", "sal cisne refinado 1kg", "loja_b"),
    ("n15", "biscoito maria bauducco 200g", "loja_c"),
    ("n16", "biscoito maria bauducco 200g", "loja_a"),  # mesmo tamanho
    ("n17", "agua mineral indaia 1,5l", "loja_a"),
    ("n18", "agua mineral crystal 500ml", "loja_c"),
]
TODOS_OS_NEGATIVOS = {
    ("n01", "n08"),
    ("n03", "n08"),
    ("n09", "n10"),
    ("n17", "n18"),
    ("n01", "n03"),
    ("n01", "n02"),
    ("n02", "n03"),
    ("n06", "n07"),
    ("n04", "n05"),
}
FAIXAS = {"[0.00, 0.30)": 2, "[0.30, 0.50)": 2, "[0.50, 0.70)": 3, "[0.70, 1.00]": 2}
COLUNAS_PARES = [
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
]
ORIGENS_POSITIVAS = {"pos_unidade", "pos_ordem", "pos_abreviacao", "pos_ruido"}


def _cfg(**alteracoes):
    base = {
        "seed": 42,
        "k": 20,
        "incluir_mesma_loja": False,
        "faixas_cosseno": [0.0, 0.3, 0.5, 0.7, 1.0],
        "n_negativos_por_faixa": dict(FAIXAS),
        "teto_negativos_por_produto": 3,
        "n_positivos": 6,
        "pesos_perturbacao": {"unidade": 1, "ordem": 1, "abreviacao": 1, "ruido": 1},
        "abreviacoes": {"leite": ["lt"], "integral": ["int"], "biscoito": ["bisc"]},
    }
    return {**base, **alteracoes}


@pytest.fixture
def treino() -> pd.DataFrame:
    df = pd.DataFrame(TEXTOS, columns=["id_produto", "descricao", "loja"])
    df["texto_normalizado"] = df["descricao"]
    df["und_val"] = [float(i + 1) for i in range(len(df))]  # distintos: acusam lado trocado
    df["und_med"] = "KG"
    df["componente"] = df["id_produto"]
    return df


def _pares(df: pd.DataFrame) -> set[tuple[str, str]]:
    return set(zip(df["id_a"], df["id_b"], strict=True))


# ── selecionar_negativos_tamanho ─────────────────────────────────────────────


def test_alocando_todos_os_candidatos_saem_exatamente_os_nove_pares_de_tamanho_diferente(treino):
    selecao = construcao.selecionar_negativos_tamanho(treino, _cfg())

    assert _pares(selecao) == TODOS_OS_NEGATIVOS


def test_nenhum_negativo_tem_tamanho_igual_ou_ausente_nem_e_da_mesma_loja(treino):
    selecao = construcao.selecionar_negativos_tamanho(treino, _cfg())
    texto = treino.set_index("id_produto")["descricao"]
    loja = treino.set_index("id_produto")["loja"]

    for a, b in _pares(selecao):
        ta, tb = construcao.tokens_numericos(texto[a]), construcao.tokens_numericos(texto[b])
        assert ta and tb and ta != tb, (a, b)
        assert loja[a] != loja[b], (a, b)


def test_selecao_traz_colunas_em_ordem_canonica_e_a_faixa_de_cada_par(treino):
    selecao = construcao.selecionar_negativos_tamanho(treino, _cfg())

    assert list(selecao.columns) == ["id_a", "id_b", "score", "faixa"]
    assert (selecao["id_a"] < selecao["id_b"]).all()
    assert selecao["faixa"].value_counts().to_dict() == FAIXAS
    por_faixa = selecao.groupby("faixa")["score"].agg(["min", "max"])
    assert por_faixa.loc["[0.70, 1.00]", "min"] >= 0.7 - 1e-9
    assert por_faixa.loc["[0.50, 0.70)", "max"] < 0.7
    assert por_faixa.loc["[0.00, 0.30)", "max"] < 0.3


def test_alocacao_menor_que_o_disponivel_respeita_a_contagem_de_cada_faixa(treino):
    alocacao = {"[0.00, 0.30)": 1, "[0.30, 0.50)": 1, "[0.50, 0.70)": 1, "[0.70, 1.00]": 1}

    selecao = construcao.selecionar_negativos_tamanho(treino, _cfg(n_negativos_por_faixa=alocacao))

    assert selecao["faixa"].value_counts().to_dict() == alocacao
    assert _pares(selecao) <= TODOS_OS_NEGATIVOS


def test_selecao_e_deterministica_por_seed_e_nao_depende_da_ordem_das_linhas(treino):
    alocacao = {"[0.00, 0.30)": 1, "[0.30, 0.50)": 1, "[0.50, 0.70)": 1, "[0.70, 1.00]": 1}
    cfg = _cfg(n_negativos_por_faixa=alocacao)

    esperado = construcao.selecionar_negativos_tamanho(treino, cfg)
    embaralhado = construcao.selecionar_negativos_tamanho(
        treino.sample(frac=1, random_state=3).reset_index(drop=True), cfg
    )

    pd.testing.assert_frame_equal(esperado, embaralhado)
    outras = {
        frozenset(
            _pares(
                construcao.selecionar_negativos_tamanho(
                    treino, _cfg(seed=s, **{"n_negativos_por_faixa": alocacao})
                )
            )
        )
        for s in range(10)
    }
    assert len(outras) > 1, "a seed não muda a amostra"


def test_teto_por_produto_limita_quantos_pares_cada_produto_recebe(treino):
    alocacao = {"[0.00, 0.30)": 0, "[0.30, 0.50)": 0, "[0.50, 0.70)": 3, "[0.70, 1.00]": 0}

    with pytest.raises(ValueError, match=r"\[0.50, 0.70\)"):
        construcao.selecionar_negativos_tamanho(
            treino, _cfg(n_negativos_por_faixa=alocacao, teto_negativos_por_produto=1)
        )
    selecao = construcao.selecionar_negativos_tamanho(
        treino, _cfg(n_negativos_por_faixa=alocacao, teto_negativos_por_produto=2)
    )

    uso = pd.concat([selecao["id_a"], selecao["id_b"]]).value_counts()
    assert len(selecao) == 3 and uso.max() <= 2


def test_faixa_com_menos_candidatos_que_o_alocado_levanta_erro_com_faixa_e_contagens(treino):
    alocacao = {**FAIXAS, "[0.70, 1.00]": 3}  # só há 2 pares nessa faixa

    with pytest.raises(ValueError, match=r"\[0.70, 1.00\].*3.*2"):
        construcao.selecionar_negativos_tamanho(treino, _cfg(n_negativos_por_faixa=alocacao))


# ── negativos da mesma loja (decisão do autor, 2026-11-13) ───────────────────

TEXTOS_MESMA_LOJA = [
    ("m01", "leite integral italac 1l", "loja_a"),
    ("m02", "leite integral italac 500ml", "loja_a"),  # mesma loja de m01, tamanho diferente
    ("m03", "leite integral italac 1l", "loja_b"),
    ("m04", "arroz branco tio joao 5kg", "loja_a"),
    ("m05", "arroz branco tio joao 1kg", "loja_a"),  # mesma loja de m04, tamanho diferente
    ("m06", "cafe pilao tradicional 500g", "loja_b"),
    ("m07", "arroz branco tio joao 5kg", "loja_b"),
]
FAIXAS_MESMA_LOJA = {"[0.00, 0.50)": 0, "[0.50, 0.70)": 2, "[0.70, 1.00]": 2}


@pytest.fixture
def treino_mesma_loja() -> pd.DataFrame:
    df = pd.DataFrame(TEXTOS_MESMA_LOJA, columns=["id_produto", "descricao", "loja"])
    df["texto_normalizado"] = df["descricao"]
    df["und_val"] = 1.0
    df["und_med"] = "KG"
    df["componente"] = df["id_produto"]
    return df


def _cfg_mesma_loja(incluir: bool, **alteracoes):
    return _cfg(
        incluir_mesma_loja=incluir,
        faixas_cosseno=[0.0, 0.5, 0.7, 1.0],
        n_negativos_por_faixa=alteracoes.pop("alocacao"),
        **alteracoes,
    )


def test_sem_incluir_a_mesma_loja_so_entram_pares_entre_lojas(treino_mesma_loja):
    alocacao = {"[0.00, 0.50)": 0, "[0.50, 0.70)": 1, "[0.70, 1.00]": 1}

    selecao = construcao.selecionar_negativos_tamanho(
        treino_mesma_loja, _cfg_mesma_loja(False, alocacao=alocacao)
    )

    assert _pares(selecao) == {("m02", "m03"), ("m05", "m07")}


def test_incluindo_a_mesma_loja_entram_tambem_os_pares_de_tamanho_diferente_dentro_dela(
    treino_mesma_loja,
):
    selecao = construcao.selecionar_negativos_tamanho(
        treino_mesma_loja, _cfg_mesma_loja(True, alocacao=FAIXAS_MESMA_LOJA)
    )

    assert _pares(selecao) == {("m01", "m02"), ("m02", "m03"), ("m04", "m05"), ("m05", "m07")}
    loja = treino_mesma_loja.set_index("id_produto")["loja"]
    assert loja["m01"] == loja["m02"] and loja["m04"] == loja["m05"]


def test_incluindo_a_mesma_loja_o_tamanho_continua_sendo_a_regra(treino_mesma_loja):
    """m01 × m03 é idêntico entre lojas e m04 × m07 também: mesmo tamanho nunca vira negativo."""
    selecao = construcao.selecionar_negativos_tamanho(
        treino_mesma_loja, _cfg_mesma_loja(True, alocacao=FAIXAS_MESMA_LOJA)
    )
    texto = treino_mesma_loja.set_index("id_produto")["descricao"]

    for a, b in _pares(selecao):
        ta, tb = construcao.tokens_numericos(texto[a]), construcao.tokens_numericos(texto[b])
        assert ta and tb and ta != tb, (a, b)


def test_incluindo_a_mesma_loja_pedir_mais_do_que_existe_levanta_erro_com_a_faixa(
    treino_mesma_loja,
):
    alocacao = {"[0.00, 0.50)": 0, "[0.50, 0.70)": 3, "[0.70, 1.00]": 0}

    with pytest.raises(ValueError, match=r"\[0.50, 0.70\)"):
        construcao.selecionar_negativos_tamanho(
            treino_mesma_loja, _cfg_mesma_loja(True, alocacao=alocacao)
        )


# ── gerar_negativos_tamanho ──────────────────────────────────────────────────


def test_negativos_saem_no_formato_dos_pares_de_treino_com_texto_e_unidade_do_treino(treino):
    negativos = construcao.gerar_negativos_tamanho(treino, _cfg())

    assert list(negativos.columns) == COLUNAS_PARES
    assert list(negativos.columns) == construcao.COLUNAS_PARES_TREINO_PXP
    assert set(negativos["origem"]) == {"neg_tamanho"}
    assert set(negativos["rotulo"]) == {"nao_match"}
    assert set(negativos["tipo_par"]) == {"produto_produto"}
    assert negativos["id_par"].is_unique
    base = treino.set_index("id_produto")
    assert (negativos["descricao_a"] == negativos["id_a"].map(base["descricao"])).all()
    assert (negativos["und_val_b"] == negativos["id_b"].map(base["und_val"])).all()
    assert negativos.loc[0, "id_par"] == construcao._hash_curto(
        f"{negativos.loc[0, 'id_a']}|{negativos.loc[0, 'id_b']}"
    )


# ── gerar_positivos_perturbados ──────────────────────────────────────────────


def test_positivos_saem_no_formato_dos_pares_de_treino_com_um_produto_por_positivo(treino):
    positivos = construcao.gerar_positivos_perturbados(treino, _cfg())

    assert list(positivos.columns) == COLUNAS_PARES
    assert len(positivos) == 6
    assert positivos["id_a"].is_unique and positivos["id_par"].is_unique
    assert set(positivos["rotulo"]) == {"match"}
    assert set(positivos["tipo_par"]) == {"produto_produto"}
    assert set(positivos["origem"]) <= ORIGENS_POSITIVAS


def test_positivo_preserva_o_tamanho_muda_o_texto_e_o_lado_b_e_sintetico(treino):
    positivos = construcao.gerar_positivos_perturbados(treino, _cfg())
    base = treino.set_index("id_produto")

    assert set(positivos["id_a"]) <= set(treino["id_produto"])
    assert (positivos["id_b"].str.startswith("sint_")).all()
    assert not set(positivos["id_b"]) & set(treino["id_produto"])
    assert (positivos["descricao_a"] == positivos["id_a"].map(base["descricao"])).all()
    assert (positivos["descricao_a"] != positivos["descricao_b"]).all()
    for a, b in zip(positivos["descricao_a"], positivos["descricao_b"], strict=True):
        assert construcao.tokens_numericos(a) == construcao.tokens_numericos(b), (a, b)
    assert (positivos["und_val_b"] == positivos["id_a"].map(base["und_val"])).all()
    assert (positivos["und_med_b"] == positivos["id_a"].map(base["und_med"])).all()


def test_pesos_so_de_unidade_geram_so_positivos_de_unidade(treino):
    cfg = _cfg(pesos_perturbacao={"unidade": 1, "ordem": 0, "abreviacao": 0, "ruido": 0})

    positivos = construcao.gerar_positivos_perturbados(treino, cfg)

    assert set(positivos["origem"]) == {"pos_unidade"}
    assert "n13" not in set(positivos["id_a"])  # sem tamanho: a unidade não se aplica


def test_mais_positivos_que_produtos_elegiveis_levanta_erro(treino):
    cfg = _cfg(
        n_positivos=18, pesos_perturbacao={"unidade": 1, "ordem": 0, "abreviacao": 0, "ruido": 0}
    )

    with pytest.raises(ValueError, match="elegíveis"):
        construcao.gerar_positivos_perturbados(treino, cfg)


def test_positivos_sao_deterministicos_e_nao_dependem_da_ordem_das_linhas(treino):
    esperado = construcao.gerar_positivos_perturbados(treino, _cfg())
    embaralhado = construcao.gerar_positivos_perturbados(
        treino.sample(frac=1, random_state=8).reset_index(drop=True), _cfg()
    )

    pd.testing.assert_frame_equal(esperado, embaralhado)
    assert not esperado.equals(construcao.gerar_positivos_perturbados(treino, _cfg(seed=7)))


# ── verificar_pares_treino_auto (a barreira crítica) ─────────────────────────


@pytest.fixture
def pares_validos(treino) -> pd.DataFrame:
    return construcao.montar_pares_treino_auto(treino, _cfg())


def test_pares_validos_passam_na_verificacao(treino, pares_validos):
    construcao.verificar_pares_treino_auto(pares_validos, treino)


def test_montagem_junta_negativos_e_positivos_com_as_origens_esperadas(pares_validos):
    contagem = pares_validos["origem"].value_counts()

    assert contagem["neg_tamanho"] == sum(FAIXAS.values())
    assert sum(contagem[o] for o in contagem.index if o.startswith("pos_")) == 6
    assert list(pares_validos.columns) == COLUNAS_PARES
    assert pares_validos["id_par"].is_unique


def test_negativo_com_tamanho_igual_falha_nomeando_o_par(treino, pares_validos):
    pares = pares_validos.copy()
    i = pares.index[pares["origem"] == "neg_tamanho"][0]
    pares.loc[i, "descricao_b"] = pares.loc[i, "descricao_a"]

    with pytest.raises(AssertionError, match="tamanho"):
        construcao.verificar_pares_treino_auto(pares, treino)


def test_positivo_que_muda_o_tamanho_falha(treino, pares_validos):
    pares = pares_validos.copy()
    i = pares.index[pares["origem"].str.startswith("pos_")][0]
    pares.loc[i, "descricao_b"] = "produto qualquer 7kg"

    with pytest.raises(AssertionError, match="tamanho"):
        construcao.verificar_pares_treino_auto(pares, treino)


def test_id_fora_do_treino_falha_com_o_id(treino, pares_validos):
    pares = pares_validos.copy()
    pares.loc[0, "id_a"] = "zzz"

    with pytest.raises(AssertionError, match="zzz"):
        construcao.verificar_pares_treino_auto(pares, treino)


def test_negativo_entre_produtos_da_mesma_loja_falha(treino):
    mesma_loja = treino.assign(loja="loja_a")
    pares = construcao.montar_pares_treino_auto(treino, _cfg())

    with pytest.raises(AssertionError, match="loja"):
        construcao.verificar_pares_treino_auto(pares, mesma_loja)


def test_negativo_da_mesma_loja_passa_quando_a_config_permite(treino):
    mesma_loja = treino.assign(loja="loja_a")
    pares = construcao.montar_pares_treino_auto(treino, _cfg())

    construcao.verificar_pares_treino_auto(pares, mesma_loja, mesma_loja_permitida=True)


def test_rotulo_incoerente_com_a_origem_falha(treino, pares_validos):
    pares = pares_validos.copy()
    pares.loc[pares["origem"] == "neg_tamanho", "rotulo"] = "match"

    with pytest.raises(AssertionError, match="rotulo"):
        construcao.verificar_pares_treino_auto(pares, treino)


def test_coluna_do_matcher_alta_falha(treino, pares_validos):
    with pytest.raises(AssertionError, match="codg_item"):
        construcao.verificar_pares_treino_auto(pares_validos.assign(codg_item="1"), treino)


def test_id_par_duplicado_falha(treino, pares_validos):
    pares = pares_validos.copy()
    pares.loc[1, "id_par"] = pares.loc[0, "id_par"]

    with pytest.raises(AssertionError, match="duplicado"):
        construcao.verificar_pares_treino_auto(pares, treino)
