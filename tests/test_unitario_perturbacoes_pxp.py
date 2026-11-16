"""
test_unitario_perturbacoes_pxp.py — Camada 1: perturbações do próprio texto e config dos pares de
treino automáticos (spec 001, RF2 reescrita pelo ADR-0015 e RF7; design-treino-pxp §5).

Cada positivo da fonte (b) é um produto contra uma versão perturbada dele mesmo. A receita aprovada
pelo autor em 2026-11-13: unidade (900ML ↔ 0,9L), inversão parcial de ordem, abreviação e ruído
tipográfico, sempre preservando o conjunto de tamanhos. Lógica pura, sem I/O de disco; os textos são
sintéticos, escritos para o teste.
"""

import importlib.util
import os
import unicodedata
from pathlib import Path

import numpy as np
import pytest
import yaml

_ROOT = os.path.join(os.path.dirname(__file__), "..")


def _load(filename: str):
    path = os.path.join(_ROOT, "scripts", filename)
    spec = importlib.util.spec_from_file_location(filename, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


construcao = _load("03_construcao_dataset.py")
SEEDS = range(30)


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c))


# ── perturbar_unidade ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("OLEO SOJA LIZA 900ML", "OLEO SOJA LIZA 0,9L"),
        ("ARROZ TIO JOAO 1KG", "ARROZ TIO JOAO 1000G"),
        ("CAFE PILAO 500G", "CAFE PILAO 0,5KG"),
        ("SUCO UVA 1L", "SUCO UVA 1000ML"),
        ("Leite Integral 1,5l", "Leite Integral 1500ml"),
        ("AGUA 350 ML", "AGUA 0,35L"),
        ("MACARRAO 500GR", "MACARRAO 0,5KG"),
        ("SUCO UVA 1LT", "SUCO UVA 1000ML"),
        ("LEITE 200ML 1L", "LEITE 0,2L 1L"),
    ],
)
def test_unidade_troca_a_primeira_expressao_por_uma_equivalente(texto, esperado):
    novo = construcao.perturbar_unidade(texto)

    assert novo == esperado
    assert construcao.tokens_numericos(novo) == construcao.tokens_numericos(texto)


@pytest.mark.parametrize("texto", ["SAL CISNE", "TEMPERO SAZON 60G", "ESSENCIA BAUNILHA 30ML"])
def test_unidade_sem_tamanho_ou_com_valor_pequeno_demais_nao_se_aplica(texto):
    """Abaixo de 100 g ou 100 ml a forma trocada (0,06KG) não existe no texto de PDV."""
    assert construcao.perturbar_unidade(texto) is None


# ── perturbar_ordem ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("seed", SEEDS)
def test_ordem_so_reordena_os_tokens_e_preserva_o_tamanho(seed):
    texto = "Biscoito Maria Bauducco Tradicional 200g"

    novo = construcao.perturbar_ordem(texto, _rng(seed))

    assert novo != texto
    assert sorted(novo.split()) == sorted(texto.split())
    assert construcao.tokens_numericos(novo) == construcao.tokens_numericos(texto)


def test_ordem_e_deterministica_para_a_mesma_seed():
    texto = "Biscoito Maria Bauducco Tradicional 200g"

    assert construcao.perturbar_ordem(texto, _rng(5)) == construcao.perturbar_ordem(texto, _rng(5))


@pytest.mark.parametrize("texto", ["LEITE 1L", "SAL", ""])
def test_ordem_com_menos_de_tres_tokens_nao_se_aplica(texto):
    assert construcao.perturbar_ordem(texto, _rng(0)) is None


# ── perturbar_abreviacao ─────────────────────────────────────────────────────

TABELA = {"vinho": ["vh", "vin"], "tinto": ["tto"], "leite": ["lt"], "macarrao": ["mac"]}


@pytest.mark.parametrize("seed", SEEDS)
def test_abreviacao_so_troca_palavras_da_tabela_e_preserva_marca_e_tamanho(seed):
    texto = "Vinho Tinto Suave Perini 750ml"

    novo = construcao.perturbar_abreviacao(texto, TABELA, _rng(seed))

    antes, depois = texto.split(), novo.split()
    trocados = [(a, d) for a, d in zip(antes, depois, strict=True) if a != d]
    assert len(antes) == len(depois)
    assert trocados, "nenhuma palavra foi abreviada"
    for original, abreviada in trocados:
        assert abreviada.lower() in TABELA[original.lower()]
    for fixa in ["Suave", "Perini", "750ml"]:
        assert fixa in depois
    assert construcao.tokens_numericos(novo) == construcao.tokens_numericos(texto)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("VINHO ALPHA 750ML", "VH ALPHA 750ML"),
        ("Vinho Alpha 750ml", "Vh Alpha 750ml"),
        ("vinho alpha 750ml", "vh alpha 750ml"),
    ],
)
def test_abreviacao_segue_o_formato_de_caixa_da_palavra_original(texto, esperado):
    assert construcao.perturbar_abreviacao(texto, {"vinho": ["vh"]}, _rng(0)) == esperado


