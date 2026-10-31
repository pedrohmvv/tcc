# Relatório de impacto — incorporação dos dados e do benchmark da TAIL ao TCC

**Data:** 2026-10-31 · **Escopo:** varredura somente leitura de `/Users/pedrohmv/TCC` e de `invoice-data-normalizer/` (clone da TAIL, commit `9d010ec`, 2026-08-24) · **Uso:** insumo para a reunião com o orientador, para o ADR-0013 e para a reescrita do plano. Nenhum outro arquivo foi alterado.

**Convenções.** `TAIL/` = `invoice-data-normalizer/`. "TAIL p.N" = página do PDF `TAIL - Title Attribute Inference Layer.pdf`. **[FATO]** = lido ou executado nesta sessão; **[INF]** = inferência a partir de fatos; **[PREMISSA]** = suposição a confirmar. Contagens de dados foram calculadas com scripts no scratchpad (nada gravado no repositório).

**[PREMISSA] Calendário.** O plano (`docs/plano_desenvolvimento.md:7`, `:37`) e o diário (`docs/diario_pesquisa.md:23`) situam a Semana 1 em 2026-09-17. Assumo **Semana 1 = 14–20/set/2026**, logo hoje (31/out) = **fim da Semana 7**, restando as **Semanas 8–16 (02/nov/2026 – 03/jan/2027)**. **Confirmar com o autor** — todo o §8 depende disso.

---

## 0. Resumo executivo

- **Veredito por cenário.** **A (substituição total): inviável no prazo.** A TAIL não tem conjunto de treino por pares, o teste tem 30 positivos e o próprio artigo diz que isso não basta para ajustar um cross-encoder com avaliação independente (TAIL p.9). Exigiria anotar um conjunto novo sobre um pool que não está em disco, e derrubaria a justificativa do modelo-base (ADR-0002) e a lacuna da proposta. **B: viável, mas fraco.** Treinar na TAIL e testar na ALTA (B1) mede transferência entre duas definições de *match* incompatíveis; testar só na TAIL (B2) se apoia em 30 positivos fora do domínio. **C: inviável no prazo**, porque soma os custos de A aos da anotação ALTA. **D (recomendado):** a ALTA continua sendo o domínio e o teste principal. A TAIL entra (i) no treino, como pares produto×produto derivados de variantes e negativos difíceis, mais um braço de ablação "com/sem TAIL"; (ii) como **teste externo pareado** de 1.200 pares contra as predições já salvas de Gemini, GPT, DeepSeek e TF-IDF; (iii) como fonte de um **segundo anotador**, o que responde à recomendação 2 do parecer.
- **Três maiores riscos.** (1) **Poder estatístico:** são 30 positivos, 12 deles vêm de 3 famílias de produto e 9 são anúncios quase idênticos que só diferem por um sufixo `#xxxx`. O IC95% do F1 do Gemini vai de ~0,64 a ~0,90. (2) **Definição de match:** a TAIL rotula "mesmo SKU"; o TCC, na fatia principal, rotula "produto genérico" (tamanho diferente = match). O benchmark só mede a fatia produto×produto, nunca a tarefa central. (3) **Base legal e qualidade:** o repositório não tem LICENSE, o pool de 30 mil títulos e o dump de 20 milhões não estão no repositório, a autorização foi só verbal, e há **duas versões dos rótulos que divergem em 4 dos 30 positivos**.
- **Decisão mais urgente:** reunião extra com o orientador **antes de qualquer código**, para aprovar o cenário e o ADR-0013. Em paralelo, pedido de autorização **por escrito** à TAIL. Contexto agravante: o M1 (ground truth fechado, Semana 6) não foi cumprido. A blocagem, a revisão do protocolo, a anotação e a partição ainda não começaram, então qualquer cenário que acrescente trabalho ao caminho crítico compromete a defesa.

---

## Decisões do autor registradas após a primeira versão (2026-10-31)

**Decisão 6 — plano da blocagem (2026-10-31).** Aceita a recomendação: (a) **amostra cega** de ~50 produtos para medir o recall da blocagem sem o viés de anotar só o que ela devolve (rótulo `sem_entrada` para produto sem entrada no dicionário); (b) **1.2 dividida**: 1.2a produto × dicionário agora, 1.2b produto × produto depois; (c) **varredura de k** em {1, 5, 10, 20, 50, 100}, TF-IDF e BM25, com a escolha feita na amostra cega e congelada em config antes de gerar os pares do teste. Registrado no ADR-0006 (emenda), spec 001, protocolo §2.1 e §3.5 e plano §6. Pendentes: como amostrar os pares do teste a partir dos candidatos, e se a amostra cega entra no teste (recomendado: sim). Os insumos reaproveitáveis da TAIL (amostragem por faixas de similaridade, distância ponderada por dígito, veto numérico) ficam para a 1.2b e para a mineração de negativos difíceis, como **ideias reimplementadas**, nunca como código copiado.

**Decisão 5 — D-12: dois adaptadores LoRA (2026-10-31), contra a recomendação do relatório (modelo único).** Um adaptador por tipo de par, sobre o mesmo checkpoint-base; sem marcador do tipo de par. Consequências: (a) **os dados da TAIL só alimentam o adaptador produto × produto**, pois não há pares produto × dicionário; o adaptador da fatia principal é treinado sem a TAIL; (b) dois treinos, duas configs e duas avaliações; a ablação é a primeira a encolher; (c) some o problema de desequilíbrio entre os pares da TAIL e os da ALTA; (d) a D-5 (Generator suspenso) passa a bloquear **só** o adaptador produto × dicionário. Registrado no ADR-0013 e nas specs 001–004. Isto prevalece sobre as menções a "marcador do tipo de par" e a "modelo único" no restante do relatório.

**Decisão 4 — D-5 e D-6 (2026-10-31).** D-5 (Dataset Generator da Dharma): **suspenso**; precisa ser decidido antes da tarefa 1.7. D-6 (2º anotador): **não haverá anotador da TAIL**; o ADR-0005 permanece como está, e a recomendação 2 do parecer segue como limitação declarada. D-12 e D-13 continuam abertas. Isto prevalece sobre as linhas D-5 e D-6 da tabela do §7 e sobre os papéis "2º anotador" do cenário D nos §0 e §3.

**Decisão 3 — kit/promoção e marca própria em produto × dicionário são não-match (2026-10-31).** Registrada no protocolo (§3.3) e no ADR-0013. Consequências: (a) em produto × dicionário a marca deixa de ser totalmente neutra, pois a marca própria exclui o match; (b) como o dicionário não tem marca, o modelo só pode aprender isso se a descrição trouxer sinais de marca própria, e pares de marca própria sem esse sinal ficarão ambíguos; (c) produtos de marca própria e kits nunca serão mapeados ao dicionário, o que reduz a cobertura do mapeamento no projeto ALTA; (d) critério de reconhecimento **fechado pelo autor**: marca própria só vale quando o texto da descrição declara; marca própria sem sinal no texto é rotulada pelas regras gerais, o que vira limitação declarada no TCC.

**Decisão 2 — cenário D adotado pelo autor (resolve D-2 pelo lado do autor).** A ALTA continua como domínio e teste principal; a TAIL entra como treino adicional (pares produto×produto), teste externo exploratório e fonte de um possível 2º anotador. **Falta o aval do orientador e o ADR-0013** (status "Proposto" até lá). Nenhum artefato do repositório foi alterado ainda.

**Decisão 1 — duas regras de match por tipo de par (resolve D-3).**

| Tipo de par | O que decide o match | Marca | Tamanho |
|---|---|---|---|
| Produto × dicionário (fatia principal) | Categoria e variante (ex.: branco × integral × parboilizado) | Não decide (o dicionário não tem marca) | Não decide (o dicionário não tem tamanho) |
| Produto × produto (fatia suplementar) | **SKU** | **Decide** | **Decide** (1 kg ≠ 5 kg) |

O benchmark da TAIL usa "mesmo SKU", então ele passa a ser comparável **só** com a fatia produto × produto, agora na mesma regra.

**Consequências que essa decisão cria (nem todas estavam na primeira versão):**

