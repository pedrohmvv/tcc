# 📓 Diário de Pesquisa

> *Registre aqui o dia-a-dia da sua pesquisa: leituras, decisões, impasses, ideias e progresso. Um bom diário de pesquisa é como um "lab notebook" — permite reconstruir o raciocínio por trás de cada decisão semanas ou meses depois.*

---

**Projeto:** Entity Matching em Produtos de Supermercado com Small Language Models Fine-Tuned
**Pesquisador(a):** Pedro Henrique Medeiros Vieira
**Período:** Ago/2026 — presente

---

## Instruções de Uso

- Adicione uma nova entrada a cada sessão de trabalho (não precisa ser todo dia).
- Seja honesto(a): registre inclusive o que **não** funcionou. Fracassos documentados são tão valiosos quanto sucessos.
- Use a estrutura abaixo como guia, mas adapte livremente.

---

## Entradas

### 📅 2026-09-17 — Preparação do repositório para início do desenvolvimento

**Duração:** _~2h (sessão com agente)_

**O que fiz hoje:**
- Levantei o status real do repositório: planejamento (9 ADRs, 5 specs, protocolo de anotação, skills, rules) estava maduro, mas `scripts/01-06` ainda eram 100% o template genérico de churn e `pyproject.toml` não tinha nenhuma dependência de EM/ML.
- Organizei o histórico git: commitei ADRs, specs, skills/rules, protocolo de anotação, docs-hub atualizados e a reescrita do `tcc_artigo` em commits separados (estavam todos não commitados misturados).
- Removi os formatos LaTeX legados do template (`latex/tcc`, `tese`, `artigo`, `dissertacao`, `livro`, `projeto`, `relatorio`) — este TCC usa só `latex/tcc_artigo/`.
- Atualizei `pyproject.toml` com as dependências reais das specs (rank-bm25, rapidfuzz, scipy/statsmodels, mlflow, pyyaml; torch/transformers/peft/accelerate/datasets como extra opcional `finetuning`) e metadados do projeto.
- Renomeei `scripts/03-06` para os nomes canônicos do `AGENTS.md` (`03_construcao_dataset.py`, `04_baselines.py`, `05_finetuning.py`, `06_avaliacao_exportacao.py`) e reescrevi `01_coleta_dados.py` para validar os brutos reais (`todos_mercados_2026-09-10.csv`, `dicionario_canonico.csv`) em vez de gerar dados fictícios. Os demais (02-06) ficaram como esqueletos que apontam para a spec correspondente.
- Atualizei `Makefile` (targets do pipeline renomeados, `latex-all`/`latex-clean-all` só com `tcc_artigo`, removi o target `notebook`).
- Escrevi a suíte de testes nas 3 camadas do `AGENTS.md` cobrindo o script 01 (9 testes passando + 1 xfail documentando o que falta em 02-06). `ruff check`, `ruff format --check` e `mypy scripts/` passam localmente.

**Decisões tomadas:**
- Ferramenta de tracking de experimentos do fine-tuning (spec 003): **MLflow**, não W&B.
- Formatos LaTeX legados: removidos agora, não deixados para depois.

**Dificuldades / Impasses:**
- **[RISCO ABERTO]** Acesso à GPU da infraestrutura Dharma-AI (ADR-0002/0003, 48-141 GB VRAM) para o fine-tuning do script 05 **ainda não está confirmado**. Preciso confirmar isso antes de chegar na spec 003 — se não houver acesso, acionar a mitigação do ADR-0009 (Gemma 2 2B / Colab Pro).
- **[ACHADO]** `Makefile`, `pyproject.toml` e `uv.lock` foram deliberadamente untracked do git numa sessão anterior (commit `8bbe54c`), mas `.github/workflows/ci.yml` (que É rastreado) depende dos três (`uv sync --group dev`, `make test`). Isso quebra o CI em qualquer push para `origin/main` — decidir se isso é intencional (CI desativado de fato?) ou se algum desses arquivos precisa voltar a ser rastreado.

**Próximos passos:**
- [ ] Decidir o destino do CI vs. arquivos untracked (ver achado acima).
- [ ] Confirmar acesso à GPU Dharma-AI ou acionar ADR-0009.
- [ ] Implementar `scripts/02_analise_exploratoria.py` (spec 001) sobre a base real.
- [ ] Implementar blocagem TF-IDF/BM25 e particionamento em `scripts/03_construcao_dataset.py` (spec 001).

---

### 📅 AAAA-MM-DD — _Próxima entrada..._

_Copie o bloco acima e continue adicionando entradas._

---

> **💡 Dica:** Ao final do projeto, seu diário será uma fonte rica para escrever a seção de Metodologia do seu trabalho. Muitas decisões que parecem óbvias agora serão impossíveis de lembrar em 6 meses.
