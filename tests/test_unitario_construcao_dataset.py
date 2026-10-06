"""
test_unitario_construcao_dataset.py — Camadas 1 e 2: limpeza da base (spec 001, RF0).

Fixture local e dedicada: concentra num só DataFrame cada defeito tratado pela
limpeza (duplicata exata, texto repetido na loja, preço zero, colunas do
matcher ALTA), sem alterar as fixtures compartilhadas do conftest.
Ver AGENTS.md §3 e docs/limpeza_dados.md.
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


def _linha(product_id, description, price, source="a_api", collected_at="2026-09-10 12:00:00"):
    return {
        "product_id": product_id,
        "description": description,
        "unit": "UN",
        "price": price,
        "location": "PB, João Pessoa, Loja",
        "source": source,
        "collected_at": collected_at,
        "und_val": 1.0,
        "und_med": "KG",
        "preco_kg": price,
        "codg_item": 6300113.0,
        "desc_ref": "ARROZ BRANCO",
        "match_score": 0.9,
    }


@pytest.fixture
def base_com_defeitos() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _linha(1, "Arroz Branco 1kg", 5.0),
            _linha(1, "Arroz Branco 1kg", 5.0),  # duplicata exata da anterior
            _linha(2, "ACUCAR CRISTAL 1 KG", 3.49),
            _linha(3, "Açúcar Cristal 1 kg", 3.19),  # mesmo texto normalizado, mesma loja
            _linha(4, "ACUCAR CRISTAL 1 KG", 3.29, source="b_api"),  # mesmo texto, outra loja
            _linha(5, "Fórmula Infantil 800g", 0.0),  # preço zero
        ]
    )


@pytest.fixture
def dicionario_com_colunas_vazias() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "desc_alim": ["ARROZ BRANCO", "ACUCAR"],
            "codg_item1": [6300113, 6300200],
            "cod_padrao": [99, 7],
            "Unnamed: 3": [None, None],
            "Unnamed: 4": [None, None],
        }
    )


class TestNormalizarTexto:
    def test_remove_acentos_caixa_e_espacos_nas_pontas(self) -> None:
        assert construcao.normalizar_texto("  Açúcar Cristal ") == "ACUCAR CRISTAL"


class TestRemoverDuplicatasExatas:
    def test_mantem_a_primeira_ocorrencia(self, base_com_defeitos: pd.DataFrame) -> None:
        resultado = construcao.remover_duplicatas_exatas(base_com_defeitos)

        assert len(resultado) == 5
        assert (resultado["product_id"] == 1).sum() == 1

    def test_nao_remove_linhas_que_diferem_em_alguma_coluna(
        self, base_com_defeitos: pd.DataFrame
    ) -> None:
        resultado = construcao.remover_duplicatas_exatas(base_com_defeitos)

        assert set(resultado["product_id"]) == {1, 2, 3, 4, 5}


class TestMarcarTextoRepetidoNaLoja:
    def test_marca_todos_os_membros_do_grupo_na_mesma_loja(
        self, base_com_defeitos: pd.DataFrame
    ) -> None:
        base = construcao.remover_duplicatas_exatas(base_com_defeitos)
        resultado = construcao.marcar_texto_repetido_na_loja(base)
        marcados = set(resultado.loc[resultado["texto_repetido_na_loja"], "product_id"])

        assert marcados == {2, 3}

    def test_nao_marca_mesmo_texto_em_lojas_diferentes(
        self, base_com_defeitos: pd.DataFrame
    ) -> None:
        base = construcao.remover_duplicatas_exatas(base_com_defeitos)
        resultado = construcao.marcar_texto_repetido_na_loja(base)

        assert not resultado.loc[resultado["product_id"] == 4, "texto_repetido_na_loja"].item()


class TestMarcarPrecoInvalido:
    def test_marca_preco_zero_sem_alterar_o_valor(self, base_com_defeitos: pd.DataFrame) -> None:
        resultado = construcao.marcar_preco_invalido(base_com_defeitos)
        linha = resultado[resultado["product_id"] == 5]

        assert linha["preco_invalido"].all()
        assert (linha["price"] == 0.0).all()
        assert resultado["preco_invalido"].sum() == 1


class TestRemoverColunasMatcherAlta:
    def test_remove_as_tres_colunas(self, base_com_defeitos: pd.DataFrame) -> None:
        resultado = construcao.remover_colunas_matcher_alta(base_com_defeitos)

        assert not {"codg_item", "desc_ref", "match_score"} & set(resultado.columns)
        assert "description" in resultado.columns


class TestLimparDicionario:
    def test_remove_colunas_sem_nome_totalmente_vazias(
        self, dicionario_com_colunas_vazias: pd.DataFrame
    ) -> None:
        resultado = construcao.limpar_dicionario(dicionario_com_colunas_vazias)

        assert list(resultado.columns) == ["desc_alim", "codg_item1", "cod_padrao"]
        assert len(resultado) == 2


class TestLimparBase:
    def test_relatorio_reproduz_cada_criterio(
        self, base_com_defeitos: pd.DataFrame, dicionario_com_colunas_vazias: pd.DataFrame
    ) -> None:
        produtos, dicionario, relatorio = construcao.limpar_base(
            base_com_defeitos, dicionario_com_colunas_vazias
        )

        assert relatorio["registros_brutos"] == 6
        assert relatorio["duplicatas_exatas_removidas"] == 1
        assert relatorio["registros_limpos"] == 5
        assert relatorio["grupos_texto_repetido_na_loja"] == 1
        assert relatorio["linhas_texto_repetido_na_loja"] == 2
        assert relatorio["precos_invalidos"] == 1
        assert relatorio["colunas_removidas_dicionario"] == ["Unnamed: 3", "Unnamed: 4"]
        assert len(produtos) == 5
        assert len(dicionario) == 2

    def test_base_limpa_nao_contem_colunas_do_matcher_alta(
        self, base_com_defeitos: pd.DataFrame, dicionario_com_colunas_vazias: pd.DataFrame
    ) -> None:
        produtos, _, _ = construcao.limpar_base(base_com_defeitos, dicionario_com_colunas_vazias)

        assert not {"codg_item", "desc_ref", "match_score"} & set(produtos.columns)

    def test_nao_altera_o_dataframe_de_entrada(
        self, base_com_defeitos: pd.DataFrame, dicionario_com_colunas_vazias: pd.DataFrame
    ) -> None:
        original = base_com_defeitos.copy()

        construcao.limpar_base(base_com_defeitos, dicionario_com_colunas_vazias)

        pd.testing.assert_frame_equal(base_com_defeitos, original)
