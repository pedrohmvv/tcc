# Regras e Diretrizes do Projeto (AGENTS.md)

Convenções de engenharia para qualquer agente ou pessoa que altere este repositório.

**Escopo do TCC, restrições inegociáveis, ADRs e mapeamento canônico dos scripts 01–06:** `CLAUDE.md`. Este arquivo não reabre essas decisões. Em conflito com o template legado (`scripts/README.md`, I/O de churn/`tex/`), prevalecem `CLAUDE.md` e as specs.

## 1. Ferramentas e dependências

- Gerenciador exclusivo: `uv`. Fonte da verdade: `pyproject.toml` + `uv.lock`.
- Não criar nem atualizar `requirements.txt`.
- Instalar: `uv sync` ou `make setup` / `make setup-dev`.
- Lint e formatação: `ruff` via `make lint` e `make format`. Estilo: aspas duplas, line-length 100, indentação de 4 espaços (`pyproject.toml`).
- Type hints em código novo; checagem com `make typecheck` (mypy).
- Antes de um comando ad-hoc, verificar se o `Makefile` já cobre (`make help`).

## 2. Pipeline

Scripts numerados em `scripts/`, sequenciais, executáveis ponta a ponta com `make pipeline`. Cada script consome a saída do anterior.

Mapeamento canônico (implementar nesta direção; ver `CLAUDE.md` e `specs/`):

| Script | Spec | Saída esperada |
|---|---|---|
| `01_coleta_dados.py` | — | `dados/brutos/` (base ALTA + dicionário; brutos são imutáveis) |
| `02_analise_exploratoria.py` | 001 | estatísticas em `resultados/` |
| `03_construcao_dataset.py` | 001 | partições e candidatos em `dados/processados/` |
| `04_baselines.py` | 002 | preditores clássicos + LLaMA zero-shot |
| `05_finetuning.py` | 003 | LoRA do Cross-Encoder |
| `06_avaliacao_exportacao.py` | 004 | métricas + exportação para `latex/tcc_artigo/` |

Os arquivos no disco ainda podem usar nomes do template (`03_preprocessamento.py`, `04_treinamento_modelo.py`, `05_avaliacao_modelo.py`, `06_exportar_figuras_eps.py`). Isso é dívida de adaptação — não tratar esse I/O (churn, `.joblib` genérico, pasta `tex/`) como o alvo. Ao reescrever, seguir a tabela acima e a spec correspondente.

Não criar subdiretórios fora das saídas esperadas em `dados/`, `modelos/`, `resultados/` e `latex/tcc_artigo/`.

## 3. Testes (`tests/`)

`pytest`, três camadas. Rodar com `make test` ou `uv run pytest tests/ -v`.

1. **Unitários puros:** lógica e bordas, sem I/O de disco.
2. **Transformação em memória:** fixtures do `conftest.py`, sem I/O de disco.
3. **Integração leve:** um teste de pipeline em `tmp_path` que verifica a passagem de artefatos 01→06.

Matplotlib/Seaborn em teste: backend `Agg` ou mock de `savefig`.

## 4. LaTeX

Única saída de texto do TCC: `latex/tcc_artigo/` (`abntex2[article]`). Compilar com `make latex DOC=tcc_artigo` (`latexmk`).

Duas categorias de arquivo em `latex/tcc_artigo/figuras/` e `tabelas/`, com regras distintas:

- **Tabelas/figuras de resultado** (números de experimento: métricas, comparações, ablação) — geradas pelo script 06, **nunca editadas à mão**. É aqui que a regra evita número digitado errado.
- **Tabelas/figuras de conteúdo qualitativo** (não derivam de resultado experimental: critérios de seleção, cronograma, diagrama do pipeline) — escritas à mão, versionadas normalmente. Hoje: `tab_criterios_selecao_slm.tex`, `tab_cronograma_execucao.tex`, `fig_pipeline.tex`.
- `tab_heterogeneidade_exemplos.tex` é caso especial: hoje escrita à mão, mas **deve migrar** para geração automática pelo script 02 assim que a EDA existir (spec 001, tarefa 1.1.4) — passa a extrair exemplos reais da base em vez de exemplo digitado.

Strings LaTeX exportadas do Pandas precisam preservar escapes (`replace("_", r"\_")` e equivalentes).

Não gerar `.docx` nem outros formatos para o texto final.

## 5. Comandos

| Comando | Efeito |
|---|---|
| `make setup` / `make setup-dev` | dependências (`uv`) |
| `make pipeline` | scripts 01→06 |
| `make latex DOC=tcc_artigo` | PDF do TCC |
| `make check` | lint + typecheck + testes (CI) |
| `make test` | pytest |
| `make typecheck` | mypy |
| `make format` / `make lint` | ruff |
| `make clean` / `make latex-clean` | caches / auxiliares LaTeX |
