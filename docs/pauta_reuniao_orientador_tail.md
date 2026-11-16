# Pauta — reunião com o orientador: dados e benchmark da TAIL

**Para:** Prof. Hilton Martins de Brito Ramalho · **De:** Pedro Henrique Medeiros Vieira · **Data:** [a marcar]
**Duração sugerida:** 30–40 minutos · **Documentos de apoio:** `docs/relatorio_impacto_tail.md` (análise completa), `docs/adr/0013-dados-tail-e-regras-de-match-por-tipo-de-par.md` (decisões), `docs/protocolo_anotacao.md` (regras revisadas)

---

## 1. O que mudou, em três linhas

- Um projeto da TAIL (liga de IA da UFPB, da qual faço parte) resolveu um problema parecido com LLMs zero-shot e publicou um benchmark de 1.200 pares de anúncios do Mercado Livre (30 positivos). Vou usar dados e benchmark da TAIL como **reforço**, sem trocar o domínio (ALTA).
- A ALTA continua sendo o domínio. **Atualização de 2026-10-31 (ADR-0014):** decidi tornar produto × produto a fatia e o teste principais, com produto × dicionário como fatia secundária. Isso muda a hipótese central e a pergunta de pesquisa da proposta v3; o texto será atualizado.
- Por causa disso, a regra de match passou a ter **duas versões, uma por tipo de par**, o que muda o texto da proposta (Seção 4.1 e a delimitação do escopo).

## 2. Estado atual (para situar o prazo)

- Feitos: validação e limpeza dos dados (script 01), análise exploratória (script 02), ADRs 0001–0013, protocolo de anotação revisado.
- **Não iniciados:** blocagem, anotação do teste, partição treino/validação/teste, geração dos dados de treino. Os scripts 03 a 06 ainda são esqueletos.
- Pelo cronograma da proposta, o marco "ground truth fechado" era o fim da Semana 6. [Confirmar a semana atual na reunião.]

## 3. Decisões que preciso que o senhor valide

| # | Proposta | Por quê | Efeito no texto da proposta |
|---|---|---|---|
| 1 | **Cenário D:** ALTA principal; TAIL como treino extra (pares produto × produto), teste externo exploratório | Os dados da TAIL não têm pares produto × dicionário, e o próprio artigo deles diz que 30 positivos não bastam para treinar e testar um cross-encoder | Objetivos, §4.1, §4.4 e Resumo |
| 2 | **Duas regras de match:** produto × dicionário decide categoria e variante; produto × produto decide SKU (marca e tamanho) | Na ALTA, 1 kg e 5 kg de arroz são produtos diferentes, mas o dicionário não tem marca nem tamanho | §4.1 e delimitação do escopo |
| 3 | **Transitividade só para categoria:** dois produtos na mesma entrada do dicionário não são necessariamente o mesmo SKU | Consequência direta da decisão 2 | Delimitação (ADR-0007 emendado) |
| 4 | **Dois adaptadores LoRA** (um por tipo de par), sobre o mesmo LLaMA 3.2 3B | Isola os dois regimes de rótulo. Custo: dois treinos, e a ablação encolhe primeiro se o prazo apertar | §4.2 e §5 |
| 5 | Em produto × dicionário, **kit/promoção e marca própria são não-match**; marca própria só vale quando o texto declara | Decisão de domínio; limitação: marca própria sem sinal no texto segue as regras gerais | Protocolo (§3.3) e limitações |
| 6 | O benchmark da TAIL é **resultado secundário e exploratório**, só para o adaptador produto × produto | 30 positivos, 12 deles de 3 famílias de produto; IC95% do F1 do melhor modelo vai de ~0,64 a ~0,90 | §4.4 e Resultados |

## 4. Pontos abertos que quero ouvir a opinião do senhor

1. **Dataset Generator da Dharma (suspenso).** Hoje não há outra fonte planejada de pares de treino produto × dicionário, e a supervisão distante por "marca + unidade" não funciona num dicionário sem marca nem tamanho. Qual caminho o senhor prefere: manter o Generator, gerar variações por regras próprias (com seed), ou outro?
2. **Tamanho do teste produto × produto.** Hoje 50–100 pares. Com poucos positivos o poder estatístico é baixo; subir para ~100–150 custa anotação. Vale a troca?
3. **Segundo anotador.** Não haverá. A recomendação 2 do parecer continua como limitação declarada (teste-reteste intra-anotador). Fica aceitável?
4. **Prazo.** Com dois adaptadores e o atraso em relação ao cronograma, a ablação é a primeira a encolher. Concorda com essa regra? Existe margem para prorrogar a entrega, se necessário?
5. **Citação da TAIL.** O artigo deles ainda não tem referência publicada verificável (BibTeX com campos em branco, PDF sem venue). Como citar um trabalho em andamento de um grupo da UFPB? Combinar coautoria ou agradecimento para o artigo derivado do TCC?

## 5. Pendências que continuam abertas

- **Autorização escrita da TAIL** (uso de dados, teste, publicação de números). Já será solicitada. Até lá, nada da TAIL é versionado, redistribuído ou publicado.
- **Autorizações da Dharma-AI e do ALTA/CNPq** (infraestrutura, abertura do repositório e do teste anotado) e a **conversa sobre propriedade intelectual**, que o parecer pede que ocorra antes da defesa.
- **Acesso à GPU da Dharma-AI** ainda não confirmado por escrito.

## 6. Encaminhamentos esperados da reunião

- [ ] Aval formal (ata ou e-mail) para as decisões 1 a 6, para o ADR-0013 deixar de ter essa condição aberta.
- [ ] Autorização para editar o `main.tex` (a proposta v3 é a fonte de verdade).
- [ ] Posição sobre o Generator, o tamanho do teste produto × produto e o prazo.
