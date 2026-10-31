# ADR-0013: Dados e benchmark da TAIL como reforço, e duas regras de match por tipo de par

**Status:** Aceito, com duas condições abertas: (1) o aval do orientador foi informado pelo autor em 2026-10-31 e **ainda precisa ser confirmado formalmente** (ata ou e-mail); (2) a autorização **escrita** da TAIL está pendente — até ela chegar, nenhum dado, predição ou código da TAIL é versionado, redistribuído ou publicado. Substitui o ADR-0004 nos pontos abaixo; emenda os ADRs 0007 e 0008. O ADR-0005 **não** é emendado: não haverá segundo anotador (decisão do autor, 2026-10-31), então a confiabilidade continua sendo só o teste-reteste intra-anotador. Análise completa e evidências: `docs/relatorio_impacto_tail.md`. **Parcialmente substituído pelo ADR-0014** (decisão 1 e o item "teste principal"): produto × produto passa a ser a fatia e o teste principais, e produto × dicionário a secundária. O restante deste ADR continua em vigor.

## Contexto
A TAIL (liga acadêmica de IA da UFPB) publicou um pipeline zero-shot de normalização de títulos com LLMs, com um benchmark de 1.200 pares do Mercado Livre rotulados como "mesmo SKU" (30 positivos, um anotador por par), predições por par de três LLMs e de dois baselines TF-IDF, e conjuntos de títulos e variantes sintéticas sem rótulo de par. O autor decidiu treinar o SLM também com dados da TAIL e usar o benchmark como comparação.

Pontos verificados que limitam esse uso: o próprio artigo da TAIL diz que 30 positivos não bastam para ajustar um cross-encoder e manter avaliação independente (TAIL p.9); o benchmark é de marketplace, não de supermercado; os dados em disco não contêm pares produto×dicionário; o repositório não tem licença.

O autor também decidiu que, para a ALTA, marca e tamanho distinguem produtos (arroz branco 1 kg ≠ 5 kg). O dicionário canônico, porém, só tem produtos genéricos, sem marca nem tamanho, então essa distinção só pode valer entre dois produtos, não entre um produto e uma entrada do dicionário.

## Decisão
1. **A ALTA continua sendo o domínio.** ~~E o teste principal (teste manual de ~300–500 pares, ADR-0004).~~ **Substituído pelo ADR-0014:** o teste principal passa a ser produto × produto; produto × dicionário é o teste secundário, com tamanho a definir.
2. **Duas regras de match, por tipo de par:**

   | Tipo de par | O que decide o match | Marca | Tamanho |
   |---|---|---|---|
   | Produto × dicionário | Categoria e variante (branco × integral × parboilizado) | Não decide, **exceto marca própria (não-match)** | Não decide |
   | Produto × produto | SKU | Decide | Decide |

   Em produto × dicionário, **kit/promoção e marca própria são não-match** (decisão do autor, 2026-10-31). Marca própria só é reconhecida quando o **texto da descrição declara**; o conhecimento do anotador sobre as marcas das redes não é usado. Limitação conhecida: marca própria sem sinal no texto é rotulada como as demais.
3. **Transitividade só para categoria.** Dois produtos que mapeiam à mesma entrada do dicionário são da mesma categoria, não necessariamente o mesmo produto. O ADR-0007 deixa de afirmar que a subtarefa intra-base "é resolvida como consequência lógica": produto × produto em nível SKU é decidido pelo próprio modelo.
4. **Dois adaptadores LoRA sobre o mesmo checkpoint-base** (LLaMA 3.2 3B), um por tipo de par: um para produto × dicionário e outro para produto × produto (decisão do autor, 2026-10-31, contra a recomendação do relatório de usar modelo único). O tipo de par define qual adaptador é usado, então a entrada não precisa de marcador. Cai a promessa de generalização "sem retreinamento" do ADR-0007. A arquitetura continua sendo Cross-Encoder (ADR-0001). O zero-shot do LLaMA continua sendo o mesmo checkpoint-base, sem adaptador (ADR-0008).
5. **Dados da TAIL entram no treino apenas como pares produto × produto:** positivos de variantes do mesmo título original e negativos minerados. A partição é por **grupo de título original** (original, todas as suas variantes e positivos ligados), aplicada **antes** de qualquer geração ou aumentação, com assert de que nenhum grupo cai em mais de uma partição e de que nenhum título do benchmark TAIL (nem quase-duplicata) está no treino ou na validação.
6. **O benchmark da TAIL é teste externo, exploratório, só da fatia produto × produto**, reportado em tabela separada: McNemar pareado contra as predições salvas da TAIL, bootstrap por cluster e contagens absolutas TP/FP/FN. O limiar do modelo vem da validação do TCC, nunca do benchmark. Não entra em comparação com a fatia produto × dicionário.
7. **Nenhum gerador ou LLM produz ou rotula pares de teste ou de validação** — vale para o Dataset Generator da Dharma, para o `attack_augmentation` da TAIL, para LLM-as-judge e para as predições de Gemini, GPT e DeepSeek. As predições da TAIL não servem de rótulo de treino enquanto esses modelos forem baselines (evita comparação circular aluno × professor).