1. **A transitividade do ADR-0007 deixa de valer como está** (`0007:9`; `main.tex:194`). Dois produtos que caem na mesma entrada do dicionário são só da **mesma categoria**, não "o mesmo produto". "Arroz Tio João 1 kg" e "Arroz Camil 5 kg" mapeiam para "ARROZ BRANCO" e são SKUs diferentes. A frase "a subtarefa intra-base é resolvida como consequência lógica" precisa ser reescrita: produto × produto em nível SKU **não** sai do mapeamento ao dicionário e precisa ser decidido pelo próprio modelo.
2. **"Sem retreino" (`main.tex:196`; `0007:12`) deixa de se sustentar.** Hoje o texto diz que o mesmo Cross-Encoder, treinado em produto × dicionário, serve também para produto × produto. Com dois regimes de rótulo, o modelo precisa ser treinado com os dois tipos de par (com marcador do tipo de par na entrada). Isso muda o §4.1 e o §4.4 do artigo e a spec 003. **[INF]** É o ponto em que a TAIL ajuda mais: as variantes dela fornecem positivos em nível SKU. Os negativos em nível SKU (mesma marca, tamanho diferente) precisam ser montados a partir da ALTA, por exemplo com `und_val`/`und_med`; isso contraria o ADR-0011 se esses campos entrarem no modelo, então devem servir só para **montar** os pares, nunca como entrada.
3. **A fatia produto × produto ganha peso.** Antes era uma validação de 50–100 pares. Agora é um segundo regime de rótulo, com treino próprio. O tamanho previsto para ela no teste (50–100 pares) deve ser revisto, porque poucos positivos já limitam o poder estatístico (risco R1).
4. **A tarefa 1.3 (revisar o protocolo) passa a ser o primeiro item e bloqueia a anotação.** `protocolo_anotacao.md:21` ("as mesmas regras aplicam-se aos dois tipos de par") deve ser removido.

---

## 1. Fatos verificados da TAIL

| # | Afirmação (hipótese de trabalho) | Verificado? | Evidência | Observação / correção |
|---|---|---|---|---|
| 1 | Tarefa da TAIL ≠ tarefa do TCC; só o F1 par-a-par é comparável | **Sim** | Pipeline título→atributos→`display_name`/`match_key` (TAIL p.5–6); métricas: constância por grupo, F1 par-a-par com *blocking*, estabilidade (TAIL p.6–7); `TAIL/inference_harness/runner.py:81-108` normaliza cada lado do par separadamente | Constância e estabilidade pressupõem uma saída gerativa (nome canônico). Para um classificador, a estabilidade é trivial (inferência determinística). **Atenção ao termo:** o "*blocking*" da TAIL é um **veto por conflito de tokens numéricos** aplicado ao par já formado (TAIL p.7; `main_supersaurus/benchmark.ipynb`, células 18/20), **não** geração de candidatos como no ADR-0006 |
| 2 | Domínio e idioma diferentes | **Sim** | Dump MeLi de ~20 milhões de títulos PT/ES; pool de 30.000 em PT, `random_state=42` (TAIL p.4; `main_supersaurus/scripts/sample_pairs.py:12-17`); NF-e em `poc_apatosaurus/data/AmostraDescMerc.csv` | **[INF]** Pela heurística de 25 termos de mercearia, só **38 dos 2.267 títulos únicos** do benchmark (1,7%) são de supermercado e **0 dos 30 positivos** são. O benchmark é de marketplace geral (eletrônicos, autopeças, utilidades) |
| 3 | O artigo diz que o benchmark não serve, como está, para treinar um cross-encoder | **Sim** | TAIL p.9: "os 30 pares positivos deste conjunto são volume insuficiente para ajustar um *cross-encoder* e, simultaneamente, manter uma avaliação independente, o que exigiria uma nova coleção rotulada com divisão própria de treino, validação e teste"; repetido como trabalho futuro em TAIL p.12 | É o ponto central deste relatório |
| 4 | 1.200 pares, 30 positivos; 300 aleatórios + 900 estratificados por `difflib` τ=0,70; anotador único; ICs largos | **Sim** | TAIL p.4–5, p.9; `main_supersaurus/dados/pairs_to_label.csv`: estratos `random` 300 (0 positivos), `match` 224 (29), `non_match` 676 (1); 2.267 títulos únicos | Confirmado também: 29/224 = 12,9% (TAIL p.2). **Acréscimo:** 12 dos 30 positivos vêm de 3 famílias ("Grama/Erva dos Gatos" 5, "Video Cassete Samsung" 4, "Kit Balde Pipoca" 3), e **9 dos 30** são anúncios idênticos exceto por um sufixo `#xxxx`. O n efetivo é menor que 30 |
| 5 | Definição de match diferente | **Sim** | TAIL p.5: `label=1` se "o mesmo SKU"; TCC: `specs/001-…/requirements.md:31-33`, `docs/protocolo_anotacao.md:50` (produto×canônico: tamanho diferente = match) | Para a fatia **produto×produto**, o protocolo é ambíguo: `protocolo_anotacao.md:27` condiciona o tamanho "à granularidade do dicionário", e `:46` tem a regra SKU. O regime SKU da TAIL bate com essa linha, não com §3.4. **Acréscimo:** alguns positivos da TAIL são mais frouxos que "mesmo SKU" (ex.: "Jaqueta Tutto Fyber 2xl" × "…Ii"; "Porta Toalha … 2040.c.flx Deca" × "… 2040 C37 Deca"), e o próprio artigo admite rótulo duvidoso no caso Sandisk (TAIL p.8) |
| 6 | Resultados reportados; limiares TF-IDF ajustados no teste; só o Gemini é determinístico | **Sim — reproduzido** | Recomputei TP/FP/FN a partir das predições salvas: Gemini Weighted 20/1/10 (P 0,952; R 0,667; F1 0,784); GPT Weighted 13/15/17 (0,448); DeepSeek Weighted 16/26/14 (0,444); TF-IDF palavra 20/17/10 (0,597); caractere 19/18/11 (0,567). McNemar exato: 0,0037 / 0,0009 / 1,9×10⁻⁵ / 3×10⁻⁸, igual à TAIL p.9 e a `revisao/T3_significancia.csv` | O limiar é escolhido por varredura nos rótulos de avaliação (`main_supersaurus/baseline.ipynb`, célula 10, `best_threshold`), e o TF-IDF é ajustado sobre o próprio corpus A∪B do teste (célula 8). As colunas de predição existem só na execução 1 (e na 2 do Gemini); nas demais execuções, o F1 médio±dp da Tabela 1 não é recomputável sem rodar o notebook |
| 7 | Inconsistências entre arquivos de pares | **Sim — esclarecido** | `benchmark/labeled_pairs/pairs_raw.csv`: 210 linhas, todas `label=0`, só "geladeira"/"ventilador". `pairs_normalized.csv`: 835 linhas = **225 pares únicos (15 positivos)** repetidos por variantes de ataque. Os 129 "positivos" são linhas, não pares, e **nenhum** desses pares ou títulos aparece no benchmark de 1.200. `main_supersaurus/dados/pairs_to_label.csv`: 1.200 linhas, 30 positivos, um rótulo `' 0'` | **Arquivo canônico: `main_supersaurus/dados/pairs_to_label.csv`**, o único com 30 positivos e o usado por `dados/pairs_normalized*.csv` e `baseline_predictions.csv` (mesma ordem de linhas). **Nova inconsistência:** `main_supersaurus/data/pairs_to_label.csv` (versionado, `TAIL/.gitignore` "!main_supersaurus/data/pairs_to_label.csv") tem **28** positivos e diverge em **4 rótulos** (linhas 629, 1081, 1130, 1183). O README (`TAIL/README.md:25`, `:113-117`) aponta o dataset de 1.200 pares para o lugar errado |
| 8 | Dados de treino candidatos | **Parcial — ver tabela 1.1** | Contagens abaixo | Não existe nenhum conjunto de **pares rotulados para treino**. O pool de 30 mil, o dump de 20 milhões, `data/train.csv` (`RUN.md:84`, `:276`) e `finetune_dataset_augmented.jsonl` (`RUN.md:251`) **não estão em disco** |
| 9 | Fine-tuning gerativo anterior com Phi-3.5-mini | **Parcial — corrigido** | `main_supersaurus/finetune_nfe_colab.ipynb` célula 6: `MODEL_NAME = "unsloth/Phi-3.5-mini-instruct"` ativo; **`Llama-3.2-3B-Instruct`** e `Qwen2.5-3B-Instruct` comentados; `LOAD_IN_4BIT = True`. Commit `5f5b123` "Finetune Llama3.2 e Phi-3.5" (2026-06-14). `poc_supersaurus/finetune_nfe_colab.ipynb`: Qwen2.5-3B. `RUN.md:243-268` descreve Qwen2.5-3B | É **destilação** das saídas do Gemini (alvo = JSON de atributos), QLoRA de 4 bits, avaliada por constância e concordância de campos **contra o Gemini**, não contra rótulo humano. Saídas no notebook: Phi FT constância 34,4% × ZS 31,8%; concordância 71,2% × 58,4% (50 originais, 238 registros; a tabela rotula erroneamente como "Qwen-mini"). Qwen2.5-3B: 44,3% × 40,7%; 65,4% × 61,2% (20 originais). **Os resultados do LLaMA 3.2 3B, o mesmo modelo-base do TCC, não estão no repositório** (`results_finetune.md` aponta para uma pasta do Google Drive) |
| 10 | `attack_augmentation` ~ papel do Dataset Generator | **Sim** | `poc_camarasaurus/scripts/attack_augmentation.py:30` (Gemini 2.5 Flash), `:73` (`temperature=0.7`), `:105` (100 títulos); 6 variantes por título em 3 tipos | É um **gerador por LLM, não determinístico**, da mesma classe de risco do Dharma Generator. Em `attack.csv`, **90 de 601 linhas** são `Fallback_Erro_LLM` (variante = cópia do original). Há também um gerador **por regras** (`poc_diplodocus/scripts/attack_augmentation.py:39-82`: typos QWERTY, `drop_words`, caixa) |
| 11 | Harness e baselines reaproveitáveis; predições salvas permitem recomputar sem API | **Parcial — com ressalvas importantes** | `benchmark/pairwise_f1.py:14-19` implementa **só o exact match** e exige colunas `normalized_a/b`; a variante **Weighted** (a do melhor resultado) vive só em `benchmark.ipynb` (células 18/20, `SIMILARITY_THRESHOLD = 0.90`); a significância com bootstrap por cluster (1.196 clusters) está em `revisao/gerar_numeros.py:43-137`. `scripts/reproduce.py:32` lê `data/attack.csv` (inexistente na raiz) e `:39` avalia sobre `pairs_raw.csv` (210 negativos) | **`reproduce.py` não reproduz a Tabela 2 como está.** Recomputar a partir das predições salvas funciona (fato 6) |
| 12 | Sem LICENSE; BibTeX incompleto; autorização verbal | **Sim** | `ls TAIL/` sem LICENSE; `README.md:136-138` "academic research purposes"; `README.md:128-133` com `author={...}`, `booktitle={...}` | O PDF está **untracked no próprio repositório da TAIL** (`git status`: `?? "TAIL - Title Attribute Inference Layer.pdf"`). **[INF]** Provavelmente é um manuscrito não publicado. `TAIL/.gitignore` ignora `nda_*.json`, o que indica existir dado sob NDA no contexto da TAIL. `octaprice_mercadolivre_*.json` contém **avaliações de usuários** do MeLi (`date`, `rating`, `content`, `product_url`) |
| 13 | `invoice-data-normalizer/` está untracked no TCC | **Sim** | `git status` inicial: `?? invoice-data-normalizer/`; `du -sh`: 122 MB (`.git` 9,8 MB) | O `*.pdf` (`.gitignore:109`) não protege o restante. Um `git add .` adicionaria um repositório aninhado (gitlink) ou, se forçado, ~52 MB de avaliações de usuários |

