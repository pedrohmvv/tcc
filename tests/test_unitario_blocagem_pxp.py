"""
test_unitario_blocagem_pxp.py — Camada 1: blocagem produto × produto (spec 001, RF1 "1b").

Cobre T0 (config), T1 (universo por texto e loja) e T2 (tokens numéricos) de
specs/001-construcao-dataset-ground-truth/tasks-1b.md. Os textos são exemplos escritos para
o teste; nenhum rótulo de par vem de dado real. Ver design-1b.md e AGENTS.md §3.
"""

import importlib.util
import os
from pathlib import Path

import pandas as pd
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

COLUNAS_UNIVERSO = [
    "id_produto",
    "id_texto",
    "descricao",
    "texto_normalizado",
    "loja",
    "und_val",
    "und_med",
]


# ── T0: configs/blocagem_pxp.yaml e carregar_config_pxp ──────────────────────

CONFIG_VALIDA = {
    "seed": 42,
    "lote_ancoras": 25,
    "alvo_ancoras_com_positivo": 30,
    "max_ancoras": 100,
    "profundidade_pool": 100,
    "ngramas": [3, 5],
    "ks": [1, 5, 10, 20, 50, 100],
    "metodo": None,
    "k": None,
    "tau_particao": 0.7,
    "n_teste": 300,
    "fracao_digito_divergente": 0.2,
}


def _gravar_config(tmp_path: Path, **alteracoes: object) -> Path:
    caminho = tmp_path / "blocagem_pxp.yaml"
    caminho.write_text(yaml.safe_dump({**CONFIG_VALIDA, **alteracoes}), encoding="utf-8")
    return caminho


def test_config_pxp_valida_carrega_os_parametros(tmp_path):
    cfg = construcao.carregar_config_pxp(_gravar_config(tmp_path))

    assert cfg["seed"] == 42
    assert cfg["lote_ancoras"] == 25
    assert cfg["alvo_ancoras_com_positivo"] == 30
    assert cfg["max_ancoras"] == 100
    assert cfg["profundidade_pool"] == 100
    assert cfg["ngramas"] == [3, 5]
    assert cfg["ks"] == [1, 5, 10, 20, 50, 100]
    assert cfg["tau_particao"] == 0.7
    assert cfg["n_teste"] == 300
    assert cfg["fracao_digito_divergente"] == 0.2


def test_config_pxp_versionada_tem_metodo_e_k_congelados_em_tfidf_k20():
    # congelados pelo autor em 2026-11-03, depois da parada do pool (mesmos da 1a: blocagem.yaml)
    cfg = construcao.carregar_config_pxp(Path(_ROOT) / "configs" / "blocagem_pxp.yaml")

    assert cfg["metodo"] == "tfidf"
    assert cfg["k"] == 20
    assert cfg["lote_ancoras"] == 25
    assert cfg["alvo_ancoras_com_positivo"] == 30
    assert cfg["max_ancoras"] == 100
    assert cfg["tau_particao"] == 0.7
    assert cfg["n_teste"] == 300


def test_config_pxp_aceita_metodo_e_k_congelados_juntos(tmp_path):
    cfg = construcao.carregar_config_pxp(_gravar_config(tmp_path, metodo="bm25", k=20))

    assert cfg["metodo"] == "bm25"
    assert cfg["k"] == 20


@pytest.mark.parametrize("metodo", ["ngramas", "embeddings", ""])
def test_config_pxp_rejeita_metodo_fora_de_tfidf_e_bm25(tmp_path, metodo):
    caminho = _gravar_config(tmp_path, metodo=metodo, k=20)

    with pytest.raises(ValueError, match="metodo"):
        construcao.carregar_config_pxp(caminho)


def test_config_pxp_rejeita_k_fora_da_varredura(tmp_path):
    caminho = _gravar_config(tmp_path, metodo="tfidf", k=30)

    with pytest.raises(ValueError, match="k"):
        construcao.carregar_config_pxp(caminho)


@pytest.mark.parametrize("alteracoes", [{"metodo": "tfidf", "k": None}, {"metodo": None, "k": 20}])
def test_config_pxp_rejeita_metodo_e_k_congelados_separadamente(tmp_path, alteracoes):
    caminho = _gravar_config(tmp_path, **alteracoes)

    with pytest.raises(ValueError, match="juntos"):
        construcao.carregar_config_pxp(caminho)


def test_config_pxp_rejeita_alvo_de_ancoras_acima_do_teto(tmp_path):
    caminho = _gravar_config(tmp_path, alvo_ancoras_com_positivo=120, max_ancoras=100)

    with pytest.raises(ValueError, match="alvo"):
        construcao.carregar_config_pxp(caminho)


@pytest.mark.parametrize("fracao", [-0.1, 1.1])
def test_config_pxp_rejeita_fracao_de_digito_divergente_fora_de_0_a_1(tmp_path, fracao):
    caminho = _gravar_config(tmp_path, fracao_digito_divergente=fracao)

    with pytest.raises(ValueError, match="fracao_digito_divergente"):
        construcao.carregar_config_pxp(caminho)


