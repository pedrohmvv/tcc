# Prompt — Análise de impacto da mudança de escopo de dados (TAIL)

> Uso: abrir uma sessão nova do Claude Code com diretório de trabalho `/Users/pedrohmv/TCC` e colar tudo abaixo da linha `---`.
> Saída esperada: um único arquivo, `docs/relatorio_impacto_tail.md`. Nada mais é alterado.

---

## Papel e objetivo

Você é um revisor técnico-metodológico sênior de um TCC de Entity Matching. Faça uma **varredura completa, somente leitura**, dos dois repositórios abaixo e produza um **relatório de impacto** de uma mudança de escopo já decidida pelo autor. O relatório será a base para (a) uma conversa com o orientador, (b) um novo ADR e (c) a reescrita do plano. Não implemente nada, não edite nenhum arquivo existente e não reabra decisões por conta própria. Onde algo precisar ser decidido, apresente as opções com prós, contras e uma recomendação, e marque como `[DECISÃO PENDENTE]`.

## Contexto da mudança (decisão do autor, não reabrir)

**Projeto atual** (`/Users/pedrohmv/TCC`, ler `CLAUDE.md`, `AGENTS.md`, `docs/plano_desenvolvimento.md` primeiro): TCC "Entity Matching em Produtos de Supermercado com SLMs Fine-Tuned" (UFPB, orientador Prof. Hilton Ramalho). Cross-Encoder (LLaMA 3.2 3B + LoRA) que classifica pares. Dados atuais: base do projeto ALTA/CNPq (PDV de supermercado, PB/CE/PI, ~30 mil registros) contra um dicionário canônico genérico de 1.593 entradas, sem marca nem tamanho. A proposta v3 aprovada pelo orientador (`latex/tcc_artigo/main.tex`) é a fonte de verdade. Mudar o escopo exige justificativa explícita e um novo ADR.

**Mudança:** o autor faz parte da TAIL (liga acadêmica de IA da UFPB). Um projeto da TAIL resolveu um problema muito próximo com **LLMs zero-shot**. O autor conversou com o líder desse projeto e **vai usar os dados da TAIL para treinar um SLM e usar o benchmark da TAIL como comparação**. O objetivo do autor é treinar um modelo. A decisão de usar dados e benchmark da TAIL está tomada. **O que ainda está em aberto é quanto dos dados ALTA permanece** (ver "Cenários" abaixo).

**Material da TAIL** (já está dentro do repositório, mas é untracked):
- Repositório: `/Users/pedrohmv/TCC/invoice-data-normalizer/` (clone de `github.com/TailUFPB/invoice-data-normalizer`, tem `.git` próprio, ~110 MB).
- Artigo: `/Users/pedrohmv/TCC/invoice-data-normalizer/TAIL - Title Attribute Inference Layer.pdf` (12 páginas, "Zero-Shot Product Title Normalization with LLMs: A Multi-Model Evaluation").
- O PDF não abre com a ferramenta Read (falta `pdftoppm`). Extraia o texto assim, gravando no scratchpad: `uv run --quiet --with pypdf python -I -c "import pypdf; r=pypdf.PdfReader('<caminho do pdf>'); open('<scratchpad>/tail.txt','w').write('\n'.join(p.extract_text() for p in r.pages))"`.

## Fatos já levantados sobre a TAIL (confirme cada um antes de usar; cite arquivo/linha ou página)

Tratei estes pontos como hipóteses de trabalho. Se algum estiver errado, diga explicitamente.