### 1.1 Inventário real de dados da TAIL em disco

| Arquivo | Linhas / estrutura | Natureza | Serve para treinar um Cross-Encoder? |
|---|---|---|---|
| `main_supersaurus/dados/pairs_to_label.csv` | 1.200 pares, 30 positivos | Rótulo humano (SKU), marketplace | **Não** (é o teste; TAIL p.9) |
| `main_supersaurus/dados/pairs_normalized*.csv`, `baseline_predictions.csv` | 1.200 × 19–22 colunas | Predições de Gemini, GPT, DeepSeek e TF-IDF | Não. São **baselines prontos** para comparação pareada |
| `benchmark/labeled_pairs/*` | 225 pares únicos (15 positivos), 2 categorias | Mini-benchmark anterior, positivos sintéticos | Marginal (pequeno, positivos construídos) |
| `poc_diplodocus/data/input/old_attack_dataset.csv` | 43.047 linhas = 9.610 originais × ~4,5 variantes | Pares original↔variante (MeLi; 3.072 originais coincidem com slugs do `octaprice`). **[INF]** gerado pelo script de regras | **Sim, só positivos** produto×produto; negativos precisam ser minerados |
| `poc_*/data/input/attack.csv` | 601 linhas = 100 originais × 6 (90 fallback) | Variantes geradas por LLM | Positivos, poucos e com 15% de cópias triviais |
| `poc_*/data/input/test.csv` | 9.610 títulos (coluna `title`) | Títulos MeLi sem rótulo | Fonte para gerar pares |
| `poc_apatosaurus/data/AmostraDescMerc.csv` | 15.000 textos; `alimentos`, `matlimpeza`, `cosmeticos` (5.000 cada) | Descrições de NF-e, **o único ativo próximo do domínio de supermercado** | Sem rótulo de par; proveniência e licença desconhecidas |
| `poc_camarasaurus/data/initial/itens_nf_normalizados.csv` | 190 títulos → **19** nomes canônicos | Supervisão gerativa (título → nome) | Pequeno demais. `train_supervised` (152) e `test_supervised` (38) saem dele por `train_test_split` por **linha** (`generate_datasets.py:66`): **os 19 produtos estão nos dois lados** (vazamento) |
| `poc_*/data/initial/octaprice_mercadolivre_{1,2}.json` | 103.476 avaliações cada; 5.658 e 12.427 URLs únicas; duplicados entre as POCs | Avaliações de usuários do MeLi | Não (só um slug de título via URL; risco legal) |

**Sobreposição com o benchmark [FATO]:** 0 títulos normalizados do benchmark de 1.200 aparecem em qualquer uma dessas fontes. Não há contaminação nos dados em disco. Se a TAIL fornecer o pool de 30 mil, os 2.267 títulos do benchmark sairão dele, e a exclusão vira obrigatória.

---

## 2. Comparabilidade TAIL × TCC

| Dimensão | TAIL | TCC (proposta v3) | Comparável? | Como tornar comparável |
|---|---|---|---|---|
| Tarefa | Extrair atributos → chave → igualdade/similaridade da chave | Classificação binária de pares (Cross-Encoder) | Só na decisão final par a par | Rodar o Cross-Encoder sobre **os mesmos 1.200 pares brutos** (`title_a`, `title_b`) |
| Par avaliado | Produto×produto (marketplace) | Produto×canônico (principal) + produto×produto (suplementar) | **Só a fatia produto×produto** | Reportar o benchmark TAIL como "teste externo produto×produto, regime SKU", em tabela separada (como já exige `avaliacao-baselines` l.22) |
| Definição de match | Mesmo SKU (TAIL p.5) | Produto genérico na fatia principal (`spec 001:31-33`) | Não na fatia principal | Regime SKU para produto×produto, **já adotado pelo autor** (Decisão 1; §7, D-3); falta escrevê-lo no protocolo |
| P/R/F1 | Sobre os 1.200 pares; recall condicionado aos candidatos amostrados (TAIL p.5, p.7) | Sobre o teste anotado | **Sim**, se forem os mesmos pares e a mesma contagem | Implementar no harness do TCC e validar com um *golden test* que reproduza 20/1/10, 13/15/17, 16/26/14, 20/17/10 e 19/18/11 (fato 6) |
| McNemar | Exato, pareado (TAIL p.9) | ADR-0008 | **Sim** — predições por par salvas | Tabela de contingência sobre as linhas de `baseline_predictions.csv` (mesma ordem de `pairs_to_label.csv`) |
| IC | Bootstrap pareado **por cluster** (1.196 clusters, `revisao/gerar_numeros.py:43`) | Não especificado | Sim | Adotar o bootstrap por cluster no benchmark TAIL e reportar ao lado do bootstrap simples |
| Limiar | Gemini: sem limiar (exact) e fixo em 0,90 (weighted); TF-IDF: **ajustado no teste** | Limiar do Cross-Encoder (probabilidade) | Assimétrico | Fixar o limiar do Cross-Encoder na **validação do TCC**, nunca no benchmark TAIL; reportar TF-IDF "como publicado (otimista)" e com limiar vindo da validação do TCC; acrescentar PR-AUC (livre de limiar, já calculado em `baseline.ipynb`) |
| MRR, Recall@K | Inexistente | Pós-blocagem sobre o dicionário (ADR-0006) | **Não** | Não se aplica ao benchmark TAIL (os pares são dados, não há ranqueamento) |
| Blocagem | Veto numérico pós-normalização; `difflib` só para **amostragem** | TF-IDF/BM25 para candidatos (ADR-0006) | Não (termos homônimos) | Explicitar no texto; sobre o benchmark TAIL o Cross-Encoder pontua os 1.200 pares sem blocagem |
| Constância por grupo | 26 grupos, 56 títulos (TAIL p.7) | — | Não | Fora de escopo |
| Estabilidade entre execuções | 3 execuções, temperatura 0 (TAIL p.10) | — | Não diretamente | No máximo, nota de que o Cross-Encoder é determinístico na inferência |
| Zero-shot | Gemini, GPT, DeepSeek (APIs, porte grande) | LLaMA 3.2 3B ZS, mesmo checkpoint (ADR-0008) | Complementares | Os LLMs da TAIL entram como **baselines externos adicionais**; não substituem o LLaMA ZS (`avaliacao-baselines` l.23) |
| Reprodutibilidade | `reproduce.py` quebrado para a Tabela 2 (fato 11); LLMs não determinísticos | Seeds e configs versionados | — | Fixar o commit TAIL `9d010ec` + SHA-256 dos CSVs usados |