def test_config_pxp_invalida_informa_o_caminho_do_yaml(tmp_path):
    caminho = _gravar_config(tmp_path, metodo="ngramas", k=20)

    with pytest.raises(ValueError, match="blocagem_pxp.yaml"):
        construcao.carregar_config_pxp(caminho)


# ── T1: deduplicar_por_texto_e_loja ──────────────────────────────────────────


def _produtos_lojas(linhas: list[tuple[str, str]]) -> pd.DataFrame:
    """(descrição, loja) → base no schema de produtos_limpos, com colunas do matcher ALTA."""
    return pd.DataFrame(
        {
            "product_id": range(1, len(linhas) + 1),
            "description": [d for d, _ in linhas],
            "source": [s for _, s in linhas],
            "und_val": 1.0,
            "und_med": "KG",
            "codg_item": 7,
            "desc_ref": "REF",
            "match_score": 0.9,
        }
    )


LINHAS_UNIVERSO = [
    ("Arroz Branco Tio Joao 1kg", "loja_a"),
    ("ARROZ BRANCO TIO JOAO 1KG", "loja_a"),  # mesmo texto normalizado, mesma loja
    ("Arroz Branco Tio Joao 1kg", "loja_b"),  # mesmo texto, outra loja
    ("Açúcar União 1kg", "loja_a"),
    ("ACUCAR UNIAO 1KG", "loja_b"),  # difere só por caixa e acento
    ("Feijão Carioca Camil 1kg", "loja_c"),
]


def test_universo_tem_uma_linha_por_texto_normalizado_e_loja():
    universo = construcao.deduplicar_por_texto_e_loja(_produtos_lojas(LINHAS_UNIVERSO))

    assert len(universo) == 5
    assert not universo.duplicated(["texto_normalizado", "loja"]).any()


def test_universo_mesmo_texto_em_duas_lojas_vira_duas_linhas_com_o_mesmo_id_texto():
    universo = construcao.deduplicar_por_texto_e_loja(_produtos_lojas(LINHAS_UNIVERSO))

    arroz = universo[universo["texto_normalizado"] == "ARROZ BRANCO TIO JOAO 1KG"]

    assert sorted(arroz["loja"]) == ["loja_a", "loja_b"]
    assert arroz["id_texto"].nunique() == 1
    assert arroz["id_produto"].nunique() == 2


def test_universo_id_texto_coincide_com_o_id_produto_da_1a():
    produtos = _produtos_lojas(LINHAS_UNIVERSO)

    universo = construcao.deduplicar_por_texto_e_loja(produtos)
    dedup_1a = construcao.deduplicar_por_texto_normalizado(produtos)

    assert set(universo["id_texto"]) == set(dedup_1a["id_produto"])


def test_universo_loja_vem_da_coluna_source():
    universo = construcao.deduplicar_por_texto_e_loja(_produtos_lojas(LINHAS_UNIVERSO))

    assert set(universo["loja"]) == {"loja_a", "loja_b", "loja_c"}


def test_universo_so_expoe_as_colunas_do_contrato_sem_matcher_alta():
    universo = construcao.deduplicar_por_texto_e_loja(_produtos_lojas(LINHAS_UNIVERSO))

    assert list(universo.columns) == COLUNAS_UNIVERSO
    assert not set(construcao.COLUNAS_MATCHER_ALTA) & set(universo.columns)


def test_universo_ids_e_representante_nao_dependem_da_ordem_de_entrada():
    produtos = _produtos_lojas(LINHAS_UNIVERSO)
    embaralhado = produtos.sample(frac=1.0, random_state=0).reset_index(drop=True)

    a = construcao.deduplicar_por_texto_e_loja(produtos)
    b = construcao.deduplicar_por_texto_e_loja(embaralhado)

    colunas = ["id_produto", "descricao"]
    pd.testing.assert_frame_equal(
        a[colunas].sort_values("id_produto").reset_index(drop=True),
        b[colunas].sort_values("id_produto").reset_index(drop=True),
    )


# ── T2: tokens_numericos e divergencia_numerica ──────────────────────────────


def test_900ml_e_0_9l_sao_o_mesmo_token_numerico():
    assert construcao.tokens_numericos("LEITE ITALAC 900ML") == construcao.tokens_numericos(
        "LEITE ITALAC 0,9L"
    )


def test_1kg_e_1000g_sao_o_mesmo_token_numerico():
    assert construcao.tokens_numericos("ARROZ 1KG") == construcao.tokens_numericos("ARROZ 1000G")


