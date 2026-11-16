# Rascunho de e-mail para a TAIL — pedido de autorização (NÃO ENVIADO)

**Para:** [NOME DO LÍDER DO PROJETO] · **Cc:** [opcional: demais autores / coordenação da liga] · **De:** Pedro Henrique Medeiros Vieira
**Assunto:** Pedido de autorização para uso do repositório e do benchmark da TAIL no meu TCC

---

Oi, [NOME],

Obrigado pela conversa. Como combinamos, vou usar dados e o benchmark do projeto TAIL no meu TCC (Entity Matching de produtos de supermercado com modelos de linguagem pequenos, UFPB, orientador Prof. Hilton Ramalho). Como o repositório `TailUFPB/invoice-data-normalizer` não tem arquivo de licença e o README fala em "academic research purposes", queria deixar o combinado **por escrito**, para eu usar e citar tudo de forma correta.

## O que eu pretendo fazer

1. **Treino:** usar os pares de títulos (original ↔ variantes) como exemplos positivos e montar negativos a partir dos outros títulos, **só no treino** do meu modelo de pares produto × produto. A partição por grupo de título original é feita antes de qualquer geração, para não haver vazamento.
2. **Teste externo:** avaliar meu modelo nos 1.200 pares de `pairs_to_label.csv`, comparando com as predições que vocês já salvaram (Gemini, GPT, DeepSeek e TF-IDF). Tratar isso como resultado **exploratório**, e reportar com cuidado, já que são 30 positivos (como o próprio artigo diz).
3. **Publicação:** reportar esses números e tabelas no TCC e, depois, num possível artigo de conferência, citando a TAIL.
4. **Não redistribuir:** eu **não** vou copiar os arquivos para um repositório público. O clone fica local e fora do git, e eu só referencio o repositório e o commit (`9d010ec`).

## O que eu preciso confirmar com vocês

1. **Posso usar, para esses fins,** os arquivos: `main_supersaurus/dados/pairs_to_label.csv`, `pairs_normalized*.csv`, `baseline_predictions.csv`, `poc_diplodocus/data/input/old_attack_dataset.csv`, `poc_*/data/input/test.csv` e `attack.csv`?
2. **Qual é a versão oficial dos rótulos?** `main_supersaurus/dados/pairs_to_label.csv` tem 30 positivos (reproduz a Tabela 2 do artigo), mas `main_supersaurus/data/pairs_to_label.csv` tem 28 e diverge em 4 linhas (629, 1081, 1130 e 1183). Qual vale, e por que mudaram?
3. **O artigo foi submetido ou publicado?** Onde? Como vocês preferem que eu cite? O BibTeX do README está com `author` e `booktitle` em branco.
4. **Origem e termos dos dados:** o dump do Mercado Livre, os arquivos `octaprice_mercadolivre_*.json` e as descrições de NF-e (`AmostraDescMerc.csv`, `itens_nf_normalizados.csv`). Alguma coisa está sob NDA ou tem restrição de uso? (Eu não pretendo usar os `octaprice_*.json`.)
5. **Código:** posso reimplementar as métricas a partir do que está documentado no artigo e conferir contra os números de vocês, ou prefere que eu cite sem reutilizar trechos? Vocês pretendem licenciar o repositório?
6. **Resultados que não estão no repositório:** a pasta do Drive de fine-tuning (`results_finetune.md`), em especial os resultados do LLaMA 3.2 3B, e as execuções 2 e 3 de GPT e DeepSeek com as colunas de predição. Posso ter acesso e mencioná-los?
7. **Autoria:** para o TCC, pretendo agradecer e citar a TAIL. Se eu levar o benchmark para um artigo derivado, como vocês preferem tratar autoria ou agradecimento? Prefiro combinar isso agora.

Se ficar mais fácil, uma resposta curta por e-mail com "autorizado" e os itens acima já resolve. Posso mandar também um resumo de como vou usar cada arquivo.

Obrigado!
Pedro Henrique Medeiros Vieira