1. **A tarefa da TAIL não é a nossa.** A TAIL faz extração de atributos e gera um nome canônico (título → `display_name`), e decide match comparando chaves. Ela avalia com (i) F1 par-a-par com blocagem, (ii) "constância por grupo" sob ataques sintéticos, (iii) estabilidade entre execuções. O TCC treina um Cross-Encoder de classificação binária de pares contra um dicionário canônico. Só o **F1 par-a-par** parece diretamente comparável. Constância e estabilidade não se aplicam a um classificador. Verifique.
2. **Domínio e idioma diferentes.** A base da TAIL é um dump do Mercado Livre (~20 milhões de títulos PT/ES; pool de 30.000 em PT, `random_state=42`), e há dados de NF-e nos `poc_*`. A nossa é PDV de supermercado.
3. **O artigo diz que o benchmark não serve, como está, para treinar um cross-encoder** (seção 4.2, ao fim do parágrafo sobre o Ditto): 30 positivos são insuficientes para ajustar um cross-encoder e manter avaliação independente, o que exigiria "uma nova coleção rotulada com divisão própria de treino, validação e teste". Esse é o ponto mais importante do relatório.
4. **Benchmark: 1.200 pares, 30 positivos (2,5%).** 300 pares aleatórios (zero positivos) + 900 estratificados por `difflib.SequenceMatcher` com limiar 0,70 (29 dos 30 positivos estão no estrato de candidatos a match). Cada par foi rotulado por **um único anotador** (os 7 autores), sem sobreposição, então não há concordância inter-anotador. Métricas são condicionadas ao conjunto de candidatos gerado. Os ICs são muito largos (ex.: +18,7 p.p. com IC [+1,1; +37,3]).
5. **Definição de match diferente da nossa.** TAIL: `label=1` se os títulos descrevem "o mesmo SKU" (tamanho e variante importam). TCC: o regime confirmado em D1 do plano é "produto genérico", em que tamanhos diferentes **são** match na fatia produto × canônico. Verifique o conflito e seu efeito sobre o uso do benchmark deles como teste.
6. **Resultados reportados** (primeira execução): Gemini 3.1 Flash-Lite weighted F1 0,784 (P 0,952; R 0,667); GPT-5.4-mini 0,448; DeepSeek V4 Flash 0,444; TF-IDF palavra 0,597 e caractere 0,567, **com limiares ajustados nos próprios rótulos de avaliação** (viés a favor dos baselines lexicais). Só Gemini foi determinístico entre três execuções.
7. **Inconsistências de dados dentro do repositório da TAIL**, a investigar: o README e o artigo falam em 1.200 pares anotados, mas `benchmark/labeled_pairs/pairs_raw.csv` tem 210 linhas, todas `label=0`; `benchmark/labeled_pairs/pairs_normalized.csv` tem 835 linhas (129 positivas); `main_supersaurus/dados/pairs_to_label.csv` tem 1.200 linhas (30 positivas, um rótulo `' 0'` com espaço). Descubra qual arquivo é o benchmark canônico e se os 129 positivos de `pairs_normalized.csv` têm relação com os 30 do artigo (por exemplo, pares derivados de ataques sintéticos).
8. **Dados de treino candidatos na TAIL**, a caracterizar com contagens reais: `poc_*/data/input/train_supervised.csv` (~152 linhas, título → nome normalizado, é supervisão generativa e não de pares), `test_supervised.csv` (~38), `attack.csv` (~600 linhas, variantes sintéticas geradas por LLM com `tipo_variacao`), `poc_apatosaurus/data/AmostraDescMerc.csv` (15.000 textos de NF-e com categoria), `itens_nf_normalizados.csv`, JSONs `octaprice_mercadolivre_*`, e o `finetune_dataset_augmented.jsonl` citado em `main_supersaurus/finetune_nfe_colab.ipynb`, que **não está no repositório**. O pool de 30.000 títulos e o dump de 20 milhões também não parecem estar versionados. Confirme o que de fato existe em disco.
9. **Já houve tentativa de fine-tuning generativo na TAIL** (notebooks `finetune_nfe_colab.ipynb` com Phi-3.5-mini via unsloth; `main_supersaurus/results_finetune.md` aponta só para uma pasta do Google Drive). Registre o que foi feito, com qual modelo e métrica, e se é um antecedente que o TCC deve citar ou comparar.
10. **Possível substituto do Dataset Generator.** `attack_augmentation` (6 variantes sintéticas por título original) faz algo parecido com o papel do Dataset Generator da Dharma na ADR-0004. A ADR-0004 nomeia o Dharma como único gerador permitido para treino e proíbe qualquer gerador no teste. Analise o que isso muda (ex.: D7-1 e D11 do plano) e o risco de vazamento, já que as variantes de um mesmo título original não podem cair em partições diferentes.
11. **Baselines e harness de código da TAIL**: `benchmark/pairwise_f1.py`, `blocking.py`, `weighted_distance.py`, `by_attack_type.py`, `mining.py`; `inference_harness/` (backends Gemini/Qwen, `normalization.py` com `SYSTEM_PROMPT` e pré-normalização regex); `scripts/reproduce.py`; `tests/`; `revisao/` (comparação com AI-PAVE-Br, tarefa de extração, provavelmente fora do nosso escopo). As predições dos LLMs já estão em `main_supersaurus/dados/pairs_normalized_*.csv` (várias execuções por modelo), então dá para recomputar os números da TAIL sem custo de API.
12. **Licença e autorização.** O README da TAIL diz "academic research purposes" e não há arquivo LICENSE. O dump do Mercado Livre pode ter termos próprios. O BibTeX da TAIL está com `author={...}` e `booktitle={...}`. A conversa com o líder foi verbal. Avalie o que precisa estar por escrito (uso dos dados, citação, coautoria ou agradecimento, abertura do conjunto de teste) e como isso se relaciona com D7 e com a restrição de reprodutibilidade (§4.6 do `main.tex`).
13. **`invoice-data-normalizer/` está untracked no repo do TCC** (`git status` mostra `??`). Recomende como tratar (`.gitignore`, submódulo, cópia curada de artefatos), considerando tamanho e licença dos dados. **Não faça nada disso, só recomende.**

