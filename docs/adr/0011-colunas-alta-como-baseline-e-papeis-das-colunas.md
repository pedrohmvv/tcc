# ADR-0011: Papéis das colunas da base e uso das colunas do matcher ALTA como baseline

**Status:** Aceito — emenda o ADR-0010 (mantém todas as proibições de rótulo/treino; acrescenta um uso permitido)

## Contexto
O ADR-0010 proibiu `codg_item`, `desc_ref` e `match_score` "em nenhuma etapa", inclusive na avaliação, e só permitiu citar `match_score` como contexto da EDA. A verificação de 2026-10-06 sobre o extrato real mostrou algo que muda o aproveitamento dessas colunas: `codg_item` está preenchido em 80,8% dos registros, 100% dos códigos preenchidos existem em `codg_item1` do dicionário canônico, e `desc_ref` é exatamente o `desc_alim` do código correspondente. Ou seja, elas contêm as **predições de um matcher em produção resolvendo a mesma tarefa do TCC** (produto → entrada canônica), com score de confiança (`match_score`). Isso é um baseline legítimo, e o mais relevante para a recomendação 5 do parecer (insuficiência dos métodos clássicos) — desde que seja pontuado contra o padrão-ouro manual, nunca usado como verdade.

Princípio que organiza este ADR: **treino, validação e teste operam exclusivamente sobre o texto dos nomes dos produtos** (`description` e `desc_alim`). Nenhuma outra coluna é feature do modelo.

## Decisão

### 1. Papéis das colunas

| Papel | Colunas | Regra |
|---|---|---|
| Texto (única entrada do modelo) | `description`, `desc_alim` | Os pares de treino, validação e teste são construídos só a partir destes campos. |
| Metadado de rastreio e pipeline | `product_id`, `source`, `location`, `collected_at` | Não entram no modelo. Servem para identificar o registro de origem de cada par (protocolo §5), deduplicar, e montar a fatia produto × produto com lojas diferentes. O registro é identificado por `(source, product_id)` — único após remover as duplicatas exatas (verificado: 1.129 duplicatas exatas = 1.129 repetições de `(product_id, source)`). |
| Metadado de unidade | `unit`, `und_val`, `und_med` | Não entram no modelo. Usados só pela supervisão distante (spec 001, RF2: "unidade normalizada") e como metadado do par no protocolo. |
| Sem relação com matching | `price`, `preco_kg` | Fora do pipeline de matching. Aparecem só em diagnóstico/EDA. |
| Predição do matcher ALTA | `codg_item`, `desc_ref`, `match_score` | Regras abaixo. |

### 2. Colunas do matcher ALTA
**Permitido:**
- (a) Caracterização descritiva na EDA (script 02), como já era.
- (b) **Baseline "ALTA atual"** (script 04): `desc_ref`/`codg_item` como predição de entrada canônica e `match_score` como score de confiança (permite curva Precision × Recall por limiar), avaliados **contra o teste manual**, com o mesmo harness dos demais baselines (McNemar, tamanho de efeito, IC — ADR-0008). Aplica-se apenas à fatia produto × canônico; o `codg_item` não existe para pares produto × produto.
- (c) Análise de erro (script 06), comparando onde ALTA e SLM discordam — somente depois do teste congelado e das métricas fixadas.

**Proibido (mantém e detalha o ADR-0010):**
- Usar como rótulo, supervisão distante, dado de treino ou de validação (inclui seleção de hiperparâmetros e early stopping).
- Mostrá-las ao anotador ou gravá-las no arquivo de anotação (viés de ancoragem contaminaria o padrão-ouro).
- Usá-las para escolher ou estratificar **quais** pares serão anotados, ou para gerar candidatos na blocagem (a blocagem é só TF-IDF/BM25 sobre texto, ADR-0006).
- Usá-las como feature de qualquer modelo.

### 3. Aplicação do baseline
- A leitura acontece **depois do congelamento do teste (marco M1)**, diretamente dos brutos, e só nos scripts 02, 04 e 06. As partições e o arquivo de anotação em `dados/processados/` **nunca** contêm essas colunas; o script 03 e o validador de anotação falham por assert se elas aparecerem.
- Os 19,2% de registros sem `codg_item` não têm predição do ALTA. O baseline é reportado **nas duas versões** — condicionado aos registros com predição (precisão sobre a cobertura) e sobre o total (ausência de predição contada como falha) — sem escolher a mais favorável após ver os resultados.

## Consequências
- O ADR-0010 permanece válido para tudo que é rótulo/treino/validação; passa a constar como emendado por este ADR.
- A spec 002 ganha o baseline "ALTA atual" (7 métodos em vez de 6) e a spec 001 ajusta o requisito não funcional correspondente.
- **A proposta v3 lista os baselines TF-IDF, BM25, Levenshtein, Jaccard, embeddings e zero-shot; este é um baseline adicional.** Levar ao orientador na R1. O `main.tex` não é alterado agora.
- O assert de descarte no script 01 previsto no ADR-0010 deixa de ser o mecanismo: o bruto continua imutável e a barreira passa a ser a ausência das colunas nas saídas do 03 e da anotação, mais a leitura restrita aos scripts 02/04/06.
- Risco assumido: um baseline com o matcher de produção dá ao leitor uma comparação concreta, mas se o SLM não superá-lo isso precisa ser reportado como resultado (ADR-0008).

## Alternativas consideradas
- **Manter a proibição total do ADR-0010:** rejeitada — joga fora a evidência empírica mais barata e mais relevante para o parecer, sem ganho de proteção contra vazamento (a proteção real está na ausência das colunas em treino/validação/teste/anotação).
- **Usar `codg_item` como supervisão distante para treino:** rejeitada — é um matching heurístico de terceiros com critérios desconhecidos e erros visíveis; contaminaria o treino e tornaria o baseline circular.
