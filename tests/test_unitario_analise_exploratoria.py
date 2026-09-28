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
