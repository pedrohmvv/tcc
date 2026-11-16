# Limpeza de Dados — Base ALTA para Entity Matching

**Projeto:** TCC — Entity Matching em Produtos de Supermercado com SLMs Fine-Tuned
**Autor:** Pedro Henrique Medeiros Vieira
**Última atualização:** 2026-10-06
**Implementação:** `scripts/01_coleta_dados.py` (`limpar_base`, `executar_limpeza`) — spec 001, RF0; ADR-0012
**Diagnóstico de origem:** `notebooks/01_sanity_check.ipynb` (veredicto: 0 bloqueantes, 8 warnings)
**Narrativa e evidências:** `notebooks/02_eda.ipynb`, Seção 6

---

## 1. Objetivo

Definir, de forma auditável, o que é tratado como **defeito de dado** antes da blocagem, e o que **não é**. Este documento está para a limpeza como o `protocolo_anotacao.md` está para a rotulagem: cada critério tem regra, justificativa e o warning do sanity check que ele resolve.

## 2. Princípios

1. **Os brutos são imutáveis.** A limpeza lê `dados/brutos/` e escreve só em `dados/processados/`. Nada é corrigido no lugar.
2. **Ruído linguístico de PDV é o objeto de estudo, não sujeira.** Abreviação, truncamento, inversão de tokens, variação de unidade, falta de acento e caixa alta **nunca** justificam remover um registro. Só se remove o que é defeito objetivo de coleta.
3. **Na dúvida, marcar em vez de remover.** Quando não há prova de defeito, o registro fica com uma flag; a decisão de como usá-la é da etapa que a consome.
4. **O modelo só vê texto (ADR-0011).** Treino, validação e teste usam `description` e `desc_alim`. As colunas do matcher ALTA (`codg_item`, `desc_ref`, `match_score`) não entram em `dados/processados/`; o baseline "ALTA atual" as lê direto dos brutos, depois do congelamento do teste.
5. **Reprodutível, não commitado.** As saídas ficam fora do git (texto derivado do ALTA, abertura ainda não autorizada — pendência D7) e são regeneradas de forma determinística por `make pipeline`. O `relatorio_limpeza.json` registra as contagens e o SHA-256 dos brutos e do conteúdo limpo, para conferir que duas execuções produzem a mesma base.

## 3. Critérios

| # | Critério | Ação | Warning do sanity check |
|---|---|---|---|
| C1 | Duplicata exata (todas as 13 colunas iguais, inclusive o timestamp) | **Remover**, mantendo a primeira ocorrência | §4 — "1.129 linhas duplicadas exatas" |
| C2 | Texto repetido na mesma loja (mesma descrição normalizada + mesma `source`, `product_id` diferente) | **Manter** e marcar `texto_repetido_na_loja = True` | §4 — "185 grupos de quase-duplicatas" |
| C3 | Preço não positivo | **Manter** e marcar `preco_invalido = True`, sem alterar o valor | §5 — "Preços iguais a zero: 1" |
| C4 | Colunas sem nome e totalmente vazias no dicionário | **Remover as colunas** em `dicionario_limpo.parquet` | §2 — "2 colunas sem nome no CSV" |
| C5 | Colunas do matcher ALTA | **Remover da base limpa** (assert no código) | — (ADR-0011, não é defeito de dado) |
| L1 | `codg_item`/`desc_ref` ausentes em 19,2% | **Nenhuma** (não imputar) — limitação do baseline | §3 — "`codg_item` ausente em 19,2%" |
| L2 | `cod_padrao` com 82,7% no valor 99 | **Nenhuma** (não recodificar) — não usado como categoria | §7 — "`cod_padrao` concentra 82,7%" |
| L3 | Unidade estruturada ausente (`und_med`/`und_val` 5,8%, `unit` 2,0%) | **Nenhuma** (não imputar a partir do texto) | §3 — "Metadado de unidade incompleto" |
| L4 | Coleta de um único dia (10/09/2026) | **Nenhuma** — limitação da base | §5 — "único dia de coleta" |

### C1 — Duplicatas exatas
**Regra.** Linhas idênticas em todas as colunas são reduzidas a uma; fica a primeira ocorrência.
**Justificativa.** São idênticas até no timestamp de coleta, então não há informação a perder em nenhuma coluna — nem nas que o modelo não vê. A ordem de manutenção é irrelevante pelo mesmo motivo, mas fixar "primeira" deixa o resultado determinístico. Mantê-las inflaria as contagens da EDA e, pior, colocaria a mesma descrição em mais de uma partição se o split não fosse por produto canônico. Concentradas em `extra_api` (1.028) e `chegou_a_feira_api` (100): padrão de coleta repetida, não de catálogo.