def test_equivalencia_de_unidade_e_exata_sem_erro_de_ponto_flutuante():
    # 1,005 * 1000 = 1004.9999999999999 em float; a equivalência tem de ser exata.
    assert not construcao.divergencia_numerica("SUCO 1,005L", "SUCO 1005ML")


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("LEITE ITALAC 900ML", "LEITE ITALAC 0,9L"),
        ("ARROZ TIO JOAO 1KG", "ARROZ TIO JOAO 1000G"),
        ("AGUA INDAIA 1,5L", "AGUA INDAIA 1.5 L"),
        ("AGUA INDAIA 500ml", "AGUA INDAIA 500 ML"),
        ("CAFE PILAO 500G 2UN", "2UN CAFE PILAO 500G"),
    ],
)
def test_nao_diverge_quando_os_tokens_numericos_sao_equivalentes(a, b):
    assert not construcao.divergencia_numerica(a, b)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("ARROZ TIO JOAO 1KG", "ARROZ TIO JOAO 5KG"),
        ("LEITE ITALAC 500ML", "LEITE ITALAC 1L"),
        ("BISCOITO MARIA 200G", "BISCOITO MARIA 400G"),
        ("CAFE PILAO 500G", "CAFE PILAO 1KG"),
    ],
)
def test_diverge_quando_o_tamanho_difere_depois_de_normalizar_a_unidade(a, b):
    assert construcao.divergencia_numerica(a, b)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("LEITE ITALAC", "LEITE ITALAC 1L"),
        ("LEITE ITALAC", "LEITE ITALAC"),
        ("", "LEITE ITALAC 1L"),
    ],
)
def test_nao_diverge_quando_algum_lado_nao_tem_numero_com_unidade(a, b):
    assert not construcao.divergencia_numerica(a, b)


def test_numero_sem_unidade_nao_conta_como_token():
    assert construcao.tokens_numericos("ARROZ TIPO 1 5KG") == construcao.tokens_numericos(
        "ARROZ TIPO 2 5KG"
    )


def test_divergencia_e_simetrica():
    a, b = "LEITE ITALAC 500ML", "LEITE ITALAC 1L"

    assert construcao.divergencia_numerica(a, b) == construcao.divergencia_numerica(b, a)


# Grafias reais da base limpa: GR (~1,2 mil menções) e LT (~120) além de g, kg, ml, l.
@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("ACHOCOLATADO MARATA 400G", "ACHOCOLATADO MARATA 400GR"),
        ("DOCE DE GOIABA 695GR", "DOCE DE GOIABA 695 G"),
        ("LEITE UHT 1L", "LEITE UHT 1LT"),
        ("LEITE UHT 1LT", "LEITE UHT 1000ML"),
        ("ARROZ 1KG", "ARROZ 1000 gr"),
    ],
)
def test_gr_e_lt_equivalem_a_g_e_l(a, b):
    assert construcao.tokens_numericos(a) == construcao.tokens_numericos(b)
    assert not construcao.divergencia_numerica(a, b)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("DOCE DE GOIABA 695 GR", "DOCE DE GOIABA 300 GR"),
        ("ACHOCOLATADO MARATA 400G", "ACHOCOLATADO MARATA SAC 200GR"),
        ("LEITE UHT 1LT", "LEITE UHT 500ML"),
        ("LEITE UHT 1L", "LEITE UHT 2LT"),
    ],
)
def test_diverge_quando_o_tamanho_em_gr_ou_lt_difere(a, b):
    assert construcao.divergencia_numerica(a, b)


def test_gr_e_lt_so_valem_colados_a_um_numero_e_fora_de_palavras():
    assert construcao.tokens_numericos("GRANDE 5 LTDA") == frozenset()


# ── T5a: decidir_proximo_lote (regra de parada do pool, Q2) ──────────────────
# Só contagens de âncoras entram: a decisão nunca vê o recall (design-1b.md §5).

ALVO, TETO, LOTE = 30, 100, 25


def _decidir(n_sorteados: int, n_com_positivo: int, **cfg: int):
    parametros = {"alvo": ALVO, "max_ancoras": TETO, "lote_ancoras": LOTE, **cfg}
    return construcao.decidir_proximo_lote(
        n_sorteados,
        n_com_positivo,
        alvo_ancoras_com_positivo=parametros["alvo"],
        max_ancoras=parametros["max_ancoras"],
        lote_ancoras=parametros["lote_ancoras"],
    )


def test_antes_do_primeiro_lote_continua_com_um_lote_cheio():
    decisao = _decidir(0, 0)

    assert decisao.motivo == "continuar"
    assert decisao.tamanho_proximo_lote == 25


def test_abaixo_do_alvo_e_do_teto_continua_com_um_lote_cheio():
    decisao = _decidir(50, 12)

    assert decisao.motivo == "continuar"
    assert decisao.tamanho_proximo_lote == 25


@pytest.mark.parametrize("n_com_positivo", [30, 31, 50])
def test_para_quando_atinge_o_alvo_de_ancoras_com_positivo(n_com_positivo):
    decisao = _decidir(75, n_com_positivo)

    assert decisao.motivo == "alvo"
    assert decisao.tamanho_proximo_lote == 0


def test_para_no_teto_de_ancoras_sorteados_sem_atingir_o_alvo():
    decisao = _decidir(100, 29)

    assert decisao.motivo == "teto"
    assert decisao.tamanho_proximo_lote == 0


def test_alvo_e_teto_ao_mesmo_tempo_registra_o_alvo():
    decisao = _decidir(100, 30)

    assert decisao.motivo == "alvo"
    assert decisao.tamanho_proximo_lote == 0


