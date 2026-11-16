# ADR-0014: Produto × produto como fatia principal; produto × dicionário como fatia secundária

**Status:** **Aceito** (decisão do autor, 2026-10-31). **Substitui parcialmente o ADR-0013** (decisão 1 e o item "teste principal") e **emenda o ADR-0007** (que fixa o foco em catálogo-dicionário). Não altera os ADRs 0001, 0004 (regra de que gerador/LLM não rotula teste ou validação), 0005, 0006, 0010 e 0011. **Os demais documentos ainda descrevem o desenho anterior** (`CLAUDE.md`, ADR-0013, ADR-0007, specs, skills, plano e a proposta v3 / `main.tex`) e precisam ser atualizados; até lá, em caso de conflito, vale este ADR.

## Contexto
A proposta v3 e o ADR-0013 tratam produto × dicionário como a fatia principal e a hipótese central, e produto × produto como fatia suplementar (~50–100 pares, tamanho aberto na D-13).

A blocagem produto × dicionário (tarefa 1.2a, `docs/resultado_blocagem_amostra_cega.md`) mostrou o limite do filtro lexical justamente nos casos em que se espera que o modelo faça diferença:
- na amostra cega, 4 de 42 produtos (9,5%) não têm a entrada correta entre os 100 primeiros candidatos, por abreviação (`CERV`), marca que embute a categoria (`NESCAFE` ⊃ `CAFE`) e variação morfológica (`COXINHA` × `COXA`);
- na base inteira, com TF-IDF e k=20, 1.959 dos 28.240 produtos distintos (6,9%) não têm nenhum candidato. Parte deles é não-alimento (sem entrada correta), parte é abreviação (`VH`, `VIN`, `ESP`). A proporção de cada grupo não foi medida.

Esses casos não chegam ao Cross-Encoder, e a vantagem do modelo sobre os métodos clássicos fica invisível exatamente onde o autor espera mostrá-la. Entre dois produtos, marca, uva e tamanho costumam ser tokens compartilhados mesmo com abreviações diferentes, então a blocagem lexical deve sofrer menos. **Isso é hipótese: a blocagem produto × produto (1.2b) ainda não foi medida.**

Além disso, a regra de SKU (marca e tamanho decidem, ADR-0013) é a que distingue produtos entre lojas. A supervisão distante por marca e unidade (spec 001, RF2) funciona em produto × produto e não em produto × dicionário; com o dicionário secundário, a suspensão do Dataset Generator (D-5) deixa de bloquear o caminho principal.

## Decisão
1. **Produto × produto passa a ser a fatia principal e o teste principal do TCC.** A hipótese central e a pergunta de pesquisa são reformuladas para essa fatia (redação a definir na atualização da proposta).
2. **Produto × dicionário é mantido como fatia secundária completa**, reportada como complementar: mantém o segundo adaptador LoRA, a blocagem 1.2a (TF-IDF, k=20, já congelada) e um teste próprio, **menor** que o atual (300–500 pares). A fatia continua tendo as limitações já documentadas (teto de recall da blocagem lexical).
3. **Mantidas sem alteração:** as duas regras de match por tipo de par (ADR-0013), os dois adaptadores LoRA sobre o mesmo checkpoint-base, a arquitetura Cross-Encoder (ADR-0001), a proibição de gerador/LLM rotular teste ou validação, e o tratamento dos dados da TAIL (nada versionado ou publicado sem autorização escrita).

