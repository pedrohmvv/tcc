"""
test_transformacao_reteste_pxp.py — Camada 2: reteste do teste produto × produto, em memória
(ADR-0005; protocolo §4; spec 001 CA "Kappa ≥ 50% do teste"; tasks-1b T10c).

O reteste mede a consistência intra-anotador: ≥ 50% dos pares do teste reanotados às cegas,
≥ 7 dias depois da primeira passada. Estes testes fixam o contrato (decisões do autor em
2026-11-16: 150 pares, sorteio estratificado, `incerto` entra no sorteio, Kappa de 3 classes e
binário):

- o sorteio é estratificado pelo estrato do par e NÃO olha o rótulo da primeira passada;
- a planilha do reteste não traz rótulo, observação nem timestamp da primeira passada, vem em
  outra ordem e nunca sobrescreve um arquivo existente;
- o Kappa é calculado por tipo de par, em 3 classes e em versão binária (sem `incerto`);
- o intervalo mínimo de 7 dias é verificado, não suposto.

Os produtos e pares são sintéticos, escritos para o teste; nenhum rótulo é de dado real.
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

# 60 pares em 3 estratos de tamanhos diferentes, para a alocação proporcional não ser trivial.
TAMANHO_ESTRATO = {"[0.90, 1.00]": 30, "[0.70, 0.90)": 20, "digito_divergente": 10}
ROTULOS = ["match", "nao_match", "incerto", "nao_match"]


@pytest.fixture
def cenario() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(pares, universo): 60 pares, 120 produtos, escritos em blocos de estrato."""
    produtos, pares = [], []
    n = 0
    for estrato, tamanho in TAMANHO_ESTRATO.items():
        for _ in range(tamanho):
            a, b = f"a{n:03d}", f"b{n:03d}"
            produtos.append((a, f"t{a}", f"SUCO {n} 1L", "X", 1.0, "L"))
            produtos.append((b, f"t{b}", f"SUCO {n}X 1L", "Y", 1.0, "L"))
            pares.append((a, b, estrato, 0.05))
            n += 1
    universo = pd.DataFrame(
        produtos, columns=["id_produto", "id_texto", "descricao", "loja", "und_val", "und_med"]
    )
    universo["texto_normalizado"] = universo["descricao"].str.lower()
    pares_df = pd.DataFrame(pares, columns=["id_a", "id_b", "estrato", "prob_inclusao"])
    return pares_df, universo


def _primeira_passada(cenario, rotulos: list[str] | None = None) -> pd.DataFrame:
    """Planilha do teste completa: rótulo, observação e timestamp preenchidos."""
    pares, universo = cenario
    planilha = construcao.montar_planilha_teste_pxp(pares, universo, 42)
    ciclo = rotulos or ROTULOS
    return planilha.assign(
        rotulo=[ciclo[i % len(ciclo)] for i in range(len(planilha))],
        observacao=[f"obs {i}" if i % 5 == 0 else "" for i in range(len(planilha))],
        timestamp_anotacao=[f"2026-11-16T10:{i % 60:02d}:00-03:00" for i in range(len(planilha))],
    )


def _estrato_por_par(cenario) -> pd.Series:
    pares, _ = cenario
    return pares.assign(
        id_par=[
            construcao._hash_curto(f"{a}|{b}")
            for a, b in zip(pares["id_a"], pares["id_b"], strict=True)
        ]
    ).set_index("id_par")["estrato"]


# ── sortear_pares_reteste ────────────────────────────────────────────────────


def test_sorteio_devolve_n_pares_unicos_que_existem_na_primeira_passada(cenario):
    pares, _ = cenario
    primeira = _primeira_passada(cenario)

    sorteio = construcao.sortear_pares_reteste(primeira, pares, n=31, seed=7)

    assert len(sorteio) == 31
    assert sorteio["id_par"].is_unique
    assert set(sorteio["id_par"]) <= set(primeira["id_par"])


def test_sorteio_e_proporcional_ao_tamanho_de_cada_estrato(cenario):
    """31 de 60: 15,5 / 10,33 / 5,17 → 16 / 10 / 5 (a sobra vai à maior parte fracionária)."""
    pares, _ = cenario
    primeira = _primeira_passada(cenario)
    estrato = _estrato_por_par(cenario)

    sorteio = construcao.sortear_pares_reteste(primeira, pares, n=31, seed=7)
    contagem = sorteio["id_par"].map(estrato).value_counts().to_dict()

    assert contagem == {"[0.90, 1.00]": 16, "[0.70, 0.90)": 10, "digito_divergente": 5}