---

## 3. Cenários A–D

| Critério | **A** Substituição total | **B1** Treino TAIL, teste ALTA | **B2** Treino ALTA, teste TAIL | **C** TAIL núcleo + ALTA externo | **D** ALTA principal + TAIL treino/teste externo (**recomendado**) |
|---|---|---|---|---|---|
| O que o Cross-Encoder aprende | Produto×produto SKU, marketplace | Produto×produto SKU, marketplace | Produto×canônico genérico, PDV | Produto×produto SKU (núcleo) | Produto×canônico (ALTA) + produto×produto (ALTA + TAIL), com indicação do tipo de par na entrada |
| Pergunta de pesquisa da v3 (`main.tex:234`, `:389`) | **Invalidada** (deixa de ser supermercado/ALTA) | Muda para transferência de domínio | Parcial: hipótese testada fora do domínio | Muda (núcleo marketplace) | **Mantida**; ganha a sub-questão "SLM fine-tuned × LLMs zero-shot de grande porte" |
| Teste principal e poder | 30 positivos (IC F1 ~±13 p.p.), ou um conjunto novo a anotar | Teste ALTA (~300–500 pares, como planejado) | 30 positivos | 30 positivos + ALTA | Teste ALTA (~300–500) + benchmark TAIL como teste **secundário**, reportado como exploratório |
| Conflito de definição de match | Nenhum interno, mas rompe com o protocolo atual | **Grave**: treino SKU × teste genérico (tamanho = match) | **Grave**: modelo genérico em teste SKU | Grave entre os dois domínios | Controlado: cada regime fica na sua fatia; precisa de um marcador do tipo de par (risco R4) |
| Anotação adicional | Novo teste sobre o pool MeLi (**ausente**) + reteste | Nenhuma além do plano | Nenhuma além do plano | Novo teste MeLi **+** teste ALTA | Nenhuma além do plano; opcional: 2º anotador TAIL sobre ~25–50% do teste ALTA |
| Reaproveita | Quase nada da EDA; ADR-0010/11/12 viram letra morta | Scripts 01/02, EDA, ADRs | Tudo | Scripts 01/02, EDA | **Tudo** o que já foi feito |
| Descarta | Script 02 (1.202 linhas), notebooks, tabelas de EDA, §4.7, o protocolo e a justificativa do ADR-0002 (continuidade ALTA, `main.tex:292`) | Nada | Nada | Pouco | Nada |
| Dependência externa | TAIL: pool/dump + licença | TAIL (dados) | TAIL (rótulos) | TAIL + ALTA | TAIL (rótulos + títulos) — **pode tirar o Dharma Generator do caminho crítico** (D7-1/D11) |
| Efeito no cronograma (premissa §0) | +4–6 semanas e nova aprovação da proposta → **não cabe** | +2–3 semanas | +1 semana | +5–7 semanas → **não cabe** | **+1 a 1,5 semana de engenharia, paralelizável à anotação**; o harness TAIL pode adiantar a Fase 2 |
| Veredito | Inviável | Viável, cientificamente fraco | Viável, fraco | Inviável | **Viável** |

**Recomendação: D.** É o único cenário que (a) cumpre a decisão do autor de treinar com dados TAIL e comparar no benchmark TAIL, (b) mantém respondível a hipótese aprovada, (c) não põe trabalho novo no caminho crítico, que já está atrasado, e (d) responde a dois pontos do parecer: segundo anotador (rec. 2) e insuficiência empírica dos clássicos (rec. 5, com os números da TAIL como evidência externa). O preço é aceitar que o benchmark TAIL fica como resultado **secundário e exploratório**, e não como o teste principal.

**Variante D′ (registrar, não recomendar agora):** o teste principal passa a ser um conjunto MeLi novo, rotulado pelo autor conforme o protocolo. Exige o pool da TAIL e muda o domínio, o que leva aos custos de A.

---

## 4. Mapa de impacto por artefato (cenário D)

Efeito: **I** = invalida, **A** = altera, **M** = mantém. Esforço: P (< 1 dia), M (1–3 dias), G (> 3 dias). A coluna "ação" indica o delta em A/C quando ele é muito diferente.

### 4.1 Escopo e hipótese

| Artefato | Hoje diz | Efeito | Ação mínima | Esf. | Bloqueia |
|---|---|---|---|---|---|
| Título | `main.tex:70` "…Produtos de Supermercado…" | M (em A: I) | Nenhuma | — | — |
| Objetivo geral | `main.tex:234` "…em dados reais do projeto ALTA/CNPq" | A | Acrescentar a comparação externa com LLMs zero-shot de grande porte | P | Aprovação do orientador |
| Objetivos específicos | `main.tex:240-247` | A | Item novo: avaliar em benchmark externo (TAIL) contra LLMs zero-shot; o item 1 passa a citar a fonte TAIL no treino | P | idem |
| Pergunta/hipótese central | `main.tex:389` | M + A | Manter H1; acrescentar H2 **exploratória** (fine-tuned × Gemini zero-shot no benchmark TAIL), declarando o poder limitado | P | idem |
| Delimitação (ADR-0007) | `main.tex:194-196`; ADR-0007:9, :12 | **A** (em A: I) | Reescrever: a transitividade vale **só para categoria**; produto×produto em nível SKU é decidido pelo modelo, treinado com os dois tipos de par (some o "sem retreino"). Só a fatia produto×produto é comparável à TAIL | M | Aprovação do orientador |
| §1, marcador dos baselines | Na `HEAD`, `main.tex:189` tinha "[resultado sumário… a inserir]"; na **árvore de trabalho** (não commitada) já virou hipótese | A | Os números da TAIL (TF-IDF 0,597/0,567 × Gemini 0,784) podem ser citados como evidência **externa** de insuficiência dos clássicos, com a ressalva de domínio | P | Autorização TAIL + referência verificada |
| Lacuna | `main.tex:225`, `:384` "Não foi identificado trabalho de EM de produtos… em PT-BR" | **A** | Matizar: a TAIL (EM via normalização, PT-BR, marketplace) e o AI-PAVE-Br (extração, PT-BR) existem; a lacuna se restringe a "PDV de supermercado + SLM fine-tuned discriminativo" | P | Verificação das referências |
| Relevância | `main.tex:380` | M | — | — | — |

### 4.2 Dados

| Artefato | Hoje diz | Efeito | Ação mínima | Esf. | Bloqueia |
|---|---|---|---|---|---|
| Origem dos dados | `CLAUDE.md:7`, `:9`; `dados/brutos/README.md:7-36` | A | Nova seção "Dados TAIL": commit `9d010ec`, arquivos usados, SHA-256, licença/autorização, versão canônica dos rótulos | P | Autorização TAIL |
| Base ALTA, limpeza | `docs/limpeza_dados.md`; ADR-0012 | M | — | — | — |
| Partição | `CLAUDE.md:53`; spec 001 RF6 (`:16`); `main.tex:285` | A | Para dados TAIL, a unidade de partição é o **grupo do título original** (original + todas as variantes + positivos ligados por union-find), sempre **antes** de gerar negativos ou aumentar | M | Script 03 |
| Vazamento entre variantes | — (não previsto) | A (novo) | Assert: nenhum original/grupo em mais de uma partição; nenhum título do benchmark TAIL (normalizado **e** quase-duplicado, ex. sufixo `#xxxx`) no treino/validação | M | Script 03 |
| Proveniência/licença | `main.tex:331`; `dados/brutos/README.md:36` | A | Acrescentar a TAIL às autorizações (ver §4.9) | P | D-1 |
| Versionamento | `.gitignore:74-81` | A | Decidir o tratamento de `invoice-data-normalizer/` (§4.9, D-8) | P | Commit seguro |

### 4.3 Ground truth e anotação

