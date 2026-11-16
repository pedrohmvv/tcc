# Pendências do autor

Itens que só o autor pode fazer ou decidir, reunidos em 2026-11-13. **O contexto completo para retomar numa sessão nova está em `docs/retomada_sessao_2026-11-13.md`** (com um prompt pronto para colar). Marque `[x]` ao concluir e anote a data. Nada aqui bloqueia o trabalho de código que já foi feito; cada item diz o que ele destrava.

## A. Caminho crítico (calendário)

A anotação é o único insumo que não se regenera por script, e o reteste só pode começar 7 dias depois da primeira passada (ADR-0005). Quanto antes a primeira passada acabar, antes o reteste fecha.

- [x] **A1. Anotar os 300 pares do teste produto × produto.** *Concluída em 2026-11-16: 140 `match`, 141 `nao_match`, 19 `incerto` (primeiro timestamp 2026-11-15T19:03, último 2026-11-16T11:30:50-03:00).*
  - Arquivo: `dados/processados/anotacoes_teste_pxp.csv` (separador `;`). Ferramenta: `ferramentas/anotador_teste.html`, aberta no Chrome ou no Edge (salva direto no arquivo).
  - Regra: `docs/protocolo_anotacao.md` §3, produto × produto. É o mesmo SKU: mesma marca, mesma variante, mesmo tamanho.
  - Rótulos: `match`, `nao_match`, `incerto`. Vazio significa "ainda não anotado".
  - O arquivo nunca é sobrescrito pelo script, e a anotação parcial é preservada.
  - Destrava: o reteste, o Kappa, o `teste.parquet` e qualquer número do modelo ou dos baselines no teste.
- [ ] **A2. Resolver os `incerto` do teste** (protocolo §3.5): adjudicar pelo dicionário ou pelos pesquisadores do ALTA. Os `incerto` não resolvidos ficam fora do teste final. **A planilha já está gerada (2026-11-16): `dados/processados/anotacoes_teste_pxp_adjudicacao.csv`, 19 pares, mesmo anotador HTML. Para cada par que você resolver (`match` ou `nao_match`), escreva a fonte na observação com o prefixo `dicionario:` ou `alta:` e o que consultou; o script recusa decisão sem prefixo. **Atualização (2026-11-16): há uma terceira fonte, `autor:`** (decisão pelo seu próprio julgamento, sem consulta; desvio do protocolo §3.5, rascunho em `docs/adr/0018-adjudicacao-de-incerto-pelo-autor-desvio-do-protocolo.md`). **Fechada em 2026-11-16: 9 decisões (2 match, 7 nao_match, todas `autor:`) e 10 incerto mantidos; 2 pares com 'Não é possível saber…' foram convertidos para incerto por instrução do autor; teste final = 290 pares.** ADR-0018 aceito e protocolo §3.5 emendado. Os pares decididos assim entram no teste com a fonte `autor_adjudicacao` e devem ser reportados com e sem eles. Quem ficar `incerto` sai do teste final. Conferir com `uv run python scripts/03_construcao_dataset.py --adjudicacao` (só valida; nunca reescreve). Cópia em branco no Desktop.** Acordado em 2026-11-16: registrar a adjudicação em **arquivo separado** (`id_par`, `rotulo_final`, `fonte`), nunca na planilha da primeira passada, para o reteste comparar contra o que você marcou de fato. O `incerto` **não** vira terceira classe do modelo por ora; reavaliar depois de contar os `incerto` da B2.
- [x] **A3 (com desvio do ADR-0005). Reteste feito em 2026-11-16, 39 minutos depois da primeira passada, por decisão do autor (prazo).** Kappa gravado em `resultados/metricas/kappa_reteste_pxp.csv` com `intervalo_minimo_cumprido=False`: 3 classes 0,8125 e binário 0,8955 (150 pares, 134 sem `incerto`). **Não é um teste-reteste de 7 dias**: mede sobretudo memória de curto prazo, é um limite superior da consistência e deve ser declarado como desvio no TCC. Pendente: emenda ou ADR novo ao ADR-0005 (rascunho só com o seu aval) e levar o desvio ao orientador (C4). Texto original da pendência, mantido abaixo:
  - ~~A3. Reteste (ADR-0005).~~ Reanotar às cegas, ≥ 7 dias depois da primeira passada. **A planilha já está gerada (2026-11-16): `dados/processados/anotacoes_teste_pxp_reteste.csv`, 150 pares estratificados, `incerto` incluído, sem rótulos, em outra ordem. Não abra antes de 2026-11-23.** Anote no mesmo anotador (`ferramentas/anotador_teste.html`) e depois rode `uv run python scripts/03_construcao_dataset.py --kappa-reteste`: ele grava o Kappa de 3 classes e o binário em `resultados/metricas/kappa_reteste_pxp.csv`, recusa-se a calcular com menos de 7 dias e o resultado é reportado mesmo abaixo de 0,75. Cópia da planilha em branco no Desktop; `make clean` a apagaria.