def test_ultimo_lote_e_truncado_quando_o_teto_nao_e_multiplo_do_lote():
    decisao = _decidir(75, 5, max_ancoras=90)

    assert decisao.motivo == "continuar"
    assert decisao.tamanho_proximo_lote == 15


def test_teto_reduzido_abaixo_do_ja_sorteado_para_no_teto():
    decisao = _decidir(100, 10, max_ancoras=75)

    assert decisao.motivo == "teto"
    assert decisao.tamanho_proximo_lote == 0


@pytest.mark.parametrize(
    ("n_sorteados", "n_com_positivo"),
    [(-1, 0), (10, -1), (10, 11)],
)
def test_contagens_impossiveis_levantam_erro(n_sorteados, n_com_positivo):
    with pytest.raises(ValueError, match="contagem"):
        _decidir(n_sorteados, n_com_positivo)


@pytest.mark.parametrize("cfg", [{"lote_ancoras": 0}, {"alvo": 0}, {"max_ancoras": 0}])
def test_parametros_nao_positivos_levantam_erro(cfg):
    with pytest.raises(ValueError, match="parâmetro"):
        _decidir(0, 0, **cfg)


# ── T6: validar_anotacao_pool (só a forma; nunca o mérito do rótulo) ──────────

COLUNAS_PLANILHA_POOL = [
    "id_par",
    "id_ancora",
    "descricao_ancora",
    "und_val_ancora",
    "und_med_ancora",
    "id_candidato",
    "descricao_candidato",
    "und_val_candidato",
    "und_med_candidato",
    "tipo_par",
    "origem",
    "rotulo",
    "ancora_concluida",
    "observacao",
    "timestamp_anotacao",
]


def _planilha_anotada(linhas: list[tuple[str, str, str, str]]) -> pd.DataFrame:
    """(âncora, candidato, rotulo, ancora_concluida) → planilha do pool já preenchida."""
    return pd.DataFrame(
        {
            "id_par": [f"{a}-{c}" for a, c, _, _ in linhas],
            "id_ancora": [a for a, _, _, _ in linhas],
            "descricao_ancora": "TEXTO DA ANCORA",
            "und_val_ancora": "1.0",
            "und_med_ancora": "KG",
            "id_candidato": [c for _, c, _, _ in linhas],
            "descricao_candidato": "TEXTO DO CANDIDATO",
            "und_val_candidato": "1.0",
            "und_med_candidato": "KG",
            "tipo_par": "produto_produto",
            "origem": "amostra_cega",
            "rotulo": [r for _, _, r, _ in linhas],
            "ancora_concluida": [x for _, _, _, x in linhas],
            "observacao": "",
            "timestamp_anotacao": "",
        }
    )[COLUNAS_PLANILHA_POOL]


def _pool_de(planilha: pd.DataFrame) -> pd.DataFrame:
    return planilha[["id_ancora", "id_candidato"]].rename(columns={"id_ancora": "id_produto"})


LINHAS_ANOTADAS = [
    ("A1", "X", "match", "sim"),
    ("A1", "Y", "", "sim"),  # vazio em âncora concluída é não-match
    ("A1", "Z", "incerto", "sim"),
    ("A2", "W", "", "sim"),
    ("A3", "X", "", ""),  # âncora ainda não concluída
    ("A3", "V", "match", ""),
]


def test_anotacao_valida_nao_levanta_erro():
    planilha = _planilha_anotada(LINHAS_ANOTADAS)

    assert construcao.validar_anotacao_pool(planilha, _pool_de(planilha)) is None


def test_anotacao_aceita_espacos_nas_pontas_do_rotulo_e_da_flag():
    planilha = _planilha_anotada([("A1", "X", " match ", " sim "), ("A1", "Y", "", " sim ")])

    construcao.validar_anotacao_pool(planilha, _pool_de(planilha))


def test_ancora_nao_concluida_e_ignorada_mesmo_sem_nenhum_rotulo():
    planilha = _planilha_anotada([("A1", "X", "", ""), ("A1", "Y", "", ""), ("A2", "W", "", "sim")])

    construcao.validar_anotacao_pool(planilha, _pool_de(planilha))


@pytest.mark.parametrize("rotulo", ["talvez", "Match", "nao_match", "sim", "1"])
def test_rotulo_fora_do_dominio_levanta_erro_com_o_id_do_par(rotulo):
    planilha = _planilha_anotada([("A1", "X", rotulo, "sim"), ("A1", "Y", "", "sim")])

    with pytest.raises(ValueError, match=r"rotulo.*A1-X"):
        construcao.validar_anotacao_pool(planilha, _pool_de(planilha))


def test_rotulo_fora_do_dominio_e_erro_mesmo_em_ancora_nao_concluida():
    planilha = _planilha_anotada([("A1", "X", "talvez", ""), ("A1", "Y", "", "")])

    with pytest.raises(ValueError, match="rotulo"):
        construcao.validar_anotacao_pool(planilha, _pool_de(planilha))