def test_sorteio_de_exatamente_metade_da_exatamente_metade_de_cada_estrato(cenario):
    pares, _ = cenario
    primeira = _primeira_passada(cenario)
    estrato = _estrato_por_par(cenario)

    sorteio = construcao.sortear_pares_reteste(primeira, pares, n=30, seed=7)
    contagem = sorteio["id_par"].map(estrato).value_counts().to_dict()

    assert contagem == {"[0.90, 1.00]": 15, "[0.70, 0.90)": 10, "digito_divergente": 5}


def test_sorteio_e_deterministico_por_seed_e_muda_com_outra_seed(cenario):
    pares, _ = cenario
    primeira = _primeira_passada(cenario)

    um = construcao.sortear_pares_reteste(primeira, pares, n=31, seed=7)
    dois = construcao.sortear_pares_reteste(primeira, pares, n=31, seed=7)
    outro = construcao.sortear_pares_reteste(primeira, pares, n=31, seed=8)

    assert um.equals(dois)
    assert set(um["id_par"]) != set(outro["id_par"])


def test_sorteio_nao_olha_o_rotulo_da_primeira_passada(cenario):
    """Mudar todos os rótulos não pode mudar quais pares voltam (sem viés de seleção)."""
    pares, _ = cenario
    uma = _primeira_passada(cenario, ["match", "nao_match", "incerto", "nao_match"])
    outra = _primeira_passada(cenario, ["incerto", "incerto", "match", "nao_match", "match"])

    s1 = construcao.sortear_pares_reteste(uma, pares, n=31, seed=7)
    s2 = construcao.sortear_pares_reteste(outra, pares, n=31, seed=7)

    assert set(s1["id_par"]) == set(s2["id_par"])


def test_incerto_pode_ser_sorteado_e_com_n_total_todos_voltam(cenario):
    pares, _ = cenario
    primeira = _primeira_passada(cenario)
    incertos = set(primeira.loc[primeira["rotulo"] == "incerto", "id_par"])

    todos = construcao.sortear_pares_reteste(primeira, pares, n=len(primeira), seed=7)
    metade = construcao.sortear_pares_reteste(primeira, pares, n=30, seed=7)

    assert incertos <= set(todos["id_par"])
    assert incertos & set(metade["id_par"]), "nenhum incerto no reteste: sorteio os está excluindo"


def test_n_abaixo_de_50_por_cento_ou_acima_do_teste_falha(cenario):
    pares, _ = cenario
    primeira = _primeira_passada(cenario)

    with pytest.raises(ValueError, match="50%"):
        construcao.sortear_pares_reteste(primeira, pares, n=29, seed=7)
    with pytest.raises(ValueError, match="61"):
        construcao.sortear_pares_reteste(primeira, pares, n=61, seed=7)


def test_primeira_passada_incompleta_falha_nomeando_os_pares(cenario):
    pares, _ = cenario
    primeira = _primeira_passada(cenario)
    pendente = primeira.loc[3, "id_par"]
    primeira.loc[3, "rotulo"] = ""

    with pytest.raises(ValueError, match=pendente):
        construcao.sortear_pares_reteste(primeira, pares, n=31, seed=7)


def test_par_sem_estrato_falha_em_vez_de_cair_num_estrato_qualquer(cenario):
    pares, _ = cenario
    primeira = _primeira_passada(cenario)
    sem_um = pares.iloc[1:].reset_index(drop=True)

    with pytest.raises(ValueError, match="estrato"):
        construcao.sortear_pares_reteste(primeira, sem_um, n=31, seed=7)


# ── montar_planilha_reteste_pxp ──────────────────────────────────────────────


def _reteste(cenario, n: int = 31, seed_sorteio: int = 7, seed_ordem: int = 8) -> pd.DataFrame:
    pares, _ = cenario
    primeira = _primeira_passada(cenario)
    sorteio = construcao.sortear_pares_reteste(primeira, pares, n=n, seed=seed_sorteio)
    return construcao.montar_planilha_reteste_pxp(primeira, sorteio, seed=seed_ordem)


def test_planilha_do_reteste_tem_o_contrato_da_planilha_do_teste(cenario):
    primeira = _primeira_passada(cenario)
    planilha = _reteste(cenario)

    assert list(planilha.columns) == construcao.COLUNAS_PLANILHA_TESTE_PXP
    assert len(planilha) == 31
    assert planilha["id_par"].is_unique
    assert set(planilha["id_par"]) <= set(primeira["id_par"])


