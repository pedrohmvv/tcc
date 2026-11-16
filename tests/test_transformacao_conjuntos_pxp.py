"""
test_transformacao_conjuntos_pxp.py — Camada 2: conjuntos derivados da partição, em memória
(spec 001, RF1 "1b"; tasks-1b T12; design-1b C11).

`validacao_pxp`: pares do pool com os dois lados na validação, um por par NÃO ordenado, com o
rótulo do autor (vazio em âncora concluída = `nao_match`; `incerto` fica de fora).
`produtos_treino_pxp`: só os produtos da partição de treino, sem par e sem rótulo.
Os produtos e rótulos são sintéticos, escritos para o teste; nenhum é de dado real.
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

COLUNAS_VALIDACAO = [
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
COLUNAS_PRODUTOS_TREINO = [
    "id_produto",
    "descricao",
    "texto_normalizado",
    "loja",
    "und_val",
    "und_med",
    "componente",
]


@pytest.fixture
def universo() -> pd.DataFrame:
    """p1..p7. p1 e p2 diferem na unidade para o teste notar se o lado for trocado."""
    linhas = [
        ("p1", "Leite A 1L", "loja_a", 1.0, "L"),
        ("p2", "Leite B 900ml", "loja_b", 900.0, "ML"),
        ("p3", "Arroz C 1kg", "loja_a", 1.0, "KG"),
        ("p4", "Arroz D 1kg", "loja_b", 1.0, "KG"),
        ("p5", "Cafe E 500g", "loja_c", 500.0, "G"),
        ("p6", "Sal F 1kg", "loja_c", 1.0, "KG"),
        ("p7", "Acucar G 1kg", "loja_a", 1.0, "KG"),
    ]
    df = pd.DataFrame(linhas, columns=["id_produto", "descricao", "loja", "und_val", "und_med"])
    df["texto_normalizado"] = df["descricao"].str.lower()
    return df


@pytest.fixture
def particao() -> pd.DataFrame:
    """p1..p4 na validação (c1 = {p1, p2}, c3 = {p3, p4}), p5 no teste, p6 e p7 no treino."""
    return pd.DataFrame(
        {
            "id_produto": ["p1", "p2", "p3", "p4", "p5", "p6", "p7"],
            "componente": ["c1", "c1", "c3", "c3", "c5", "c6", "c7"],
            "particao": ["validacao"] * 4 + ["teste"] + ["treino"] * 2,
        }
    )


def _pool(*linhas: tuple[str, str, str]) -> pd.DataFrame:
    """Planilha do pool (só ids e rótulo importam; o texto da planilha é lixo de propósito)."""
    df = pd.DataFrame(linhas, columns=["id_ancora", "id_candidato", "rotulo"])
    for coluna in construcao.COLUNAS_PLANILHA_POOL:
        if coluna not in df.columns:
            df[coluna] = "texto da planilha, que não deve vazar"
    return df[construcao.COLUNAS_PLANILHA_POOL]


def _pares(df: pd.DataFrame) -> set[tuple[str, str]]:
    return set(zip(df["id_a"], df["id_b"], strict=True))


# ── montar_validacao_pxp ─────────────────────────────────────────────────────


def test_so_entram_pares_com_os_dois_lados_na_validacao(universo, particao):
    pool = _pool(("p1", "p2", "match"), ("p1", "p5", ""), ("p1", "p6", ""), ("p3", "p4", ""))

    validacao = construcao.montar_validacao_pxp(pool, universo, particao)

    assert _pares(validacao) == {("p1", "p2"), ("p3", "p4")}


def test_rotulo_vazio_vira_nao_match_match_continua_e_incerto_fica_de_fora(universo, particao):
    pool = _pool(
        ("p1", "p2", "match"),
        ("p1", "p3", ""),
        ("p2", "p3", "incerto"),
        ("p3", "p4", "  "),
    )

    validacao = construcao.montar_validacao_pxp(pool, universo, particao)

    rotulos = dict(zip(zip(validacao["id_a"], validacao["id_b"], strict=True), validacao["rotulo"]))
    assert rotulos == {("p1", "p2"): "match", ("p1", "p3"): "nao_match", ("p3", "p4"): "nao_match"}


def test_par_visto_dos_dois_lados_com_o_mesmo_rotulo_conta_uma_vez_em_ordem_canonica(
    universo, particao
):
    pool = _pool(("p2", "p1", "match"), ("p1", "p2", "match"))

    validacao = construcao.montar_validacao_pxp(pool, universo, particao)

    assert len(validacao) == 1
    assert (validacao.loc[0, "id_a"], validacao.loc[0, "id_b"]) == ("p1", "p2")


def test_texto_e_unidade_vem_do_universo_e_acompanham_a_orientacao_canonica(universo, particao):
    pool = _pool(("p2", "p1", ""))  # na planilha p2 é a âncora; na saída p1 vem primeiro

    linha = construcao.montar_validacao_pxp(pool, universo, particao).iloc[0]

    assert (linha["descricao_a"], linha["und_val_a"], linha["und_med_a"]) == (
        "Leite A 1L",
        1.0,
        "L",
    )
    assert (linha["descricao_b"], linha["und_val_b"], linha["und_med_b"]) == (
        "Leite B 900ml",
        900.0,
        "ML",
    )
    assert "planilha" not in " ".join(str(v) for v in linha.to_numpy())


@pytest.mark.parametrize("rotulo_de_ida", ["match", "incerto"])
def test_mesmo_par_com_rotulos_diferentes_nos_dois_sentidos_levanta_erro_com_os_ids(
    universo, particao, rotulo_de_ida
):
    pool = _pool(("p1", "p2", rotulo_de_ida), ("p2", "p1", ""))

    with pytest.raises(ValueError, match="p1-p2"):
        construcao.montar_validacao_pxp(pool, universo, particao)


def test_conflito_fora_da_validacao_nao_levanta_erro(universo, particao):
    """O par (p1, p5) toca o teste e nunca vai à validação: o conflito dele não é problema aqui."""
    pool = _pool(("p1", "p5", "match"), ("p5", "p1", ""), ("p3", "p4", ""))

    validacao = construcao.montar_validacao_pxp(pool, universo, particao)

    assert _pares(validacao) == {("p3", "p4")}


def test_validacao_tem_as_colunas_do_contrato_com_tipo_e_origem_fixos(universo, particao):
    validacao = construcao.montar_validacao_pxp(
        _pool(("p1", "p2", "match"), ("p3", "p4", "")), universo, particao
    )

    assert list(validacao.columns) == COLUNAS_VALIDACAO
    assert set(validacao["tipo_par"]) == {"produto_produto"}
    assert set(validacao["origem"]) == {"amostra_cega"}
    assert not set(construcao.COLUNAS_MATCHER_ALTA) & set(validacao.columns)


def test_validacao_e_ordenada_e_nao_depende_da_ordem_das_linhas_do_pool(universo, particao):
    pool = _pool(("p3", "p4", ""), ("p1", "p2", "match"), ("p1", "p3", ""), ("p2", "p4", ""))

    esperado = construcao.montar_validacao_pxp(pool, universo, particao)
    embaralhado = construcao.montar_validacao_pxp(
        pool.sample(frac=1, random_state=4).reset_index(drop=True), universo, particao
    )

    assert esperado.equals(embaralhado)
    assert list(zip(esperado["id_a"], esperado["id_b"], strict=True)) == sorted(_pares(esperado))


def test_id_par_e_o_hash_do_par_em_ordem_canonica(universo, particao):
    validacao = construcao.montar_validacao_pxp(_pool(("p2", "p1", "")), universo, particao)

    assert validacao.loc[0, "id_par"] == construcao._hash_curto("p1|p2")


def test_rotulo_fora_do_dominio_no_pool_levanta_erro_em_vez_de_virar_rotulo(universo, particao):
    """`nao-match` (com hífen, do protocolo) não vale no pool: só vazio, `match` e `incerto`."""
    with pytest.raises(ValueError, match="nao-match"):
        construcao.montar_validacao_pxp(_pool(("p1", "p2", "nao-match")), universo, particao)


def test_id_do_pool_fora_da_particao_levanta_erro_com_o_id(universo, particao):
    with pytest.raises(ValueError, match="zzz"):
        construcao.montar_validacao_pxp(_pool(("p1", "zzz", "")), universo, particao)


def test_validacao_sem_nenhum_par_levanta_erro_em_vez_de_devolver_vazio(universo, particao):
    pool = _pool(("p1", "p5", ""), ("p6", "p7", ""))  # nenhum par com os dois lados na validação

    with pytest.raises(ValueError, match="validação"):
        construcao.montar_validacao_pxp(pool, universo, particao)


# ── montar_produtos_treino_pxp ───────────────────────────────────────────────


def test_produtos_de_treino_so_traz_a_particao_de_treino_com_o_componente(universo, particao):
    treino = construcao.montar_produtos_treino_pxp(universo, particao)

    assert list(treino.columns) == COLUNAS_PRODUTOS_TREINO
    assert list(treino["id_produto"]) == ["p6", "p7"]
    assert list(treino["componente"]) == ["c6", "c7"]
    assert list(treino["descricao"]) == ["Sal F 1kg", "Acucar G 1kg"]


def test_produtos_de_treino_nao_carrega_colunas_do_matcher_alta_mesmo_que_o_universo_traga(
    universo, particao
):
    contaminado = universo.assign(codg_item="1", desc_ref="x", match_score=0.9)

    treino = construcao.montar_produtos_treino_pxp(contaminado, particao)

    assert not set(construcao.COLUNAS_MATCHER_ALTA) & set(treino.columns)


def test_produto_do_universo_fora_da_particao_levanta_erro_com_o_id(universo, particao):
    com_p8 = pd.concat([universo, universo.iloc[[0]].assign(id_produto="p8")], ignore_index=True)

    with pytest.raises(ValueError, match="p8"):
        construcao.montar_produtos_treino_pxp(com_p8, particao)


def test_treino_vazio_levanta_erro(universo, particao):
    sem_treino = particao.assign(particao=particao["particao"].replace("treino", "validacao"))

    with pytest.raises(ValueError, match="treino"):
        construcao.montar_produtos_treino_pxp(universo, sem_treino)