def test_abreviacao_reconhece_a_palavra_sem_acento():
    assert (
        construcao.perturbar_abreviacao("Macarrão Adria 500g", TABELA, _rng(0)) == "Mac Adria 500g"
    )


def test_abreviacao_sem_palavra_da_tabela_nao_se_aplica():
    assert construcao.perturbar_abreviacao("Arroz Tio Joao 1kg", TABELA, _rng(0)) is None


def test_abreviacao_e_deterministica_para_a_mesma_seed():
    texto = "Vinho Tinto Suave Perini 750ml"

    assert construcao.perturbar_abreviacao(
        texto, TABELA, _rng(3)
    ) == construcao.perturbar_abreviacao(texto, TABELA, _rng(3))


# ── perturbar_ruido_tipografico ──────────────────────────────────────────────


def _remocao_interior(original: str, novo: str) -> bool:
    base = _sem_acento(original)
    return any(base[:i] + base[i + 1 :] == novo for i in range(1, len(base) - 1))


@pytest.mark.parametrize("seed", SEEDS)
def test_ruido_so_tira_acento_ou_uma_letra_interior_e_preserva_digitos(seed):
    texto = "Fabricação Própria Panetone Frutas 400g"

    novo = construcao.perturbar_ruido_tipografico(texto, _rng(seed))

    antes, depois = texto.split(), novo.split()
    assert novo != texto
    assert len(antes) == len(depois)
    assert construcao.tokens_numericos(novo) == construcao.tokens_numericos(texto)
    letras_removidas = 0
    for original, alterado in zip(antes, depois, strict=True):
        if original == alterado or _sem_acento(original) == alterado:
            continue
        assert not any(ch.isdigit() for ch in original)
        assert len(original) >= 6 and original[0] == alterado[0]
        assert _remocao_interior(original, alterado), (original, alterado)
        letras_removidas += 1
    assert letras_removidas <= 1


def test_ruido_e_deterministico_para_a_mesma_seed():
    texto = "Fabricação Própria Panetone Frutas 400g"

    assert construcao.perturbar_ruido_tipografico(texto, _rng(4)) == (
        construcao.perturbar_ruido_tipografico(texto, _rng(4))
    )


@pytest.mark.parametrize("texto", ["SAL 1KG", "AGUA 1L"])
def test_ruido_sem_acento_e_sem_palavra_longa_nao_se_aplica(texto):
    assert construcao.perturbar_ruido_tipografico(texto, _rng(0)) is None


# ── carregar_config_treino_pxp ───────────────────────────────────────────────

CONFIG_TREINO = {
    "seed": 42,
    "k": 20,
    "incluir_mesma_loja": True,
    "faixas_cosseno": [0.0, 0.3, 0.5, 0.7, 1.0],
    "n_negativos_por_faixa": {
        "[0.00, 0.30)": 2,
        "[0.30, 0.50)": 2,
        "[0.50, 0.70)": 3,
        "[0.70, 1.00]": 2,
    },
    "teto_negativos_por_produto": 3,
    "n_positivos": 6,
    "pesos_perturbacao": {"unidade": 1, "ordem": 1, "abreviacao": 1, "ruido": 1},
    "abreviacoes": {"Vinho": ["vh", "vin"], "tinto": ["tto"], "leite": ["lt"]},
}


def _gravar_config_treino(tmp_path: Path, **alteracoes: object) -> Path:
    caminho = tmp_path / "pares_treino_pxp.yaml"
    caminho.write_text(yaml.safe_dump({**CONFIG_TREINO, **alteracoes}), encoding="utf-8")
    return caminho


def test_config_treino_valida_carrega_e_normaliza_as_chaves_da_tabela(tmp_path):
    cfg = construcao.carregar_config_treino_pxp(_gravar_config_treino(tmp_path))

    assert cfg["seed"] == 42 and cfg["k"] == 20
    assert cfg["incluir_mesma_loja"] is True
    assert cfg["faixas_cosseno"] == [0.0, 0.3, 0.5, 0.7, 1.0]
    assert cfg["n_negativos_por_faixa"]["[0.50, 0.70)"] == 3
    assert cfg["teto_negativos_por_produto"] == 3 and cfg["n_positivos"] == 6
    assert cfg["abreviacoes"]["vinho"] == ["vh", "vin"]  # "Vinho" vira "vinho"


def test_config_treino_versionada_traz_a_receita_e_a_tabela_de_abreviacoes():
    cfg = construcao.carregar_config_treino_pxp(Path(_ROOT) / "configs" / "pares_treino_pxp.yaml")

    assert sum(cfg["n_negativos_por_faixa"].values()) > 0 and cfg["n_positivos"] > 0
    assert cfg["incluir_mesma_loja"] is True  # decisão do autor, 2026-11-13
    assert {"vinho", "leite", "biscoito"} <= set(cfg["abreviacoes"])
    assert set(cfg["pesos_perturbacao"]) == {"unidade", "ordem", "abreviacao", "ruido"}


