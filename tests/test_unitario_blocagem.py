"""
test_unitario_blocagem.py — Camadas 1 e 2: blocagem produto × dicionário (spec 001, RF1 "1a").

Fixture local e dedicada: dicionário de 6 entradas com variantes (ARROZ BRANCO/INTEGRAL,
LEITE INTEGRAL/DESNATADO). Tem de ter mais de 2 entradas: com 2 documentos o IDF do
BM25 (`rank-bm25`) é 0 para termos que aparecem em só um deles e todo score zera.
Ver AGENTS.md §3, ADR-0006 (emenda de 2026-10-31) e docs/protocolo_anotacao.md §2.1.
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


coleta = _load("01_coleta_dados.py")
construcao = _load("03_construcao_dataset.py")

COLUNAS_PLANILHA = [
    "id_produto",
    "descricao",
    "tipo_par",
    "origem",
    "und_val",
    "und_med",
    "entrada_indicada",
    "observacao",
    "timestamp_anotacao",
]


@pytest.fixture
def dicionario_blocagem() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "desc_alim": [
                "ARROZ BRANCO",
                "ARROZ INTEGRAL",
                "FEIJAO CARIOCA",
                "LEITE INTEGRAL",
                "LEITE DESNATADO",
                "AGUA MINERAL",
            ],
            "codg_item1": [1, 2, 3, 4, 5, 6],
            "cod_padrao": [99] * 6,
        }
    )


def _produtos(descricoes: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "product_id": range(1, len(descricoes) + 1),
            "description": descricoes,
            "und_val": 1.0,
            "und_med": "KG",
            "source": "a_api",
            "match_score": 0.9,
        }
    )


@pytest.fixture
def produtos_dedup() -> pd.DataFrame:
    return construcao.deduplicar_por_texto_normalizado(
        _produtos(
            [
                "Arroz Branco Tio Joao 1kg",
                "Arroz Integral Camil 1kg",
                "Feijao Carioca Kicaldo 1kg",
                "Leite Integral Italac 1L",
                "Agua Mineral Sem Gas Indaia 5l",
                "Leite Desnatado Italac 1L",
            ]
        )
    )


# ── Deduplicação (critério C2) ──────────────────────────────────────────────


class TestDeduplicar:
    def test_texto_igual_apos_normalizar_vira_uma_linha(self) -> None:
        df = _produtos(["Arroz Branco Tio João 1kg", "ARROZ BRANCO TIO JOAO 1KG ", "Feijao 1kg"])
        dedup = construcao.deduplicar_por_texto_normalizado(df)
        assert len(dedup) == 2
        arroz = dedup[dedup["descricao"].str.contains("Arroz", case=False)].iloc[0]
        assert arroz["n_registros"] == 2

    def test_id_produto_nao_depende_da_ordem_das_linhas(self) -> None:
        df = _produtos(["Arroz Branco 1kg", "Feijao Carioca 1kg", "Leite Integral 1L"])
        direto = construcao.deduplicar_por_texto_normalizado(df)
        invertido = construcao.deduplicar_por_texto_normalizado(df.iloc[::-1])
        assert set(direto["id_produto"]) == set(invertido["id_produto"])

    def test_nao_carrega_colunas_do_matcher_alta(self) -> None:
        dedup = construcao.deduplicar_por_texto_normalizado(_produtos(["Arroz Branco 1kg"]))
        assert not {"codg_item", "desc_ref", "match_score"} & set(dedup.columns)


# ── Ranqueamento TF-IDF e BM25 ──────────────────────────────────────────────


@pytest.mark.parametrize("metodo", ["tfidf", "bm25"])
class TestRanquear:
    def _ranquear(self, metodo, produtos, dicionario, k):
        funcao = {"tfidf": construcao.ranquear_tfidf, "bm25": construcao.ranquear_bm25}[metodo]
        return funcao(produtos, dicionario, k)

    def test_variante_correta_fica_em_primeiro(
        self, metodo, produtos_dedup, dicionario_blocagem
    ) -> None:
        r = self._ranquear(metodo, produtos_dedup, dicionario_blocagem, 5)
        integral = produtos_dedup[produtos_dedup["descricao"].str.contains("Integral Camil")]
        topo = r[(r["id_produto"] == integral.iloc[0]["id_produto"]) & (r["rank"] == 1)]
        assert topo.iloc[0]["desc_alim"] == "ARROZ INTEGRAL"

    def test_no_maximo_k_candidatos_por_produto(
        self, metodo, produtos_dedup, dicionario_blocagem
    ) -> None:
        r = self._ranquear(metodo, produtos_dedup, dicionario_blocagem, 2)
        assert r.groupby("id_produto").size().max() <= 2

    def test_nenhum_candidato_com_score_zero(
        self, metodo, produtos_dedup, dicionario_blocagem
    ) -> None:
        r = self._ranquear(metodo, produtos_dedup, dicionario_blocagem, 6)
        assert (r["score"] > 0).all()

    def test_produto_sem_termo_em_comum_nao_tem_candidato(
        self, metodo, dicionario_blocagem
    ) -> None:
        dedup = construcao.deduplicar_por_texto_normalizado(_produtos(["Cueca Boxer Lupo M"]))
        assert self._ranquear(metodo, dedup, dicionario_blocagem, 5).empty

    def test_saida_tem_colunas_metodo_e_rank_ordenado(
        self, metodo, produtos_dedup, dicionario_blocagem
    ) -> None:
        r = self._ranquear(metodo, produtos_dedup, dicionario_blocagem, 6)
        assert list(r.columns) == ["id_produto", "metodo", "rank", "desc_alim", "score"]
        assert (r["metodo"] == metodo).all()
        for _, grupo in r.groupby("id_produto"):
            assert list(grupo["rank"]) == list(range(1, len(grupo) + 1))
            assert list(grupo["score"]) == sorted(grupo["score"], reverse=True)

    def test_resultado_e_deterministico(self, metodo, produtos_dedup, dicionario_blocagem) -> None:
        a = self._ranquear(metodo, produtos_dedup, dicionario_blocagem, 6)
        b = self._ranquear(metodo, produtos_dedup, dicionario_blocagem, 6)
        pd.testing.assert_frame_equal(a, b)


def test_desempate_pelo_indice_do_dicionario(dicionario_blocagem) -> None:
    """LEITE casa igual com LEITE INTEGRAL (idx 3) e LEITE DESNATADO (idx 4): idx menor primeiro."""
    dedup = construcao.deduplicar_por_texto_normalizado(_produtos(["Leite"]))
    r = construcao.ranquear_tfidf(dedup, dicionario_blocagem, 2)
    assert list(r["desc_alim"]) == ["LEITE INTEGRAL", "LEITE DESNATADO"]


# ── Camada 2: fixtures do conftest → limpeza (01) → dedup → blocagem ────────


@pytest.mark.parametrize("metodo", ["tfidf", "bm25"])
def test_base_limpa_do_conftest_acha_a_entrada_no_topo(
    metodo, produtos_brutos_variados_exemplo, dicionario_blocagem
) -> None:
    produtos, _, _ = coleta.limpar_base(produtos_brutos_variados_exemplo, dicionario_blocagem)
    dedup = construcao.deduplicar_por_texto_normalizado(produtos)
    funcao = {"tfidf": construcao.ranquear_tfidf, "bm25": construcao.ranquear_bm25}[metodo]
    r = funcao(dedup, dicionario_blocagem, 5)
    topo = r[r["rank"] == 1].merge(dedup[["id_produto", "descricao"]], on="id_produto")
    por_descricao = dict(zip(topo["descricao"], topo["desc_alim"], strict=True))
    assert por_descricao["Arroz Branco Tio Joao 1kg"] == "ARROZ BRANCO"
    assert por_descricao["Água Mineral Sem Gás Indaia 5l"] == "AGUA MINERAL"


# ── Amostra cega ────────────────────────────────────────────────────────────


class TestSorteio:
    def test_mesma_seed_mesma_amostra(self, produtos_dedup) -> None:
        a = construcao.sortear_amostra_cega(produtos_dedup, n=3, seed=42)
        b = construcao.sortear_amostra_cega(produtos_dedup, n=3, seed=42)
        pd.testing.assert_frame_equal(a, b)

    def test_amostra_tem_exatamente_n_linhas_distintas(self, produtos_dedup) -> None:
        a = construcao.sortear_amostra_cega(produtos_dedup, n=4, seed=42)
        assert len(a) == 4
        assert a["id_produto"].is_unique

    def test_amostra_nao_depende_da_ordem_de_entrada(self, produtos_dedup) -> None:
        a = construcao.sortear_amostra_cega(produtos_dedup, n=3, seed=42)
        b = construcao.sortear_amostra_cega(produtos_dedup.iloc[::-1], n=3, seed=42)
        assert set(a["id_produto"]) == set(b["id_produto"])

    def test_n_maior_que_disponivel_levanta_erro(self, produtos_dedup) -> None:
        with pytest.raises(ValueError, match="amostra"):
            construcao.sortear_amostra_cega(produtos_dedup, n=100, seed=42)


class TestPlanilha:
    def test_colunas_exatas_sem_candidato_e_sem_colunas_alta(self, produtos_dedup) -> None:
        amostra = construcao.sortear_amostra_cega(produtos_dedup, n=3, seed=42)
        planilha = construcao.montar_planilha_amostra_cega(
            amostra.assign(match_score=0.9, desc_ref="X", codg_item=1, score=0.5)
        )
        assert list(planilha.columns) == COLUNAS_PLANILHA

    def test_campos_de_anotacao_vazios_e_tipo_origem_fixos(self, produtos_dedup) -> None:
        amostra = construcao.sortear_amostra_cega(produtos_dedup, n=3, seed=42)
        planilha = construcao.montar_planilha_amostra_cega(amostra)
        assert (
            planilha["entrada_indicada"].isna().all() or (planilha["entrada_indicada"] == "").all()
        )
        assert (planilha["tipo_par"] == "produto_canonico").all()
        assert (planilha["origem"] == "amostra_cega").all()


class TestValidarAnotacao:
    def _planilha(self, entradas: list) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "id_produto": [f"p{i}" for i in range(len(entradas))],
                "entrada_indicada": entradas,
            }
        )

    def test_aceita_entrada_do_dicionario_sem_entrada_e_incerto(self, dicionario_blocagem) -> None:
        planilha = self._planilha(["ARROZ BRANCO", "sem_entrada", "incerto"])
        construcao.validar_anotacao_amostra_cega(planilha, dicionario_blocagem)

    @pytest.mark.parametrize("vazio", [None, "", "  "])
    def test_rejeita_celula_vazia(self, vazio, dicionario_blocagem) -> None:
        with pytest.raises(ValueError, match="p1"):
            construcao.validar_anotacao_amostra_cega(
                self._planilha(["ARROZ BRANCO", vazio]), dicionario_blocagem
            )

    def test_rejeita_entrada_inexistente_no_dicionario(self, dicionario_blocagem) -> None:
        with pytest.raises(ValueError, match="p0"):
            construcao.validar_anotacao_amostra_cega(
                self._planilha(["ARROZ BRANCO TIPO 1"]), dicionario_blocagem
            )


# ── Recall da blocagem isolada ──────────────────────────────────────────────


def test_recall_por_k_calculado_a_mao() -> None:
    """p1 acerta no rank 1; p2 no rank 3; p3 não tem a entrada correta na lista;
    p4 = sem_entrada e p5 = incerto ficam fora do denominador e são contados à parte."""
    rankings = pd.DataFrame(
        [
            ("p1", "tfidf", 1, "ARROZ BRANCO", 0.9),
            ("p1", "tfidf", 2, "ARROZ INTEGRAL", 0.8),
            ("p2", "tfidf", 1, "LEITE DESNATADO", 0.9),
            ("p2", "tfidf", 2, "LEITE INTEGRAL", 0.8),
            ("p2", "tfidf", 3, "AGUA MINERAL", 0.7),
            ("p3", "tfidf", 1, "ARROZ BRANCO", 0.9),
            ("p4", "tfidf", 1, "ARROZ BRANCO", 0.9),
        ],
        columns=["id_produto", "metodo", "rank", "desc_alim", "score"],
    )
    anotacao = pd.DataFrame(
        {
            "id_produto": ["p1", "p2", "p3", "p4", "p5"],
            "entrada_indicada": [
                "ARROZ BRANCO",
                "AGUA MINERAL",
                "FEIJAO CARIOCA",
                "sem_entrada",
                "incerto",
            ],
        }
    )
    recall = construcao.calcular_recall_por_k(rankings, anotacao, ks=[1, 5])
    por_k = recall.set_index("k")
    assert list(recall["metodo"].unique()) == ["tfidf"]
    assert por_k.loc[1, "recall"] == pytest.approx(1 / 3)
    assert por_k.loc[5, "recall"] == pytest.approx(2 / 3)
    assert (recall["n_com_entrada"] == 3).all()
    assert (recall["n_sem_entrada"] == 1).all()
    assert (recall["n_incerto"] == 1).all()
    assert por_k.loc[5, "n_acertos"] == 2


@pytest.mark.parametrize("metodo", ["tfidf", "bm25"])
def test_empate_real_de_score_desempata_pelo_indice_do_dicionario(metodo) -> None:
    """Entradas com os mesmos tokens em ordem diferente têm score idêntico: vale o menor índice."""
    dicionario = pd.DataFrame(
        {
            "desc_alim": [
                "FEIJAO PRETO",
                "INTEGRAL LEITE",
                "LEITE INTEGRAL",
                "ARROZ BRANCO",
                "AGUA MINERAL",
                "FARINHA DE TRIGO",
            ],
            "codg_item1": [1, 2, 3, 4, 5, 6],
            "cod_padrao": [99] * 6,
        }
    )
    dedup = construcao.deduplicar_por_texto_normalizado(_produtos(["Leite Integral"]))
    funcao = {"tfidf": construcao.ranquear_tfidf, "bm25": construcao.ranquear_bm25}[metodo]
    r = funcao(dedup, dicionario, 2)
    assert r.iloc[0]["score"] == r.iloc[1]["score"]
    assert list(r["desc_alim"]) == ["INTEGRAL LEITE", "LEITE INTEGRAL"]


# ── Tabela LaTeX do recall (função pura) ────────────────────────────────────


@pytest.fixture
def recall_exemplo() -> pd.DataFrame:
    linhas = []
    for metodo, valores in (("tfidf", [0.4524, 0.8095]), ("bm25", [0.4286, 0.7381])):
        for k, recall in zip([1, 5], valores, strict=True):
            linhas.append(
                {
                    "metodo": metodo,
                    "k": k,
                    "recall": recall,
                    "n_com_entrada": 42,
                    "n_acertos": round(recall * 42),
                    "n_sem_entrada": 8,
                    "n_incerto": 0,
                }
            )
    return pd.DataFrame(linhas)


class TestTabelaRecall:
    def test_k_nas_linhas_e_um_metodo_por_coluna_com_percentual_em_pt_br(
        self, recall_exemplo
    ) -> None:
        tex = construcao.montar_tabela_recall_tex(recall_exemplo)
        assert r"\textbf{k} & \textbf{TF-IDF} & \textbf{BM25} \\" in tex
        assert r"1 & 45,2\% & 42,9\% \\" in tex
        assert r"5 & 81,0\% & 73,8\% \\" in tex
        assert tex.index("1 & 45,2") < tex.index("5 & 81,0")

    def test_so_inclui_os_metodos_presentes(self, recall_exemplo) -> None:
        tex = construcao.montar_tabela_recall_tex(
            recall_exemplo[recall_exemplo["metodo"] == "tfidf"]
        )
        assert "TF-IDF" in tex
        assert "BM25" not in tex

    def test_nota_de_rodape_traz_as_contagens_fora_do_calculo(self, recall_exemplo) -> None:
        tex = construcao.montar_tabela_recall_tex(recall_exemplo)
        assert "42 produtos com entrada correspondente" in tex
        assert "8 sem entrada" in tex
        assert "0 incertos" in tex

    def test_estrutura_latex_marca_de_geracao_e_label(self, recall_exemplo) -> None:
        tex = construcao.montar_tabela_recall_tex(recall_exemplo)
        assert tex.startswith("% Gerado automaticamente por scripts/03_construcao_dataset.py")
        assert r"\label{tab:recall-blocagem}" in tex
        assert r"\begin{tabular}{lcc}" in tex
        assert r"\end{table}" in tex