- [ ] **A5. Anotar os pares da opção B2 (treino).** Escolhida em 2026-11-13. Cerca de 3.974 pares do treino com mesmo tamanho e cosseno ≥ 0,5, estimativa de 1,5 a 5,5 h e ~430 positivos. Arquivo `dados/processados/anotacoes_treino_b2_pxp.csv`, mesma ferramenta e mesma regra do teste (`anotador_teste.html`, protocolo §3), rótulos `match`, `nao_match`, `incerto`. **A planilha já está gerada** (2026-11-13, 3.974 pares, sem rótulo, em ordem embaralhada). Não precisa terminar antes dos 300 pares do teste, mas o treino do adaptador só usa a B2 depois de pronta. O mesmo anotador abre os dois arquivos. **O treino já lê o que você anotar, em qualquer quantidade** (a planilha é embaralhada, então um pedaço anotado é uma amostra sem viés): é só rodar `uv run python scripts/03_construcao_dataset.py` e o `treino_pxp.parquet` passa a incluí-lo. Os `incerto` e os pares pendentes ficam de fora.
- [ ] **A4. Teste produto × dicionário (fatia secundária).** Decidir como amostrar os pares (`[DECISÃO PENDENTE]` da spec 001 e Q3) e anotar os 100 pares. Destrava o CA-1b-05 por completo.

## B. Dados e publicação (risco de exposição)

O repositório é **público** (`pedrohmvv/tcc`).

- [ ] **B1. Backup dos dados anotados.** Fora do git, sem backup hoje: os 3 lotes do pool (`dados/processados/pool_cego/lote_01..03.csv`, semanas de trabalho) e `pares_teste_pxp.csv`. A planilha do teste passa a entrar nessa lista conforme você anota. Decidir: remoto privado, ou commit depois da autorização do ALTA (C2).
- [ ] **B2. Dado da ALTA que já está público.** `anotacoes_amostra_cega.csv` (50 descrições reais) foi enviado ao remoto na branch `origin/feat/blocagem-e-fatia-principal`. Decidir se aceita, se pede a autorização do ALTA, ou se remove do remoto (remover do histórico exige cuidado; me peça antes de qualquer reescrita).
- [ ] **B3. Não commitar as planilhas anotadas sem decidir B1 e C2.** `dados/processados/anotacoes_teste_pxp.csv` (e, quando existir, `anotacoes_treino_b2_pxp.csv`) aparecem como arquivos novos para o git e entrariam num `git add -A`, porque o nome casa com a exceção `anotacoes*.csv` do `.gitignore`. A B2 também é trabalho seu que não se regenera: entra na lista do backup (B1).
- [ ] **B4. `proposta_tcc.docx` solto na raiz.** Destoa da regra "LaTeX é a única saída do texto". Mover para fora do repositório, ignorar ou remover.
- [ ] **B5. Commitar a 1.2b.** Nada da branch `feat/blocagem-produto-x-produto` está commitado (script 03, specs, testes, configs, ferramentas). Peça o commit quando quiser; por padrão eu deixo de fora `anotacoes_teste_pxp.csv` e `proposta_tcc.docx`.

## C. Autorizações e avais externos

- [ ] **C1. Dharma-AI:** autorização formal por escrito (infra e ferramenta de geração, abertura futura do repositório ou do teste anotado, avaliação de patente ou registro com o orientador). Ainda não solicitada.
- [ ] **C2. ALTA/CNPq:** autorização para abrir o repositório e o conjunto de teste anotado. Ainda não confirmada com os coordenadores. É bloqueio real de publicação.
- [ ] **C3. TAIL (ADR-0013), uso só local.** Guardar os áudios e mensagens de WhatsApp do dono do projeto **fora do git**; pedir uma confirmação de texto de uma linha; registrar no diário. O `main.tex` mantém `[a confirmar]`. Publicar qualquer coisa com dado da TAIL continua dependendo de autorização formal escrita.
- [ ] **C4. Orientador:** confirmar formalmente o aval ao ADR-0013 (ata ou e-mail) e validar o protocolo de anotação, que ainda não foi validado com ele. Pauta sugerida: ADR-0014, a partição por componente (τ = 0,7), a validação com só 25 `match` e o vazamento residual de 28,4%.

## D. Infraestrutura (bloqueia o treino, script 05)

