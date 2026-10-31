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
