"""
conftest.py — Fixtures compartilhadas para toda a suite de testes.

Fixtures de dados representam amostras mínimas do domínio (produtos brutos
do ALTA e entradas do dicionário canônico) para as camadas de testes
unitários e de transformação em memória (ver AGENTS.md, seção 3).
"""

import os
import sys

import pandas as pd
import pytest

# Adiciona a raiz do projeto ao path para que os scripts sejam importáveis
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SEED = 42


# ── Fixtures de dados ───────────────────────────────────────────────────────


@pytest.fixture
def produtos_brutos_exemplo() -> pd.DataFrame:
    """Amostra mínima de produtos brutos coletados (schema de dados/brutos/todos_mercados_*.csv)."""
    return pd.DataFrame(
        [
            {
                "product_id": 1,
                "description": "Água Mineral Sem Gás Indaia 5l",
                "unit": "UN",
                "price": 13.99,
                "location": "PB, João Pessoa, Pedro Gondim",
                "source": "ajuba_api",
                "collected_at": "2026-09-10 12:38:09",
            },
            {
                "product_id": 2,
                "description": "Agua Mineral C/gas Grf Pet 1,5l Indaia",
                "unit": "UN",
                "price": 4.99,
                "location": "PB, João Pessoa, Pedro Gondim",
                "source": "ajuba_api",
                "collected_at": "2026-09-10 12:38:09",
            },
        ]
    )


@pytest.fixture
def produtos_brutos_variados_exemplo() -> pd.DataFrame:
    """Amostra com múltiplas fontes/estados, para testar distribuições (spec 001, tarefa 1.1.1)."""
    return pd.DataFrame(
        [
            {
                "product_id": 1,
                "description": "Água Mineral Sem Gás Indaia 5l",
                "unit": "UN",
                "price": 13.99,
                "location": "PB, João Pessoa, Pedro Gondim",
                "source": "ajuba_api",
                "collected_at": "2026-09-10 12:38:09",
                "match_score": 0.92,
            },
            {
                "product_id": 2,
                "description": "Agua Mineral C/gas Grf Pet 1,5l Indaia",
                "unit": "UN",
                "price": 4.99,
                "location": "PB, João Pessoa, Pedro Gondim",
                "source": "ajuba_api",
                "collected_at": "2026-09-10 12:38:09",
                "match_score": 0.65,
            },
            {
                "product_id": 3,
                "description": "Arroz Branco Tio Joao 1kg",
                "unit": "UN",
                "price": 6.49,
                "location": "CE, Fortaleza, Centro",
                "source": "diniz_api",
                "collected_at": "2026-09-10 12:40:00",
                "match_score": 0.88,
            },
            {
                "product_id": 3,
                "description": "Arroz Branco Tio Joao 1kg",
                "unit": "UN",
                "price": 6.79,
                "location": "PI, Teresina, Centro",
                "source": "guedes_api",
                "collected_at": "2026-09-10 12:41:00",
                "match_score": 0.71,
            },
        ]
    )


@pytest.fixture
def dicionario_canonico_exemplo() -> pd.DataFrame:
    """Amostra mínima do dicionário canônico (schema de dados/brutos/dicionario_canonico.csv)."""
    return pd.DataFrame(
        [
            {"desc_alim": "AGUA MINERAL", "codg_item1": 8201004, "cod_padrao": 99},
            {"desc_alim": "ARROZ BRANCO", "codg_item1": 6300113, "cod_padrao": 99},
        ]
    )