## Decisões ainda abertas
- **[DECISÃO PENDENTE] Tamanho do teste produto × produto**, agora principal. 50–100 pares provavelmente não bastam para uma fatia principal; o benchmark da TAIL tem só 30 positivos. Depende de como amostrar (faixas de similaridade, para evitar prevalência de ~2,5% de positivos) e do esforço de anotação possível.
- **[DECISÃO PENDENTE] Tamanho do teste produto × dicionário**, agora secundário (a v3 prevê ~250–450 pares).
- **[DECISÃO PENDENTE] Como medir o recall da blocagem produto × produto (1.2b).** Não há dicionário para dar a verdade de referência, e `codg_item` é proibido (ADR-0011). Exige desenho próprio de amostra cega entre lojas.
- **[DECISÃO PENDENTE] Papel do benchmark da TAIL**, que usa o mesmo regime de SKU da fatia principal. Hoje é teste externo exploratório (30 positivos); este ADR não o altera.
- **[SUSPENSO, inalterado] Dataset Generator (D-5):** continua bloqueando só o treino do adaptador produto × dicionário (tarefa 1.7).

## Consequências
- **A proposta v3 e o `main.tex` descrevem o desenho anterior** até serem atualizados (tarefa 5.3 do plano). Calendário: execução de 16 semanas, anotação no caminho crítico; a mudança chega no meio do prazo.
- **1.2a permanece válida** como fatia secundária. A **1.2b passa para o caminho crítico**.
- **Esforço de anotação é redistribuído:** o grosso passa para pares produto × produto. A anotação continua exclusiva do autor, sem gerador ou LLM.
- **A comparação com baselines e TAIL ganha sentido na fatia principal** (mesma regra de SKU), mas o benchmark externo continua exploratório.
- **Risco assumido pelo autor:** o resultado da blocagem produto × produto pode não ser melhor que o de produto × dicionário; se não for, o argumento deste ADR enfraquece. A 1.2b mede isso.
- **Reverte parcialmente o ADR-0007:** a alternativa "duas avaliações completas e independentes", rejeitada lá por custo de anotação e de blocagem sem dicionário, e o item "avaliação plena da subtarefa intra-base fica como trabalho futuro" deixam de valer. O ADR-0007 rejeitou essas opções por serem incompatíveis com o prazo de 16 semanas solo; este ADR as adota com o dicionário em tamanho menor, e o autor assume esse custo.
- **Documentos atualizados em 2026-10-31:** `CLAUDE.md`, `AGENTS.md`, `README.md`, ADRs 0004, 0006, 0007 e 0013 (cabeçalhos e trechos afetados), specs 001–004, skills `dominio-entity-matching`, `avaliacao-baselines` e `protocolo-anotacao-em`, `docs/protocolo_anotacao.md`, `docs/plano_desenvolvimento.md`, `docs/pauta_reuniao_orientador_tail.md`, `docs/diario_pesquisa.md`, `dados/processados/README.md` e `scripts/README.md`.
- **`main.tex` atualizado em 2026-10-31** (Resumo, Abstract, §1, objetivos, §4.1–4.4, §4.7, hipótese central, trabalhos futuros, `fig_pipeline.tex` e `tab_cronograma_execucao.tex`). Marcadores ainda no texto: `[a definir]` para o tamanho do teste de cada fatia, a unidade de partição da fatia produto × produto e o uso da ferramenta de geração (D-5); `[a confirmar]` para a autorização escrita da TAIL e a forma de citação.
- **Pendente:** a Tabela de heterogeneidade (script 02) ainda mostra pares de lojas na mesma entrada do dicionário; será regerada com pares do mesmo SKU conferidos pelo autor.

## Alternativas consideradas
- **Manter o ADR-0013 como está** (produto × dicionário principal): é o que a proposta v3 aprovou. Mantém o escopo aprovado, mas deixa a vantagem esperada do modelo (abreviação, ruído de PDV) fora do alcance da blocagem na fatia principal.
- **Inverter e descartar o dicionário:** rejeitada pelo autor. O dicionário continua como fatia secundária completa, por ligação com o ALTA e porque a 1.2a já está feita.
- **Duas fatias co-principais:** não adotada pelo autor.
- **Resolver pela blocagem (n-gramas de caracteres) e manter o desenho atual:** continuaria dentro do ADR-0006, mas exigiria declarar a variante antes e medi-la em amostra nova (usar os 4 casos já vistos inflaria o recall). Não exclui esta decisão e pode ser adotada junto com ela.