| Artefato | Hoje diz | Efeito | Ação mínima | Esf. | Bloqueia |
|---|---|---|---|---|---|
| ADR-0004 | Gerador = Dharma, só treino; teste manual ALTA (`0004:9-11`, `:16`) | **A → substituir por ADR-0013** | Generalizar: **nenhum gerador ou LLM** (Dharma, `attack_augmentation` da TAIL, LLM-as-judge, predições Gemini da TAIL) produz ou rotula teste; o rótulo humano da TAIL é admitido como **teste externo**; as variantes de ataque são só treino | P | Tudo que é treino |
| Restrição no `CLAUDE.md` | `CLAUDE.md:50` cita só o Dharma | A | Generalizar o texto junto com o ADR-0013 | P | — |
| ADR-0005 | Teste-reteste, sem 2º anotador por indisponibilidade (`0005:20`) | A (oportunidade) | Integrante da TAIL **sem acesso ao pipeline do TCC** anota um subconjunto do teste ALTA → Kappa inter-anotador real (rec. 2 do parecer). O benchmark TAIL não tem confiabilidade medida: declarar | P | D-6 |
| Protocolo §2/§3 | `protocolo_anotacao.md:6`, `:21`, `:27`, `:46` | **A** | Tarefa 1.3: escrever as **duas regras já decididas** (produto×dicionário = categoria e variante; produto×produto = SKU com marca e tamanho); remover `:21`; reescrever os exemplos da §6, que hoje misturam os regimes; separar as regras de marca (§3.3, só produto×produto) | M | Anotação (1.4) |
| Volume a anotar | Plano 1.4: ~250–450 + 50–100 (`plano:375-376`) | M | Inalterado em D. Em A/C: +300–500 pares MeLi + reteste ≥50% | — | — |
| Rótulos da TAIL | Duas versões (fato 7) | A | Fixar `main_supersaurus/dados/pairs_to_label.csv` (30 positivos) **após confirmação da TAIL**; normalizar `' 0'`; nunca editar | P | D-4 |
| Rotular pares TAIL pelo autor? | — | Opcional | Reanotar às cegas os 224 do estrato `match` dá a concordância Pedro×TAIL. **Não substitui** o rótulo TAIL na comparação com os números publicados | M | — |

### 4.4 Benchmark e métricas

| Artefato | Hoje diz | Efeito | Ação mínima | Esf. | Bloqueia |
|---|---|---|---|---|---|
| Spec 002 | 5 clássicos + LLaMA ZS + "ALTA atual" = 7 métodos (`spec 002:10-13`, `:20`) | A | Nova seção "Benchmark externo TAIL": clássicos sem blocagem sobre os 1.200 pares; LLaMA ZS; Gemini, GPT, DeepSeek e TF-IDF TAIL **importados das predições salvas** | M | Script 04 |
| Spec 004 | McNemar + efeito + IC; ablação de 2 fatores (`spec 004:10`, `:12`) | A | Tabela separada para o benchmark TAIL com McNemar pareado e **bootstrap por cluster**; ablação "com/sem dados TAIL" como fator candidato | M | Script 06 |
| Skill `avaliacao-baselines` | "mesma blocagem para todos" (l.21); "5 baselines + ZS" (l.21); ZS = mesmo checkpoint (l.23) | A | Regra para o teste externo: sem blocagem (pares dados); limiar nunca ajustado no teste; os LLMs TAIL são baselines externos e não substituem o ZS | P | — |
| `pairwise_f1.py` da TAIL | Só exact match (`pairwise_f1.py:14-19`) | — | **Não reusar como está.** Reimplementar P/R/F1 a partir de uma coluna de predição binária e validar com o *golden test* (fato 6). Como não há LICENSE, copiar código exige permissão | P | D-1 |
| Recall@K/MRR | ADR-0006:14; `main.tex:316` | M | Só para o teste ALTA produto×canônico; declarar "não aplicável" no benchmark TAIL | P | — |
| Limiar TF-IDF da TAIL | Ajustado no teste (TAIL p.8; `baseline.ipynb` c.10) | A | Reportar os dois: "como publicado" e "limiar da validação do TCC" | P | — |
| Pipeline progressivo | `spec 004:13`; `main.tex:327` | M | Opcional: também sobre o benchmark TAIL | — | — |

### 4.5 Modelo e treino

| Artefato | Hoje diz | Efeito | Ação mínima | Esf. | Bloqueia |
|---|---|---|---|---|---|
| ADR-0001 | Cross-Encoder único | M (pressionado) | Os dados TAIL são naturalmente **gerativos** (título → nome/atributos), e a TAIL já tentou destilar. Não reabrir: só pares entram no treino | — | — |
| ADR-0002 | LLaMA 3.2 3B; justificativa de exclusão de 10–30B = continuidade ALTA (`0002:19`, `:22`; `main.tex:292`) | M (em A: **revisar**) | Em D, nada muda. Citar como antecedente que a TAIL testou LLaMA 3.2 3B, Phi-3.5 e Qwen2.5 **gerativos** com ganhos pequenos (fato 9). Em A, a justificativa central cai junto com a ALTA, e esse era o "ponto mais frágil" do parecer | P | — |
| ADR-0003/0009 | LoRA bf16; contingência Colab/Gemma | M | — (a TAIL usou QLoRA de 4 bits em T4/L4, o que não muda o ADR) | — | — |
| Spec 003 | RF2 "mesmo formato na avaliação" (`spec 003:11`) | A | Formato de entrada com **marcador do tipo de par** (`[CANÔNICO]`/`[PRODUTO]`), porque os regimes de rótulo diferem; config de mistura de fontes (ALTA, TAIL) versionada | P | Script 05 |
| Volume de treino | Generator + supervisão distante + aumento (`main.tex:277`) | A | A TAIL fornece **positivos produto×produto** (até ~43 mil pares de variantes, 9.610 grupos) e títulos para minerar negativos difíceis. **Não** fornece pares produto×canônico. `train_supervised` (152) é inútil (19 produtos, vazado) | M | D-5 |
| Destilação do Gemini | — | Proibir se o Gemini for baseline | Não usar predições/chaves do Gemini TAIL como rótulo de treino enquanto o Gemini for comparação no benchmark (aluno × professor, comparação circular) | — | — |

### 4.6 Pipeline, código e testes

| Artefato | Hoje diz | Efeito | Ação mínima | Esf. | Bloqueia |
|---|---|---|---|---|---|
| `scripts/01_coleta_dados.py` | Valida e limpa só a ALTA (`:12-21`) | A | Ingerir os artefatos TAIL curados (lista fechada), com SHA-256 e commit no relatório, `strip()` nos rótulos; ALTA inalterada | M | 03 |
| `scripts/02_analise_exploratoria.py` | EDA ALTA (1.202 linhas) | M (em A: I) | Opcional: 1–2 números de caracterização da TAIL (fração de mercearia, comprimento) | P | — |
| `scripts/03_construcao_dataset.py` | Esqueleto; Generator e partição (`:29-32`) | A | Construtor de pares TAIL (positivos de variantes + negativos minerados), partição por grupo **antes** da geração, asserts de vazamento (§4.2) | M | 04/05 |
| `scripts/04_baselines.py` | `BASELINES` (`:40`) | A | Avaliação no benchmark externo + importação das predições TAIL | M | 06 |
| `scripts/05_finetuning.py` | Esqueleto | A (leve) | Marcador do tipo de par; mistura de fontes via YAML | P | — |
| `scripts/06_avaliacao_exportacao.py` | `comparar_com_baselines` (`:49`) | A | Tabela externa, McNemar contra as predições TAIL, bootstrap por cluster, exportação para `latex/` | M | Escrita |
| `tests/` | 01/02 cobertos; integração `test_integracao_pipeline.py:34`, `:306` | M + A | Novos: *golden test* da Tabela 2 TAIL (com fixture mínima, sem depender do clone); assert de grupo/vazamento; normalização do rótulo `' 0'` | M | — |
| ADR-0010/11/12 | Colunas ALTA | M (em A: obsoletos) | — | — | — |
| `Makefile`/`pyproject.toml` | Deps atuais cobrem pandas, sklearn, statsmodels | M | Nenhuma dependência nova (o `difflib` é stdlib) | — | — |
| Harness TAIL | `inference_harness/` (Gemini/Qwen, Python 3.11, `google-generativeai`) | — | **Não integrar.** O TCC exige Python ≥3.14 (`pyproject.toml:15`), e o harness não tem licença. Reusar só **ideias documentadas** (amostragem por estratos, veto numérico) com citação | — | — |

### 4.7 Artigo (`main.tex`)

