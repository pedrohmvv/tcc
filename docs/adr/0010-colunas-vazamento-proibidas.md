# ADR-0010: Colunas `codg_item`, `desc_ref` e `match_score` são vazamento proibido

**Status:** Aceito — CRÍTICO. **Emendado pelo ADR-0011** (2026-10-06): as proibições de rótulo, treino, validação e anotação continuam; o ADR-0011 acrescenta o uso permitido como baseline "ALTA atual" avaliado contra o teste manual e substitui o assert de descarte no script 01 por restrições de leitura por script.

## Contexto
`dados/brutos/todos_mercados_2026-09-10.csv` contém três colunas produzidas pelo pipeline de produção do ALTA, independente e anterior a este TCC: `codg_item` e `desc_ref` (código e descrição de referência já associados por um matching heurístico do ETL) e `match_score` (score de confiança desse matching). `dados/brutos/README.md` já registra essas colunas como risco de vazamento metodológico e proíbe seu uso na anotação e no treino, mas essa restrição vive apenas nesse README — não em ADR, spec ou checagem automatizada, o que não sobrevive a um lapso de memória ao longo das 16 semanas.

## Decisão
As colunas `codg_item`, `desc_ref` e `match_score` **nunca** são usadas como insumo de rótulo, em nenhuma etapa deste TCC — nem na anotação manual do padrão-ouro (ADR-0004), nem na supervisão distante ou geração de treino (spec 001), nem no treino do Cross-Encoder (spec 003), nem na avaliação (spec 002/004). Usá-las contaminaria a avaliação com os critérios (desconhecidos) de um matching de terceiros já aplicado pelo ALTA.

Uso permitido, e apenas esse: `match_score` pode ser **reportado na EDA** (script 02) como caracterização do estado atual do matching heurístico do ALTA — insumo direto para a recomendação 5 do parecer do orientador (sustentar empiricamente que os métodos clássicos são insuficientes). Reportar como contexto é legítimo; usar como rótulo, em qualquer forma, não é.

A ingestão dos dados brutos (script 01) descarta as três colunas por **assert explícito**, não por convenção — se qualquer uma delas alcançar as etapas de anotação, geração ou treino, o pipeline deve falhar de forma visível, não silenciosa.

## Consequências
- `specs/001-construcao-dataset-ground-truth/requirements.md` ganha um requisito não funcional exigindo a checagem automatizada (ver spec atualizada).
- O script 01 (`01_coleta_dados.py`) é responsável por descartar as três colunas antes de qualquer etapa seguinte consumir a saída.
- O script 02 (`02_analise_exploratoria.py`) é a única exceção autorizada a ler `match_score`, e apenas para fins de caracterização descritiva — não deve propagar a coluna adiante no pipeline.
- Violar esta decisão invalida a avaliação inteira do TCC, no mesmo grau de gravidade do ADR-0004.

## Alternativas consideradas
- **Manter a restrição só como convenção documentada no README:** rejeitada — já se mostrou insuficiente (a restrição não chegou a nenhum ADR, spec ou skill em três semanas de repositório), e o custo de um assert é mínimo frente ao custo de uma avaliação inteira invalidada.
