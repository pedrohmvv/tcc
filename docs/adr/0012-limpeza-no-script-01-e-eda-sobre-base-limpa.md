# ADR-0012: Limpeza no script 01 e EDA sobre a base limpa

**Status:** Aceito — emenda o ADR-0011 quanto a *onde* a limpeza ocorre e *qual base* a EDA descreve (as regras de uso das colunas do matcher ALTA não mudam)

## Contexto
A limpeza da base (critérios C1–C5 de `docs/limpeza_dados.md`) foi implementada como primeiro passo do script 03. Mas o pipeline roda em ordem (01 → 06, cada script consome a saída do anterior), e o script 02 gera as tabelas e figuras de EDA de `latex/tcc_artigo/` **antes** do 03. Resultado: as tabelas do TCC descreviam a base bruta, incluindo 1.129 duplicatas exatas (3,7%), enquanto todo o restante do pipeline usaria a base limpa.

O efeito não é cosmético. As duplicatas se concentram na `extra_api` (PI, Teresina): com elas, PI aparece como o maior estado (10.909 registros); sem elas, PB passa à frente (10.286 vs. 9.881). As prevalências de ruído mudam cerca de 1 ponto percentual, as contagens de hapax e de grafias de unidade mudam, e a amostra de `tab_exemplos_ruido.tex` é sorteada sobre outra base. O texto do TCC teria de conviver com dois universos de números.

Ler a saída do 03 a partir do 02 quebraria a ordem do pipeline. A alternativa coerente é antecipar a limpeza.

## Decisão
1. **A limpeza passa a ser responsabilidade do script 01.** Além de validar os brutos, ele aplica `limpar_base` e grava `dados/processados/{produtos_limpos,dicionario_limpo}.parquet` + `relatorio_limpeza.json`. `dados/brutos/` continua imutável.
2. **O script 02 descreve a base limpa.** Lê `dados/processados/`. A única leitura dos brutos que permanece no 02 é a de `match_score` (uso (a) do ADR-0011), sobre os brutos deduplicados pelo mesmo critério C1, para que a caracterização do matcher ALTA cubra os mesmos registros que o resto da EDA.
3. **O script 03 consome a base limpa** e não limpa nada.
4. Os critérios C1–C5 e as regras do ADR-0011 não mudam. Em particular, as colunas `codg_item`, `desc_ref` e `match_score` continuam fora de `dados/processados/`; como agora quem grava essa pasta primeiro é o 01, a remoção dessas colunas (com assert) acontece no 01. Isso **não** restaura o mecanismo original do ADR-0010 (descartar as colunas na ingestão para todos): os brutos seguem intactos e o baseline "ALTA atual" continua lendo-os diretamente, depois do congelamento do teste.

## Consequências
- O ADR-0011 passa a constar como emendado por este ADR no ponto em que dizia que o assert do script 01 "deixa de ser o mecanismo": a barreira continua sendo a ausência das colunas em `dados/processados/`, agora garantida pelo 01.
- Todas as tabelas e figuras de EDA em `latex/tcc_artigo/` são regeneradas sobre 29.130 registros; o §4.7 do TCC reporta explicitamente o volume coletado (30.259) e o volume após a deduplicação (29.130).
- `make eda` passa a depender de `make coleta` ter gravado a base limpa — o que `make pipeline` já garante pela ordem.
- O script 01 deixa de ser "só leitura": isso muda o mapeamento descrito em `CLAUDE.md`, `AGENTS.md` §2 e `scripts/README.md`, atualizados junto.

## Alternativas consideradas
- **Manter a EDA sobre a base bruta e declarar no texto "a coleta como chegou":** rejeitada pelo autor — o TCC passaria a reportar dois conjuntos de números para a mesma base, e o ranking dos estados se inverteria entre a EDA e os experimentos.
- **Fazer o 02 ler a saída do 03:** rejeitada — quebra a ordem 01 → 06 do pipeline.
- **Criar um script de limpeza novo entre o 01 e o 02:** rejeitada — renumeraria o pipeline inteiro, que já está mapeado nas specs, ADRs e na proposta.