@pytest.mark.parametrize("flag", ["x", "SIM", "nao", "1"])
def test_flag_de_ancora_concluida_fora_do_dominio_levanta_erro(flag):
    planilha = _planilha_anotada([("A1", "X", "", flag), ("A1", "Y", "", flag)])

    with pytest.raises(ValueError, match="ancora_concluida"):
        construcao.validar_anotacao_pool(planilha, _pool_de(planilha))


def test_flag_mista_dentro_de_uma_ancora_levanta_erro_com_o_id_da_ancora():
    planilha = _planilha_anotada(
        [("A1", "X", "", "sim"), ("A1", "Y", "", ""), ("A2", "W", "", "sim")]
    )

    with pytest.raises(ValueError, match=r"ancora_concluida.*A1"):
        construcao.validar_anotacao_pool(planilha, _pool_de(planilha))


def test_par_fora_do_pool_levanta_erro_com_o_id():
    planilha = _planilha_anotada([("A1", "X", "", "sim"), ("A1", "INTRUSO", "", "sim")])
    pool = _pool_de(planilha.iloc[:1])

    with pytest.raises(ValueError, match=r"fora do pool.*INTRUSO"):
        construcao.validar_anotacao_pool(planilha, pool)


def test_linha_apagada_da_planilha_levanta_erro_em_vez_de_virar_nao_match():
    completa = _planilha_anotada(LINHAS_ANOTADAS)
    sem_uma_linha = completa.drop(index=1)

    with pytest.raises(ValueError, match=r"faltam.*A1-Y"):
        construcao.validar_anotacao_pool(sem_uma_linha, _pool_de(completa))


def test_ancora_inteira_apagada_da_planilha_levanta_erro():
    completa = _planilha_anotada(LINHAS_ANOTADAS)
    sem_a2 = completa[completa["id_ancora"] != "A2"]

    with pytest.raises(ValueError, match=r"faltam.*A2-W"):
        construcao.validar_anotacao_pool(sem_a2, _pool_de(completa))