| Seção | Hoje | Efeito (D) | Ação mínima |
|---|---|---|---|
| Resumo/Abstract | `:102`, `:109` | A | Uma frase sobre o benchmark externo; manter o resto |
| Introdução | `:168-196` | A | Parágrafo: na mesma instituição, um pipeline zero-shot com LLMs (TAIL) atinge F1 0,784 em marketplace; a questão é se um SLM fine-tuned compete a custo menor. A delimitação (`:194-196`) é reescrita conforme a Decisão 1: transitividade só para categoria, sem "sem retreino" |
| Revisão | `:215-225` | A | Subseção "EM e normalização de produtos em PT-BR com LLMs" (TAIL + candidatas verificadas); matizar a lacuna (`:225`) |
| §4.1 Dataset | `:275-285` | **A** | Fontes de treino (ALTA + TAIL); regra de gerador generalizada; partição por grupo de original para a TAIL; definição de match por tipo de par; papel e limites do benchmark TAIL |
| §4.2 Modelo | `:290-306` | M | — |
| §4.3 Blocagem | `:314-316` | A (nota) | Distinguir do "*blocking*" da TAIL; o benchmark externo não passa por blocagem |
| §4.4 Avaliação | `:321-323` | A | Avaliação externa pareada, bootstrap por cluster, política de limiar |
| §4.5 Pipeline progressivo | `:327` | M | — |
| §4.6 Reprodutibilidade | `:331` | A | Commit `9d010ec`, SHA-256, condição de autorização TAIL |
| §4.7 Caracterização | `:336-358` | M | (Opcional) um parágrafo sobre a composição do benchmark TAIL |
| Cronograma | `:365-371`; `tabelas/tab_cronograma_execucao.tex` | A | Replanejar (§8); vira relato no TCC final (spec 005 RF1) |
| §6.4 Horizonte | `:393` | A | Novo marcador `[a confirmar]` para a autorização TAIL |
| Trabalhos futuros | `:403-406` | A | Avaliação plena em marketplace com conjunto rotulado próprio (o que a TAIL p.12 também propõe) |
| `fig_pipeline.tex` | `:15` dicionário | A | Caixa "benchmark externo TAIL" na saída de avaliação |

**Referências — candidatas a verificar, nenhuma adicionada.** Pela skill `verificacao-citacoes`, nada entra em `referencias.bib` só por constar na lista da TAIL (p.12). Já auditado e presente: Li et al. 2020 (Ditto, `li2020`). **Candidatas** (dados conforme a TAIL, **não verificados**):

| Referência (como citada pela TAIL) | Relevância para o TCC |
|---|---|
| Zhang, Groth, Calixto, Schelter (2025), EDBT, pp. 922–934 — EM *cross-dataset* com LLMs e SLMs | **Alta** (SLMs em EM; variação entre modelos) |
| Brinkmann, Baumann, Bizer (2024), ADBIS, LNCS 14918, pp. 217–230 | Média (normalização de atributos com LLM) |
| Brinkmann, Shraga, Bizer (2023), arXiv:2310.12537 | Média |
| Fan et al. (2024), ICDE, pp. 3696–3709 — *in-context learning* para ER | Média (custo de LLM em ER) |
| Gazzola et al. (2025), STIL, pp. 149–160 — AI-PAVE-Br | Média (PT-BR, produtos; afeta a lacuna) |
| More (2016), arXiv:1608.04670 | Baixa–média |
| Neres de Sousa et al. (2025), SBBD; Zheng et al. (2023), NeurIPS | Baixa |
| **O próprio artigo TAIL** | Necessária, mas hoje **não verificável**: BibTeX com placeholders (`README.md:128-133`), PDF não versionado, sem venue. Fica `[VERIFICAR]` até haver publicação ou uma forma de citação aprovada pela TAIL |

Qualquer mudança de escopo em `main.tex` exige **aprovação do orientador**: a v3 é a fonte de verdade (`CLAUDE.md:11`).

### 4.8 Skills, rules e docs

| Artefato | Hoje diz | Efeito | Ação mínima |
|---|---|---|---|
| `CLAUDE.md` | Projeto (`:7`, `:9`); restrição só do Dharma (`:50`); script 03 com Generator (`:28`) | A | Fontes TAIL; restrição generalizada; ADR-0013 |
| `AGENTS.md` | Tabela §2 (`:20-29`) | A | Entradas TAIL do 01/03/04 |
| `docs/plano_desenvolvimento.md` | D1–D19, fases e cronograma | A | Novos itens D20+ (§7) e replanejamento (§8) |
| `scripts/README.md` | Restrições (`:49`) | A | Generalizar o gerador; mencionar a TAIL |
| `dados/brutos/README.md`, `dados/processados/README.md` | Só ALTA | A | Seção TAIL; novas saídas (`pares_tail_*`) |
| Skill `reprodutibilidade-ml` | Só o Dharma (l.16); partição por produto canônico (l.15) | A | Unidade de partição para a TAIL; regra de gerador generalizada |
| Skill `dominio-entity-matching` | Blocagem (l.9); vazamento (l.14) | A | Homonímia de "*blocking*"; vazamento por variantes |
| Skill `protocolo-anotacao-em` | Regra geral SKU-like (l.11); regime genérico (l.24-25) | A | Sincronizar com a tarefa 1.3 (regime por tipo de par) |
| Skill `avaliacao-baselines` | ver §4.4 | A | idem |
| Skill `verificacao-citacoes` | Lista auditada (l.18) | M | Só cresce após verificação |
| Skill `abnt-latex` | — | M | — |
| `.cursor/rules/pipeline-python.mdc` | "Dataset Generator nunca toca o teste" (l.13) | A | Generalizar |
| `.cursor/rules/specs-e-adrs.mdc`, `latex-abnt.mdc` | — | M | — |
| `docs/diario_pesquisa.md` | Uma entrada (2026-09-17) | A | Registrar a conversa com a TAIL e esta análise |

### 4.9 Legal, autoria e versionamento

| Item | Situação | Efeito | Ação mínima |
|---|---|---|---|
| Licença do repositório TAIL | Sem LICENSE; "academic research purposes" (`README.md:136-138`) | **Risco** | **[INF]** Sem licença, código e dados ficam com todos os direitos reservados por padrão. Uso, cópia e publicação de números exigem **autorização escrita** que nomeie os artefatos |
| Dados MeLi | Dump de 20 milhões (ausente); avaliações de usuários em `octaprice_*.json` | **Risco** | Perguntar a origem (API, *scraping*, parceria "Octaprice"?) e os termos. Não usar `octaprice_*.json` no TCC. **Não verifiquei** os termos de uso do MeLi |
| NF-e (`AmostraDescMerc`, `itens_nf`) | Proveniência desconhecida; `nda_*.json` no `.gitignore` da TAIL | Risco | Só usar com origem e licença declaradas pela TAIL |
| Artigo TAIL | Não publicado (**[INF]**); 7 autores (TAIL p.1), Pedro não está entre eles | — | Citar como trabalho da TAIL; se os resultados de fine-tuning (Drive) forem mencionados, só com permissão |
| Coautoria | TCC individual; artigo derivado (`main.tex:247`, plano 6.4.1) | Decidir | O TCC leva agradecimento + citação. O artigo de conferência que usar o benchmark TAIL deve ter a coautoria ou o agradecimento **combinados por escrito** antes da submissão |
| Abertura (§4.6, `main.tex:331`) | Já condicionada à ALTA e à Dharma | A | Acrescentar a TAIL. Não redistribuir o benchmark nem as predições TAIL no repositório do TCC sem permissão: referenciar o repositório e o commit |
| D7-1 / D11 (Dharma Generator) | Bloqueavam a Semana 6 (`plano:135`, `:173`) | **A** | Em D, se o Generator for substituído por aumento próprio + variantes TAIL (D-5), saem do caminho crítico; a GPU Dharma (ADR-0003) continua |
| D7-2 (ALTA) | Abertura dos dados/teste | M | Continua necessária em B, C e D; some só em A |
| `invoice-data-normalizer/` untracked | 122 MB, `.git` próprio | Risco de commit acidental | **Recomendação (D-8):** (1) `.gitignore` do clone inteiro; (2) cópia **curada** dos poucos artefatos usados para `dados/brutos/tail/` (já ignorada pela regra `dados/brutos/*`), com SHA-256 e commit `9d010ec` registrados pelo script 01. **Submódulo:** só se a TAIL licenciar o repositório; ele aponta para um repositório que pode mudar ou fechar e arrasta 52 MB de avaliações de usuários |

---

## 5. ADRs

