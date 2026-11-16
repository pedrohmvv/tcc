# Prompt: planejar completamente o harness de avaliação e os baselines

> Para colar numa sessão **nova** do Claude Code, na raiz do repositório. É uma sessão **só de planejamento**: o resultado é um plano completo para o autor aprovar, sem código. Escrito em 2026-11-16, depois do fechamento do teste final (`docs/retomada_sessao_2026-11-16.md`).

```
Você está retomando o TCC "Entity Matching em Produtos de Supermercado com SLMs Fine-Tuned" (UFPB, autor Pedro) numa sessão nova, sem contexto prévio. Responda em português.

TAREFA: planejar COMPLETAMENTE o harness de avaliação e os baselines (scripts 04 e 06, specs 002 e 004). Esta sessão é SOMENTE DE LEITURA E PLANEJAMENTO: não edite nem crie arquivos, não escreva código nem testes, não rode o pipeline (`scripts/03_construcao_dataset.py`), não instale nada (em especial o extra `finetuning`), não faça commit nem push, e não toque nas planilhas `dados/processados/anotacoes_*.csv`. São permitidos: ler arquivos, `git status`, `git log`, `make check` (só roda testes) e leituras de CSV/parquet para contagens e formas (sem exibir descrições reais de produtos da ALTA).

1) LEIA, nesta ordem:
CLAUDE.md, AGENTS.md, docs/retomada_sessao_2026-11-16.md (estado atual; o de 13/11 está substituído), docs/pendencias_autor.md, a memória retomada-1-2b-blocagem-produto-x-produto (em ~/.claude/projects/-Users-pedrohmv-TCC/memory/), docs/adr/0001, 0003, 0004, 0005, 0006, 0008, 0009, 0010, 0011, 0013, 0014, 0015, 0016 e 0018, specs/002-baselines-classicos, specs/003-finetuning-cross-encoder, specs/004-avaliacao-e-ablacao, specs/001-construcao-dataset-ground-truth/{requirements,design-treino-pxp}.md, docs/protocolo_anotacao.md, as skills do projeto avaliacao-baselines, dominio-entity-matching, reprodutibilidade-ml e protocolo-anotacao-em (em .claude/skills/), e os esqueletos scripts/04_baselines.py e scripts/06_avaliacao_exportacao.py. As specs 002, 003 e 004 NÃO foram lidas em nenhuma sessão anterior: o plano parte delas.

2) VERIFIQUE o estado real contra o documento de retomada, sem corrigir nada: `git status --short` e `git log --oneline -5` (os commits da finalização de 2026-11-16 devem estar no topo; as quatro planilhas `anotacoes_*.csv` e `proposta_tcc.docx` ficam sem commit de propósito); `make check` (espera 982 testes verdes); e, por leitura, a forma e as contagens de dados/processados/teste_pxp.parquet (espera 290 pares, 15 colunas, 142 match e 148 nao_match, colunas `fonte_rotulo`, `estrato`, `prob_inclusao`), validacao_pxp.parquet (5.906 pares, 25 match) e treino_pxp.parquet (37.958 pares; origens neg_tamanho, pos_*, tail_variante, tail_nf, tail_negativo; 0 autor_b2). Aponte qualquer divergência.

3) FATOS JÁ ESTABELECIDOS (não re-derive; confirme só se a leitura contradisser):
- O teste é ESTRATIFICADO (6 estratos, `prob_inclusao` de 2,3e-05 a 0,040): métrica agregada exige ponderar por 1/prob_inclusao OU relatar por estrato. O estrato digito_divergente tem 0 match e texto_identico tem 12 de 12 match: os estratos extremos são triviais para qualquer baseline.
- A validação tem só 25 match em 5.906 pares (prevalência ~0,4%); o teste tem ~49% de match bruto. Não escolher limiar por F1 bruto na validação: usar PR-AUC e reponderar ou subamostrar negativos para a prevalência-alvo (decisão do autor, 2026-11-13).
- ADR-0018: o desempenho deve ser reportado COM e SEM os 9 pares `autor_adjudicacao`. ADR-0016: o Kappa do reteste (0,8125 / 0,8955) vem de intervalo de 39 min e NÃO é teste-reteste de 7 dias.
- O harness deve ser CONGELADO antes de ler qualquer resultado de modelo (skill avaliacao-baselines).
- ADR-0011: o baseline "ALTA atual" (colunas do matcher) só existe para produto × dicionário, só lê as colunas diretamente dos brutos, só nos scripts 02/04/06 e só DEPOIS do teste congelado, reportado nas duas versões (com e sem cobertura).
- ADR-0013 item 6: o benchmark externo da TAIL (`dados/brutos/tail/pairs_to_label.csv`, 1.200 pares, 30 positivos; rótulo com espaço a normalizar com strip) é só teste exploratório da fatia p×p, com McNemar pareado contra as predições salvas da TAIL, bootstrap por cluster e TP/FP/FN absolutos; o limiar vem da validação do TCC. As PREDIÇÕES da TAIL (`pairs_normalized*.csv`, `baseline_predictions.csv`, no clone invoice-data-normalizer/main_supersaurus/dados/) NÃO foram copiadas para dados/brutos/tail/. O clone tem duas cópias do benchmark que diferem em 4 rótulos (usada a de `dados/`); não se sabe qual a TAIL confirmou. Nada da TAIL é versionado ou publicado.
- A fatia p×d (produto × dicionário) ainda não tem teste (100 pares pendentes), nem treino (D-5 suspenso). O plano deve dizer o que do harness serve às duas fatias e o que só serve à p×p.
- O LLaMA zero-shot e o fine-tuning dependem de GPU da Dharma-AI (D1 a D4 do autor, ainda sem resposta). O plano deve separar o que roda sem GPU (TF-IDF, BM25, Levenshtein, Jaccard, possivelmente embeddings genéricos em CPU) do que exige GPU.
- O script 03 tem ~4.500 linhas; decidir se o harness fica nos scripts 04 e 06 ou em módulo auxiliar fora da numeração, justificando.

4) ENTREGUE um plano completo, nesta ordem, citando arquivo e seção de onde veio cada afirmação e dizendo "não sei" quando os documentos não responderem:
a) Escopo e fronteiras: o que é harness, o que é baseline, o que é script 04, o que é script 06; o que fica FORA (treino, script 05).
b) Contratos de dados: entradas (teste, validação, treino, predições dos baselines), formato do arquivo de predições por método (colunas, ids, score, limiar), saídas em resultados/ e latex/tcc_artigo/ (tabelas e figuras geradas, nunca editadas à mão, AGENTS.md §4).
c) Métricas e estatística, por spec e ADR: Precision/Recall/F1, PR-AUC, MRR, Recall@K (e o que significam aqui), McNemar (ADR-0008), IC por bootstrap (por par e por cluster/componente), ponderação por 1/prob_inclusao, relato por estrato, com e sem `autor_adjudicacao`, escolha de limiar só na validação, tratamento do desbalanceamento 0,4% × 49%. Diga quais decisões são do autor.
d) Baselines: lista final (specs 002/ADR-0011), como cada um produz score, onde o limiar entra, o que roda sem GPU, e o que fazer com o LLaMA zero-shot enquanto não há GPU.
e) Golden test da spec 002: o que é, como se constrói sem usar dado real como rótulo, e que ele vem ANTES de qualquer número novo.
f) Benchmark externo da TAIL: o que falta (predições não copiadas, versão do benchmark, autorização), o que o harness precisa para o McNemar pareado e o bootstrap por cluster.
g) Congelamento do harness: o que significa congelar, o que registrar (config YAML versionada, seeds, hashes dos insumos) e quando.
h) Quebra em tarefas T1..Tn, cada uma com: entrega, camada de teste (unitário puro / transformação em memória / integração em tmp_path, AGENTS.md §3), dependências, o que pode rodar já, o que depende do autor e o ponto de parada no RED. Ordem sugerida e caminho crítico.
i) Riscos e o que NÃO pode ser verificado ainda (por exemplo: poder estatístico com 25 match na validação, estratos triviais, domínio da TAIL, ausência de GPU), e as armadilhas que mais causam dano.
j) No máximo 5 PERGUNTAS ao autor, só as que mudam o plano.

REGRAS que valem em tudo: TDD com parada no RED para o autor ver; nenhum commit nem push sem o autor pedir; nenhum LLM ou gerador gera ou rotula teste ou validação; só o autor anota; Cross-Encoder é a única arquitetura; nada da TAIL é versionado ou publicado; `codg_item`, `desc_ref` e `match_score` nunca entram em rótulo, treino, validação, blocagem, seleção de pares ou planilha; antes de editar documentos (protocolo, ADRs, main.tex) pedir aval; nunca inventar referência bibliográfica (skill verificacao-citacoes); seeds fixas e configs versionadas; tudo ou nada nas funções que gravam; falhar alto; relatar fielmente o que não foi verificado.

Termine com uma única pergunta: "Aprova este plano, e por qual tarefa devo começar?", listando as 2 ou 3 primeiras tarefas que fariam mais sentido e por quê. Depois da aprovação do autor, o plano pode ser salvo em specs/004-avaliacao-e-ablacao/ (só então; nesta sessão não escreva arquivos).
```

## Notas de quem escreveu (não fazem parte do prompt)

- As specs 002 a 004 e o esqueleto dos scripts 04 e 06 **não foram lidos** ao escrever este prompt; ele lista o que a sessão nova deve ler e os fatos que já saíram de outras fontes.
- Pontos que provavelmente exigirão decisão do autor: cópia das predições da TAIL para `dados/brutos/tail/`; versão do benchmark; limiar e prevalência-alvo da validação; módulo auxiliar × scripts 04/06; o que fazer com o LLaMA zero-shot sem GPU.