def test_id_par_duplicado_levanta_erro():
    planilha = _planilha_anotada([("A1", "X", "", "sim"), ("A1", "Y", "", "sim")])
    duplicada = pd.concat([planilha, planilha.iloc[:1]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicado"):
        construcao.validar_anotacao_pool(duplicada, _pool_de(planilha))


def test_planilha_vazia_levanta_erro():
    planilha = _planilha_anotada(LINHAS_ANOTADAS).iloc[0:0]

    with pytest.raises(ValueError, match="vazia"):
        construcao.validar_anotacao_pool(planilha, _pool_de(planilha))


def test_coluna_faltando_levanta_erro_com_o_nome_da_coluna():
    planilha = _planilha_anotada(LINHAS_ANOTADAS)

    with pytest.raises(ValueError, match=r"colunas.*rotulo"):
        construcao.validar_anotacao_pool(planilha.drop(columns=["rotulo"]), _pool_de(planilha))


@pytest.mark.parametrize(
    "coluna", ["codg_item", "desc_ref", "match_score", "metodo", "rank", "score"]
)
def test_coluna_proibida_na_planilha_levanta_erro(coluna):
    planilha = _planilha_anotada(LINHAS_ANOTADAS)
    com_proibida = planilha.assign(**{coluna: "x"})

    with pytest.raises(ValueError, match=rf"proibid.*{coluna}"):
        construcao.validar_anotacao_pool(com_proibida, _pool_de(planilha))


# ── T7: resumir_ancoras_pool, calcular_recall_pxp e a tabela .tex ─────────────
# Cenário: A1 e A2 têm positivo; A3 concluída sem positivo; A4 sem candidato no pool (sem linha);
# A5 não concluída (o `match` dela não conta). Há 3 pares positivos e 1 par incerto.

ANCORAS_SORTEADAS = ["A1", "A2", "A3", "A4", "A5"]
LINHAS_RECALL = [
    ("A1", "X", "match", "sim"),
    ("A1", "Y", "", "sim"),
    ("A1", "Z", "incerto", "sim"),
    ("A2", "W", "match", "sim"),
    ("A2", "V", "match", "sim"),
    ("A3", "U", "", "sim"),
    ("A5", "T", "match", ""),
]
COLUNAS_RECALL_PXP = [
    "metodo",
    "k",
    "recall",
    "n_positivos",
    "n_acertos",
    "acerto_ancora",
    "n_ancoras_com_positivo",
    "n_ancoras_acerto",
    "n_ancoras_sorteadas",
    "n_ancoras_concluidas",
    "n_ancoras_sem_positivo",
    "n_ancoras_nao_concluidas",
    "n_pares_incerto",
]


def _ranking_pxp(linhas: list[tuple[str, str, int]], metodo: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id_produto": [a for a, _, _ in linhas],
            "id_candidato": [c for _, c, _ in linhas],
            "metodo": metodo,
            "rank": [r for _, _, r in linhas],
            "score": [1.0 / r for _, _, r in linhas],
        }
    )


@pytest.fixture
def rankings_recall() -> pd.DataFrame:
    tfidf = _ranking_pxp(
        [("A1", "Y", 1), ("A1", "X", 3), ("A2", "W", 1), ("A2", "V", 30), ("A5", "T", 1)], "tfidf"
    )
    bm25 = _ranking_pxp([("A1", "X", 1), ("A2", "W", 2), ("A9", "Q", 1)], "bm25")  # V nunca aparece
    return pd.concat([tfidf, bm25], ignore_index=True)


def _recall(rankings, ks=(1, 5, 50, 100), metodos=None, linhas=LINHAS_RECALL):
    return construcao.calcular_recall_pxp(
        rankings, _planilha_anotada(linhas), ANCORAS_SORTEADAS, list(ks), metodos
    )


def _linha(recall: pd.DataFrame, metodo: str, k: int) -> pd.Series:
    return recall[(recall["metodo"] == metodo) & (recall["k"] == k)].iloc[0]


def test_resumo_das_ancoras_conta_candidatos_matches_e_incertos():
    resumo = construcao.resumir_ancoras_pool(_planilha_anotada(LINHAS_RECALL), ANCORAS_SORTEADAS)

    por_ancora = resumo.set_index("id_ancora")
    assert list(resumo["id_ancora"]) == ANCORAS_SORTEADAS
    assert por_ancora.loc["A1", ["n_candidatos", "n_match", "n_incerto"]].tolist() == [3, 1, 1]
    assert por_ancora.loc["A2", ["n_candidatos", "n_match", "n_incerto"]].tolist() == [2, 2, 0]
    assert por_ancora.loc["A3", ["n_candidatos", "n_match", "n_incerto"]].tolist() == [1, 0, 0]


def test_resumo_ancora_sem_candidato_conta_como_concluida_sem_positivo():
    resumo = construcao.resumir_ancoras_pool(
        _planilha_anotada(LINHAS_RECALL), ANCORAS_SORTEADAS
    ).set_index("id_ancora")

    assert bool(resumo.loc["A4", "concluida"]) is True
    assert resumo.loc["A4", ["n_candidatos", "n_match"]].tolist() == [0, 0]
    assert bool(resumo.loc["A5", "concluida"]) is False
    assert bool(resumo.loc["A1", "concluida"]) is True


def test_resumo_com_ancora_fora_dos_sorteados_levanta_erro_com_o_id():
    with pytest.raises(ValueError, match="A5"):
        construcao.resumir_ancoras_pool(_planilha_anotada(LINHAS_RECALL), ["A1", "A2", "A3", "A4"])


def test_recall_tem_uma_linha_por_metodo_e_k_com_as_colunas_do_contrato(rankings_recall):
    recall = _recall(rankings_recall)

    assert list(recall.columns) == COLUNAS_RECALL_PXP
    assert len(recall) == 2 * 4
    assert set(recall["metodo"]) == {"tfidf", "bm25"}


def test_recall_por_par_no_tfidf(rankings_recall):
    recall = _recall(rankings_recall)

    # positivos: A1-X (rank 3), A2-W (rank 1), A2-V (rank 30) → 3 pares
    assert _linha(recall, "tfidf", 1)["recall"] == pytest.approx(1 / 3)
    assert _linha(recall, "tfidf", 5)["recall"] == pytest.approx(2 / 3)
    assert _linha(recall, "tfidf", 50)["recall"] == pytest.approx(1.0)
    assert _linha(recall, "tfidf", 5)[["n_positivos", "n_acertos"]].tolist() == [3, 2]


def test_positivo_que_o_metodo_nunca_devolveu_conta_como_perda(rankings_recall):
    recall = _recall(rankings_recall)

    assert _linha(recall, "bm25", 1)["recall"] == pytest.approx(1 / 3)  # só A1-X
    assert _linha(recall, "bm25", 5)["recall"] == pytest.approx(2 / 3)  # + A2-W
    assert _linha(recall, "bm25", 100)["recall"] == pytest.approx(2 / 3)  # A2-V ausente


def test_acerto_por_ancora_exige_ao_menos_um_positivo_no_topo_k(rankings_recall):
    recall = _recall(rankings_recall)

    assert _linha(recall, "tfidf", 1)["acerto_ancora"] == pytest.approx(1 / 2)  # só A2
    assert _linha(recall, "tfidf", 5)["acerto_ancora"] == pytest.approx(1.0)
    assert _linha(recall, "bm25", 1)["acerto_ancora"] == pytest.approx(1 / 2)  # só A1
    assert _linha(recall, "tfidf", 1)[["n_ancoras_com_positivo", "n_ancoras_acerto"]].tolist() == [
        2,
        1,
    ]


def test_contagens_a_parte_nao_entram_no_denominador(rankings_recall):
    linha = _linha(_recall(rankings_recall), "tfidf", 5)

    assert linha["n_ancoras_sorteadas"] == 5
    assert linha["n_ancoras_concluidas"] == 4  # A1, A2, A3 e A4 (sem candidato)
    assert linha["n_ancoras_sem_positivo"] == 2  # A3 e A4
    assert linha["n_ancoras_nao_concluidas"] == 1  # A5
    assert linha["n_pares_incerto"] == 1  # A1-Z


def test_match_de_ancora_nao_concluida_nao_conta_como_positivo(rankings_recall):
    linha = _linha(_recall(rankings_recall), "tfidf", 1)

    assert linha["n_positivos"] == 3  # A5-T tem rank 1 no tfidf, mas A5 não foi concluída


def test_par_incerto_nao_conta_como_positivo_nem_como_perda(rankings_recall):
    sem_incerto = [(a, c, r if r != "incerto" else "", f) for a, c, r, f in LINHAS_RECALL]

    com = _linha(_recall(rankings_recall), "tfidf", 5)
    sem = _linha(_recall(rankings_recall, linhas=sem_incerto), "tfidf", 5)

    assert com["recall"] == pytest.approx(sem["recall"])
    assert (com["n_positivos"], sem["n_positivos"]) == (3, 3)


def test_ranking_de_outros_ancoras_e_de_candidatos_nao_anotados_e_ignorado(rankings_recall):
    # A9 está no ranking do bm25 mas não foi sorteada; a conta não pode mudar
    sem_a9 = rankings_recall[rankings_recall["id_produto"] != "A9"]

    pd.testing.assert_frame_equal(_recall(rankings_recall), _recall(sem_a9))


def test_sem_nenhum_positivo_o_recall_e_nan_e_nao_levanta_erro(rankings_recall):
    sem_positivos = [(a, c, "" if r == "match" else r, f) for a, c, r, f in LINHAS_RECALL]

    linha = _linha(_recall(rankings_recall, linhas=sem_positivos), "tfidf", 5)

    assert pd.isna(linha["recall"])
    assert pd.isna(linha["acerto_ancora"])
    assert linha["n_positivos"] == 0


def test_metodos_pedidos_restringem_a_saida(rankings_recall):
    recall = _recall(rankings_recall, metodos=["bm25"])

    assert set(recall["metodo"]) == {"bm25"}


def test_recall_com_ancora_fora_dos_sorteados_levanta_erro(rankings_recall):
    with pytest.raises(ValueError, match="A5"):
        construcao.calcular_recall_pxp(
            rankings_recall, _planilha_anotada(LINHAS_RECALL), ["A1", "A2", "A3", "A4"], [1, 5]
        )


def test_tabela_tex_traz_os_numeros_do_csv_e_a_nota_de_limite_superior(rankings_recall):
    tex = construcao.montar_tabela_recall_pxp_tex(_recall(rankings_recall, ks=(1, 5, 50, 100)))

    assert "Gerado automaticamente por scripts/03_construcao_dataset.py" in tex
    assert "\\label{tab:recall-blocagem-pxp}" in tex
    assert "TF-IDF" in tex
    assert "BM25" in tex
    assert "33,3\\%" in tex and "66,7\\%" in tex and "100,0\\%" in tex
    assert "2 âncoras com positivo" in tex
    assert "3 pares positivos" in tex
    assert "limite superior" in tex
    for k in (1, 5, 50, 100):
        assert f"\n{k} &" in tex


# ── T10 (config): faixas, alocação por estrato, mínimo de score do tamanho divergente, 80/20 ──

CONFIG_TESTE = {
    "faixas": [0.0, 0.5, 0.7, 0.9, 1.0],
    "score_minimo_digito_divergente": 0.5,
    "n_por_estrato": {
        "texto_identico": 12,
        "digito_divergente": 60,
        "[0.90, 1.00]": 100,
        "[0.70, 0.90)": 100,
        "[0.50, 0.70)": 20,
        "[0.00, 0.50)": 8,
    },
}


def test_config_pxp_sem_as_chaves_do_teste_devolve_none(tmp_path):
    cfg = construcao.carregar_config_pxp(_gravar_config(tmp_path))

    assert cfg["faixas"] is None
    assert cfg["n_por_estrato"] is None
    assert cfg["score_minimo_digito_divergente"] is None


def test_config_pxp_aceita_a_alocacao_do_teste(tmp_path):
    cfg = construcao.carregar_config_pxp(_gravar_config(tmp_path, **CONFIG_TESTE))

    assert cfg["faixas"] == [0.0, 0.5, 0.7, 0.9, 1.0]
    assert cfg["n_por_estrato"]["texto_identico"] == 12
    assert cfg["score_minimo_digito_divergente"] == 0.5


def test_config_pxp_versionada_traz_o_cenario_c_com_300_pares_e_20_por_cento_de_digito():
    cfg = construcao.carregar_config_pxp(Path(_ROOT) / "configs" / "blocagem_pxp.yaml")

    assert cfg["n_por_estrato"] == CONFIG_TESTE["n_por_estrato"]
    assert sum(cfg["n_por_estrato"].values()) == cfg["n_teste"] == 300
    assert cfg["n_por_estrato"]["digito_divergente"] / cfg["n_teste"] == pytest.approx(
        cfg["fracao_digito_divergente"]
    )
    assert "proporcao_treino" not in cfg  # a partição é por componente, sem proporção


@pytest.mark.parametrize(
    ("alteracoes", "trecho"),
    [
        ({"faixas": [0.1, 0.5, 1.0]}, "faixas"),
        ({"faixas": [0.0, 0.9, 0.5, 1.0]}, "faixas"),
        (
            {"n_por_estrato": {**CONFIG_TESTE["n_por_estrato"], "texto_identico": 13}},
            "n_teste",
        ),
        (
            {
                "n_por_estrato": {
                    **CONFIG_TESTE["n_por_estrato"],
                    "digito_divergente": 50,
                    "texto_identico": 22,
                }
            },
            "digito_divergente",
        ),
        (
            {
                "n_por_estrato": {
                    k: v for k, v in CONFIG_TESTE["n_por_estrato"].items() if k != "[0.00, 0.50)"
                }
            },
            "estratos",
        ),
        ({"n_por_estrato": {**CONFIG_TESTE["n_por_estrato"], "outro": 0}}, "estratos"),
        ({"score_minimo_digito_divergente": 1.5}, "score_minimo_digito_divergente"),
    ],
    ids=[
        "faixas_nao_comecam_em_0",
        "faixas_nao_crescentes",
        "soma_diferente_de_n_teste",
        "fracao_de_digito_inconsistente",
        "estrato_faltando",
        "estrato_desconhecido",
        "score_minimo_fora",
    ],
)
def test_config_pxp_rejeita_a_alocacao_do_teste_invalida(tmp_path, alteracoes, trecho):
    caminho = _gravar_config(tmp_path, **{**CONFIG_TESTE, **alteracoes})

    with pytest.raises(ValueError, match=trecho):
        construcao.carregar_config_pxp(caminho)


def test_config_pxp_rejeita_a_chave_obsoleta_proporcao_treino(tmp_path):
    """Decisão de 2026-11-13: validação = pool, treino = o restante; não há proporção a ajustar.

    Aceitar a chave em silêncio deixaria alguém achar que 0,8 vale para alguma coisa.
    """
    with pytest.raises(ValueError, match="proporcao_treino"):
        construcao.carregar_config_pxp(_gravar_config(tmp_path, proporcao_treino=0.8))


# ── b2_cosseno_minimo: corte de cosseno dos pares do treino que o autor anota (opção B2) ──────


def test_config_pxp_sem_b2_cosseno_minimo_devolve_none(tmp_path):
    cfg = construcao.carregar_config_pxp(_gravar_config(tmp_path))

    assert cfg["b2_cosseno_minimo"] is None


def test_config_pxp_aceita_b2_cosseno_minimo(tmp_path):
    cfg = construcao.carregar_config_pxp(_gravar_config(tmp_path, b2_cosseno_minimo=0.5))

    assert cfg["b2_cosseno_minimo"] == 0.5


@pytest.mark.parametrize("valor", [0.0, -0.1, 1.5])
def test_config_pxp_rejeita_b2_cosseno_minimo_fora_de_zero_a_um(tmp_path, valor):
    with pytest.raises(ValueError, match="b2_cosseno_minimo"):
        construcao.carregar_config_pxp(_gravar_config(tmp_path, b2_cosseno_minimo=valor))


def test_config_pxp_versionada_traz_o_corte_de_cosseno_da_b2():
    cfg = construcao.carregar_config_pxp(Path(_ROOT) / "configs" / "blocagem_pxp.yaml")

    assert cfg["b2_cosseno_minimo"] == 0.5


# ── n_reteste e seed_reteste: reteste do teste (ADR-0005; T10c; decisão do autor em 2026-11-16) ─


def test_config_pxp_sem_as_chaves_do_reteste_devolve_none(tmp_path):
    cfg = construcao.carregar_config_pxp(_gravar_config(tmp_path))

    assert cfg["n_reteste"] is None
    assert cfg["seed_reteste"] is None


def test_config_pxp_aceita_n_reteste_e_seed_reteste(tmp_path):
    cfg = construcao.carregar_config_pxp(_gravar_config(tmp_path, n_reteste=150, seed_reteste=43))

    assert cfg["n_reteste"] == 150
    assert cfg["seed_reteste"] == 43


@pytest.mark.parametrize(
    "alteracoes",
    [{"n_reteste": 150}, {"seed_reteste": 43}],
    ids=["so_n", "so_seed"],
)
def test_config_pxp_rejeita_so_uma_das_chaves_do_reteste(tmp_path, alteracoes):
    with pytest.raises(ValueError, match="n_reteste.*seed_reteste"):
        construcao.carregar_config_pxp(_gravar_config(tmp_path, **alteracoes))


@pytest.mark.parametrize("n", [0, -1, 149, 301])
def test_config_pxp_rejeita_n_reteste_fora_de_50_por_cento_a_100_por_cento_do_teste(tmp_path, n):
    with pytest.raises(ValueError, match="n_reteste"):
        construcao.carregar_config_pxp(_gravar_config(tmp_path, n_reteste=n, seed_reteste=43))


def test_config_pxp_versionada_traz_o_reteste_de_150_pares_com_seed_43():
    cfg = construcao.carregar_config_pxp(Path(_ROOT) / "configs" / "blocagem_pxp.yaml")

    assert cfg["n_reteste"] == 150
    assert cfg["seed_reteste"] == 43
    assert cfg["n_reteste"] >= 0.5 * cfg["n_teste"]