@pytest.fixture
def produtos_entre_lojas_exemplo() -> pd.DataFrame:
    """17 produtos em 3 lojas, no schema de produtos_limpos, para a blocagem produto × produto.

    `grupo_sku` existe só nesta fixture (a base real não tem rótulo de par): marca os produtos
    que o desenho do teste trata como o mesmo SKU. Casos embutidos: o mesmo SKU escrito de formas
    diferentes (leite em 3 lojas, arroz, óleo com 900ML × 0,9L), texto idêntico entre lojas
    (feijão), SKUs distintos que só diferem no tamanho (café 500G × 1KG), um produto sem token
    em comum com as outras lojas (biscoito) e dois produtos com score empatado (açúcar e sal).
    """
    linhas = [
        ("Leite Integral Italac 1L", "loja_a", "leite_italac_1l"),
        ("LT ITALAC INTEGRAL 1000ML", "loja_b", "leite_italac_1l"),
        ("Leite Italac Integral 1 L", "loja_c", "leite_italac_1l"),
        ("Arroz Branco Tio Joao 1kg", "loja_a", "arroz_tio_joao_1kg"),
        ("ARROZ TIO JOAO BRANCO 1KG", "loja_b", "arroz_tio_joao_1kg"),
        ("Oleo De Soja Liza 900ml", "loja_a", "oleo_liza_900ml"),
        ("OLEO SOJA LIZA 0,9L", "loja_c", "oleo_liza_900ml"),
        ("Cafe Pilao Tradicional 500g", "loja_a", "cafe_pilao_500g"),
        ("CAFE PILAO TRADICIONAL 1KG", "loja_b", "cafe_pilao_1kg"),
        ("Feijao Carioca Camil 1kg", "loja_a", "feijao_camil_1kg"),
        ("FEIJAO CARIOCA CAMIL 1KG", "loja_c", "feijao_camil_1kg"),
        ("Agua Mineral Indaia 1,5l", "loja_a", "agua_indaia"),
        ("Biscoito Maria Bauducco 200g", "loja_b", "biscoito_bauducco"),
        ("Macarrao Espaguete Adria 500g", "loja_b", "macarrao_adria"),
        ("Sabao em Po Omo 1kg", "loja_c", "sabao_omo"),
        ("Acucar Uniao 1kg", "loja_c", "acucar_uniao"),
        ("Sal Cisne 1kg", "loja_c", "sal_cisne"),
    ]
    return pd.DataFrame(
        {
            "product_id": range(1, len(linhas) + 1),
            "description": [d for d, _, _ in linhas],
            "source": [s for _, s, _ in linhas],
            "und_val": 1.0,
            "und_med": "KG",
            "grupo_sku": [g for _, _, g in linhas],
        }
    )


@pytest.fixture
def produtos_brutos_inversao_exemplo() -> pd.DataFrame:
    """Par com o mesmo multiconjunto de tokens em ordem diferente, lojas diferentes.

    Fixture dedicada (não estende `produtos_brutos_variados_exemplo`) para
    isolar o teste de detecção de inversão de ordem sem recalcular as
    dezenas de asserções numéricas já fixadas sobre a outra fixture.
    """
    return pd.DataFrame(
        [
            {
                "product_id": 10,
                "description": "Suco Uva Del Valle 1,5L",
                "source": "ajuba_api",
                "location": "PB, João Pessoa, Pedro Gondim",
            },
            {
                "product_id": 11,
                "description": "Suco Del Valle Uva 1,5l",
                "source": "diniz_api",
                "location": "CE, Fortaleza, Centro",
            },
        ]
    )


@pytest.fixture
def par_match_exemplo() -> tuple[str, str]:
    """Par (produto bruto, entrada canônica) que deve ser rotulado como match."""
    return ("Água Mineral Sem Gás Indaia 5l", "AGUA MINERAL")


@pytest.fixture
def par_nao_match_exemplo() -> tuple[str, str]:
    """Par (produto bruto, entrada canônica) que deve ser rotulado como não-match."""
    return ("Água Mineral Sem Gás Indaia 5l", "ARROZ BRANCO")


