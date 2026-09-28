"""
test_unitario_analise_exploratoria.py — Camada 1: testes unitários puros (sem I/O de disco).

Ver AGENTS.md, seção 3, camada 1.
"""

import importlib.util
import os

import pytest

_ROOT = os.path.join(os.path.dirname(__file__), "..")


def _load(filename: str):
    path = os.path.join(_ROOT, "scripts", filename)
    spec = importlib.util.spec_from_file_location(filename, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


eda = _load("02_analise_exploratoria.py")


class TestExtrairEstado:
    def test_extrai_sigla_de_location_bem_formado(self) -> None:
        assert eda.extrair_estado("PB, João Pessoa, Pedro Gondim") == "PB"

    def test_ignora_espacos_ao_redor_da_sigla(self) -> None:
        assert eda.extrair_estado(" CE , Fortaleza, Centro") == "CE"

    def test_location_sem_virgula_levanta_value_error(self) -> None:
        with pytest.raises(ValueError, match="location"):
            eda.extrair_estado("PB")


class TestTemUnidadeColada:
    def test_detecta_grama_colada_ao_numero(self) -> None:
        assert eda.tem_unidade_colada("Mini Sorvete Kibon Chicabon Caixa 92G") is True

    def test_detecta_mililitro_colado_ao_numero(self) -> None:
        assert eda.tem_unidade_colada("Sidra Celebrate 660ml") is True

    def test_nao_detecta_quando_ha_espaco_entre_numero_e_unidade(self) -> None:
        assert eda.tem_unidade_colada("Sidra Celebrate 660 ml") is False

    def test_nao_detecta_descricao_sem_unidade(self) -> None:
        assert eda.tem_unidade_colada("Bisteca Bovina do Peito Dianteiro") is False


class TestEstaEmCaixaAlta:
    def test_detecta_descricao_totalmente_maiuscula(self) -> None:
        assert eda.esta_em_caixa_alta("MAIONESE HEINZ BACON 215G") is True

    def test_nao_detecta_descricao_com_case_misto(self) -> None:
        assert eda.esta_em_caixa_alta("Leite em Pó Integral Instantâneo Ninho 380g") is False


class TestEstaSemAcentuacao:
    def test_detecta_palavra_que_deveria_ter_acento(self) -> None:
        assert eda.esta_sem_acentuacao("Cafe 3 Coracoes Portinari Cafe 1942 250g") is True

    def test_nao_detecta_quando_ha_acentuacao(self) -> None:
        assert eda.esta_sem_acentuacao("Café em Cápsula Torrado e Moído Intenso") is False


class TestNormalizarParaComparacao:
    def test_remove_acentos_e_normaliza_caixa(self) -> None:
        assert eda.normalizar_para_comparacao("Água Mineral") == "AGUA MINERAL"

    def test_ja_normalizado_permanece_igual(self) -> None:
        assert eda.normalizar_para_comparacao("ARROZ BRANCO") == "ARROZ BRANCO"


class TestEscaparLatex:
    def test_escapa_underscore(self) -> None:
        assert eda.escapar_latex("Leite_Integral") == r"Leite\_Integral"

    def test_escapa_e_comercial_e_percentual(self) -> None:
        assert eda.escapar_latex("A & B 50%") == r"A \& B 50\%"

    def test_texto_sem_caracteres_especiais_permanece_igual(self) -> None:
        assert eda.escapar_latex("Arroz Branco") == "Arroz Branco"


class TestTemAbreviatura:
    def test_detecta_barra_de_abreviacao(self) -> None:
        assert eda.tem_abreviatura("Canjica C/ Pacoca 200g") is True

    def test_detecta_ponto_de_truncamento(self) -> None:
        assert eda.tem_abreviatura("Alho 200g (aprox. 3und.)") is True

    def test_nao_detecta_descricao_sem_abreviatura(self) -> None:
        assert eda.tem_abreviatura("Coco Ralado Menina 100g") is False
