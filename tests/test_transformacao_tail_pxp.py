"""
test_transformacao_tail_pxp.py — Camada 2: pares da TAIL para o treino produto × produto, em
memória (ADR-0013; ADR-0015; spec 001 RF8; design-treino-pxp §10; decisões do autor em 2026-11-16
D1 a D6). Bloco P5a: títulos, positivos, filtros de tamanho, grupos, quase-duplicatas do benchmark
e teto por grupo. Os negativos e a orquestração são o bloco P5b.

Títulos e pares sintéticos, escritos para o teste; nada vem do clone da TAIL.
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

# ── titulo_do_slug (os títulos do octaprice vêm só da URL do anúncio) ────────


@pytest.mark.parametrize(
    ("url", "esperado"),
    [
        (
            "https://produto.mercadolivre.com.br/MLB-3149572356-shampoo-prevent-100ml-10und-_JM",
            "shampoo prevent 100ml 10und",
        ),
        (
            "https://www.mercadolivre.com.br/shampoo-coco-354g-monday-haircare/p/MLB2003353394",
            "shampoo coco 354g monday haircare",
        ),
        (
            "https://www.mercadolivre.com.br/-shampoo-de-tintura-castanho/p/MLB2001998359",
            "shampoo de tintura castanho",
        ),
        (
            "https://produto.mercadolivre.com.br/MLB-1-selante-1-litro-_JM?x=1&y=2#polycard",
            "selante 1 litro",
        ),
        (  # terceiro formato, encontrado nos dados reais (1 de 18.084 URLs): /up/MLBU<id>
            "https://www.mercadolivre.com.br/progressiva-sem-formol-1000ml-brilho/up/MLBU2862420488"
            "?pdp_filters=item_id:MLB3917659819",
            "progressiva sem formol 1000ml brilho",
        ),
    ],
)
def test_titulo_do_slug_cobre_os_dois_formatos_de_url_e_ignora_query_e_fragmento(url, esperado):
    assert construcao.titulo_do_slug(url) == esperado


@pytest.mark.parametrize("url", ["https://exemplo.com/x", "", "não é url"])
def test_titulo_do_slug_de_formato_desconhecido_falha_nomeando_a_url(url):
    with pytest.raises(ValueError, match="url"):
        construcao.titulo_do_slug(url)


# ── normalizar_titulo_tail ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        (
            "Óculos Exemplo Virtual 3d Vr Box + Controle",
            "oculos exemplo virtual 3d vr box controle",
        ),
        (
            " .Fita Industrial. 10cm X 50mt .Marca. ",
            "fita industrial 10cm x 50mt marca",
        ),
        ("", ""),
    ],
)
def test_normalizar_titulo_tira_acento_caixa_pontuacao_e_espaco_repetido(texto, esperado):
    assert construcao.normalizar_titulo_tail(texto) == esperado


def test_normalizar_titulo_e_idempotente():
    uma_vez = construcao.normalizar_titulo_tail("Peça Exemplo 335433 Marca-Modelo, 2010/2014")

    assert construcao.normalizar_titulo_tail(uma_vez) == uma_vez


# ── construir_pares_variante (old_attack_dataset.csv + attack.csv) ───────────

COLUNAS_VARIANTE = ["titulo_a", "titulo_b", "fonte", "tipo_variacao"]


@pytest.fixture
def fontes_variante() -> tuple[pd.DataFrame, pd.DataFrame]:
    old = pd.DataFrame(
        {
            "original": ["Suco Uva Tial 1L"] * 4 + ["Arroz Tio Joao 5kg"] * 2 + ["Sal Cisne 1kg"],
            "attacked": [
                "Suco Uva Tial 1L",  # idêntica: descartada
                "SUCO UVA TIAL 1L.",  # idêntica depois de normalizar: descartada
                "Suco de Uva Tial 1000ml",
                "Suco Uva Tial 1L Novo",
                "Arroz Tio Joao 5kg",  # idêntica
                "Arroz T. Joao 5 Kg",
                "",  # variante vazia: descartada
            ],
        }
    )
    attack = pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "original": [
                "Suco Uva Tial 1L",
                "Suco Uva Tial 1L",
                "Sal Cisne 1kg",
                "Arroz Tio Joao 5kg",
            ],
            "tipo_variacao": [
                "Abreviacao",
                "Fallback_Erro_LLM",
                "Erro_Digitacao",
                "Notacao_Unidades",
            ],
            "attacked": [
                "Suco Uv Tial 1L",
                "Suco Uva Tial 1L Lixo",
                "Sal Cizne 1kg",
                "Arroz T. Joao 5 Kg",
            ],
        }
    )
    return old, attack


def test_pares_de_variante_tem_as_colunas_do_contrato(fontes_variante):
    pares = construcao.construir_pares_variante(*fontes_variante)

    assert list(pares.columns) == COLUNAS_VARIANTE


def test_variante_igual_ao_original_depois_de_normalizar_e_variante_vazia_sao_descartadas(
    fontes_variante,
):
    pares = construcao.construir_pares_variante(*fontes_variante)

    normalizados = [
        (construcao.normalizar_titulo_tail(a), construcao.normalizar_titulo_tail(b))
        for a, b in zip(pares["titulo_a"], pares["titulo_b"], strict=True)
    ]
    assert all(a != b and b != "" for a, b in normalizados)
    assert "SUCO UVA TIAL 1L." not in set(pares["titulo_b"])


def test_fallback_erro_llm_do_attack_e_descartado(fontes_variante):
    pares = construcao.construir_pares_variante(*fontes_variante)

    assert "Suco Uva Tial 1L Lixo" not in set(pares["titulo_b"])
    assert "Fallback_Erro_LLM" not in set(pares["tipo_variacao"].dropna())


def test_par_repetido_nas_duas_fontes_fica_uma_vez_e_com_a_fonte_old_attack(fontes_variante):
    pares = construcao.construir_pares_variante(*fontes_variante)
    repetido = pares[
        (pares["titulo_a"] == "Arroz Tio Joao 5kg") & (pares["titulo_b"] == "Arroz T. Joao 5 Kg")
    ]

    assert len(repetido) == 1
    assert repetido.iloc[0]["fonte"] == "old_attack"
    assert not pares.duplicated(["titulo_a", "titulo_b"]).any()


def test_variante_do_attack_traz_o_tipo_e_a_do_old_attack_traz_nulo(fontes_variante):
    pares = construcao.construir_pares_variante(*fontes_variante).set_index("titulo_b")

    assert pares.loc["Suco Uv Tial 1L", "fonte"] == "attack"
    assert pares.loc["Suco Uv Tial 1L", "tipo_variacao"] == "Abreviacao"
    assert pd.isna(pares.loc["Suco Uva Tial 1L Novo", "tipo_variacao"])


def test_pares_de_variante_nao_dependem_da_ordem_das_linhas(fontes_variante):
    old, attack = fontes_variante

    um = construcao.construir_pares_variante(old, attack)
    outro = construcao.construir_pares_variante(old.iloc[::-1], attack.iloc[::-1])

    assert um.equals(outro)


# ── filtrar_positivos_por_tamanho (D1: sem tamanho fora por padrão) ──────────


@pytest.fixture
def pares_de_tamanho() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "titulo_a": ["suco uva 1l", "suco uva 1l", "suco uva 1l", "suco", "suco uva 200 ml"],
            "titulo_b": [
                "suco de uva 1000ml",
                "suco uva 500ml",
                "suco uva",
                "suco uva tial",
                "suco uva 200ml",
            ],
        }
    )


def test_tamanho_igual_depois_de_normalizar_a_unidade_e_mantido(pares_de_tamanho):
    mantidos = construcao.filtrar_positivos_por_tamanho(pares_de_tamanho, incluir_sem_tamanho=False)

    assert {"suco de uva 1000ml", "suco uva 200ml"} <= set(mantidos["titulo_b"])


def test_tamanho_diferente_ou_perdido_na_variante_e_descartado(pares_de_tamanho):
    mantidos = construcao.filtrar_positivos_por_tamanho(pares_de_tamanho, incluir_sem_tamanho=True)

    assert "suco uva 500ml" not in set(mantidos["titulo_b"])
    assert "suco uva" not in set(mantidos["titulo_b"])


def test_sem_tamanho_nos_dois_lados_so_entra_com_a_chave_ligada(pares_de_tamanho):
    desligada = construcao.filtrar_positivos_por_tamanho(
        pares_de_tamanho, incluir_sem_tamanho=False
    )
    ligada = construcao.filtrar_positivos_por_tamanho(pares_de_tamanho, incluir_sem_tamanho=True)

    assert "suco uva tial" not in set(desligada["titulo_b"])
    assert "suco uva tial" in set(ligada["titulo_b"])
    assert len(ligada) == len(desligada) + 1


def test_filtro_de_tamanho_preserva_colunas_e_ordem(pares_de_tamanho):
    mantidos = construcao.filtrar_positivos_por_tamanho(pares_de_tamanho, incluir_sem_tamanho=True)

    assert list(mantidos.columns) == list(pares_de_tamanho.columns)
    assert list(mantidos.index) == sorted(mantidos.index)


# ── construir_pares_nf (itens_nf_normalizados.csv: grupos de 10 títulos) ─────


def test_pares_nf_sao_todos_os_pares_dentro_de_cada_grupo():
    itens = pd.DataFrame(
        {
            "title": ["a1", "a2", "a3", "b1", "b2", "c1"],
            "normalized": ["A", "A", "A", "B", "B", "C"],
        }
    )

    pares = construcao.construir_pares_nf(itens)

    assert list(pares.columns) == ["titulo_a", "titulo_b", "fonte"]
    assert len(pares) == 3 + 1 + 0
    assert set(pares["fonte"]) == {"nf"}
    assert set(zip(pares["titulo_a"], pares["titulo_b"], strict=True)) == {
        ("a1", "a2"),
        ("a1", "a3"),
        ("a2", "a3"),
        ("b1", "b2"),
    }


def test_pares_nf_nao_misturam_grupos_nem_repetem_titulo_igual():
    itens = pd.DataFrame({"title": ["a1", "a1", "a2", "b1"], "normalized": ["A", "A", "A", "B"]})

    pares = construcao.construir_pares_nf(itens)

    assert list(zip(pares["titulo_a"], pares["titulo_b"], strict=True)) == [("a1", "a2")]


def test_19_grupos_de_10_titulos_dao_855_pares():
    itens = pd.DataFrame(
        {
            "title": [f"item {g} {i}" for g in range(19) for i in range(10)],
            "normalized": [f"g{g}" for g in range(19) for _ in range(10)],
        }
    )

    assert len(construcao.construir_pares_nf(itens)) == 19 * 45 == 855


# ── agrupar_titulos_tail (union-find: original, variantes e positivos ligados) ─


def test_titulos_ligados_por_pares_formam_um_grupo_mesmo_em_cadeia():
    pares = pd.DataFrame({"titulo_a": ["a", "b", "x"], "titulo_b": ["b", "c", "y"]})

    grupo = construcao.agrupar_titulos_tail(pares)

    assert grupo["a"] == grupo["b"] == grupo["c"]
    assert grupo["x"] == grupo["y"]
    assert grupo["a"] != grupo["x"]
    assert set(grupo.index) == {"a", "b", "c", "x", "y"}


def test_o_id_do_grupo_nao_depende_da_ordem_das_linhas():
    pares = pd.DataFrame({"titulo_a": ["a", "b", "x"], "titulo_b": ["b", "c", "y"]})

    um = construcao.agrupar_titulos_tail(pares)
    outro = construcao.agrupar_titulos_tail(pares.iloc[::-1])

    assert um.sort_index().equals(outro.sort_index())


# ── excluir_grupos_quase_duplicatas (D2: grupo inteiro, limiar 0,9 fixado a priori) ─


@pytest.fixture
def grupos_e_benchmark() -> tuple[pd.Series, list[str]]:
    titulos = {
        "Shampoo Exemplo Antiqueda Forte 100ml": "g_identico",
        "shampoo exemplo forte 100 ml cabelos": "g_identico",  # inocente, mas do mesmo grupo
        "kit shampoo condicionador marcax creme pentear brilho forte tratamento 150g novo": (
            "g_quase"
        ),
        "kit shampoo marcax brilho forte 150g": "g_quase",
        "arroz tio joao tipo 1 pacote 5kg": "g_limpo",
        "arroz tio joao integral pacote 5kg": "g_limpo",
    }
    benchmark = [
        "SHAMPOO EXEMPLO ANTIQUEDA FORTE 100ML",
        "kit shampoo condicionador marcax creme pentear brilho forte tratamento 150g",
        "oculos exemplo virtual 3d vr box",
    ]
    return pd.Series(titulos, name="grupo"), benchmark


def test_titulo_identico_ao_do_benchmark_depois_de_normalizar_exclui_o_grupo_inteiro(
    grupos_e_benchmark,
):
    grupos, benchmark = grupos_e_benchmark

    mantidos, exclusoes = construcao.excluir_grupos_quase_duplicatas(grupos, benchmark, 0.9)

    assert "g_identico" not in set(mantidos)
    assert "shampoo exemplo forte 100 ml cabelos" not in set(mantidos.index)
    motivos = exclusoes[exclusoes["grupo"] == "g_identico"]["motivo"]
    assert "identico" in set(motivos)


def test_quase_duplicata_acima_do_limiar_exclui_o_grupo_inteiro(grupos_e_benchmark):
    grupos, benchmark = grupos_e_benchmark

    mantidos, exclusoes = construcao.excluir_grupos_quase_duplicatas(grupos, benchmark, 0.9)

    assert "g_quase" not in set(mantidos)
    assert "quase_duplicata" in set(exclusoes[exclusoes["grupo"] == "g_quase"]["motivo"])


def test_grupo_sem_parecido_com_o_benchmark_fica(grupos_e_benchmark):
    grupos, benchmark = grupos_e_benchmark

    mantidos, exclusoes = construcao.excluir_grupos_quase_duplicatas(grupos, benchmark, 0.9)

    assert set(mantidos) == {"g_limpo"}
    assert set(mantidos.index) == {
        "arroz tio joao tipo 1 pacote 5kg",
        "arroz tio joao integral pacote 5kg",
    }
    assert "g_limpo" not in set(exclusoes["grupo"])


def test_exclusoes_registram_o_titulo_do_benchmark_que_causou(grupos_e_benchmark):
    grupos, benchmark = grupos_e_benchmark

    _, exclusoes = construcao.excluir_grupos_quase_duplicatas(grupos, benchmark, 0.9)

    assert list(exclusoes.columns) == ["grupo", "titulo", "motivo", "titulo_benchmark"]
    linha = exclusoes[exclusoes["motivo"] == "identico"].iloc[0]
    assert linha["titulo_benchmark"] == "SHAMPOO EXEMPLO ANTIQUEDA FORTE 100ML"


def test_sem_titulos_no_benchmark_nada_e_excluido(grupos_e_benchmark):
    grupos, _ = grupos_e_benchmark

    mantidos, exclusoes = construcao.excluir_grupos_quase_duplicatas(grupos, [], 0.9)

    assert mantidos.equals(grupos)
    assert exclusoes.empty


@pytest.mark.parametrize("limiar", [0.0, -0.1, 1.5])
def test_limiar_fora_de_zero_a_um_falha(grupos_e_benchmark, limiar):
    grupos, benchmark = grupos_e_benchmark

    with pytest.raises(ValueError, match="limiar"):
        construcao.excluir_grupos_quase_duplicatas(grupos, benchmark, limiar)


# ── limitar_pares_por_grupo (D4: teto por grupo, seed fixa) ──────────────────


@pytest.fixture
def pares_com_grupo() -> pd.DataFrame:
    linhas = [(f"g1 t{i}", f"g1 u{i}", "g1") for i in range(10)]
    linhas += [("g2 a", "g2 b", "g2"), ("g2 c", "g2 d", "g2")]
    return pd.DataFrame(linhas, columns=["titulo_a", "titulo_b", "grupo"])


def test_teto_limita_cada_grupo_e_nao_toca_nos_menores(pares_com_grupo):
    limitado = construcao.limitar_pares_por_grupo(pares_com_grupo, teto=3, seed=42)

    assert limitado["grupo"].value_counts().to_dict() == {"g1": 3, "g2": 2}
    assert list(limitado.columns) == list(pares_com_grupo.columns)


def test_teto_e_deterministico_por_seed_e_nao_depende_da_ordem_das_linhas(pares_com_grupo):
    um = construcao.limitar_pares_por_grupo(pares_com_grupo, teto=3, seed=42)
    outro = construcao.limitar_pares_por_grupo(pares_com_grupo.iloc[::-1], teto=3, seed=42)
    diferente = construcao.limitar_pares_por_grupo(pares_com_grupo, teto=3, seed=7)

    assert um.reset_index(drop=True).equals(outro.reset_index(drop=True))
    assert set(um["titulo_a"]) != set(diferente["titulo_a"])


def test_teto_menor_que_um_falha(pares_com_grupo):
    with pytest.raises(ValueError, match="teto"):
        construcao.limitar_pares_por_grupo(pares_com_grupo, teto=0, seed=42)