### C2 — Texto repetido na mesma loja
**Regra.** Marcar, sem remover, todos os registros de um grupo (descrição normalizada, `source`) com mais de um membro.
**Justificativa.** Em todos os grupos o `product_id` é diferente e o timestamp é o mesmo, o que descarta "atualização de preço durante o dia". Em 149 dos 185 grupos o preço difere (mediana +22,6%). O cenário mais provável são **SKUs distintos do catálogo da loja com o mesmo nome** (ex.: `CUECA LUPO AM BOXER MICROF.` com 7 ids — tamanhos/cores fora do texto). Não é defeito comprovado de coleta. **Consequência para a etapa seguinte:** ao gerar candidatos e sortear pares para anotação, o script 03 (que consome a base limpa) deve deduplicar por texto normalizado, para o anotador não rotular a mesma descrição duas vezes. Como o split é por produto canônico, textos idênticos caem na mesma partição — sem vazamento.

### C3 — Preço não positivo
**Regra.** Marcar `preco_invalido = True`; manter o registro e o valor original.
**Justificativa.** O único caso (`Fórmula Infantil NAN Comfor HMO de 6 a 12 meses 800g`, R$ 0,00, `atacadao_api`) tem texto íntegro, e o preço não entra no matching. Remover descartaria uma descrição válida sem ganho.

### C4 — Colunas vazias do dicionário
**Regra.** Remover colunas `Unnamed: *` 100% vazias.
**Justificativa.** Artefato do CSV original (`prep_padrao.csv`), já registrado em `dados/brutos/README.md`.

### C5 — Colunas do matcher ALTA
**Regra.** `codg_item`, `desc_ref` e `match_score` não existem na base limpa; o código falha por assert se aparecerem.
**Justificativa.** ADR-0011: as partições e a anotação nunca podem contê-las. Como a base limpa é a entrada de tudo que vem depois, removê-las aqui impede que cheguem à blocagem, à anotação ou ao treino por acidente.

### L1–L4 — Limitações documentadas, sem tratamento
- **L1.** Imputar `codg_item` significaria inventar predições do matcher ALTA — mudaria o baseline, não os dados de treino/teste. O baseline é reportado nas duas versões (condicionada e total), conforme ADR-0011.
- **L2.** `cod_padrao` tem significado não confirmado com o ALTA; o `main.tex` já decidiu não usá-lo como categoria. Mantido no dicionário limpo, sem uso.
- **L3.** Na base limpa, dos 1.722 registros sem `und_med`/`und_val` só 7,8% trazem a unidade no texto, e dos 399 sem nenhuma unidade estruturada, 0% (na base bruta: 1.756 / 7,9% e 409 / 0% — ver `notebooks/02_eda.ipynb`, §4.3). Ou seja, a ausência quase nunca é recuperável pelo texto — são majoritariamente itens vendidos por peso ou unidade (ex.: `Bife de Pernil Suíno`). Afeta a supervisão distante (spec 001, RF2) e, na fatia principal produto × produto (ADR-0014), a comparação de tamanho nesses itens; para o par produto × canônico, tamanho diferente continua sendo match (protocolo §3.4).
- **L4.** Sem série temporal: a base não representa o histórico do ALTA. Citar no §4.7.

## 4. Resultado (fonte: `dados/processados/relatorio_limpeza.json`)

| Métrica | Valor |
|---|---|
| Registros brutos | 30.259 |
| Duplicatas exatas removidas (C1) | 1.129 (3,7%) |
| Registros na base limpa | 29.130 |
| Grupos / linhas marcados (C2) | 185 / 394 |
| Preços inválidos marcados (C3) | 1 |
| Colunas removidas do dicionário (C4) | `Unnamed: 3`, `Unnamed: 4` |
| SHA-256 `todos_mercados_2026-09-10.csv` | `8f6e566f…344a841b` |
| SHA-256 do conteúdo de `produtos_limpos` | `36c9448c…5e578ff2` |

Os números acima são cópia do relatório gerado pelo script 01 para esses SHA-256 dos brutos (idênticos aos da versão anterior, quando a limpeza ficava no script 03); se os brutos mudarem, regenerar e atualizar esta seção.

---

*Atualizar este documento sempre que um critério for adicionado, alterado ou removido — e citar o warning do sanity check que motivou a mudança.*
