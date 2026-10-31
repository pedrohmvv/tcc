"""
test_unitario_heterogeneidade.py — Camadas 1 e 2: pares de mesmo SKU para a Tabela de
heterogeneidade da Introdução (EDA, script 02; ADR-0014: produto × produto é a fatia principal).

Fixture local e dedicada: cada produto representa uma situação que a seleção deve aceitar
ou descartar. O autor confirma à mão quais candidatos são de fato o mesmo produto; o código
só propõe candidatos (nunca decide o mérito). Ver AGENTS.md §3.
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


eda = _load("02_analise_exploratoria.py")


def _df(linhas: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "product_id": range(1, len(linhas) + 1),
            "description": [d for d, _ in linhas],
            "source": [s for _, s in linhas],
        }
    )


PAR_ESPERADO = ("Vinho Chileno Cono Sur Carmenere 750ml", "VH CHI CONO SUR 1551 CARMENERE 750ML")


@pytest.fixture
def produtos_mesmo_sku() -> pd.DataFrame:
    return _df(
        [
            ("Vinho Chileno Cono Sur Carmenere 750ml", "loja_a"),  # par esperado, lado A
            ("VH CHI CONO SUR 1551 CARMENERE 750ML", "loja_b"),  # par esperado, lado B
            ("Vinho Chileno Cono Sur Carmenere 1l", "loja_b"),  # tamanho diferente
            ("Arroz Camil Tipo 1 1kg", "loja_a"),  # mesma loja do par abaixo
            ("ARROZ CAMIL T1 1KG", "loja_a"),
            ("Suco Uva Del Valle 1,5L", "loja_a"),  # inversão pura de tokens
            ("Suco Del Valle Uva 1,5l", "loja_b"),
            ("Feijao Carioca Kicaldo 1kg", "loja_a"),  # mesmo texto normalizado
            ("FEIJÃO CARIOCA KICALDO 1KG", "loja_b"),
            ("Cuscuz Flocao Nordestino", "loja_a"),  # sem tamanho
            ("CUSCUZ FLOCAO NORDESTINO PCT", "loja_b"),
            ("Biscoito Maria Bauducco 200g", "loja_a"),  # só 1 token em comum
            ("Biscoito Oreo Recheado 200g", "loja_b"),
        ]
    )


# ── extrair_tamanho ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("descricao", "esperado"),
    [
        ("Arroz Tio Joao 1kg", (1000.0, "g")),
        ("Arroz Tio Joao 500 g", (500.0, "g")),
        ("Biscoito Maria 200GR", (200.0, "g")),
        ("Leite Italac 1L", (1000.0, "ml")),
        ("Leite Italac 1000ML", (1000.0, "ml")),
        ("Oleo Liza 0,9L", (900.0, "ml")),
        ("Suco Del Valle 1,5l", (1500.0, "ml")),
        ("Cerveja Amstel Lata 269ml", (269.0, "ml")),
        ("Ovos Brancos 12 und", (12.0, "un")),
        ("Feijao Carioca Kicaldo", None),
    ],
)
def test_extrair_tamanho_normaliza_para_unidade_base(descricao, esperado) -> None:
    assert eda.extrair_tamanho(descricao) == esperado


def test_extrair_tamanho_equivalentes_dao_o_mesmo_valor() -> None:
    assert eda.extrair_tamanho("Leite 1L") == eda.extrair_tamanho("Leite 1000ML")
    assert eda.extrair_tamanho("Oleo 0,9L") == eda.extrair_tamanho("Oleo 900ml")


# ── selecionar_candidatos_mesmo_sku ──────────────────────────────────────────


class TestCandidatosMesmoSku:
    def _selecionar(self, df, **kw):
        return eda.selecionar_candidatos_mesmo_sku(df, n=10, seed=42, max_df=3, **kw)

    def test_so_o_par_de_mesmo_sku_com_grafia_diferente_e_candidato(
        self, produtos_mesmo_sku
    ) -> None:
        cand = self._selecionar(produtos_mesmo_sku)
        assert len(cand) == 1
        linha = cand.iloc[0]
        assert (linha["supermercado_a"], linha["supermercado_b"]) == PAR_ESPERADO

    def test_colunas_e_lojas_diferentes(self, produtos_mesmo_sku) -> None:
        cand = self._selecionar(produtos_mesmo_sku)
        assert list(cand.columns) == [
            "id_par",
            "supermercado_a",
            "supermercado_b",
            "source_a",
            "source_b",
            "tamanho",
            "tokens_comuns",
        ]
        assert (cand["source_a"] != cand["source_b"]).all()
        assert cand.iloc[0]["tamanho"] == "750 ml"

    def test_id_par_estavel_independente_da_ordem_das_linhas(self, produtos_mesmo_sku) -> None:
        direto = self._selecionar(produtos_mesmo_sku)
        invertido = self._selecionar(produtos_mesmo_sku.iloc[::-1].reset_index(drop=True))
        assert direto.iloc[0]["id_par"] == invertido.iloc[0]["id_par"]
        assert len(direto.iloc[0]["id_par"]) == 12

    def test_n_limita_e_mesma_seed_mesmo_resultado(self) -> None:
        df = _df(
            [
                ("Vinho Cono Sur Carmenere 750ml", "loja_a"),
                ("VH CONO SUR CARMENERE 750ML", "loja_b"),
                ("Cerveja Heineken Long Neck 330ml", "loja_a"),
                ("CERV HEINEKEN LONG NECK 330ML", "loja_b"),
                ("Cafe Pilao Tradicional Vacuo 500g", "loja_a"),
                ("CAFE PILAO TRADICIONAL VACUO 500G", "loja_b"),
                ("Cafe Pilao Tradicional Almofada 250g", "loja_a"),
                ("CAFE PILAO TRAD ALMOFADA 250G", "loja_b"),
            ]
        )
        a = eda.selecionar_candidatos_mesmo_sku(df, n=2, seed=42, max_df=4)
        b = eda.selecionar_candidatos_mesmo_sku(df, n=2, seed=42, max_df=4)
        assert len(a) == 2
        pd.testing.assert_frame_equal(a, b)

    def test_base_sem_pares_devolve_tabela_vazia_com_colunas(self) -> None:
        cand = eda.selecionar_candidatos_mesmo_sku(
            _df([("Arroz Camil 1kg", "loja_a")]), n=5, seed=42, max_df=3
        )
        assert cand.empty
        assert "id_par" in cand.columns


# ── selecionar_exemplos_confirmados ──────────────────────────────────────────


class TestConfirmados:
    @pytest.fixture
    def candidatos(self, produtos_mesmo_sku) -> pd.DataFrame:
        return eda.selecionar_candidatos_mesmo_sku(produtos_mesmo_sku, n=10, seed=42, max_df=3)

    def test_devolve_so_os_confirmados_no_formato_da_tabela(self, candidatos) -> None:
        id_par = candidatos.iloc[0]["id_par"]
        exemplos = eda.selecionar_exemplos_confirmados(candidatos, [id_par])
        assert exemplos == [{"supermercado_a": PAR_ESPERADO[0], "supermercado_b": PAR_ESPERADO[1]}]

    def test_lista_vazia_nao_devolve_exemplos(self, candidatos) -> None:
        assert eda.selecionar_exemplos_confirmados(candidatos, []) == []

    def test_id_desconhecido_levanta_erro_com_o_id(self, candidatos) -> None:
        with pytest.raises(ValueError, match="abc123def456"):
            eda.selecionar_exemplos_confirmados(candidatos, ["abc123def456"])