@pytest.mark.parametrize(
    ("alteracoes", "trecho"),
    [
        ({"faixas_cosseno": [0.1, 0.5, 1.0]}, "faixas"),
        ({"k": 0}, "k"),
        ({"incluir_mesma_loja": "sim"}, "incluir_mesma_loja"),
        ({"n_negativos_por_faixa": {"[0.00, 1.00]": 1}}, "n_negativos_por_faixa"),
        (
            {
                "n_negativos_por_faixa": {
                    **CONFIG_TREINO["n_negativos_por_faixa"],
                    "[0.00, 0.30)": -1,
                }
            },
            "n_negativos_por_faixa",
        ),
        ({"teto_negativos_por_produto": 0}, "teto_negativos_por_produto"),
        ({"n_positivos": -1}, "n_positivos"),
        ({"pesos_perturbacao": {"unidade": 1, "outro": 1}}, "pesos_perturbacao"),
        ({"pesos_perturbacao": {"unidade": -1, "ordem": 1}}, "pesos_perturbacao"),
        ({"pesos_perturbacao": {"unidade": 0, "ordem": 0}}, "pesos_perturbacao"),
        ({"abreviacoes": {"vinho": ["vinhos"]}}, "abreviacoes"),
        ({"abreviacoes": {"vinho": ["vinho"]}}, "abreviacoes"),
        ({"abreviacoes": {"vinho": ["v1"]}}, "abreviacoes"),
        ({"abreviacoes": {"vinho": []}}, "abreviacoes"),
    ],
    ids=[
        "faixas_nao_comecam_em_0",
        "k_zero",
        "mesma_loja_nao_booleana",
        "faixas_sem_correspondencia",
        "contagem_negativa",
        "teto_zero",
        "positivos_negativos",
        "peso_de_tipo_desconhecido",
        "peso_negativo",
        "todos_os_pesos_zero",
        "abreviacao_mais_longa",
        "abreviacao_igual",
        "abreviacao_com_digito",
        "abreviacao_vazia",
    ],
)
def test_config_treino_invalida_levanta_erro_com_o_nome_da_chave(tmp_path, alteracoes, trecho):
    with pytest.raises(ValueError, match=trecho):
        construcao.carregar_config_treino_pxp(_gravar_config_treino(tmp_path, **alteracoes))


def test_config_treino_sem_incluir_mesma_loja_levanta_erro(tmp_path):
    """A chave é obrigatória: um default silencioso mudaria a amostra de negativos."""
    sem_a_chave = {k: v for k, v in CONFIG_TREINO.items() if k != "incluir_mesma_loja"}
    caminho = tmp_path / "pares_treino_pxp.yaml"
    caminho.write_text(yaml.safe_dump(sem_a_chave), encoding="utf-8")

    with pytest.raises(ValueError, match="incluir_mesma_loja"):
        construcao.carregar_config_treino_pxp(caminho)


# ── perturbar_ordem com tamanho escrito com espaço (achado na base real, 2026-11-13) ──────────
# 13 de 6.000 positivos mudaram o conjunto de tamanhos porque "750 ML" são dois tokens e a troca
# os separava. A barreira crítica pegou; a perturbação precisa preservar a expressão inteira.

TEXTOS_COM_TAMANHO_ESPACADO = [
    "VH ITA MARCA EXEMPLO CALEO TTO 750 ML",
    "Shampoo Marca Exemplo Cabelos Claros 200 Ml",
    "Peixe Exemplo Salgado 7/9 Kg",
    "TINTA COR TON 7.1 L.EXEMPLO MED 135G",
    "Mini Pizza Sabor Exemplo 155 g",
]


@pytest.mark.parametrize("texto", TEXTOS_COM_TAMANHO_ESPACADO)
def test_ordem_nunca_separa_o_numero_da_unidade(texto):
    aplicou = 0
    for seed in range(60):
        novo = construcao.perturbar_ordem(texto, _rng(seed))
        if novo is None:
            continue
        aplicou += 1
        assert construcao.tokens_numericos(novo) == construcao.tokens_numericos(texto), novo
        assert sorted(novo.split()) == sorted(texto.split())
    assert aplicou > 0, "a perturbação de ordem deixou de se aplicar a esse texto"


@pytest.mark.parametrize(
    "perturbacao",
    [
        lambda t, r: construcao.perturbar_ordem(t, r),
        lambda t, r: construcao.perturbar_abreviacao(t, TABELA, r),
        lambda t, r: construcao.perturbar_ruido_tipografico(t, r),
        lambda t, r: construcao.perturbar_unidade(t),
    ],
    ids=["ordem", "abreviacao", "ruido", "unidade"],
)
@pytest.mark.parametrize(
    "texto", TEXTOS_COM_TAMANHO_ESPACADO + ["Vinho Tinto 750 ml Fabricação Própria"]
)
def test_nenhuma_perturbacao_muda_o_conjunto_de_tamanhos_nem_devolve_texto_igual(
    perturbacao, texto
):
    for seed in range(40):
        novo = perturbacao(texto, _rng(seed))
        if novo is not None:
            assert construcao.tokens_numericos(novo) == construcao.tokens_numericos(texto), novo
            assert novo != texto
