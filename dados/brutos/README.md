# 📥 Dados Brutos (Raw Data)

> **Este diretório contém os dados originais, exatamente como foram coletados. Eles NUNCA devem ser modificados manualmente.**

---

## 📦 Dados reais do projeto ALTA/CNPq

### Nome do arquivo: `todos_mercados_2026-09-10.csv`

**Fonte:** ETL do projeto ALTA/CNPq (`cnpq-precos-etl`), extrato consolidado de 8 APIs de supermercado.
**Data de coleta:** 10/09/2026 (coleta pontual — não representa a série histórica completa do ALTA).
**Responsável pela coleta:** Equipe/pipeline do projeto ALTA.
**Tamanho:** 30.259 registros × 13 colunas.
**Formato:** CSV, separador vírgula, encoding UTF-8.

**Descrição das variáveis:**
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `product_id` | Inteiro | Identificador do produto na fonte de origem |
| `description` | Texto | Descrição bruta do produto, conforme PDV |
| `unit` | Categórico | Unidade de venda (UN, KG, ...) |
| `price` | Contínuo | Preço coletado |
| `location` | Texto | Estado, cidade e loja (ex.: "PB, João Pessoa, Pedro Gondim") |
| `source` | Categórico | Rede de origem (ajuba\_api, diniz\_api, mateus\_api, extra\_api, guedes\_api, pinheiro\_api, atacadao\_api, chegou\_a\_feira\_api) |
| `collected_at` | Timestamp | Data/hora da coleta |
| `und_val`, `und_med` | Numérico / categórico | Valor e unidade de medida normalizados |
| `preco_kg` | Contínuo | Preço normalizado por kg |
| `codg_item` | Numérico | Código de item já associado pelo ETL do ALTA |
| `desc_ref` | Texto | Descrição de referência já associada pelo ETL do ALTA |
| `match_score` | Contínuo | Score de confiança de um matching heurístico já aplicado pelo ETL |

**Observações:**
- **Dados sensíveis:** nenhum dado pessoal; preços e descrições de produtos são públicos.
- **⚠️ Risco de vazamento metodológico:** as colunas `codg_item`, `desc_ref` e `match_score` refletem um matching heurístico **já aplicado pelo pipeline de produção do ALTA**, anterior e independente deste TCC. Essas colunas **não devem ser usadas como insumo na anotação manual do conjunto de teste** (padrão-ouro, ADR-0004) nem no treinamento do Cross-Encoder deste trabalho — usá-las contaminaria a avaliação com os critérios (desconhecidos) de um matching de terceiros. Podem, no máximo, ser citadas como contexto do pipeline de origem dos dados.
- **Restrições de uso:** dados do projeto ALTA/CNPq; abertura pública condicionada à autorização dos coordenadores do ALTA/CNPq e da Dharma-AI (ver `main.tex`, §4.6 "Reprodutibilidade").

### Nome do arquivo: `dicionario_canonico.csv`

**Fonte:** Dicionário canônico de produtos enviado pela equipe do projeto ALTA.
**Data de coleta:** Não informada pelo ALTA na entrega do arquivo (original: `prep_padrao.csv`, `cnpq-precos-etl/entity_matching/data/`).
**Responsável pela coleta:** Equipe do projeto ALTA.
**Tamanho:** 1.593 entradas × 3 colunas (mais 2 colunas vazias no CSV original).
**Formato:** CSV, separador ponto-e-vírgula (`;`), encoding UTF-8.

**Descrição das variáveis:**
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `desc_alim` | Texto | Descrição canônica do produto genérico (sem marca/tamanho — ex.: "ARROZ BRANCO") |
| `codg_item1` | Numérico | Código de item, granularidade de produto genérico |
| `cod_padrao` | Categórico | 10 valores distintos (`1`–`9`, mais `99`; não existe o valor `0`); **significado não confirmado com o ALTA** — candidato a campo de categoria, ver `main.tex` §4.1/§4.7 |

**Observações:**
- Confirma a granularidade do dicionário como **produto genérico**, não SKU/marca — resolve a dúvida de `main.tex` §4.1 sobre a regra de tamanho/unidade.
- `cod_padrao`: **[a confirmar com o time do ALTA]** antes de assumir como sinal de categoria para estratificação/blocagem.
- Mais entradas podem ser geradas a partir deste dicionário (paráfrases/variações), conforme ADR-0004.

---

## ⚠️ Regras Importantes

1. **Nunca edite** arquivos neste diretório manualmente
2. **Nunca sobrescreva** com dados processados — use `dados/processados/` para isso
3. Este diretório está no `.gitignore` por padrão (dados podem ser grandes). Para dados pequenos (<50MB), remova a linha correspondente do `.gitignore`
4. Para datasets grandes, considere Git LFS ou hospedagem externa (ver README principal)