| ADR | Decisão | Justificativa (1 linha) |
|---|---|---|
| 0001 Cross-Encoder único | **Mantém** | Os dados TAIL pressionam rumo ao gerativo, mas D só consome pares |
| 0002 LLaMA 3.2 3B | **Mantém** (A: revisar) | A justificativa pela continuidade ALTA segue válida em D; em A ela cai |
| 0003 LoRA bf16 | **Mantém** | Independe dos dados |
| 0004 Ground truth treino/teste | **Substituir (ADR-0013)** | Novas fontes de treino; a regra "nenhum gerador no teste" precisa cobrir o *attack* TAIL, LLM-as-judge e as predições de LLM; entra o teste externo humano |
| 0005 Teste-reteste | **Revisar** | 2º anotador agora disponível (TAIL) → Kappa inter-anotador; o benchmark TAIL não tem confiabilidade |
| 0006 Blocagem TF-IDF/BM25 | **Mantém** (+ nota) | Não se aplica ao benchmark externo; desfazer a homonímia com o "*blocking*" TAIL |
| 0007 Escopo catálogo-dicionário | **Revisar** (A: invalida) | A tarefa central continua, mas a transitividade vale só para categoria e o "sem retreino" cai (Decisão 1) |
| 0008 McNemar + efeito + IC | **Mantém** (emenda leve no ADR-0013) | Acrescentar o bootstrap por cluster e a leitura do McNemar com 2,5% de positivos |
| 0009 Contingência | **Mantém** | Independe dos dados |
| 0010 Colunas proibidas | **Mantém** (A: obsoleto) | ALTA permanece |
| 0011 Papéis das colunas / baseline ALTA | **Mantém** (A: obsoleto) | idem |
| 0012 Limpeza no 01 | **Mantém** (A: obsoleto) | idem; o 01 também passa a ingerir a TAIL curada |

### 5.1 Esboço do ADR-0013 (não criado)

> **ADR-0013: Incorporação dos dados e do benchmark da TAIL — treino adicional e teste externo**
> **Status:** Proposto — substitui o ADR-0004 nos pontos indicados; emenda os ADRs 0005, 0007 e 0008.
>
> **Contexto.** Um projeto da TAIL (UFPB) publicou internamente um pipeline zero-shot de normalização de títulos com LLMs, com um benchmark de 1.200 pares MeLi rotulados como "mesmo SKU" (30 positivos), predições por par de três LLMs e dois baselines TF-IDF, além de títulos e variantes sintéticas sem rótulo de par. O autor decidiu treinar o SLM também com dados da TAIL e usar o benchmark como comparação. O benchmark não tem tamanho para treino com avaliação independente (TAIL p.9), é de outro domínio e usa outra definição de match, e os ativos da TAIL não incluem pares produto×canônico.
>
> **Decisão.** (1) A ALTA continua sendo o domínio e o **teste principal** (ADR-0004, teste manual). (2) Dados TAIL entram **só no treino**, como pares produto×produto: positivos de variantes do mesmo original e negativos minerados, particionados **por grupo de original antes** de qualquer geração, com exclusão por assert dos títulos (e quase-duplicatas) do benchmark. (3) O benchmark TAIL (`main_supersaurus/dados/pairs_to_label.csv`, commit `9d010ec`, versão confirmada pela TAIL) é **teste externo produto×produto em regime SKU**, reportado à parte e como exploratório, com McNemar pareado contra as predições TAIL salvas e bootstrap por cluster; o limiar nunca é ajustado nele. (4) **Nenhum gerador ou LLM** (Dharma Generator, `attack_augmentation`, LLM-as-judge, predições Gemini/GPT/DeepSeek) produz ou rotula pares de teste ou de validação; as predições TAIL não são rótulo de treino enquanto forem baseline. (4b) **Duas regras de match por tipo de par:** produto×dicionário decide categoria e variante, sem marca e sem tamanho; produto×produto decide SKU, com marca e tamanho. A transitividade do ADR-0007 vale só para categoria, e o modelo é treinado com os dois tipos de par (marcador do tipo de par na entrada), sem a promessa de generalização "sem retreino". (5) [DECISÃO PENDENTE D-5] papel do Dharma Generator. (6) [DECISÃO PENDENTE D-6] 2º anotador TAIL para um subconjunto do teste ALTA.
>
> **Consequências.** Hipótese da v3 preservada; H2 exploratória. A fatia produto×produto adota o regime SKU no protocolo; o ADR-0007 é emendado (transitividade só para categoria; sem "sem retreino"). Specs 001–004, skills e `CLAUDE.md` são atualizados. As autorizações passam a incluir a TAIL. Risco assumido: com 30 positivos, só diferenças grandes (≳15–20 p.p. de F1) são distinguíveis no benchmark externo.
>
> **Alternativas consideradas.** A (substituição total), B1/B2 (cross-domain), C (TAIL como núcleo): rejeitadas por poder estatístico, conflito de definição de match e prazo (ver relatório §3).

---

## 6. Riscos metodológicos novos

| # | Risco | Evidência | Mitigação |
|---|---|---|---|
| R1 | **Poder estatístico** do benchmark TAIL | 30 positivos; o bootstrap simples do F1 do Gemini dá IC95% [0,64; 0,90] (meu cálculo, 10 mil reamostras, seed 0); Δ vs TF-IDF com IC [+1,1; +37,3] (TAIL p.9); **[INF]** erro-padrão do recall em 0,67 com n=30 ≈ 0,086 (±17 p.p.) | Tratar como **exploratório**; reportar contagens absolutas TP/FP/FN, IC por cluster e McNemar; não decidir hiperparâmetros com ele. O poder principal vem do teste ALTA. **[INF]** Com ~300–500 pares e ~40% de positivos, o erro-padrão do recall cai para ~±6–7 p.p. |
| R2 | **Positivos concentrados e triviais** | 12/30 em 3 famílias; 9/30 só diferem por `#xxxx` | Reportar também o F1 sem os pares de sufixo e por família (análise de sensibilidade, definida **antes** de ver os resultados) |
| R3 | **Rótulos instáveis** | 4/30 positivos divergem entre `dados/` e `data/`; anotador único; caso Sandisk admitido (TAIL p.8) | Fixar a versão com a TAIL por escrito; opcional: reanotação cega do estrato `match` por Pedro para medir a concordância |
| R4 | **Definição de match desalinhada** | SKU (TAIL) × genérico (TCC) | **Reduzido pela Decisão 1:** a fatia produto×produto passa a ser SKU, igual à TAIL. Resta: escrever as regras no protocolo, usar marcador do tipo de par na entrada e nunca misturar as fatias numa tabela |
| R5 | **Vazamento por variantes** | Na própria TAIL, `train/test_supervised` vazam os 19 produtos (`generate_datasets.py:66`) | Partição por grupo (union-find de original + variantes) antes da geração; asserts; exclusão de títulos do benchmark por texto normalizado **e** similaridade alta |
| R6 | **Viés de limiar nos baselines TAIL** | Limiar varrido no teste; TF-IDF ajustado em A∪B do teste | Dupla reportagem (publicado × limiar da validação); PR-AUC; o limiar do Cross-Encoder vem da validação |
| R7 | **Avaliação condicionada ao candidato** | Recall só sobre pares amostrados; 300 aleatórios sem positivos (TAIL p.11) | Declarar que o recall não estima a cobertura no catálogo |
| R8 | **Domínio** | ~1,7% de títulos de mercearia (heurística); 0/30 positivos | Não generalizar resultados do benchmark para supermercado; a TAIL no treino é **ablação mensurável** ("com/sem TAIL" no teste ALTA) e não premissa |
| R9 | **Circularidade aluno×professor** | Tentação de usar as saídas do Gemini como rótulo | Proibido no ADR-0013 enquanto o Gemini for baseline |
| R10 | **Prazo** | M1 (Semana 6) não cumprido; anotação não iniciada | D não acrescenta trabalho ao caminho crítico; cortar ablação primeiro (regra `main.tex:365`) |
| R11 | **Legal/autoria** | Sem LICENSE; autorização verbal | Autorização escrita antes de usar ou publicar qualquer número (§7, D-1) |

---

## 7. Decisões pendentes