## Decisões ainda abertas
- **[SUSPENSO] Papel do Dataset Generator da Dharma** (relatório D-5): o autor deixou em suspenso em 2026-10-31. Precisa ser decidido **antes da geração de treino produto × dicionário** (tarefa 1.7), porque hoje não há outra fonte planejada de pares produto × dicionário. Enquanto estiver suspenso, nenhuma chamada ao Generator é feita e nenhuma tarefa pode depender dele.
- **[DECISÃO PENDENTE] Tamanho do teste produto × produto** (D-13), hoje 50–100 pares. Agora é a fatia principal (ADR-0014), então a faixa original provavelmente não basta.

## Consequências
- ~~A hipótese central e a pergunta de pesquisa da proposta v3 são preservadas.~~ **Substituído pelo ADR-0014:** a hipótese central e a pergunta de pesquisa passam à fatia produto × produto. O resultado no benchmark TAIL é exploratório: com 30 positivos, só diferenças grandes de F1 (da ordem de 15–20 p.p.) são distinguíveis.
- A fatia produto × produto deixa de ser só uma validação e vira um segundo regime de rótulo, com treino próprio. A tarefa 1.3 do plano (protocolo) bloqueia a anotação.
- Spec 001 (partição por grupo para a TAIL, assert de vazamento), spec 002 (benchmark externo), spec 003 (dois adaptadores), spec 004 (tabela externa) e as skills `reprodutibilidade-ml`, `avaliacao-baselines` e `protocolo-anotacao-em` precisam ser atualizadas.
- A restrição inegociável do `CLAUDE.md` sobre o Dataset Generator passa a valer para qualquer gerador ou LLM.
- Autorizações em aberto passam a incluir a TAIL. Não redistribuir o benchmark nem as predições da TAIL no repositório do TCC: referenciar o repositório e o commit `9d010ec`, com SHA-256 dos arquivos usados.
- `invoice-data-normalizer/` fica fora do git (`.gitignore`). Se a TAIL autorizar, uma cópia curada dos poucos artefatos usados vai para `dados/brutos/tail/`, também ignorada pelo git.
- **Os dados da TAIL só alimentam o adaptador produto × produto.** A TAIL não tem pares produto × dicionário, então o adaptador produto × dicionário (a fatia que este ADR tratava como principal; secundária desde o ADR-0014) é treinado sem dados da TAIL. A comparação "com/sem TAIL" só se aplica ao adaptador produto × produto, e o benchmark externo só avalia esse adaptador.
- **Custo dos dois adaptadores:** dois treinos, duas configs e duas avaliações. Se o prazo apertar, a ablação encolhe primeiro (regra do `main.tex` §5), nunca a anotação. Um treino de adaptador pode ser dispensado só com novo ADR.
- Risco assumido: o benchmark externo é de outro domínio e usa SKU por anúncio; seus números não devem ser extrapolados para supermercado.

## Alternativas consideradas
- **A — Substituição total pela TAIL:** rejeitada. Sem pares de treino, 30 positivos, dados-fonte ausentes, derruba a proposta aprovada e o prazo.
- **B1/B2 — Treino e teste em domínios diferentes:** rejeitadas. Medem transferência entre duas definições de match, e o teste fora da ALTA tem poder estatístico baixo.
- **C — TAIL como núcleo, ALTA como segundo domínio:** rejeitada. Soma os custos de A à anotação da ALTA e não cabe no prazo.
- **D′ — Teste principal novo em dados do Mercado Livre:** não adotada agora. Exigiria o pool de títulos da TAIL, que não está disponível, e mudaria o domínio.
- **Tudo em nível SKU, com dicionário estendido por marca e tamanho:** não adotada. Reabriria o ADR-0007 e o desenho do teste, com custo de anotação incompatível com o prazo.
- **Marca e tamanho por campos estruturados (`und_val`, `und_med`) fora do modelo:** não adotada. O ADR-0011 proíbe esses campos como entrada do modelo; podem servir só para montar pares.
- **Modelo único com marcador do tipo de par:** recomendado pelo relatório (um treino, aprendizado compartilhado), mas não adotado: o autor preferiu isolar os dois regimes de rótulo em adaptadores separados. Pode ser retomado por novo ADR se o custo de dois treinos se mostrar inviável.
