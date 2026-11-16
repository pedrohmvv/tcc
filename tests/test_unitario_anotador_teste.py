"""
test_unitario_anotador_teste.py — Camada 1: contrato entre `ferramentas/anotador_teste.html` e o
script 03 (spec 001, tasks-1b T10b).

O anotador é uma página estática que lê e grava a planilha do teste produto × produto. Se as
colunas ou os rótulos dele divergirem dos do script, a planilha deixa de validar depois de meses
de anotação; este teste fixa os dois lados juntos.
"""

import importlib.util
import os
import re

_ROOT = os.path.join(os.path.dirname(__file__), "..")
_HTML = os.path.join(_ROOT, "ferramentas", "anotador_teste.html")


def _load(filename: str):
    path = os.path.join(_ROOT, "scripts", filename)
    spec = importlib.util.spec_from_file_location(filename, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


construcao = _load("03_construcao_dataset.py")


def _lista_js(nome: str) -> list[str]:
    """Extrai `const NOME = [ 'a', 'b', ... ];` do HTML (a lógica pura do anotador)."""
    with open(_HTML, encoding="utf-8") as f:
        html = f.read()
    achado = re.search(rf"const {nome} = \[(.*?)\];", html, flags=re.DOTALL)
    assert achado, f"const {nome} não encontrada em anotador_teste.html"
    return re.findall(r"'([^']*)'", achado.group(1))


def test_colunas_do_anotador_sao_as_da_planilha_do_script_03():
    assert _lista_js("COLUNAS") == construcao.COLUNAS_PLANILHA_TESTE_PXP


def test_rotulos_do_anotador_sao_os_do_script_03():
    assert _lista_js("ROTULOS") == list(construcao.ROTULOS_TESTE)


def test_anotador_nao_menciona_estrato_nem_colunas_do_matcher_alta():
    with open(_HTML, encoding="utf-8") as f:
        html = f.read().lower()
    for proibida in ["estrato", "prob_inclusao", "codg_item", "desc_ref", "match_score"]:
        assert proibida not in html, proibida
