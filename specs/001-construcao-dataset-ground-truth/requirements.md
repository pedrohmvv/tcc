# Spec 001: Construção do dataset e ground truth

**Script correspondente:** `scripts/03_construcao_dataset.py` (RF0: `scripts/01_coleta_dados.py`; EDA: `scripts/02_analise_exploratoria.py`)
**ADRs relacionados:** 0004, 0005, 0006, 0007, 0010, 0011, 0012, 0013, 0014

## Objetivo
Produzir partições treino/validação/teste sem vazamento, combinando geração assistida (treino) e anotação manual independente (teste), a partir de dados reais do projeto ALTA.

## Requisitos funcionais
0. Limpar a base no script 01, antes de qualquer outra etapa (`limpar_base`/`executar_limpeza`; ADR-0012), lendo `dados/brutos/` sem alterá-lo e gravando `dados/processados/{produtos_limpos,dicionario_limpo}.parquet` + `relatorio_limpeza.json` (contagens e SHA-256). Remove só defeito objetivo de coleta (duplicatas exatas); marca, sem remover, texto repetido na mesma loja e preço não positivo; remove as colunas vazias sem nome do dicionário e as colunas do matcher ALTA (ADR-0011). Nunca remove ruído linguístico de PDV. Critérios e justificativas em `docs/limpeza_dados.md`. Todas as etapas seguintes — inclusive a EDA do script 02 — consomem a base limpa.
1. Gerar candidatos via blocagem lexical (TF-IDF/BM25) do produto (base limpa) contra o dicionário canônico (ADR-0006, emenda de 2026-10-31). Dividido em duas partes:
   - **1a (produto × dicionário):** produtos deduplicados por texto normalizado (critério C2) antes de qualquer sorteio; TF-IDF e BM25 sobre o dicionário; varredura de k em {1, 5, 10, 20, 50, 100}; recall da blocagem isolada medido na **amostra cega** (~50 produtos, sorteio com seed fixa, o autor indica a entrada correta sem ver os candidatos ou registra `sem_entrada`); método e k escolhidos nessa amostra, gravados em config YAML e congelados **antes** de gerar os pares do teste. Saída: `dados/processados/candidatos_blocagem.parquet` e a planilha da amostra cega (sem candidatos).
   - **1b (produto × produto, entre lojas):** **fatia principal (ADR-0014) e próxima tarefa no caminho crítico.** O tamanho do teste (D-13) e a forma de medir o recall da blocagem entre produtos (sem dicionário e sem `codg_item`) estão em aberto. Amostragem por faixas de similaridade (para não repetir os 2,5% de positivos do benchmark da TAIL) e negativos difíceis por dígito divergente, com os mesmos cuidados de partição e vazamento.
   - `[DECISÃO PENDENTE]` Como amostrar os pares produto × dicionário do teste (fatia secundária, ADR-0014; tamanho a definir, menor que os ~250–450 originais) a partir dos candidatos (por faixa de similaridade, incluindo negativos difíceis). Define o balanceamento entre match e não-match; decidir ao fim da 1a, antes de montar a planilha de anotação (tarefa 1.4.1).
2. Aplicar supervisão distante: pares com correspondência de marca + unidade normalizada recebem rótulo provisório automático. `[DECISÃO PENDENTE]` O dicionário não tem marca nem tamanho, então esse critério só se aplica a pares produto × produto (a fatia principal, ADR-0014); para produto × dicionário a heurística precisa ser reformulada em termos de categoria/variante (ver D-5 no ADR-0013).
3. **[SUSPENSO — ADR-0013, D-5; decidir antes da tarefa 1.7. Nenhuma chamada ao Generator até lá.]** Invocar o Dataset Generator (Dharma) para gerar pares sintéticos de TREINO apenas — paráfrases/variações das entradas reais do dicionário canônico (nunca gera as entradas canônicas em si).
4. Ingerir o arquivo de anotação manual (produzido fora do pipeline automatizado, seguindo `docs/protocolo_anotacao.md`) como fonte do conjunto de TESTE.
5. Incluir na ingestão de teste as duas fatias: pares (produto, produto), a fatia principal, sem dicionário, e pares (produto, entrada canônica), a fatia secundária (ADR-0014).
6. Aplicar particionamento estratificado por produto canônico **antes** de qualquer geração ou aumentação — produtos do teste nunca aparecem na base que alimenta a geração de treino.
7. Aplicar aumentação sintética (perturbação de tokens: abreviação, troca de unidade, inversão de ordem) somente ao conjunto de treino, após o particionamento.
8. **Dados da TAIL (ADR-0013), só treino do adaptador produto × produto.** Construir pares a partir das variantes de título (positivos) e de negativos minerados, a partir dos artefatos curados em `dados/brutos/tail/` (ignorado pelo git, SHA-256 e commit `9d010ec` registrados). A unidade de partição é o **grupo de título original** (original, variantes e positivos ligados por union-find), aplicada **antes** de gerar negativos ou aumentar. Os rótulos do benchmark TAIL são normalizados (`strip()`) e nunca editados.
9. **Benchmark TAIL como teste externo.** Ingerir `main_supersaurus/dados/pairs_to_label.csv` (versão confirmada pela TAIL) como teste externo produto × produto. Nunca entra em treino nem em validação.