def test_planilha_do_reteste_e_cega_sem_rotulo_observacao_nem_timestamp(cenario):
    planilha = _reteste(cenario)

    for coluna in ["rotulo", "observacao", "timestamp_anotacao"]:
        assert (planilha[coluna].fillna("") == "").all(), coluna
    assert not {"estrato", "prob_inclusao", "score", "metodo", "rank"} & set(planilha.columns)


def test_planilha_do_reteste_nao_vaza_o_texto_da_observacao_da_primeira_passada(cenario):
    planilha = _reteste(cenario)

    assert not planilha.astype(str).apply(lambda c: c.str.contains("obs ")).any().any()


def test_planilha_do_reteste_marca_todas_as_linhas_como_reteste(cenario):
    planilha = _reteste(cenario)

    assert set(planilha["reteste"]) == {"sim"}


def test_texto_e_unidade_do_reteste_sao_os_mesmos_da_primeira_passada(cenario):
    primeira = _primeira_passada(cenario).set_index("id_par")
    planilha = _reteste(cenario).set_index("id_par")
    colunas = ["id_a", "descricao_a", "und_val_a", "und_med_a", "id_b", "descricao_b"]

    assert planilha[colunas].equals(primeira.loc[planilha.index, colunas])


def test_reteste_vem_em_ordem_diferente_da_primeira_passada_e_deterministica(cenario):
    primeira = _primeira_passada(cenario)
    planilha = _reteste(cenario)
    ordem_original = [i for i in primeira["id_par"] if i in set(planilha["id_par"])]

    assert list(planilha["id_par"]) != ordem_original
    assert _reteste(cenario).equals(planilha)
    assert not _reteste(cenario, seed_ordem=9).equals(planilha)


def test_reteste_nao_herda_a_ordem_por_estrato(cenario):
    estrato = _estrato_por_par(cenario)
    planilha = _reteste(cenario)
    sequencia = list(planilha["id_par"].map(estrato))

    trocas = sum(1 for x, y in zip(sequencia, sequencia[1:], strict=False) if x != y)
    assert trocas > 2 * len(TAMANHO_ESTRATO), f"ordem ainda em blocos ({trocas} trocas)"


def test_planilha_do_reteste_tem_nome_proprio_e_nunca_sobrescreve(cenario, tmp_path):
    planilha = _reteste(cenario)

    assert construcao.ARQUIVO_PLANILHA_RETESTE_PXP == "anotacoes_teste_pxp_reteste.csv"
    caminho = construcao.gravar_planilha_teste_pxp(
        planilha, tmp_path, construcao.ARQUIVO_PLANILHA_RETESTE_PXP
    )
    antes = caminho.read_bytes()

    with pytest.raises(FileExistsError):
        construcao.gravar_planilha_teste_pxp(
            planilha, tmp_path, construcao.ARQUIVO_PLANILHA_RETESTE_PXP
        )
    assert caminho.read_bytes() == antes


# ── calcular_kappa_reteste ───────────────────────────────────────────────────


