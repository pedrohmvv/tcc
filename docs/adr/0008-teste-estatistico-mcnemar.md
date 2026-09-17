# ADR-0008: Teste de McNemar + tamanho de efeito, hipótese central não superdimensionada

**Status:** Aceito

## Contexto
O parecer do orientador (v2) apontou que a hipótese central original ("superará, de forma estatisticamente significativa") era forte demais para um conjunto de teste de 300–500 pares — o poder estatístico pode ser insuficiente para diferenças de pequena magnitude.

## Decisão
- Reportar significância via teste pareado adequado à comparação de classificadores sobre o mesmo conjunto de teste (McNemar).
- Reportar também tamanho de efeito e intervalos de confiança, independentemente do resultado do teste de hipótese.
- Hipótese central reformulada: o SLM fine-tuned "supera" os baselines e o mesmo modelo zero-shot — sem prometer significância estatística garantida a priori.

## Consequências
- Intelectualmente honesto: diferenças pequenas podem não atingir significância com N=300–500 sem que isso invalide a direção do efeito observado.
- O baseline "modelo genérico sem especialização" da hipótese é operacionalizado como o próprio LLaMA 3.2 3B zero-shot (mesmo checkpoint-base do fine-tuning) — isola o efeito da especialização de diferenças de arquitetura/capacidade.

## Alternativas consideradas
- **Teste t ou ANOVA sobre métricas agregadas:** inadequado — McNemar é o teste padrão para comparar dois classificadores sobre o mesmo conjunto pareado de exemplos.
