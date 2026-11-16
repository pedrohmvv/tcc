# ADR-0018: Adjudicação de `incerto` do teste pelo julgamento do autor (desvio do protocolo §3.5)

**Status:** **Aceito** (revisado e aprovado pelo autor em 2026-11-16, junto com a emenda ao protocolo). **Emenda o ADR-0005 apenas no item "casos indecidíveis… adjudicados por consulta ao dicionário canônico"** e **emenda o `docs/protocolo_anotacao.md` §3.5** (texto na seção "Emenda ao protocolo §3.5"; já aplicada ao protocolo). Não altera o ADR-0004 (nenhum gerador ou LLM rotula teste ou validação) nem as regras de match por tipo de par (ADR-0013). Complementa o ADR-0016, que trata de outro desvio do ADR-0005 (o intervalo do reteste). O cabeçalho do ADR-0005 e o `main.tex` §4.1 **ainda não foram atualizados** (dependem do aval do autor). A numeração 0018 deixa o 0017 reservado ao CPT (pendência E5).

## Contexto
O protocolo §3.5 e o ADR-0005 dizem que um par `incerto` é rótulo **transitório**: é adjudicado por consulta ao dicionário canônico oficial ou, quando necessário, aos pesquisadores do projeto ALTA, e os não resolvidos **não integram** o teste final.

Fatos de 2026-11-16:
- A primeira passada dos 300 pares do teste produto × produto terminou com 19 `incerto` (140 `match`, 141 `nao_match`).
- A planilha de adjudicação (`anotacoes_teste_pxp_adjudicacao.csv`) foi gerada com esses 19 pares, no mesmo contrato de 15 colunas do teste, e exige que cada decisão (`match` ou `nao_match`) traga na observação a **fonte** com um prefixo fechado, para o desvio nunca ficar implícito.
- O autor respondeu que conseguia adjudicar com o dicionário. Na planilha, porém, as observações das decisões descrevem o raciocínio do autor sobre o texto das duas descrições (por exemplo, marcas ou linhas diferentes), e nenhuma cita uma consulta ao dicionário ou aos pesquisadores do ALTA. O autor decidiu **aceitar essas decisões como uma terceira fonte**, e não consultar o dicionário ou o ALTA para elas.
- As 11 decisões iniciais (2 `match` e 9 `nao_match`) receberam o prefixo `autor:`. Duas delas (`6a87afc7ad64` e `dd9a62abbe8f`) tinham observação "Não é possível saber…" e o autor mandou convertê-las para `incerto` (a conversão mudou só a coluna `rotulo`, conferida célula a célula; backup do estado anterior fora do repositório).
- Estado final da adjudicação em 2026-11-16: **9 decisões (2 `match` e 7 `nao_match`), todas `autor_adjudicacao`, e 10 `incerto` mantidos**. Compondo com a primeira passada, o teste final tem **290 pares** (142 `match` e 148 `nao_match`); os 10 `incerto` ficam fora (6 em `[0.70, 0.90)`, 3 em `[0.90, 1.00]` e 1 em `digito_divergente`).

## Decisão
1. A adjudicação de `incerto` aceita **três fontes**, registradas pelo prefixo da observação (sensível a maiúscula, com texto obrigatório depois dele):
   - `dicionario:` consulta ao dicionário canônico (protocolo §3.5, inalterado);
   - `alta:` consulta aos pesquisadores do ALTA (protocolo §3.5, inalterado);
   - **`autor:`** decisão pelo próprio julgamento do autor, sem consulta externa. **É o desvio** deste ADR.
2. No teste final, a fonte de cada rótulo fica registrada em `fonte_rotulo`: `autor_primeira_passada`, `dicionario`, `alta` ou `autor_adjudicacao`. O desempenho **deve ser reportado com e sem** os pares `autor_adjudicacao`.
3. Os pares que continuarem `incerto` continuam **fora** do teste final (regra do protocolo §3.5, inalterada).
4. A primeira passada nunca é alterada: a adjudicação fica em arquivo separado, e o reteste e o Kappa comparam contra o que o autor marcou de fato.

## Emenda ao protocolo §3.5 (aprovada pelo autor e aplicada em 2026-11-16)
Acrescentado ao fim da §3.5:

> **Adjudicação pelo autor (`autor:`).** Quando a consulta ao dicionário ou aos pesquisadores do ALTA não for feita ou não resolver, o autor pode decidir o par pelo próprio julgamento, desde que registre na observação o prefixo `autor:` e o raciocínio. Esses pares entram no teste final com a fonte `autor_adjudicacao` e são reportados à parte (ADR-0018). Informação ausente na descrição **continua** sendo motivo para manter `incerto`: o prefixo `autor:` não autoriza tratar a ausência de informação como `nao_match`.

## Consequências
- **O teste fica mais fraco justamente nos pares mais difíceis.** São os pares que o próprio autor marcou `incerto` na primeira passada, e agora o rótulo vem da mesma pessoa, sem fonte independente. Isso reforça a limitação de anotador único (ADR-0005, `main.tex` §4.1).
- **Regra implícita evitada.** Dois pares tinham observação "Não é possível saber…" e estavam como `nao_match`. Pelo protocolo §3.5, informação ausente é a definição de `incerto`; tratar "não sei" como `nao_match` acrescentaria uma regra que o protocolo não tem. O autor mandou convertê-los para `incerto`, e a emenda acima deixa explícito que o prefixo `autor:` não autoriza essa leitura.
- **Análise de sensibilidade obrigatória.** Como a fonte fica registrada, o teste deve ser avaliado com e sem os pares `autor_adjudicacao`, e a diferença reportada.
- **Documentos a sincronizar, com o aval do autor:** o protocolo §3.5 já foi emendado; faltam o cabeçalho do ADR-0005 e o `main.tex` §4.1, que hoje diz que os casos indecidíveis são adjudicados por consulta ao dicionário.
- **Reversível:** se o autor consultar o dicionário ou os pesquisadores do ALTA depois, basta trocar o prefixo e o texto da observação e validar de novo.

## Alternativas consideradas
- **Consultar o dicionário ou os pesquisadores do ALTA para todos os 19:** mantém o protocolo como está, mas o autor optou por não fazê-lo agora. Continua possível.
- **Devolver todos a `incerto` e excluí-los:** mantém o protocolo e não cria fonte nova, mas descarta pares que o autor sabe decidir e encolhe o teste.
- **Aceitar a decisão do autor sem registrar a fonte:** descartada. Esconderia o desvio e impediria a análise de sensibilidade.
- **Aceitar observação sem prefixo como `autor:` por padrão:** descartada. O prefixo explícito é a trava contra esquecer de registrar a fonte.