- [ ] **D1. Acesso à GPU da Dharma-AI** e a VRAM real. É o gatilho do plano de contingência do ADR-0009.
- [ ] **D2. D9:** o ambiente de teste usa `load_in_4bit: True`, o que contradiz o ADR-0003 (LoRA em bf16, sem quantização). Resolver antes de treinar.
- [ ] **D3. Aceitar a licença do LLaMA 3.2 3B** no Hugging Face.
- [ ] **D4. Confirmar `torch` e `peft`** no Python ≥ 3.14, que é o requisito do `pyproject.toml`. *Verificado em 2026-11-13:* `torch`, `transformers`, `peft` e `accelerate` **não estão instalados** neste ambiente (são o extra `finetuning`), mas o `uv.lock` já resolve `torch 2.14.0` com wheels para o Python 3.14 (macOS arm64, Linux e Windows), além de `peft`, `transformers` e `accelerate`. Falta instalar (`uv sync --extra finetuning`, download de alguns GB) e rodar um smoke test; peça quando quiser.
- [ ] **D5. Dataset Generator (D-5, suspenso).** Decidir, antes da tarefa 1.7, a fonte dos pares produto × dicionário para treinar o adaptador secundário. Só bloqueia esse adaptador, não o principal.

## E. Documentos que dependem do seu aval

- [ ] **E1. T13 do `tasks-1b.md`:** protocolo §2.2 (como anotar o pool), plano 1.4.3, ADRs e `main.tex` que ainda dizem "a definir" para D-13 e para a partição, e `docs/resultado_blocagem_pxp.md`. Eu só edito com o seu aval para cada arquivo.
- [ ] **E2. `main.tex` (tarefa 5.3):** atualizar para o ADR-0014 e declarar a limitação da validação (25 `match`, rótulo só do autor) e o vazamento residual (23 de 81, 28,4%).
- [ ] **E3. Diário (`docs/diario_pesquisa.md`):** sem entrada depois de 2026-10-31. Registrar a partição (τ = 0,7 mantido, validação = pool, sem 80/20, medido em 2026-11-13), a limitação da validação e o status da TAIL. Posso redigir uma proposta.
- [ ] **E4. Decidir se a partição merece um ADR novo.** A decisão de 2026-11-13 está registrada na spec 001 e no `design-1b.md`, não em ADR. Por regra, mudança de decisão registrada em ADR exige ADR novo, mas esta não reabre nenhum ADR existente.
- [ ] **E6. Revisar o texto do ADR-0015** (`docs/adr/0015-rotulos-de-treino-produto-x-produto-sem-supervisao-distante.md`, status "Proposto") e, se concordar, mudar o status para "Aceito". Ao aceitar, sincronizar com o seu aval: `main.tex` §4 (cita "supervisão distante" entre os mecanismos de treino), ADR-0011 (a linha de metadado de unidade cita a RF2) e `docs/plano_desenvolvimento.md`. O cabeçalho do ADR-0004 já aponta para o ADR-0015.
- [ ] **E7. Revisar a tabela de abreviações** em `configs/pares_treino_pxp.yaml` (23 palavras, cada forma observada nos produtos de treino com DF ≥ 5). Corrija, apague ou acrescente entradas à vontade; depois peça para regenerar `pares_treino_auto_pxp.parquet` (é um comando só, e é regenerável). Só `pos_abreviacao` (573 de 6.000 positivos) depende dela.
- [ ] **E5. CPT (opcional, só "se der tempo"):** exige ADR novo e emenda da spec 003 antes de qualquer implementação.

## F. Virão de mim, para você aprovar

- [x] **F1. Fechar o desenho dos pares de treino produto × produto (P4).** *Concluída em 2026-11-13: você escolheu a B2 e aprovou a reescrita da RF2 por ADR novo e a receita de perturbação.* Opção **B2** escolhida em 2026-11-13 (proposta em `specs/001-construcao-dataset-ground-truth/design-treino-pxp.md`, seção 8). A medição mostrou que marca + tamanho (RF2) não é viável (precisão 3,1%) e que só o negativo por tamanho diferente é um rótulo certo (3.283 de 3.283). Faltam duas aprovações suas: (a) reescrever a RF2 e o trecho de supervisão distante do ADR-0004, por ADR novo, sem reabrir o 0004; (b) a receita de perturbação da parte A, em especial a abreviação.
- ~~**Formato do `teste.parquet`** na ingestão da anotação.~~ *Feito em 2026-11-16: `uv run python scripts/03_construcao_dataset.py --teste` gera `teste_pxp.parquet` (290 pares) e o resumo por estrato.*

## G. Perguntas em aberto para o autor responder

- [ ] **G1. Tempo real da anotação do pool.** Os timestamps indicam cerca de 2 h numa tarde (3/11; o lote 3, com 3.719 candidatos, foi gerado às 17:59 e concluído até 18:21), mas o texto de retomada falava em "semanas de trabalho". Qual foi o tempo real? As estimativas de esforço da B2 (1,5 a 5,5 h) escalam com isso.
- [x] **G2 (decidido em 2026-11-16: o filtro de tamanho vale para variantes e notas fiscais; sem tamanho fica fora por padrão).** No P5, o que fazer com as 13.085 variantes da TAIL sem tamanho reconhecível (não verificáveis): excluir, incluir com peso menor ou amostrar para revisão sua?
