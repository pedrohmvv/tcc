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

### 📅 2026-10-31 — Análise de impacto da TAIL e decisões de escopo

**Duração:** _sessão longa com agente_

**O que fiz hoje:**
- Pedi uma varredura somente leitura do repositório da TAIL (`invoice-data-normalizer/`) e do TCC. O relatório está em `docs/relatorio_impacto_tail.md`.
- Decidi usar o cenário D: ALTA como domínio e teste principal; TAIL como treino extra de pares produto × produto e teste externo exploratório.
- Defini duas regras de match por tipo de par (produto × dicionário: categoria e variante; produto × produto: SKU, com marca e tamanho). Kit/promoção e marca própria declarada no texto são não-match em produto × dicionário.
- Escrevi o ADR-0013, revisei o protocolo de anotação, sincronizei specs 001–004, skills, regra do Cursor e `CLAUDE.md`. Criei a pauta do orientador e o rascunho do e-mail para a TAIL (não enviado).
- Defini o plano da blocagem: amostra cega de ~50 produtos para medir o recall, varredura de k e congelamento do método antes de gerar os pares do teste (emenda ao ADR-0006).

**Decisões tomadas:**
- Dois adaptadores LoRA, um por tipo de par (contra a recomendação de modelo único do relatório).
- Dataset Generator da Dharma suspenso (D-5). Sem segundo anotador da TAIL (D-6).
- Aval do orientador **informado por mim, ainda não formalizado**. Autorização da TAIL **verbal, ainda não escrita**.

**Dificuldades / Impasses:**
- **[RISCO]** O cronograma da proposta está atrasado: blocagem, anotação, partição e treino não iniciados. A anotação é o caminho crítico.
- **[RISCO]** Sem o Generator, não há fonte planejada de pares de treino produto × dicionário (a supervisão distante por "marca + unidade" não funciona num dicionário sem marca nem tamanho).
- **[ACHADO]** O benchmark da TAIL tem 30 positivos (12 de 3 famílias de produto) e duas versões dos rótulos que divergem em 4 linhas.
- **[RISCO]** Marca própria só é reconhecida quando o texto declara: marca própria sem sinal no texto vira limitação a declarar no TCC.

**Próximos passos:**
- [ ] Marcar a reunião com o orientador e enviar o e-mail à TAIL.
- [ ] Blocagem 1.2a (testes primeiro), amostra cega e recall.
- [ ] Decidir a D-5 (Generator) antes da tarefa 1.7 e a D-13 (tamanho do teste produto × produto).
- [ ] Editar o `main.tex` só depois do aval formal do orientador.

---

### 📅 2026-10-31 — Blocagem 1.2a e inversão das fatias (ADR-0014)

**Duração:** _sessão longa com agente_

**O que fiz hoje:**
- Implementei a blocagem produto × dicionário no script 03 (TF-IDF e BM25, varredura de k, deduplicação por texto normalizado, amostra cega), com testes primeiro e `make check` verde.
- Anotei a amostra cega (50 produtos) e medi o recall: TF-IDF supera ou empata com o BM25 em todos os k; teto de 90,5% (4 de 42 produtos não são recuperados em nenhum k). Congelei TF-IDF e k=20 em `configs/blocagem.yaml` e registrei em `docs/resultado_blocagem_amostra_cega.md`.
- Decidi tornar produto × produto a fatia principal, com produto × dicionário como secundária (ADR-0014), e propaguei a mudança para a documentação (exceto o `main.tex`).

**Decisões tomadas:**
- TF-IDF, k=20 (alternativa considerada: k=50).
- ADR-0014: produto × produto é a fatia e o teste principais; produto × dicionário permanece como fatia secundária completa, com teste menor.

**Dificuldades / Impasses:**
- **[ACHADO]** 1.959 dos 28.240 produtos (6,9%) ficam sem nenhum candidato com TF-IDF e k=20. Parte é não-alimento; parte é abreviação (`VH`, `VIN`, `ESP`). A proporção de cada grupo não foi medida.
- **[RISCO]** O ADR-0007 rejeitara "duas avaliações completas e independentes" por custo de anotação e de blocagem sem dicionário; o ADR-0014 as retoma, com o dicionário em tamanho menor. O custo de anotação migra em parte para produto × produto.
- **[RISCO]** A blocagem entre produtos ainda não foi medida; se não for melhor que a produto × dicionário, o argumento do ADR-0014 enfraquece.

**Próximos passos:**
- [ ] Desenhar a 1.2b: como medir o recall da blocagem entre produtos (sem dicionário e sem `codg_item`).
- [ ] Decidir os tamanhos dos testes por fatia (D-13 e o teste produto × dicionário).
- [ ] Atualizar o `main.tex` (tarefa 5.3) com a nova hipótese central.

---

### 📅 AAAA-MM-DD — _Próxima entrada..._

_Copie o bloco acima e continue adicionando entradas._

---

> **💡 Dica:** Ao final do projeto, seu diário será uma fonte rica para escrever a seção de Metodologia do seu trabalho. Muitas decisões que parecem óbvias agora serão impossíveis de lembrar em 6 meses.