| # | Decisão | Dono | Opções | Recomendação | Prazo sugerido |
|---|---|---|---|---|---|
| D-1 | Autorização TAIL por escrito | [PEDRO] → [TAIL] | (a) e-mail do líder; (b) e-mail do líder + ciência dos 7 autores/coordenação da liga | (b), com a lista de artefatos, os usos (treino, teste, publicação de números), a citação e a (não) redistribuição | Semana 8 |
| D-2 | Cenário de escopo | [AMBOS] → [ORIENTADOR] | A, B1, B2, C, D, D′ | **D** | Semana 8 (reunião extra) |
| D-3 | Regime de match produto×produto | [PEDRO] + [ORIENTADOR] | (a) SKU (tamanho e marca importam, alinhado à TAIL); (b) genérico | **DECIDIDO pelo autor em 2026-10-31: (a)**, junto com a regra genérica para produto×dicionário. Falta o orientador aprovar e a tarefa 1.3 escrever | Semana 8 (aprovação) |
| D-4 | Versão canônica dos rótulos TAIL | [TAIL] | `dados/` (30) × `data/` (28) | `dados/`, que reproduz o artigo; pedir confirmação e o porquê das 4 trocas | Semana 8 |
| D-5 | Papel do Dharma Generator | [PEDRO] + [ORIENTADOR] | (a) manter Dharma + TAIL; (b) substituir por aumento por regras próprio (com seed) + variantes TAIL já geradas; (c) só TAIL | (b): tira D7-1/D11 do caminho crítico e evita a não reprodutibilidade de LLM; muda `main.tex:102`, `:277` → precisa de aprovação | Semana 8 |
| D-6 | 2º anotador | [PEDRO] + [TAIL] | (a) nenhum (ADR-0005 como está); (b) um integrante TAIL em ~25–50% do teste ALTA, sem acesso ao pipeline | (b): responde à rec. 2 do parecer | Antes do início da anotação |
| D-7 | Calendário e prazo da defesa | [PEDRO] + [ORIENTADOR] | (a) manter a Semana 16; (b) prorrogar | Confirmar a premissa do §0; com (a), cortar a ablação para 1 fator e mirar ~300 pares | Semana 8 |
| D-8 | Tratamento de `invoice-data-normalizer/` | [PEDRO] | `.gitignore` / submódulo / cópia curada | `.gitignore` + cópia curada com hash (§4.9) | Antes do próximo commit |
| D-9 | Pedir à TAIL o pool de 30 mil e o dump | [PEDRO] | Pedir / não pedir | Não é necessário em D; pedir só se D′ for considerado | — |
| D-10 | Coautoria do artigo derivado | [AMBOS] + [TAIL] | Coautoria / agradecimento | Combinar por escrito antes de qualquer submissão | Antes da Semana 16 |
| D-11 | Uso de `AmostraDescMerc` (NF-e de supermercado) | [PEDRO] + [TAIL] | Usar como texto do domínio para supervisão distante / não usar | Só com proveniência e licença declaradas; senão, não usar | Semana 9 |
| D-12 | **(novo)** Como o modelo cobre os dois regimes de rótulo | [PEDRO] + [ORIENTADOR] | (a) um único modelo, treinado com os dois tipos de par e marcador do tipo na entrada; (b) dois adaptadores LoRA, um por tipo | (a): mantém "um Cross-Encoder" (ADR-0001) e um único conjunto de hiperparâmetros; (b) só se (a) mostrar interferência entre regimes. Ambos exigem emendar o ADR-0007 | Semana 8 |
| D-13 | **(novo)** Tamanho do teste produto×produto | [PEDRO] + [ORIENTADOR] | (a) manter 50–100 pares; (b) subir (ex.: ~150) | (b) se der tempo: a fatia agora é um regime próprio, e com poucos positivos ela fica sem poder estatístico (R1). Cada par a mais custa anotação, e a anotação é o caminho crítico | Antes da anotação |

---

## 8. Plano de ação sequenciado (cenário D, premissa do §0)

| Semana | Tarefa (numeração do plano quando existir) | Dono |
|---|---|---|
| **8** (02–08/nov) | Reunião extra com o orientador: D-2, D-3, D-5, D-7 (com este relatório) | [PEDRO] |
| 8 | Pedido escrito à TAIL: D-1, D-4, D-6, D-11 | [PEDRO] |
| 8 | Redigir o ADR-0013 após o aval do orientador; atualizar `CLAUDE.md:50`, as skills e as rules (§4.8) | [AMBOS] |
| 8 | D-8: `.gitignore` do clone; cópia curada + hash **só após** D-1 | [CURSOR] |
| 8 | **1.2 Blocagem ALTA** (atrasada, independente do cenário) e **1.3 protocolo** com o regime por tipo de par | [CURSOR] / [PEDRO] |
| **9** | **1.4 Anotação ALTA** começa, com piloto de Kappa (~50 pares); briefing do 2º anotador TAIL | [PEDRO] |
| 9 | **2.1 Harness** + *golden test* da Tabela 2 TAIL (adianta a Fase 2: os rótulos TAIL já existem) | [CURSOR] |
| 9–10 | Construtor de pares TAIL (script 03) com partição por grupo e asserts | [CURSOR] |
| 10 | Anotação continua; **2.2** clássicos sobre o benchmark TAIL | [PEDRO] / [CURSOR] |
| 11 | Fim da anotação; 1ª passada do reteste já fechada na Semana 9–10 para caber ≥7 dias; **1.6 partição ALTA**, **1.7 treino** (sem Dharma se D-5 = b) → **M1′** | [AMBOS] |
| 12 | **2.3** LLaMA ZS nos dois testes; Kappa intra (e inter, se D-6 = b) | [CURSOR] / [PEDRO] |
| 12–13 | **3.x** fine-tuning (smoke test → treino); braço "sem TAIL" como ablação principal | [CURSOR] |
| 14 | **4.1–4.2** comparação ALTA + tabela externa TAIL; **4.5** análise de erro reduzida | [CURSOR] / [PEDRO] |
| 15 | **5.4** fechamento do texto; rascunho ao orientador | [PEDRO] |
| 16 | Defesa | [PEDRO] |

Regra de absorção (`main.tex:365`): a primeira a encolher é a ablação (fica 1 fator: "com/sem TAIL" **ou** "com/sem aumento", a definir em D-7), depois o pipeline progressivo. Nunca a anotação.

**Perguntas para o orientador.**
1. Aprova o cenário D? Se preferir A ou C, há prorrogação possível?
2. Essa mudança exige nova versão formal da proposta ou basta registro em ADR + ata de reunião?
3. Aceita as duas regras por tipo de par (categoria e variante em produto×dicionário; SKU com marca e tamanho em produto×produto), a limitação da transitividade (só categoria) e a H2 explicitamente exploratória?
4. Aceita retirar o Dharma Generator do caminho crítico (muda o Resumo e o §4.1)?
5. Um integrante da TAIL serve como 2º anotador do ponto de vista metodológico?
6. Calendário: confirma a Semana 16 e o corte da ablação?
7. Como citar um trabalho da TAIL ainda não publicado?
8. Coautoria do artigo derivado.

**Perguntas para o líder da TAIL.**
1. Pode autorizar por escrito o uso de: `pairs_to_label.csv`, as predições `pairs_normalized*.csv`/`baseline_predictions.csv`, `old_attack_dataset.csv`, `test.csv`, `attack.csv`? Para treino, teste e publicação de números?
2. Qual versão de `pairs_to_label.csv` é a oficial, e por que 4 rótulos mudaram?
3. O artigo foi submetido ou publicado? Onde? Como devo citar?
4. Qual a origem e os termos do dump MeLi, das avaliações `octaprice` e das NF-e (`AmostraDescMerc`, `itens_nf`)? Algo está sob NDA (`nda_*.json`)?
5. Posso reutilizar trechos de código (sem LICENSE)? Pretendem licenciar o repositório?
6. Alguém da TAIL pode anotar um subconjunto do meu teste, às cegas e sem ver meu pipeline?
7. Podem compartilhar os resultados do fine-tuning do LLaMA 3.2 3B (Drive) e o `finetune_dataset_augmented.jsonl`, e posso mencioná-los?
8. Podem fornecer as execuções 2 e 3 de GPT/DeepSeek com as colunas de predição?
9. Expectativa de coautoria ou agradecimento?

---

## 9. Limites desta análise

- **Suíte de testes da TAIL não executada:** a execução de código externo foi bloqueada pelo ambiente. As afirmações sobre `pairwise_f1.py` e `reproduce.py` vêm de leitura do código.
- **`make check` do TCC não executado** (o pytest grava caches no repositório). O estado dos testes não foi reconfirmado.
- **Sem acesso à web:** termos de uso do Mercado Livre, licença do AI-PAVE-Br e metadados das referências candidatas **não verificados**.
- **Google Drive** da TAIL (`results_finetune.md`) inacessível: os resultados do LLaMA 3.2 3B gerativo são desconhecidos.
- **Pool de 30 mil, dump de 20 milhões, `data/train.csv` e `finetune_dataset_augmented.jsonl`** ausentes. A origem dos títulos do benchmark não foi rastreada.
- **Fração de mercearia** (1,7%) é heurística por palavras-chave, não classificação.
- **Tabela 1 da TAIL** (constância, estabilidade, F1 médio±dp) não foi recomputada; só a Tabela 2 e a significância.
- **Não li célula a célula** `classifier_api.ipynb`, `model_v2*.ipynb`, os notebooks das POCs nem `revisao/pave_*.py`. Os notebooks de fine-tuning foram lidos por padrões e saídas.
- **Geração de `old_attack_dataset.csv`** pelo script de regras é inferência (mesma POC, nome "old"), não fato.
- **Conteúdo da conversa verbal** com o líder da TAIL é desconhecido; a análise assume só o que o autor descreveu.
- **Calendário:** premissa declarada no §0, a confirmar.
- **Árvore de trabalho com mudanças não commitadas** (incluindo `main.tex`): as linhas citadas referem-se ao estado em disco em 2026-10-31, não à `HEAD`.
