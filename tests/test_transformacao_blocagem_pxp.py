"""
test_transformacao_blocagem_pxp.py — Camada 2: blocagem produto × produto em memória
(spec 001, RF1 "1b", tasks T3 e T4 de specs/001-construcao-dataset-ground-truth/tasks-1b.md).

Usa a fixture `produtos_entre_lojas_exemplo` do conftest. Os grupos de SKU vêm da fixture,
escritos para o teste; nenhum rótulo de par é de dado real.
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

COLUNAS_RANKING_PXP = ["id_produto", "id_candidato", "metodo", "rank", "score"]
METODOS = ["tfidf", "bm25"]


@pytest.fixture
def universo(produtos_entre_lojas_exemplo) -> pd.DataFrame:
    return construcao.deduplicar_por_texto_e_loja(produtos_entre_lojas_exemplo)


def _id(universo: pd.DataFrame, texto_normalizado: str, loja: str) -> str:
    linha = universo[
        (universo["texto_normalizado"] == texto_normalizado) & (universo["loja"] == loja)
    ]
    assert len(linha) == 1, f"fixture sem {texto_normalizado!r} em {loja}"
    return str(linha["id_produto"].iloc[0])


def _candidatos(ranking: pd.DataFrame, id_ancora: str) -> list[str]:
    do_ancora = ranking[ranking["id_produto"] == id_ancora].sort_values("rank")
    return list(do_ancora["id_candidato"])


@pytest.mark.parametrize("metodo", METODOS)
def test_ranking_tem_as_colunas_do_contrato(universo, metodo):
    ranking = construcao.ranquear_entre_lojas(universo, metodo, 20)

    assert list(ranking.columns) == COLUNAS_RANKING_PXP
    assert set(ranking["metodo"]) == {metodo}
    assert not set(construcao.COLUNAS_MATCHER_ALTA) & set(ranking.columns)


@pytest.mark.parametrize("metodo", METODOS)
def test_candidato_nunca_e_da_mesma_loja_nem_o_proprio_ancora(universo, metodo):
    ranking = construcao.ranquear_entre_lojas(universo, metodo, 100)
    loja = universo.set_index("id_produto")["loja"]

    assert len(ranking) > 0
    assert (ranking["id_produto"] != ranking["id_candidato"]).all()
    assert (ranking["id_produto"].map(loja) != ranking["id_candidato"].map(loja)).all()


@pytest.mark.parametrize("metodo", METODOS)
def test_mesmo_sku_escrito_de_formas_diferentes_e_o_candidato(universo, metodo):
    ranking = construcao.ranquear_entre_lojas(universo, metodo, 20)

    leite_a = _id(universo, "LEITE INTEGRAL ITALAC 1L", "loja_a")
    leite_b = _id(universo, "LT ITALAC INTEGRAL 1000ML", "loja_b")
    leite_c = _id(universo, "LEITE ITALAC INTEGRAL 1 L", "loja_c")
    arroz_a = _id(universo, "ARROZ BRANCO TIO JOAO 1KG", "loja_a")
    arroz_b = _id(universo, "ARROZ TIO JOAO BRANCO 1KG", "loja_b")
    oleo_a = _id(universo, "OLEO DE SOJA LIZA 900ML", "loja_a")
    oleo_c = _id(universo, "OLEO SOJA LIZA 0,9L", "loja_c")

    assert set(_candidatos(ranking, leite_a)) == {leite_b, leite_c}
    assert _candidatos(ranking, arroz_a)[0] == arroz_b
    assert _candidatos(ranking, oleo_a)[0] == oleo_c


@pytest.mark.parametrize("metodo", METODOS)
def test_texto_identico_entre_lojas_e_o_primeiro_candidato(universo, metodo):
    ranking = construcao.ranquear_entre_lojas(universo, metodo, 20)

    feijao_a = _id(universo, "FEIJAO CARIOCA CAMIL 1KG", "loja_a")
    feijao_c = _id(universo, "FEIJAO CARIOCA CAMIL 1KG", "loja_c")

    assert _candidatos(ranking, feijao_a)[0] == feijao_c


def test_tfidf_de_texto_identico_tem_cosseno_1(universo):
    ranking = construcao.ranquear_entre_lojas(universo, "tfidf", 20)

    feijao_a = _id(universo, "FEIJAO CARIOCA CAMIL 1KG", "loja_a")
    primeiro = ranking[(ranking["id_produto"] == feijao_a) & (ranking["rank"] == 1)]

    assert primeiro["score"].iloc[0] == pytest.approx(1.0)


@pytest.mark.parametrize("metodo", METODOS)
def test_rank_comeca_em_1_e_o_score_nao_aumenta_e_nunca_e_zero(universo, metodo):
    ranking = construcao.ranquear_entre_lojas(universo, metodo, 100)

    for _, grupo in ranking.groupby("id_produto"):
        ordenado = grupo.sort_values("rank")
        assert list(ordenado["rank"]) == list(range(1, len(ordenado) + 1))
        assert ordenado["score"].is_monotonic_decreasing
    assert (ranking["score"] > 0).all()


@pytest.mark.parametrize("metodo", METODOS)
def test_k_limita_o_numero_de_candidatos_por_ancora(universo, metodo):
    ranking = construcao.ranquear_entre_lojas(universo, metodo, 1)

    assert ranking.groupby("id_produto").size().max() == 1


@pytest.mark.parametrize("metodo", METODOS)
def test_produto_sem_token_em_comum_com_outras_lojas_nao_tem_candidato(universo, metodo):
    ranking = construcao.ranquear_entre_lojas(universo, metodo, 100)

    biscoito_b = _id(universo, "BISCOITO MARIA BAUDUCCO 200G", "loja_b")

    assert biscoito_b not in set(ranking["id_produto"])


@pytest.mark.parametrize("metodo", METODOS)
def test_empate_de_score_desempata_por_id_candidato_crescente(universo, metodo):
    ranking = construcao.ranquear_entre_lojas(universo, metodo, 100)

    arroz_a = _id(universo, "ARROZ BRANCO TIO JOAO 1KG", "loja_a")
    acucar_c = _id(universo, "ACUCAR UNIAO 1KG", "loja_c")
    sal_c = _id(universo, "SAL CISNE 1KG", "loja_c")
    do_arroz = ranking[ranking["id_produto"] == arroz_a].set_index("id_candidato")["score"]

    assert do_arroz[acucar_c] == pytest.approx(do_arroz[sal_c])  # a fixture tem de empatar
    candidatos = _candidatos(ranking, arroz_a)
    assert candidatos.index(min(acucar_c, sal_c)) < candidatos.index(max(acucar_c, sal_c))


@pytest.mark.parametrize("metodo", METODOS)
def test_ranking_nao_depende_da_ordem_das_linhas_do_universo(universo, metodo):
    de_frente = construcao.ranquear_entre_lojas(universo, metodo, 100)
    de_tras = construcao.ranquear_entre_lojas(
        universo.iloc[::-1].reset_index(drop=True), metodo, 100
    )

    ordem = ["id_produto", "rank"]
    pd.testing.assert_frame_equal(
        de_frente.sort_values(ordem).reset_index(drop=True),
        de_tras.sort_values(ordem).reset_index(drop=True),
    )


@pytest.mark.parametrize("metodo", ["ngramas", "embeddings", ""])
def test_metodo_fora_de_tfidf_e_bm25_levanta_erro(universo, metodo):
    with pytest.raises(ValueError, match="metodo"):
        construcao.ranquear_entre_lojas(universo, metodo, 20)


@pytest.mark.parametrize("metodo", METODOS)
def test_universo_de_uma_loja_so_devolve_ranking_vazio_com_as_colunas(universo, metodo):
    de_uma_loja = universo[universo["loja"] == "loja_a"].reset_index(drop=True)

    ranking = construcao.ranquear_entre_lojas(de_uma_loja, metodo, 20)

    assert ranking.empty
    assert list(ranking.columns) == COLUNAS_RANKING_PXP


# ── T4: ranquear_ngramas (só para formar o pool; nunca blocagem oficial) ──────


def _universo_local(linhas: list[tuple[str, str]]) -> pd.DataFrame:
    """(descrição, loja) → universo da 1b, para casos que a fixture compartilhada não cobre."""
    return construcao.deduplicar_por_texto_e_loja(
        pd.DataFrame(
            {
                "product_id": range(1, len(linhas) + 1),
                "description": [d for d, _ in linhas],
                "source": [s for _, s in linhas],
                "und_val": 1.0,
                "und_med": "KG",
            }
        )
    )


@pytest.fixture
def universo_marca_embute_categoria() -> pd.DataFrame:
    """`CAFE` × `NESCAFE`: nenhuma palavra em comum, mas vários n-gramas de caracteres."""
    return _universo_local(
        [
            ("Cafe Soluvel", "loja_a"),
            ("Nescafe Original", "loja_b"),
            ("Arroz Branco", "loja_b"),
            ("Detergente Liquido", "loja_b"),
            ("Feijao Preto", "loja_c"),
        ]
    )


def test_ngramas_tem_as_colunas_do_contrato_e_so_os_ancoras_pedidos(universo):
    leite_a = _id(universo, "LEITE INTEGRAL ITALAC 1L", "loja_a")
    arroz_b = _id(universo, "ARROZ TIO JOAO BRANCO 1KG", "loja_b")

    ranking = construcao.ranquear_ngramas(universo, [leite_a, arroz_b], 20)

    assert list(ranking.columns) == COLUNAS_RANKING_PXP
    assert set(ranking["metodo"]) == {"ngramas"}
    assert set(ranking["id_produto"]) == {leite_a, arroz_b}
    assert not set(construcao.COLUNAS_MATCHER_ALTA) & set(ranking.columns)


def test_ngramas_candidato_nunca_e_da_mesma_loja_nem_o_proprio_ancora(universo):
    ranking = construcao.ranquear_ngramas(universo, list(universo["id_produto"]), 100)
    loja = universo.set_index("id_produto")["loja"]

    assert len(ranking) > 0
    assert (ranking["id_produto"] != ranking["id_candidato"]).all()
    assert (ranking["id_produto"].map(loja) != ranking["id_candidato"].map(loja)).all()


def test_ngramas_mesmo_sku_escrito_de_formas_diferentes_vem_primeiro(universo):
    leite_a = _id(universo, "LEITE INTEGRAL ITALAC 1L", "loja_a")
    leite_b = _id(universo, "LT ITALAC INTEGRAL 1000ML", "loja_b")
    leite_c = _id(universo, "LEITE ITALAC INTEGRAL 1 L", "loja_c")
    arroz_a = _id(universo, "ARROZ BRANCO TIO JOAO 1KG", "loja_a")
    arroz_b = _id(universo, "ARROZ TIO JOAO BRANCO 1KG", "loja_b")

    ranking = construcao.ranquear_ngramas(universo, [leite_a, arroz_a], 20)

    assert set(_candidatos(ranking, leite_a)[:2]) == {leite_b, leite_c}
    assert _candidatos(ranking, arroz_a)[0] == arroz_b


def test_ngramas_recupera_o_que_a_blocagem_por_palavras_perde(universo_marca_embute_categoria):
    u = universo_marca_embute_categoria
    cafe_a = _id(u, "CAFE SOLUVEL", "loja_a")
    nescafe_b = _id(u, "NESCAFE ORIGINAL", "loja_b")

    por_palavras = construcao.ranquear_entre_lojas(u, "tfidf", 20)
    por_ngramas = construcao.ranquear_ngramas(u, [cafe_a], 20)

    assert cafe_a not in set(por_palavras["id_produto"])
    assert _candidatos(por_ngramas, cafe_a) == [nescafe_b]


def test_ngramas_respeita_o_intervalo_de_n_recebido(universo_marca_embute_categoria):
    u = universo_marca_embute_categoria
    cafe_a = _id(u, "CAFE SOLUVEL", "loja_a")

    com_3_a_5 = construcao.ranquear_ngramas(u, [cafe_a], 20, ngramas=(3, 5))
    so_com_6 = construcao.ranquear_ngramas(u, [cafe_a], 20, ngramas=(6, 6))

    assert len(com_3_a_5) == 1
    assert so_com_6.empty  # " CAFE " (6 caracteres) não está em nenhum n-grama de NESCAFE


def test_ngramas_rank_comeca_em_1_o_score_nao_aumenta_e_nunca_e_zero(universo):
    ranking = construcao.ranquear_ngramas(universo, list(universo["id_produto"]), 100)

    for _, grupo in ranking.groupby("id_produto"):
        ordenado = grupo.sort_values("rank")
        assert list(ordenado["rank"]) == list(range(1, len(ordenado) + 1))
        assert ordenado["score"].is_monotonic_decreasing
    assert (ranking["score"] > 0).all()


def test_ngramas_k_limita_o_numero_de_candidatos_por_ancora(universo):
    ranking = construcao.ranquear_ngramas(universo, list(universo["id_produto"]), 1)

    assert ranking.groupby("id_produto").size().max() == 1


def test_ngramas_nao_dependem_da_ordem_das_linhas_do_universo(universo):
    ids = list(universo["id_produto"])

    de_frente = construcao.ranquear_ngramas(universo, ids, 100)
    de_tras = construcao.ranquear_ngramas(universo.iloc[::-1].reset_index(drop=True), ids, 100)

    ordem = ["id_produto", "rank"]
    pd.testing.assert_frame_equal(
        de_frente.sort_values(ordem).reset_index(drop=True),
        de_tras.sort_values(ordem).reset_index(drop=True),
    )


def test_ngramas_sem_ancoras_devolve_ranking_vazio_com_as_colunas(universo):
    ranking = construcao.ranquear_ngramas(universo, [], 20)

    assert ranking.empty
    assert list(ranking.columns) == COLUNAS_RANKING_PXP


def test_ngramas_com_ancora_fora_do_universo_levanta_erro_com_o_id(universo):
    with pytest.raises(ValueError, match="id_inexistente"):
        construcao.ranquear_ngramas(universo, ["id_inexistente"], 20)


def test_ngramas_nao_e_um_metodo_oficial_de_blocagem():
    assert "ngramas" not in construcao.METODOS
    assert "ngramas" not in construcao._RANQUEADORES


# ── T5a: sortear_ancoras (permutação semeada; o lote N é um prefixo) ──────────


def test_ancoras_sao_uma_permutacao_do_universo_sem_filtro(universo):
    ancoras = construcao.sortear_ancoras(universo, 42)

    assert list(ancoras.columns) == list(universo.columns)
    assert len(ancoras) == len(universo)
    assert sorted(ancoras["id_produto"]) == sorted(universo["id_produto"])


def test_ancoras_mesma_seed_mesma_ordem(universo):
    a = construcao.sortear_ancoras(universo, 42)
    b = construcao.sortear_ancoras(universo, 42)

    pd.testing.assert_frame_equal(a, b)


def test_ancoras_seeds_diferentes_dao_ordens_diferentes(universo):
    a = construcao.sortear_ancoras(universo, 42)
    b = construcao.sortear_ancoras(universo, 43)

    assert list(a["id_produto"]) != list(b["id_produto"])


def test_ancoras_nao_dependem_da_ordem_das_linhas_do_universo(universo):
    de_frente = construcao.sortear_ancoras(universo, 42)
    de_tras = construcao.sortear_ancoras(universo.iloc[::-1].reset_index(drop=True), 42)

    pd.testing.assert_frame_equal(de_frente, de_tras)


def test_ancoras_nao_alteram_o_universo_recebido(universo):
    copia = universo.copy()

    construcao.sortear_ancoras(universo, 42)

    pd.testing.assert_frame_equal(universo, copia)


# ── T5b: montar_pool, montar_planilha_pool e gravar_planilha_pool ─────────────

COLUNAS_PLANILHA_POOL = [
    "id_par",
    "id_ancora",
    "descricao_ancora",
    "und_val_ancora",
    "und_med_ancora",
    "id_candidato",
    "descricao_candidato",
    "und_val_candidato",
    "und_med_candidato",
    "tipo_par",
    "origem",
    "rotulo",
    "ancora_concluida",
    "observacao",
    "timestamp_anotacao",
]
COLUNAS_PROIBIDAS_NO_POOL = [
    *("codg_item", "desc_ref", "match_score"),
    *("metodo", "rank", "score"),
]


def _ranking(linhas: list[tuple[str, str, int]], metodo: str) -> pd.DataFrame:
    """(âncora, candidato, rank) → ranking no formato das funções de blocagem."""
    return pd.DataFrame(
        {
            "id_produto": [a for a, _, _ in linhas],
            "id_candidato": [c for _, c, _ in linhas],
            "metodo": metodo,
            "rank": [r for _, _, r in linhas],
            "score": [1.0 / r for _, _, r in linhas],
        }
    )


def test_pool_e_a_uniao_dos_metodos_ate_a_profundidade():
    palavras = _ranking([("A", "X", 1), ("A", "Y", 2)], "tfidf")
    bm25 = _ranking([("A", "Y", 1), ("A", "Z", 3)], "bm25")

    pool = construcao.montar_pool([palavras, bm25], profundidade=2)

    assert set(zip(pool["id_produto"], pool["id_candidato"], strict=True)) == {
        ("A", "X"),
        ("A", "Y"),
    }


def test_pool_nao_repete_par_e_nao_guarda_proveniencia():
    a = _ranking([("A", "X", 1), ("A", "Y", 2)], "tfidf")
    b = _ranking([("A", "X", 1), ("B", "Y", 1)], "bm25")

    pool = construcao.montar_pool([a, b], profundidade=100)

    assert list(pool.columns) == ["id_produto", "id_candidato"]
    assert not pool.duplicated().any()
    assert len(pool) == 3


def test_pool_sem_rankings_ou_vazio_devolve_tabela_vazia_com_colunas():
    vazio = construcao.montar_pool([], profundidade=100)

    assert vazio.empty
    assert list(vazio.columns) == ["id_produto", "id_candidato"]


def test_pool_com_profundidade_invalida_levanta_erro():
    with pytest.raises(ValueError, match="profundidade"):
        construcao.montar_pool([_ranking([("A", "X", 1)], "tfidf")], profundidade=0)


@pytest.fixture
def pool_do_lote(universo):
    """Pool de 3 âncoras do universo de exemplo, com os três métodos, como na etapa real."""
    ancoras = construcao.sortear_ancoras(universo, 42).iloc[:3]
    ids = list(ancoras["id_produto"])
    rankings = [
        construcao.ranquear_entre_lojas(universo, "tfidf", 100),
        construcao.ranquear_entre_lojas(universo, "bm25", 100),
        construcao.ranquear_ngramas(universo, ids, 100),
    ]
    return ancoras, construcao.montar_pool(rankings, profundidade=100)


def test_pool_do_lote_contem_o_mesmo_sku_de_outra_loja(universo):
    leite_a = _id(universo, "LEITE INTEGRAL ITALAC 1L", "loja_a")
    leite_b = _id(universo, "LT ITALAC INTEGRAL 1000ML", "loja_b")
    leite_c = _id(universo, "LEITE ITALAC INTEGRAL 1 L", "loja_c")
    rankings = [
        construcao.ranquear_entre_lojas(universo, "tfidf", 100),
        construcao.ranquear_ngramas(universo, [leite_a], 100),
    ]

    pool = construcao.montar_pool(rankings, profundidade=100)

    do_leite = pool[pool["id_produto"] == leite_a]
    assert {leite_b, leite_c} <= set(do_leite["id_candidato"])


def test_planilha_pool_tem_as_colunas_do_contrato_sem_proveniencia_nem_matcher_alta(
    universo, pool_do_lote
):
    ancoras, pool = pool_do_lote

    planilha = construcao.montar_planilha_pool(ancoras, universo, pool)

    assert list(planilha.columns) == COLUNAS_PLANILHA_POOL
    assert not set(COLUNAS_PROIBIDAS_NO_POOL) & set(planilha.columns)


def test_planilha_pool_traz_o_tipo_de_par_a_origem_e_campos_do_autor_vazios(universo, pool_do_lote):
    ancoras, pool = pool_do_lote

    planilha = construcao.montar_planilha_pool(ancoras, universo, pool)

    assert len(planilha) > 0
    assert set(planilha["tipo_par"]) == {"produto_produto"}
    assert set(planilha["origem"]) == {"amostra_cega"}
    for coluna in ["rotulo", "ancora_concluida", "observacao", "timestamp_anotacao"]:
        assert set(planilha[coluna]) == {""}


def test_planilha_pool_so_tem_candidatos_de_outra_loja_e_textos_do_universo(universo, pool_do_lote):
    ancoras, pool = pool_do_lote

    planilha = construcao.montar_planilha_pool(ancoras, universo, pool)
    por_id = universo.set_index("id_produto")

    assert (
        planilha["id_ancora"].map(por_id["loja"]) != planilha["id_candidato"].map(por_id["loja"])
    ).all()
    assert (planilha["descricao_ancora"] == planilha["id_ancora"].map(por_id["descricao"])).all()
    assert (
        planilha["descricao_candidato"] == planilha["id_candidato"].map(por_id["descricao"])
    ).all()


def test_planilha_pool_so_inclui_os_ancoras_do_lote_na_ordem_do_sorteio(universo, pool_do_lote):
    ancoras, pool = pool_do_lote
    dois = ancoras.iloc[:2]

    planilha = construcao.montar_planilha_pool(dois, universo, pool)

    na_ordem = list(dict.fromkeys(planilha["id_ancora"]))
    assert na_ordem == [i for i in dois["id_produto"] if i in set(planilha["id_ancora"])]
    assert set(planilha["id_ancora"]) <= set(dois["id_produto"])


def test_planilha_pool_ordena_os_candidatos_alfabeticamente_dentro_de_cada_ancora(
    universo, pool_do_lote
):
    ancoras, pool = pool_do_lote

    planilha = construcao.montar_planilha_pool(ancoras, universo, pool)

    for _, grupo in planilha.groupby("id_ancora", sort=False):
        normalizados = [construcao.normalizar_texto(d) for d in grupo["descricao_candidato"]]
        assert normalizados == sorted(normalizados)


def test_planilha_pool_tem_id_de_par_unico_e_estavel(universo, pool_do_lote):
    ancoras, pool = pool_do_lote

    a = construcao.montar_planilha_pool(ancoras, universo, pool)
    b = construcao.montar_planilha_pool(ancoras, universo, pool)

    assert a["id_par"].is_unique
    pd.testing.assert_frame_equal(a, b)


def test_planilha_pool_com_id_fora_do_universo_levanta_erro_com_o_id(universo):
    ancoras = construcao.sortear_ancoras(universo, 42).iloc[:1]
    pool = pd.DataFrame(
        {"id_produto": [ancoras["id_produto"].iloc[0]], "id_candidato": ["id_inexistente"]}
    )

    with pytest.raises(ValueError, match="id_inexistente"):
        construcao.montar_planilha_pool(ancoras, universo, pool)


def test_ancora_sem_candidato_no_pool_nao_gera_linha(universo):
    biscoito_b = _id(universo, "BISCOITO MARIA BAUDUCCO 200G", "loja_b")
    ancoras = universo[universo["id_produto"] == biscoito_b]
    rankings = [construcao.ranquear_entre_lojas(universo, "tfidf", 100)]

    planilha = construcao.montar_planilha_pool(
        ancoras, universo, construcao.montar_pool(rankings, profundidade=100)
    )

    assert planilha.empty
    assert list(planilha.columns) == COLUNAS_PLANILHA_POOL


def test_gravar_planilha_pool_escreve_lote_com_dois_digitos(tmp_path, universo, pool_do_lote):
    ancoras, pool = pool_do_lote
    planilha = construcao.montar_planilha_pool(ancoras, universo, pool)

    caminho = construcao.gravar_planilha_pool(planilha, tmp_path / "pool_cego", 1)

    assert caminho == tmp_path / "pool_cego" / "lote_01.csv"
    lida = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False)
    assert list(lida.columns) == COLUNAS_PLANILHA_POOL
    assert len(lida) == len(planilha)
    assert (
        construcao.gravar_planilha_pool(planilha, tmp_path / "pool_cego", 12).name == "lote_12.csv"
    )


def test_gravar_planilha_pool_nunca_sobrescreve_lote_existente(tmp_path, universo, pool_do_lote):
    ancoras, pool = pool_do_lote
    planilha = construcao.montar_planilha_pool(ancoras, universo, pool)
    caminho = construcao.gravar_planilha_pool(planilha, tmp_path, 1)
    caminho.write_text("anotação do autor", encoding="utf-8")

    with pytest.raises(FileExistsError, match="lote_01.csv"):
        construcao.gravar_planilha_pool(planilha, tmp_path, 1)

    assert caminho.read_text(encoding="utf-8") == "anotação do autor"


def test_gravar_planilha_pool_com_numero_de_lote_invalido_levanta_erro(
    tmp_path, universo, pool_do_lote
):
    ancoras, pool = pool_do_lote
    planilha = construcao.montar_planilha_pool(ancoras, universo, pool)

    with pytest.raises(ValueError, match="lote"):
        construcao.gravar_planilha_pool(planilha, tmp_path, 0)


# ── T8: ranquear_entre_lojas restrito aos âncoras do lote ─────────────────────


@pytest.mark.parametrize("metodo", METODOS)
def test_ranking_restrito_aos_ancoras_e_igual_ao_ranking_completo_filtrado(universo, metodo):
    ids = list(construcao.sortear_ancoras(universo, 42)["id_produto"].iloc[:4])

    completo = construcao.ranquear_entre_lojas(universo, metodo, 100)
    restrito = construcao.ranquear_entre_lojas(universo, metodo, 100, ids_ancoras=ids)

    esperado = completo[completo["id_produto"].isin(ids)]
    ordem = ["id_produto", "rank"]
    pd.testing.assert_frame_equal(
        restrito.sort_values(ordem).reset_index(drop=True),
        esperado.sort_values(ordem).reset_index(drop=True),
    )
    assert set(restrito["id_produto"]) <= set(ids)


@pytest.mark.parametrize("metodo", METODOS)
def test_ranking_restrito_com_ancora_fora_do_universo_levanta_erro_com_o_id(universo, metodo):
    with pytest.raises(ValueError, match="id_inexistente"):
        construcao.ranquear_entre_lojas(universo, metodo, 20, ids_ancoras=["id_inexistente"])


@pytest.mark.parametrize("metodo", METODOS)
def test_ranking_restrito_sem_ancoras_devolve_ranking_vazio_com_as_colunas(universo, metodo):
    ranking = construcao.ranquear_entre_lojas(universo, metodo, 20, ids_ancoras=[])

    assert ranking.empty
    assert list(ranking.columns) == COLUNAS_RANKING_PXP


# ── T9: taxas_positivos_por_faixa (calibração da alocação do teste, só no pool) ──────────────

COLUNAS_TAXAS = [
    "faixa",
    "n_pares",
    "n_match",
    "n_incerto",
    "taxa_match",
    "n_digito_divergente",
    "n_match_digito_divergente",
]
FAIXAS = [0.0, 0.5, 0.9, 1.0]


def _universo_taxas() -> pd.DataFrame:
    linhas = [
        ("A", "tA", "ARROZ TIO JOAO 1KG", "X"),
        ("B", "tA", "ARROZ TIO JOAO 1KG", "Y"),  # mesmo texto da âncora, outra loja
        ("C", "tC", "ARROZ TIO JOAO 5KG", "Y"),
        ("D", "tD", "ARROZ CAMIL 1KG", "Z"),
        ("E", "tE", "FEIJAO CARIOCA 1KG", "Z"),
        ("F", "tF", "ARROZ TIO JOAO TIPO 1 1 KG", "Z"),
        ("A2", "tA2", "LEITE ITALAC 1L", "X"),
        ("G", "tG", "LEITE ITALAC 1LT", "Y"),
        ("H", "tH", "LEITE PIRACANJUBA 1L", "Z"),
    ]
    return pd.DataFrame(linhas, columns=["id_produto", "id_texto", "descricao", "loja"])


def _rankings_taxas() -> pd.DataFrame:
    linhas = [
        ("A", "B", 1, 1.0),
        ("A", "C", 2, 0.92),
        ("A", "F", 3, 0.85),
        ("A", "D", 4, 0.55),
        ("A", "E", 5, 0.20),
        ("A2", "G", 1, 0.95),
        ("A2", "H", 2, 0.50),
    ]
    return pd.DataFrame(
        [(a, c, "tfidf", r, s) for a, c, r, s in linhas], columns=COLUNAS_RANKING_PXP
    )


def _planilha_taxas(**rotulos: str) -> pd.DataFrame:
    """Pool anotado: todo par do ranking, com os rótulos dados por candidato (padrão: vazio)."""
    ranking = _rankings_taxas()
    return pd.DataFrame(
        {
            "id_ancora": ranking["id_produto"],
            "id_candidato": ranking["id_candidato"],
            "rotulo": [rotulos.get(c, "") for c in ranking["id_candidato"]],
            "ancora_concluida": "sim",
        }
    )


def _taxas(planilha=None, rankings=None, *, k=20, faixas=FAIXAS, metodo="tfidf"):
    return construcao.taxas_positivos_por_faixa(
        _rankings_taxas() if rankings is None else rankings,
        _planilha_taxas(B="match", F="match", G="match") if planilha is None else planilha,
        _universo_taxas(),
        metodo=metodo,
        k=k,
        faixas=faixas,
    )


def test_taxas_por_faixa_contam_pares_matches_e_taxa_com_estrato_proprio_de_texto_identico():
    taxas = _taxas()

    assert list(taxas.columns) == COLUNAS_TAXAS
    esperado = pd.DataFrame(
        [
            ("texto_identico", 1, 1, 0, 1.0, 0, 0),
            ("[0.00, 0.50)", 1, 0, 0, 0.0, 0, 0),
            ("[0.50, 0.90)", 3, 1, 0, 1 / 3, 0, 0),
            ("[0.90, 1.00]", 2, 1, 0, 0.5, 1, 0),
            ("total", 7, 3, 0, 3 / 7, 1, 0),
        ],
        columns=COLUNAS_TAXAS,
    )
    pd.testing.assert_frame_equal(taxas, esperado)


def test_par_de_texto_identico_nao_conta_na_faixa_de_score_mais_alta():
    taxas = _taxas().set_index("faixa")

    # a faixa alta tem só C (0,92) e G (0,95); B (score 1,0, texto idêntico) fica no estrato próprio
    assert taxas.loc["[0.90, 1.00]", "n_pares"] == 2
    assert taxas.loc["texto_identico", "n_pares"] == 1


def test_incerto_conta_a_parte_e_fica_fora_do_denominador_da_taxa():
    taxas = _taxas(_planilha_taxas(B="match", F="match", G="match", D="incerto")).set_index("faixa")

    linha = taxas.loc["[0.50, 0.90)"]
    assert linha["n_pares"] == 3
    assert linha["n_incerto"] == 1
    assert linha["taxa_match"] == pytest.approx(1 / 2)


def test_faixa_so_com_incertos_tem_taxa_indefinida():
    planilha = _planilha_taxas(B="match", E="incerto")

    taxas = _taxas(planilha).set_index("faixa")

    assert pd.isna(taxas.loc["[0.00, 0.50)", "taxa_match"])


def test_digito_divergente_conta_pares_e_matches_marcados_neles():
    taxas = _taxas(_planilha_taxas(B="match", C="match")).set_index("faixa")

    assert taxas.loc["[0.90, 1.00]", "n_digito_divergente"] == 1
    assert taxas.loc["[0.90, 1.00]", "n_match_digito_divergente"] == 1


def test_so_entram_os_pares_ate_o_rank_k():
    taxas = _taxas(k=3).set_index("faixa")

    assert taxas.loc["total", "n_pares"] == 5  # A: B, C, F; A2: G, H (D e E estão além do top-3)


def test_par_do_topk_ausente_da_planilha_levanta_erro_com_os_ids():
    planilha = _planilha_taxas(B="match")
    planilha = planilha[planilha["id_candidato"] != "F"]

    with pytest.raises(ValueError, match="A-F"):
        _taxas(planilha)


def test_ancora_nao_concluida_fica_fora_das_taxas():
    planilha = _planilha_taxas(B="match", F="match", G="match")
    planilha.loc[planilha["id_ancora"] == "A2", "ancora_concluida"] = ""

    taxas = _taxas(planilha).set_index("faixa")

    assert taxas.loc["total", "n_pares"] == 5  # só as 5 linhas da âncora A


@pytest.mark.parametrize(
    "faixas",
    [[0.1, 0.5, 1.0], [0.0, 0.5, 0.9], [0.0, 0.9, 0.5, 1.0], [0.0, 1.0, 1.0], [0.0]],
    ids=["nao_comeca_em_0", "nao_termina_em_1", "nao_crescente", "repetida", "curta_demais"],
)
def test_faixas_invalidas_levantam_erro(faixas):
    with pytest.raises(ValueError, match="faixas"):
        _taxas(faixas=faixas)


def test_metodo_ausente_dos_rankings_levanta_erro():
    with pytest.raises(ValueError, match="bm25"):
        _taxas(metodo="bm25")


def test_taxas_nao_dependem_da_ordem_das_linhas_de_entrada():
    ranking = _rankings_taxas().iloc[::-1].reset_index(drop=True)
    planilha = _planilha_taxas(B="match", F="match", G="match").iloc[::-1].reset_index(drop=True)

    pd.testing.assert_frame_equal(_taxas(planilha, ranking), _taxas())


# ── T10: sortear_pares_teste (300 pares estratificados, cada produto em no máximo um par) ──────

ESTRATOS_SORTEIO = {
    "texto_identico": 2,
    "digito_divergente": 4,
    "[0.00, 0.50)": 3,
    "[0.50, 0.70)": 3,
    "[0.70, 0.90)": 4,
    "[0.90, 1.00]": 4,
}


def _cfg_sorteio(**alteracoes):
    cfg = {
        "seed": 42,
        "metodo": "tfidf",
        "k": 20,
        "n_teste": 20,
        "faixas": [0.0, 0.5, 0.7, 0.9, 1.0],
        "score_minimo_digito_divergente": 0.5,
        "fracao_digito_divergente": 0.2,
        "n_por_estrato": dict(ESTRATOS_SORTEIO),
    }
    cfg.update(alteracoes)
    return cfg


def _cenario_sorteio(n_por_estrato: int = 30):
    """Candidatos sintéticos: por estrato, `n` pares com todos os produtos distintos.

    Estratos: texto idêntico (score 1,0), tamanho divergente (0,8), e uma faixa de score cada. Mais
    3 pares de tamanho divergente com score 0,3, que devem ficar na faixa baixa, não no estrato de
    dígito, porque ficam abaixo do mínimo.
    """
    produtos, pares, n = [], [], 0

    def novo(texto: str, loja: str, id_texto: str | None = None) -> str:
        nonlocal n
        n += 1
        produtos.append((f"p{n:04d}", id_texto or f"t{n:04d}", texto, loja))
        return f"p{n:04d}"

    for i in range(n_por_estrato):
        a, b = novo(f"SUCO UVA {i} 1L", "X", f"idem{i}"), novo(f"SUCO UVA {i} 1L", "Y", f"idem{i}")
        pares.append((a, b, 1.0))
        a, b = novo(f"ARROZ A{i} 1KG", "X"), novo(f"ARROZ A{i} 5KG", "Y")
        pares.append((a, b, 0.8))
        for faixa, score in enumerate([0.2, 0.6, 0.8, 0.95]):
            a, b = novo(f"ITEM {faixa}{i} 1KG", "X"), novo(f"ITEM {faixa}{i}X 1KG", "Z")
            pares.append((a, b, score))
    for i in range(3):
        a, b = novo(f"FEIJAO F{i} 1KG", "X"), novo(f"FEIJAO F{i} 5KG", "Y")
        pares.append((a, b, 0.3))
    universo = pd.DataFrame(produtos, columns=["id_produto", "id_texto", "descricao", "loja"])
    candidatos = pd.DataFrame(pares, columns=["id_produto", "id_candidato", "score"])
    return candidatos, universo


def _sortear(candidatos=None, universo=None, **cfg):
    if candidatos is None:
        candidatos, universo = _cenario_sorteio()
    return construcao.sortear_pares_teste(candidatos, universo, _cfg_sorteio(**cfg))


def test_sorteio_devolve_as_colunas_do_contrato_sem_rotulo():
    pares = _sortear()

    assert list(pares.columns) == ["id_a", "id_b", "estrato", "prob_inclusao"]
    assert len(pares) == 20


def test_sorteio_respeita_a_alocacao_por_estrato():
    pares = _sortear()

    assert pares["estrato"].value_counts().to_dict() == ESTRATOS_SORTEIO


def test_cada_produto_aparece_em_no_maximo_um_par():
    pares = _sortear()

    produtos = list(pares["id_a"]) + list(pares["id_b"])
    assert len(produtos) == len(set(produtos))


def test_os_pares_sao_entre_lojas_diferentes_e_canonicos():
    candidatos, universo = _cenario_sorteio()
    pares = _sortear(candidatos, universo)

    loja = universo.set_index("id_produto")["loja"]
    assert (pares["id_a"].map(loja) != pares["id_b"].map(loja)).all()
    assert (pares["id_a"] < pares["id_b"]).all()


def test_prob_inclusao_e_alocado_sobre_candidatos_do_estrato():
    pares = _sortear().set_index("estrato")

    # 30 pares por estrato; o de dígito tem 30 (score 0,8), a faixa baixa tem 30 + 3 (score 0,3)
    assert pares.loc["digito_divergente", "prob_inclusao"].iloc[0] == pytest.approx(4 / 30)
    assert pares.loc["texto_identico", "prob_inclusao"].iloc[0] == pytest.approx(2 / 30)
    assert pares.loc["[0.00, 0.50)", "prob_inclusao"].iloc[0] == pytest.approx(3 / 33)
    assert pares.loc["[0.90, 1.00]", "prob_inclusao"].iloc[0] == pytest.approx(4 / 30)


def test_digito_divergente_abaixo_do_score_minimo_fica_na_faixa_baixa():
    candidatos, universo = _cenario_sorteio()
    pares = _sortear(candidatos, universo)

    em_digito = pares[pares["estrato"] == "digito_divergente"]
    scores = candidatos.set_index(["id_produto", "id_candidato"])["score"]
    for a, b in zip(em_digito["id_a"], em_digito["id_b"], strict=True):
        assert max(scores.get((a, b), 0), scores.get((b, a), 0)) >= 0.5


def test_texto_identico_so_aparece_no_estrato_proprio_e_nao_na_faixa_alta():
    candidatos, universo = _cenario_sorteio()
    pares = _sortear(candidatos, universo)

    id_texto = universo.set_index("id_produto")["id_texto"]
    mesmo_texto = pares["id_a"].map(id_texto) == pares["id_b"].map(id_texto)
    assert set(pares.loc[mesmo_texto, "estrato"]) == {"texto_identico"}
    assert (pares.loc[~mesmo_texto, "estrato"] != "texto_identico").all()


def test_par_listado_nos_dois_sentidos_conta_uma_vez():
    candidatos, universo = _cenario_sorteio()
    invertidos = candidatos.rename(
        columns={"id_produto": "id_candidato", "id_candidato": "id_produto"}
    )
    duplicado = pd.concat([candidatos, invertidos[candidatos.columns]], ignore_index=True)

    pares = _sortear(duplicado, universo).set_index("estrato")

    assert pares.loc["digito_divergente", "prob_inclusao"].iloc[0] == pytest.approx(4 / 30)


def test_mesma_seed_da_o_mesmo_sorteio_e_seed_diferente_da_outro():
    primeiro, repetido = _sortear(), _sortear()
    outro = _sortear(seed=7)

    pd.testing.assert_frame_equal(primeiro, repetido)
    assert not primeiro[["id_a", "id_b"]].equals(outro[["id_a", "id_b"]])


def test_sorteio_nao_depende_da_ordem_das_linhas_de_entrada():
    candidatos, universo = _cenario_sorteio()

    embaralhado = candidatos.sample(frac=1, random_state=1).reset_index(drop=True)

    pd.testing.assert_frame_equal(_sortear(candidatos, universo), _sortear(embaralhado, universo))


def test_estrato_com_menos_candidatos_que_o_alocado_levanta_erro_com_o_nome():
    candidatos, universo = _cenario_sorteio(n_por_estrato=3)
    alocacao = {
        **ESTRATOS_SORTEIO,
        "digito_divergente": 3,
        "[0.70, 0.90)": 3,
    }  # só a faixa alta falta

    with pytest.raises(ValueError, match=r"\[0\.90, 1\.00\]"):
        _sortear(candidatos, universo, n_teste=sum(alocacao.values()), n_por_estrato=alocacao)


def test_estrato_cujos_pares_dividem_um_produto_nao_e_preenchido_em_silencio():
    candidatos, universo = _cenario_sorteio()
    estrela = candidatos[candidatos["score"] == 0.95].copy()
    estrela["id_produto"] = estrela["id_produto"].iloc[0]  # todos os pares usam o mesmo produto
    candidatos = pd.concat([candidatos[candidatos["score"] != 0.95], estrela], ignore_index=True)

    with pytest.raises(ValueError, match=r"\[0\.90, 1\.00\]"):
        _sortear(candidatos, universo)


@pytest.mark.parametrize("campo", ["metodo", "k"])
def test_sorteio_com_metodo_ou_k_nao_congelados_falha(campo):
    candidatos, universo = _cenario_sorteio()

    with pytest.raises(ValueError, match="congel"):
        _sortear(candidatos, universo, **{campo: None})


@pytest.mark.parametrize("campo", ["faixas", "n_por_estrato", "score_minimo_digito_divergente"])
def test_sorteio_sem_alocacao_na_config_falha(campo):
    candidatos, universo = _cenario_sorteio()

    with pytest.raises(ValueError, match=campo):
        _sortear(candidatos, universo, **{campo: None})
