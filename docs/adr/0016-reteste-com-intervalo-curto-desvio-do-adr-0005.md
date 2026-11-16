# ADR-0016: Reteste do teste produto × produto com intervalo de 39 minutos (desvio do ADR-0005)

**Status:** **Proposto** (rascunho de 2026-11-16). O autor decidiu, em 2026-11-16, aceitar o reteste já feito, por prazo, e ainda precisa revisar este texto. **Emenda o ADR-0005 apenas no item "intervalo ≥ 7 dias".** Não altera o resto do ADR-0005 (teste-reteste intra-anotador, ≥ 50% do teste, sem acesso aos rótulos originais, Kappa por tipo de par, faixa desejável ≥ 0,75, `incerto` fora do teste final) nem os ADRs 0004, 0013 e 0014. O cabeçalho do ADR-0005 **ainda não aponta** para este ADR: editá-lo depende do aval do autor. Antes de passar a "Aceito", o desvio deve ser levado ao orientador (pendência C4).

## Contexto
O ADR-0005 e o protocolo §4 exigem que o reteste comece pelo menos 7 dias depois da anotação original, sem acesso aos rótulos da primeira passada. O objetivo do intervalo é que a segunda passada seja quase independente da primeira, e não uma lembrança dela. Nenhum dos dois documentos justifica o número sete: é uma convenção do projeto, e nenhuma fonte primária sobre o intervalo foi verificada.

Fatos de 2026-11-16 (timestamps das planilhas e `resultados/metricas/kappa_reteste_pxp.csv`):
- A primeira passada (300 pares) terminou às 11:30:50 (-03:00).
- A planilha do reteste (150 pares, às cegas, em outra ordem) foi gerada pelo Claude nesse mesmo dia, sem nenhuma trava de data. Ela devia ser aberta só a partir de 2026-11-23. O autor a anotou entre 12:09:50 e 12:18:50.
- O intervalo, contado do **último** timestamp da primeira passada ao **primeiro** do reteste, foi de **39 minutos** (0,65 h).
- O autor decidiu não esperar os 7 dias por causa do prazo. O prazo restante das 16 semanas não está registrado nos documentos lidos.

Resultado (150 pares, sorteio estratificado pelo estrato original, sem olhar o rótulo, `incerto` incluído; seed 43):

| | Kappa | Concordância | Pares |
|---|---|---|---|
| 3 classes (`match`, `nao_match`, `incerto`) | 0,8125 | 89,3% | 150 |
| Binário (sem `incerto` em nenhuma passada) | 0,8955 | 94,8% | 134 |

Matriz (linhas: primeira passada; colunas: reteste):

| | incerto | match | nao_match |
|---|---|---|---|
| incerto | 7 | 3 | 5 |
| match | 0 | 65 | 5 |
| nao_match | 1 | 2 | 62 |

## Decisão
1. O reteste de 2026-11-16 é **aceito como medida exploratória de consistência de curto prazo**, e **não** como o teste-reteste de 7 dias do ADR-0005. O número não pode ser apresentado como confirmação de que o critério de anotação é estável ao longo do tempo.
2. O desvio fica registrado de forma que não se perca: `kappa_reteste_pxp.csv` traz `intervalo_horas` e `intervalo_minimo_cumprido` (`False` neste caso). O script só calcula o Kappa com menos de 7 dias com o aceite explícito `--aceitar-intervalo-curto`, e emite um aviso (`DESVIO DO ADR-0005`).
3. O texto do TCC (`main.tex` §4.1, que hoje diz "intervalo de pelo menos sete dias") deve declarar o desvio, o intervalo real (39 minutos) e a leitura "limite superior da consistência, inflado por memória de curto prazo".
4. O critério de aceite do Kappa na spec 001 continua **desmarcado**: o intervalo de 7 dias não foi cumprido.

## Consequências
- **Não há evidência de estabilidade em 7 dias.** O Kappa de 0,8125 acima da faixa desejável (0,75) não pode ser lido como cumprimento do ADR-0005. Mede principalmente a lembrança dos próprios rótulos.
- **O `incerto` é a classe menos estável** mesmo com o intervalo curto: dos 15 `incerto` da primeira passada que voltaram, 7 repetiram `incerto`, 3 viraram `match` e 5 viraram `nao_match`. Isso reforça adiar o `incerto` como classe do modelo (memória `decisao-incerto-como-classe-adiada`).
- **Limitação a declarar no TCC**, somada à de anotador único (ADR-0005, `main.tex` §4.1): o reteste foi feito sem o intervalo previsto.
- **Documentos a sincronizar, com o aval do autor:** cabeçalho do ADR-0005, `main.tex` §4.1, protocolo §4 (passo 2) e a nota no critério de aceite da spec 001.
- **Reversível:** o complemento do teste (os outros 150 pares, que o autor ainda não reviu) pode ser anotado a partir de 2026-11-23 e daria um reteste com intervalo válido, sem repetir pares vistos duas vezes. Exigiria código novo (sorteio do complemento, segunda planilha). Se feito, este ADR passa a "Substituído" ou ganha uma emenda com o Kappa válido.
- **Lição de processo:** a planilha de uma etapa com intervalo mínimo não deve ser gerada antes da data. Uma trava em `--reteste` (verificar 7 dias do fim da primeira passada) foi proposta e **não** foi implementada.

## Alternativas consideradas
- **Esperar até 2026-11-23 e refazer os mesmos 150 pares:** descartada pelo autor por prazo, e metodologicamente fraca: o autor já viu cada par duas vezes e a nova passada ficaria contaminada pela do dia 16.
- **Anotar o complemento (os outros 150 pares) a partir de 2026-11-23:** válida e barata (cerca de dez minutos no ritmo do autor, estimativa), mas não adotada agora. Fica como caminho aberto.
- **Descartar o reteste de 2026-11-16 sem registro:** descartada. O dado existe e é informativo sobre a estabilidade do `incerto`; o que não pode é ser usado como teste-reteste de 7 dias.
- **Reduzir o intervalo mínimo do ADR-0005 para um valor menor:** não recomendada. O resultado só é defensável diante do orientador se o intervalo for justificado, e nenhuma justificativa foi verificada.