## Cenários de escopo a analisar (cada um com o impacto completo, depois recomende um)

- **A — Substituição total:** treino e teste vêm da TAIL; ALTA sai do TCC.
- **B — Treino TAIL, teste ALTA (ou o contrário):** avaliação cross-domain; discutir também o que acontece com o benchmark comparativo.
- **C — Dados TAIL como núcleo + ALTA como validação externa/estudo de domínio:** o benchmark da TAIL entra como comparação direta e a ALTA como segundo domínio.
- **D — Outro arranjo que você identificar** (por exemplo, o conjunto TAIL de 1.200 pares apenas como teste externo e um conjunto novo maior, rotulado pelo autor conforme `docs/protocolo_anotacao.md`, como teste principal).

Para cada cenário: o que o Cross-Encoder passa a aprender e avaliar, se a pergunta de pesquisa e a hipótese central da proposta v3 continuam respondíveis, poder estatístico do teste (use as contagens reais de positivos), custo de anotação adicional, o que do trabalho já feito (scripts 01 e 02, EDA, ADR-0010/0011/0012, notebooks) é reaproveitado ou descartado, e efeito no cronograma (o plano indica ~Semana 7 de 16, sem blocagem, anotação nem partição ainda; **não assuma a data de início, pergunte ou declare a premissa**).

## Varredura obrigatória do repositório do TCC

Leia por completo, não só os títulos: `CLAUDE.md`, `AGENTS.md`, `docs/plano_desenvolvimento.md` (as 729 linhas), `docs/adr/0001` a `0012`, `specs/001` a `005`, `docs/protocolo_anotacao.md`, `docs/limpeza_dados.md`, `dados/brutos/README.md`, `dados/processados/README.md`, `latex/tcc_artigo/main.tex`, `latex/tcc_artigo/referencias.bib` e `tabelas/` e `figuras/`, `scripts/01` a `06` + `scripts/README.md`, `tests/`, `notebooks/`, `Makefile`, `pyproject.toml`, `.claude/skills/*`, `.cursor/rules/*`, `.gitignore`, `docs/diario_pesquisa.md`. Se o contexto apertar, delegue a leitura por área a subagentes `Explore` em paralelo, mas verifique pessoalmente qualquer afirmação que entre no relatório.

Para cada artefato, responda: o que ele afirma hoje (com `arquivo:linha`), se a mudança o **invalida**, **altera** ou **não afeta**, e qual a ação mínima. Cubra no mínimo:
1. **Escopo e hipótese:** título, objetivo geral e específicos, pergunta de pesquisa, hipótese central, delimitações (ADR-0007), "Seção 1" e o marcador de resultado sumário dos baselines.
2. **Dados:** origem, granularidade, tamanho, partição por produto canônico, vazamento (inclusive entre variantes de ataque do mesmo título), qualidade, proveniência e licença, hash/versionamento, onde os brutos ficam fora do git.
3. **Ground truth e anotação:** ADR-0004 e 0005 (Kappa com teste-reteste), `protocolo_anotacao.md`, quantos pares o TCC ainda precisaria anotar, o conflito de definição de match (item 5 acima) e a regra "nunca usar o Dataset Generator no teste" (vale também para ataques e para LLM-as-judge?).
4. **Benchmark e métricas:** o que da TAIL é comparável e o que não é (F1 par-a-par com blocagem condicionada ao candidato vs. nossas P/R/F1, MRR, Recall@K pós-blocagem, McNemar); como garantir mesma entrada, mesmo conjunto de pares e mesma implementação de métrica (reusar `pairwise_f1.py` como está, ou reimplementar e validar contra os números do artigo); como tratar o fato de os baselines TF-IDF da TAIL terem limiar ajustado no teste; o que fazer com a blocagem TF-IDF/BM25 (ADR-0006) frente ao candidato por `difflib` da TAIL; spec 002 (cinco baselines + zero-shot) e spec 004 (testes estatísticos, ablação, pipeline progressivo).
5. **Modelo e treino:** ADR-0001/0002/0003/0009; efeito sobre a escolha do modelo-base (por exemplo, comparar com o Phi-3.5-mini que a TAIL já tentou, ou manter LLaMA 3.2 3B), spec 003 e o tamanho/qualidade dos dados de treino disponíveis (153 pares supervisionados é pouco). Não reabra a ADR-0001 (Cross-Encoder é a única arquitetura): diga apenas se a mudança de dados a pressiona.
6. **Pipeline e código:** o que muda em cada script 01–06 e nos testes (nomes, entradas, asserts anti-vazamento, ADR-0010/0012 sobre colunas da ALTA), e o que pode ser reaproveitado do harness da TAIL.
7. **Artigo (`main.tex`):** seção por seção (Resumo, Introdução, Revisão, Metodologia §4.1–§4.7, Resultados esperados, §6.4, Cronograma), incluindo o que vira "trabalho relacionado" (a TAIL e a literatura que ela cita). **Regra inegociável:** nenhuma referência pode entrar em `referencias.bib` só porque aparece na lista do artigo da TAIL; cada uma precisa de verificação em fonte primária (skill `verificacao-citacoes`). Liste quais referências do artigo da TAIL parecem relevantes (por exemplo Brinkmann et al., Fan et al., Zhang et al., Li et al./Ditto, Gazzola et al., More) como **candidatas a verificar**, não como adicionadas. Mencione também a necessidade de aprovação do orientador, já que a proposta v3 é a fonte de verdade.
8. **Skills, rules, AGENTS/CLAUDE.md:** o que fica desatualizado.
9. **Questões éticas, legais e de autoria:** licença/ToS dos dados, autorização escrita da TAIL, dados do ALTA (D7-2) e da Dharma-AI (D7-1, D11) que deixam de ser caminho crítico em cada cenário, e o que isso muda para publicação/abertura.