def _passadas(r1: list[str], r2: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    ids = [f"p{i:02d}" for i in range(len(r1))]
    primeira = pd.DataFrame({"id_par": ids, "rotulo": r1})
    reteste = pd.DataFrame({"id_par": ids, "rotulo": r2})
    return primeira, reteste


def test_kappa_binario_com_valor_conhecido():
    """po = 0,8; pe = 0,5 → kappa = 0,6."""
    r1 = ["match"] * 5 + ["nao_match"] * 5
    r2 = ["match"] * 4 + ["nao_match"] + ["nao_match"] * 4 + ["match"]
    primeira, reteste = _passadas(r1, r2)

    r = construcao.calcular_kappa_reteste(primeira, reteste)

    assert r["kappa_3_classes"] == pytest.approx(0.6)
    assert r["kappa_binario"] == pytest.approx(0.6)
    assert r["n_pares"] == 10


def test_kappa_de_3_classes_e_o_binario_sem_incerto_sao_calculados_separados():
    """3 classes: po = 4/6, pe = 12/36 → 0,5. Binário: os 3 pares sem incerto concordam → 1,0."""
    r1 = ["match", "match", "nao_match", "nao_match", "incerto", "incerto"]
    r2 = ["match", "match", "nao_match", "incerto", "incerto", "match"]
    primeira, reteste = _passadas(r1, r2)

    r = construcao.calcular_kappa_reteste(primeira, reteste)

    assert r["kappa_3_classes"] == pytest.approx(0.5)
    assert r["kappa_binario"] == pytest.approx(1.0)
    assert r["n_pares"] == 6
    assert r["n_binario"] == 3


def test_kappa_com_concordancia_total_e_um():
    r = ["match", "nao_match", "incerto", "match", "nao_match", "incerto"]
    primeira, reteste = _passadas(r, list(r))

    assert construcao.calcular_kappa_reteste(primeira, reteste)["kappa_3_classes"] == 1.0


def test_kappa_so_com_um_rotulo_nas_duas_passadas_falha_em_vez_de_dar_nan():
    primeira, reteste = _passadas(["match"] * 5, ["match"] * 5)

    with pytest.raises(ValueError, match="indefinido"):
        construcao.calcular_kappa_reteste(primeira, reteste)


def test_kappa_so_considera_os_pares_que_voltaram_no_reteste():
    r1 = ["match", "nao_match", "match", "nao_match", "incerto", "match"]
    primeira, _ = _passadas(r1, r1)
    reteste = primeira.iloc[[0, 1, 2, 3]].assign(rotulo=["match", "nao_match", "match", "match"])

    r = construcao.calcular_kappa_reteste(primeira, reteste)

    assert r["n_pares"] == 4


def test_reteste_com_par_fora_da_primeira_passada_ou_sem_rotulo_falha():
    primeira, reteste = _passadas(["match", "nao_match"] * 3, ["match", "nao_match"] * 3)

    estranho = reteste.assign(id_par=["p00", "p01", "p02", "p03", "p04", "zzz"])
    with pytest.raises(ValueError, match="zzz"):
        construcao.calcular_kappa_reteste(primeira, estranho)

    vazio = reteste.assign(rotulo=["match", "nao_match", "match", "nao_match", "match", ""])
    with pytest.raises(ValueError, match="p05"):
        construcao.calcular_kappa_reteste(primeira, vazio)


# ── verificar_intervalo_reteste ──────────────────────────────────────────────


def _com_timestamp(ts: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"id_par": [f"p{i}" for i in range(len(ts))], "timestamp_anotacao": ts})


def test_intervalo_de_7_dias_completos_e_aceito():
    primeira = _com_timestamp(["2026-11-15T19:03:14-03:00", "2026-11-16T11:30:50-03:00"])
    reteste = _com_timestamp(["2026-11-23T11:30:50-03:00", "2026-11-23T12:00:00-03:00"])

    construcao.verificar_intervalo_reteste(primeira, reteste, dias=7)


def test_intervalo_menor_que_7_dias_falha_contando_do_fim_da_primeira_passada():
    primeira = _com_timestamp(["2026-11-15T19:03:14-03:00", "2026-11-16T11:30:50-03:00"])
    reteste = _com_timestamp(["2026-11-23T11:30:49-03:00", "2026-11-23T12:00:00-03:00"])

    with pytest.raises(ValueError, match="7 dias"):
        construcao.verificar_intervalo_reteste(primeira, reteste, dias=7)


def test_intervalo_sem_timestamp_falha_em_vez_de_assumir():
    primeira = _com_timestamp(["2026-11-16T11:30:50-03:00", ""])
    reteste = _com_timestamp(["2026-11-23T11:30:50-03:00"])

    with pytest.raises(ValueError, match="timestamp"):
        construcao.verificar_intervalo_reteste(primeira, reteste, dias=7)


# ── calcular_intervalo_reteste (desvio declarado do ADR-0005, decisão do autor em 2026-11-16) ──


def test_intervalo_e_medido_do_fim_da_primeira_passada_ao_inicio_do_reteste():
    primeira = _com_timestamp(["2026-11-15T19:03:14-03:00", "2026-11-16T11:30:50-03:00"])
    reteste = _com_timestamp(["2026-11-16T12:09:50-03:00", "2026-11-16T12:18:50-03:00"])

    intervalo = construcao.calcular_intervalo_reteste(primeira, reteste)

    assert intervalo.total_seconds() / 3600 == pytest.approx(0.65)


def test_intervalo_sem_timestamp_falha_tambem_no_calculo():
    primeira = _com_timestamp(["2026-11-16T11:30:50-03:00", ""])
    reteste = _com_timestamp(["2026-11-23T11:30:50-03:00"])

    with pytest.raises(ValueError, match="timestamp"):
        construcao.calcular_intervalo_reteste(primeira, reteste)