## Requisitos não funcionais
- Seed fixa no particionamento e em toda etapa estocástica.
- `[CRÍTICO]` Nenhuma chamada ao Dataset Generator deve tocar os produtos reservados ao teste — validar isso com um assert/checagem explícita no script, não apenas por convenção. A regra vale para **qualquer gerador ou LLM** (Dataset Generator, `attack_augmentation` da TAIL, LLM-as-judge, predições de LLM): nenhum produz ou rotula pares de teste ou de validação (ADR-0013).
- `[CRÍTICO]` Assert: nenhum grupo de título original da TAIL em mais de uma partição, e nenhum título do benchmark TAIL (normalizado, e quase-duplicatas como variações de sufixo) no treino ou na validação.
- `[CRÍTICO]` Treino, validação e teste usam exclusivamente o texto dos nomes (`description`, `desc_alim`) — ADR-0011. As colunas `codg_item`, `desc_ref` e `match_score` (matching pré-existente do ALTA) nunca alimentam rótulo, supervisão distante, treino, validação, blocagem, seleção de pares para anotação nem o arquivo de anotação (ADR-0010/0011). As partições e o arquivo de anotação em `dados/processados/` não podem conter essas colunas: o script 03 e o validador de anotação falham por assert se aparecerem. Só os scripts 02 (EDA), 04 (baseline "ALTA atual") e 06 (análise de erro) as leem, direto dos brutos, e o 04/06 só depois do congelamento do teste.
- Registrar recall da blocagem isoladamente (fração de vezes que o candidato correto está entre os top-k antes do reranqueamento) — necessário para a spec 004. Medido na **amostra cega**, nunca só nos pares anotados do teste (que são condicionados aos candidatos). Seed fixa no sorteio da amostra e config YAML versionada com o método e o k congelados.

## Critérios de aceite
- [ ] Partições treino/val/teste versionadas, sem sobreposição de produto canônico entre elas.
- [ ] Conjunto de teste por fatia: produto × produto (principal; tamanho em aberto, D-13) e produto × dicionário (secundária; tamanho menor que os ~300–500 originais, a definir). Ver ADR-0014.
- [ ] Kappa de teste-reteste calculado sobre ≥50% do conjunto de teste (ADR-0005), reportado mesmo se abaixo de 0,75 (com discussão).
- [ ] Nenhum produto do teste presente na base usada pelo Dataset Generator (checagem automatizada, não manual). Aplicável só se o Generator for retomado (D-5).
- [ ] Nenhum grupo da TAIL em mais de uma partição; nenhum título do benchmark TAIL no treino/validação (checagem automatizada).
- [ ] Recall da blocagem por k (1 a 100), TF-IDF e BM25, medido na amostra cega; método e k congelados em config antes de gerar os pares do teste.

## Regra de granularidade — resolvida

O dicionário canônico (`dados/brutos/dicionario_canonico.csv`) tem uma entrada por **produto genérico**, sem marca e sem tamanho (ex.: `ARROZ BRANCO`, `ARROZ INTEGRAL`) — confirmado por inspeção direta do arquivo (1.593 entradas de dados). Logo, **há uma regra por tipo de par** (ADR-0013, `docs/protocolo_anotacao.md` §3):
- **Produto × entrada canônica:** decide categoria e variante. Tamanho e marca não decidem; exceções de não-match: kit/promoção e marca própria (esta só quando o texto da descrição declara).
- **Produto × produto:** decide SKU. Marca e tamanho decidem (1 kg ≠ 5 kg).

Cada linha de anotação registra o tipo de par, e o script de ingestão aplica a validação do tipo correspondente. Dois produtos na mesma entrada do dicionário são da mesma categoria, não necessariamente o mesmo SKU (emenda ao ADR-0007).