## Formato do relatório (`docs/relatorio_impacto_tail.md`, em português)

0. **Resumo executivo** (≤15 linhas): veredito sobre viabilidade de cada cenário, a recomendação, os três maiores riscos e a decisão mais urgente.
1. **Fatos verificados da TAIL**: tabela `afirmação | verificado? (sim/não/parcial) | evidência (arquivo:linha ou página) | observação`. Corrija os itens acima que estiverem errados.
2. **Comparabilidade da tarefa e das métricas** (TAIL × TCC), em tabela.
3. **Cenários A–D**: tabela comparativa e recomendação justificada.
4. **Mapa de impacto por artefato**: tabela `artefato | hoje diz (arquivo:linha) | efeito (Invalida/Altera/Mantém) | ação mínima | esforço (P/M/G) | bloqueia o quê`. Agrupe por: escopo, dados, anotação, benchmark/métricas, modelo/treino, código/testes, artigo, skills/docs, legal/autoria.
5. **ADRs**: para cada um dos 12, "mantém / revisar / substituir" com uma linha de justificativa, e o esboço do ADR novo (Contexto/Decisão/Consequências) que registraria a mudança, **sem criar o arquivo**.
6. **Riscos metodológicos novos** (poder estatístico com 30 positivos, vazamento por variantes, desalinhamento de definição de match, viés de limiar nos baselines da TAIL, avaliação condicionada ao candidato, domínio) com mitigação para cada um.
7. **Decisões pendentes**: lista numerada, cada uma com dono ([PEDRO], [ORIENTADOR], [TAIL], [AMBOS]), opções, recomendação e prazo sugerido.
8. **Plano de ação sequenciado** para as próximas semanas (reaproveitando a numeração de tarefas do plano de desenvolvimento onde fizer sentido) e perguntas a levar à reunião com o orientador e ao líder da TAIL.
9. **Limites desta análise**: o que não foi possível verificar e por quê.

## Regras de conduta

- **Somente leitura.** O único arquivo que você cria é `docs/relatorio_impacto_tail.md`. Não toque em `main.tex`, ADRs, specs, scripts, `referencias.bib`, `.gitignore` nem nos dados. Sem commit. Rodar `make check` ou scripts de contagem é permitido, desde que não grave dentro do repositório (use o scratchpad).
- **Evidência antes de afirmação.** Todo número e toda alegação sobre o conteúdo de um arquivo precisa vir de leitura ou execução nesta sessão, com `arquivo:linha` ou página do PDF. Separe explicitamente **fato verificado**, **inferência** e **suposição**. Se não conseguir verificar algo, diga.
- **Não decida pelo autor** o que está aberto. Não invente critérios de match fora de `docs/protocolo_anotacao.md`. Não rotule pares de teste. Respeite as restrições inegociáveis do `CLAUDE.md` (LaTeX único, Cross-Encoder único, split por produto antes de qualquer geração, seeds fixas, nada em `referencias.bib` sem verificação).
- **Seja conciso e acionável.** Prefira tabelas a prosa. Sem repetir o que o plano já diz; aponte só o delta causado pela mudança.
- Ao terminar, responda com ≤10 linhas: o veredito, os três maiores riscos, o caminho do relatório e as decisões que precisam do autor primeiro.
