# Spec 001: Construção do dataset e ground truth

**Script correspondente:** `scripts/03_construcao_dataset.py`
**ADRs relacionados:** 0004, 0005, 0006, 0007, 0010

## Objetivo
Produzir partições treino/validação/teste sem vazamento, combinando geração assistida (treino) e anotação manual independente (teste), a partir de dados reais do projeto ALTA.

## Requisitos funcionais
1. Gerar candidatos via blocagem lexical (TF-IDF/BM25) do produto bruto contra o dicionário canônico (ADR-0006).
2. Aplicar supervisão distante: pares com correspondência de marca + unidade normalizada recebem rótulo provisório automático.
3. Invocar o Dataset Generator (Dharma) para gerar pares sintéticos de TREINO apenas — paráfrases/variações das entradas reais do dicionário canônico (nunca gera as entradas canônicas em si).
4. Ingerir o arquivo de anotação manual (produzido fora do pipeline automatizado, seguindo `docs/protocolo_anotacao.md`) como fonte do conjunto de TESTE.
5. Incluir na ingestão de teste tanto pares (produto, entrada canônica) quanto a fatia suplementar (produto, produto) sem dicionário (ADR-0007).
6. Aplicar particionamento estratificado por produto canônico **antes** de qualquer geração ou aumentação — produtos do teste nunca aparecem na base que alimenta a geração de treino.
7. Aplicar aumentação sintética (perturbação de tokens: abreviação, troca de unidade, inversão de ordem) somente ao conjunto de treino, após o particionamento.

## Requisitos não funcionais
- Seed fixa no particionamento e em toda etapa estocástica.
- `[CRÍTICO]` Nenhuma chamada ao Dataset Generator deve tocar os produtos reservados ao teste — validar isso com um assert/checagem explícita no script, não apenas por convenção.
- `[CRÍTICO]` As colunas `codg_item`, `desc_ref` e `match_score` (matching heurístico pré-existente do ETL do ALTA) nunca alimentam rótulo de anotação, supervisão distante ou treino (ADR-0010) — o script 01 descarta as três por assert explícito antes de qualquer etapa seguinte consumir a saída; `match_score` só pode ser lido pelo script 02, e apenas para caracterização descritiva na EDA.
- Registrar recall da blocagem isoladamente (fração de vezes que o candidato correto está entre os top-k antes do reranqueamento) — necessário para a spec 004.

## Critérios de aceite
- [ ] Partições treino/val/teste versionadas, sem sobreposição de produto canônico entre elas.
- [ ] Conjunto de teste com ~300–500 pares (produto, canônico) + ~50–100 pares (produto, produto).
- [ ] Kappa de teste-reteste calculado sobre ≥50% do conjunto de teste (ADR-0005), reportado mesmo se abaixo de 0,75 (com discussão).
- [ ] Nenhum produto do teste presente na base usada pelo Dataset Generator (checagem automatizada, não manual).

## Regra de granularidade — resolvida

O dicionário canônico (`dados/brutos/dicionario_canonico.csv`) tem uma entrada por **produto genérico**, sem marca e sem tamanho (ex.: `ARROZ BRANCO`, `ARROZ INTEGRAL`) — confirmado por inspeção direta do arquivo (1.593 entradas de dados). Logo, para pares (produto, entrada canônica): **produtos de tamanhos diferentes são match**, desde que a categoria/variante coincida. A regra de "mesma marca" não se aplica a essa fatia, pois a entrada canônica não carrega marca — ela se aplica apenas à fatia suplementar (produto, produto), onde ambos os lados têm marca (ADR-0007). O script de ingestão não precisa suportar duas regras alternativas; a regra única acima é a que vale.