@pytest.fixture
def fontes_tail_exemplo() -> dict[str, pd.DataFrame]:
    """Fontes sintéticas no formato do `ler_fontes_tail` (P5b). Nada vem do clone da TAIL.

    Casos embutidos: variantes que preservam o tamanho (8 pares), uma que o corrompe, uma sem
    tamanho, um grupo cujo título é do benchmark, uma variante `Fallback_Erro_LLM`; dois grupos de
    nota fiscal (um com 5 títulos de mesmo tamanho = 10 pares; outro sem tamanho); títulos do
    octaprice (os dois formatos de URL), um deles igual a um título do benchmark.
    """
    old_attack = pd.DataFrame(
        [
            ("Suco Uva Tial 1L", "Suco de Uva Tial 1000ml"),
            ("Suco Uva Tial 1L", "Suco Uva Tial 1L Novo"),
            ("Arroz Tio Joao 5kg", "Arroz T Joao 5kg"),
            ("Feijao Carioca Camil 1kg", "Feijao Carioca Camil 1000g"),
            ("Leite Integral Italac 1L", "Leite Integral Italac 1000ml"),
            ("Oleo de Soja Liza 900ml", "Oleo Soja Liza 0,9L"),
            ("Cafe Pilao Tradicional 500g", "Cafe Pilao Tradicional 0,5kg"),
            ("Biscoito Maria Bauducco 200g", "Biscoito Maria Bauducco 200"),  # tamanho corrompido
            ("Pao de Forma Wickbold", "Pao Forma Wickbold"),  # sem tamanho
            ("Shampoo Exemplo Antiqueda 100ml", "Shampoo Exemplo Antiqueda 0,1L"),  # benchmark
        ],
        columns=["original", "attacked"],
    )
    attack = pd.DataFrame(
        {
            "id": ["1", "2"],
            "original": ["Macarrao Espaguete Adria 500g", "Macarrao Espaguete Adria 500g"],
            "tipo_variacao": ["Erro_Digitacao", "Fallback_Erro_LLM"],
            "attacked": ["Macarrao Espagete Adria 500g", "lixo do llm"],
        }
    )
    itens_nf = pd.DataFrame(
        {
            "title": [
                "Biscoito Maria Bauducco 200g",
                "Bisc Maria Bauducco 200g",
                "Biscoito Maria Bauduco 200g",
                "Bisc M Bauducco 200g",
                "Biscoito Mar Bauducco 200g",
                "Pao Sem Tamanho A",
                "Pao Sem Tamanho B",
                "Pao Sem Tamanho C",
            ],
            "normalized": ["BISCOITO MARIA"] * 5 + ["PAO SEM TAMANHO"] * 3,
        }
    )
    base = "https://produto.mercadolivre.com.br/MLB-{n}-{slug}-_JM"
    www = "https://www.mercadolivre.com.br/{slug}/p/MLB{n}"
    urls = [
        base.format(n=1, slug="suco-uva-tial-500ml"),
        base.format(n=2, slug="arroz-tio-joao-1kg"),
        base.format(n=3, slug="feijao-carioca-camil-500g"),
        base.format(n=4, slug="leite-integral-italac-500ml"),
        base.format(n=5, slug="oleo-soja-liza-500ml"),
        base.format(n=6, slug="cafe-pilao-tradicional-250g"),
        www.format(n=7, slug="macarrao-espaguete-adria-1kg"),
        www.format(n=8, slug="suco-laranja-tial-1l"),  # igual a um título do benchmark
        www.format(n=9, slug="arroz-branco-camil-5kg"),
        www.format(n=10, slug="feijao-preto-camil-1kg"),
    ]
    benchmark = pd.DataFrame(
        {
            "title_a": ["Shampoo Exemplo Antiqueda 100ml", "Oculos Exemplo Virtual 3d Vr Box"],
            "title_b": ["Suco Laranja Tial 1L", "Oculos Exemplo Vr Box Novo"],
            "candidate_label": ["match", "match"],
            "similarity_score": ["0.9", "0.8"],
            "label": ["1", "0"],
        }
    )
    return {
        "old_attack": old_attack,
        "attack": attack,
        "itens_nf": itens_nf,
        "octaprice": pd.DataFrame({"product_url": urls}),
        "benchmark": benchmark,
    }
