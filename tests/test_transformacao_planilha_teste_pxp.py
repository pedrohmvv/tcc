"""
test_transformacao_planilha_teste_pxp.py — Camada 2: planilha de anotação do teste produto ×
produto, em memória (spec 001, RF1 "1b", CA-1b-05; plano 1.4.1 e 1.4.6; tasks-1b T10b).

A planilha é onde o autor anota os 300 pares do teste às cegas. Estes testes fixam o contrato:
nada que revele estrato, score ou método (nem a ordem das linhas), rótulo explícito nos dois
sentidos (`match`, `nao_match`, `incerto`; vazio é "ainda não anotado") e validação só de forma.
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

COLUNAS_ESPERADAS = [
    "id_par",
    "id_a",
    "descricao_a",
    "und_val_a",
    "und_med_a",
    "id_b",
    "descricao_b",
    "und_val_b",
    "und_med_b",
    "tipo_par",
    "origem",
    "rotulo",
    "observacao",
    "timestamp_anotacao",
    "reteste",
]
PROIBIDAS = ["estrato", "prob_inclusao", "score", "metodo", "rank", "codg_item", "desc_ref"]
ESTRATOS = ["texto_identico", "digito_divergente", "[0.90, 1.00]", "[0.70, 0.90)"]
N_POR_ESTRATO = 10


@pytest.fixture
def cenario() -> tuple[pd.DataFrame, pd.DataFrame]:
    """40 pares em 4 estratos, escritos em blocos (um estrato após o outro), 80 produtos."""
    produtos, pares = [], []
    for e, estrato in enumerate(ESTRATOS):
        for i in range(N_POR_ESTRATO):
            n = e * N_POR_ESTRATO + i
            a, b = f"a{n:03d}", f"b{n:03d}"
            produtos.append((a, f"t{a}", f"SUCO {n} 1L", "X", 1.0, "L"))
            produtos.append((b, f"t{b}", f"SUCO {n}X 1L", "Y", 1.0, "L"))
            pares.append((a, b, estrato, 0.05))
    universo = pd.DataFrame(
        produtos,
        columns=["id_produto", "id_texto", "descricao", "loja", "und_val", "und_med"],
    )
    universo["texto_normalizado"] = universo["descricao"].str.lower()
    pares_df = pd.DataFrame(pares, columns=["id_a", "id_b", "estrato", "prob_inclusao"])
    return pares_df, universo


def _montar(cenario, seed: int = 42) -> pd.DataFrame:
    pares, universo = cenario
    return construcao.montar_planilha_teste_pxp(pares, universo, seed)


def _anotada(planilha: pd.DataFrame, rotulo: str = "nao_match") -> pd.DataFrame:
    return planilha.assign(rotulo=rotulo)


# ── montar_planilha_teste_pxp ────────────────────────────────────────────────


def test_planilha_tem_as_colunas_do_contrato_e_uma_linha_por_par(cenario):
    planilha = _montar(cenario)

    assert list(planilha.columns) == COLUNAS_ESPERADAS
    assert len(planilha) == len(cenario[0])
    assert planilha["id_par"].is_unique


def test_planilha_nao_revela_estrato_score_metodo_nem_colunas_do_matcher_alta(cenario):
    planilha = _montar(cenario)

    assert not set(PROIBIDAS) & set(planilha.columns)


def test_planilha_sai_sem_rotulo_e_com_tipo_e_origem_fixos(cenario):
    planilha = _montar(cenario)

    assert set(planilha["tipo_par"]) == {"produto_produto"}
    assert set(planilha["origem"]) == {"teste"}
    for coluna in ["rotulo", "observacao", "timestamp_anotacao", "reteste"]:
        assert (planilha[coluna].fillna("") == "").all(), coluna


def test_planilha_traz_o_texto_e_a_unidade_de_cada_lado(cenario):
    pares, universo = cenario
    planilha = _montar(cenario)
    descricao = universo.set_index("id_produto")["descricao"]

    assert (planilha["descricao_a"] == planilha["id_a"].map(descricao)).all()
    assert (planilha["descricao_b"] == planilha["id_b"].map(descricao)).all()
    assert set(planilha["und_med_a"]) == {"L"}


def test_a_ordem_das_linhas_nao_segue_o_estrato(cenario):
    """O sorteio escreve os estratos em blocos; a planilha não pode herdar esse padrão."""
    pares, _ = cenario
    planilha = _montar(cenario)
    estrato = pares.set_index(["id_a", "id_b"])["estrato"]
    sequencia = [estrato[(a, b)] for a, b in zip(planilha["id_a"], planilha["id_b"], strict=True)]

    trocas = sum(1 for x, y in zip(sequencia, sequencia[1:], strict=False) if x != y)
    assert trocas > 2 * len(ESTRATOS), f"ordem ainda em blocos de estrato ({trocas} trocas)"


def test_mesma_seed_da_a_mesma_planilha_e_seed_diferente_da_outra_ordem(cenario):
    assert _montar(cenario, 7).equals(_montar(cenario, 7))
    assert list(_montar(cenario, 7)["id_par"]) != list(_montar(cenario, 8)["id_par"])


def test_ordem_nao_depende_da_ordem_das_linhas_de_entrada(cenario):
    pares, universo = cenario
    embaralhado = pares.sample(frac=1, random_state=1).reset_index(drop=True)

    esperado = construcao.montar_planilha_teste_pxp(pares, universo, 42)
    obtido = construcao.montar_planilha_teste_pxp(embaralhado, universo, 42)

    assert esperado.equals(obtido)


def test_id_par_e_estavel_e_nao_depende_da_posicao(cenario):
    a = _montar(cenario, 1).set_index(["id_a", "id_b"])["id_par"]
    b = _montar(cenario, 2).set_index(["id_a", "id_b"])["id_par"]

    assert a.sort_index().equals(b.sort_index())


def test_produto_fora_do_universo_levanta_erro_com_o_id(cenario):
    pares, universo = cenario
    sem_um = universo[universo["id_produto"] != "a000"]

    with pytest.raises(ValueError, match="a000"):
        construcao.montar_planilha_teste_pxp(pares, sem_um, 42)


# ── validar_anotacao_teste_pxp ───────────────────────────────────────────────


def _validar(planilha, cenario, **kwargs):
    construcao.validar_anotacao_teste_pxp(planilha, cenario[0], **kwargs)


def test_planilha_recem_montada_e_valida_enquanto_incompleta(cenario):
    _validar(_montar(cenario), cenario)


@pytest.mark.parametrize("rotulo", ["match", "nao_match", "incerto"])
def test_rotulos_do_dominio_sao_aceitos(cenario, rotulo):
    _validar(_anotada(_montar(cenario), rotulo), cenario, completa=True)


def test_rotulo_fora_do_dominio_levanta_erro_com_o_id_do_par(cenario):
    planilha = _montar(cenario)
    planilha.loc[3, "rotulo"] = "talvez"

    with pytest.raises(ValueError, match=planilha.loc[3, "id_par"]):
        _validar(planilha, cenario)


def test_rotulo_do_pool_sem_o_underscore_nao_e_aceito(cenario):
    """`não-match` vazio vale no pool; no teste o autor decide cada par, nos dois sentidos."""
    planilha = _montar(cenario)
    planilha.loc[0, "rotulo"] = "nao-match"

    with pytest.raises(ValueError, match="rotulo"):
        _validar(planilha, cenario)


def test_exigir_completa_falha_com_rotulo_vazio_e_nomeia_o_par(cenario):
    planilha = _anotada(_montar(cenario))
    planilha.loc[5, "rotulo"] = ""

    with pytest.raises(ValueError, match=planilha.loc[5, "id_par"]):
        _validar(planilha, cenario, completa=True)


def test_par_apagado_levanta_erro(cenario):
    planilha = _montar(cenario).iloc[1:]

    with pytest.raises(ValueError, match="faltam"):
        _validar(planilha, cenario)


def test_par_que_nao_e_do_teste_levanta_erro(cenario):
    planilha = _montar(cenario)
    planilha.loc[0, "id_b"] = "zzz"

    with pytest.raises(ValueError, match="fora do teste"):
        _validar(planilha, cenario)


def test_id_par_duplicado_levanta_erro(cenario):
    planilha = _montar(cenario)
    planilha.loc[1, "id_par"] = planilha.loc[0, "id_par"]

    with pytest.raises(ValueError, match="duplicado"):
        _validar(planilha, cenario)


@pytest.mark.parametrize("coluna", ["estrato", "score", "codg_item"])
def test_coluna_proibida_levanta_erro(cenario, coluna):
    planilha = _montar(cenario).assign(**{coluna: 1})

    with pytest.raises(ValueError, match=coluna):
        _validar(planilha, cenario)


def test_coluna_ausente_levanta_erro(cenario):
    planilha = _montar(cenario).drop(columns=["rotulo"])

    with pytest.raises(ValueError, match="rotulo"):
        _validar(planilha, cenario)


def test_planilha_vazia_levanta_erro(cenario):
    with pytest.raises(ValueError, match="vazia"):
        _validar(_montar(cenario).iloc[0:0], cenario)


# ── gravar_planilha_teste_pxp ────────────────────────────────────────────────


def test_grava_com_nome_que_o_gitignore_versiona_e_separador_ponto_e_virgula(cenario, tmp_path):
    caminho = construcao.gravar_planilha_teste_pxp(_montar(cenario), tmp_path)

    # `.gitignore` libera `dados/processados/anotacoes*.csv`: o padrão-ouro tem de ser versionável
    assert caminho.name == "anotacoes_teste_pxp.csv"
    assert pd.read_csv(caminho, sep=";", dtype=str).shape[1] == len(COLUNAS_ESPERADAS)


def test_nunca_sobrescreve_a_planilha_onde_o_autor_anota(cenario, tmp_path):
    construcao.gravar_planilha_teste_pxp(_montar(cenario), tmp_path)

    with pytest.raises(FileExistsError):
        construcao.gravar_planilha_teste_pxp(_montar(cenario), tmp_path)
