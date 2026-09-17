# =============================================================================
#  📊  Makefile — Repositório-Modelo para Trabalhos Acadêmicos
# =============================================================================
#  Gerenciado com uv  ·  https://docs.astral.sh/uv/
#  Execute  make help  para ver todos os comandos disponíveis.
# =============================================================================

.DEFAULT_GOAL := help
SHELL         := /bin/bash

# ── Cores ANSI ───────────────────────────────────────────────────────────────
CYAN    := $(shell printf '\033[36m')
GREEN   := $(shell printf '\033[32m')
YELLOW  := $(shell printf '\033[33m')
RED     := $(shell printf '\033[31m')
MAGENTA := $(shell printf '\033[35m')
BOLD    := $(shell printf '\033[1m')
RESET   := $(shell printf '\033[0m')

# ── Documento ─────────────────────────────────────────────────────────────
# Este TCC usa um único formato (abntex2[article]): latex/tcc_artigo/.
#   make latex   (compila latex/tcc_artigo/main.tex)
DOC     ?= tcc_artigo
PYTHON  := uv run python
SCRIPTS := scripts
TEX_DIR := latex

# =============================================================================
#  🆘  Ajuda
# =============================================================================

.PHONY: help
help: ## 🆘  Mostra este menu de ajuda
	@echo ""
	@echo "  $(BOLD)$(CYAN)📊  Repositório-Modelo Acadêmico — Comandos Disponíveis$(RESET)"
	@echo "  $(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "  $(YELLOW)💡 Dica:$(RESET) Comece com $(BOLD)make setup$(RESET) e depois $(BOLD)make pipeline$(RESET)"
	@echo "  $(YELLOW)📄  Para compilar um documento:$(RESET) $(BOLD)make latex DOC=tcc_artigo$(RESET)"
	@echo ""

# =============================================================================
#  🔧  Ambiente & Instalação
# =============================================================================

.PHONY: setup
setup: ## 🔧  Instala dependências com uv (primeira vez)
	@echo ""
	@echo "  $(BOLD)$(GREEN)🔧  Preparando o ambiente de desenvolvimento...$(RESET)"
	@echo "  $(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	uv sync
	@echo ""
	@echo "  $(GREEN)✅  Ambiente pronto! Todas as dependências instaladas.$(RESET)"
	@echo ""

.PHONY: setup-dev
setup-dev: ## 🔧  Instala dependências + ferramentas de dev
	@echo ""
	@echo "  $(BOLD)$(GREEN)🔧  Instalando ambiente completo (prod + dev)...$(RESET)"
	uv sync --group dev
	@echo ""
	@echo "  $(GREEN)✅  Ambiente dev pronto! ruff + pytest disponíveis.$(RESET)"
	@echo ""

.PHONY: update
update: ## ♻️   Atualiza dependências para últimas versões
	@echo ""
	@echo "  $(BOLD)$(CYAN)♻️   Atualizando dependências...$(RESET)"
	uv lock --upgrade
	uv sync
	@echo ""
	@echo "  $(GREEN)✅  Dependências atualizadas com sucesso!$(RESET)"
	@echo ""

# =============================================================================
#  🚀  Pipeline de Dados
# =============================================================================

.PHONY: pipeline
pipeline: coleta eda construir-dataset baselines finetuning avaliar ## 🚀  Executa o pipeline completo (01 → 06)
	@echo ""
	@echo "  $(BOLD)$(GREEN)🎉  Pipeline completo executado com sucesso!$(RESET)"
	@echo "  $(YELLOW)📄  Execute $(BOLD)make latex$(RESET)$(YELLOW) para compilar o PDF.$(RESET)"
	@echo ""

.PHONY: coleta
coleta: ## 📥  01 — Carrega base ALTA + dicionário canônico
	@echo ""
	@echo "  $(BOLD)$(MAGENTA)📥  Etapa 01 · Carregando dados brutos...$(RESET)"
	$(PYTHON) $(SCRIPTS)/01_coleta_dados.py
	@echo "  $(GREEN)✅  Dados brutos validados em dados/brutos/$(RESET)"
	@echo ""

.PHONY: eda
eda: ## 🔍  02 — Análise exploratória (spec 001)
	@echo ""
	@echo "  $(BOLD)$(MAGENTA)🔍  Etapa 02 · Análise exploratória em andamento...$(RESET)"
	$(PYTHON) $(SCRIPTS)/02_analise_exploratoria.py
	@echo "  $(GREEN)✅  EDA concluída! Estatísticas em resultados/$(RESET)"
	@echo ""

.PHONY: construir-dataset
construir-dataset: ## 🧩  03 — Blocagem, candidatos e partições (spec 001)
	@echo ""
	@echo "  $(BOLD)$(MAGENTA)🧩  Etapa 03 · Construindo dataset e ground truth...$(RESET)"
	$(PYTHON) $(SCRIPTS)/03_construcao_dataset.py
	@echo "  $(GREEN)✅  Partições e candidatos salvos em dados/processados/$(RESET)"
	@echo ""

.PHONY: baselines
baselines: ## 📐  04 — Baselines clássicos + LLaMA zero-shot (spec 002)
	@echo ""
	@echo "  $(BOLD)$(MAGENTA)📐  Etapa 04 · Rodando baselines...$(RESET)"
	$(PYTHON) $(SCRIPTS)/04_baselines.py
	@echo "  $(GREEN)✅  Métricas dos baselines salvas em resultados/metricas/$(RESET)"
	@echo ""

.PHONY: finetuning
finetuning: ## 🧠  05 — Fine-tuning LoRA do Cross-Encoder (spec 003)
	@echo ""
	@echo "  $(BOLD)$(MAGENTA)🧠  Etapa 05 · Fine-tuning do Cross-Encoder...$(RESET)"
	$(PYTHON) $(SCRIPTS)/05_finetuning.py
	@echo "  $(GREEN)✅  Adaptador LoRA salvo em modelos/$(RESET)"
	@echo ""

.PHONY: avaliar
avaliar: ## 📊  06 — Avaliação, ablação e exportação para LaTeX (spec 004)
	@echo ""
	@echo "  $(BOLD)$(MAGENTA)📊  Etapa 06 · Avaliando e exportando resultados...$(RESET)"
	$(PYTHON) $(SCRIPTS)/06_avaliacao_exportacao.py
	@echo "  $(GREEN)✅  Métricas e tabelas LaTeX geradas em latex/tcc_artigo/$(RESET)"
	@echo ""

# =============================================================================
#  📄  LaTeX — Compilação Multi-Documento
# =============================================================================
#  Uso:
#    make latex              → compila o tipo padrão (tcc_artigo)
#    make latex DOC=tcc      → compila o TCC padrão (capítulos)
#    make latex DOC=artigo   → compila o artigo solto
#    make latex DOC=tese     → compila a tese
#    make latex DOC=livro    → compila o livro didático
# =============================================================================

.PHONY: latex
latex: ## 📄  Compila o documento LaTeX (PDF) — use DOC=tipo para selecionar
	@echo ""
	@echo "  $(BOLD)$(CYAN)📄  Compilando $(DOC)/main.tex → PDF...$(RESET)"
	@echo "  $(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	cd $(TEX_DIR)/$(DOC) && latexmk -pdf -interaction=nonstopmode main.tex
	@echo ""
	@echo "  $(GREEN)✅  PDF gerado: $(TEX_DIR)/$(DOC)/main.pdf$(RESET)"
	@echo ""

.PHONY: latex-clean
latex-clean: ## 🧹  Remove artefatos de compilação LaTeX
	@echo ""
	@echo "  $(YELLOW)🧹  Limpando artefatos LaTeX...$(RESET)"
	cd $(TEX_DIR)/$(DOC) && latexmk -C main.tex 2>/dev/null || true
	@echo "  $(GREEN)✅  Artefatos LaTeX removidos!$(RESET)"
	@echo ""

.PHONY: latex-all
latex-all: ## 📚  Compila todos os tipos de documento (só tcc_artigo neste TCC)
	@echo ""
	@echo "  $(BOLD)$(CYAN)📚  Compilando todos os documentos...$(RESET)"
	@for doc in tcc_artigo; do \
		echo ""; \
		echo "  $(MAGENTA)→ Compilando $$doc...$(RESET)"; \
		$(MAKE) latex DOC=$$doc --no-print-directory; \
	done
	@echo ""
	@echo "  $(GREEN)✅  Todos os PDFs gerados!$(RESET)"
	@echo ""

.PHONY: latex-clean-all
latex-clean-all: ## 🧹  Remove artefatos de todos os documentos
	@echo ""
	@echo "  $(YELLOW)🧹  Limpando artefatos de todos os documentos...$(RESET)"
	@for doc in tcc_artigo; do \
		echo "  → Limpando $$doc"; \
		(cd $(TEX_DIR)/$$doc && latexmk -C main.tex 2>/dev/null) || true; \
	done
	@echo "  $(GREEN)✅  Artefatos de todos os documentos removidos!$(RESET)"
	@echo ""

# =============================================================================
#  📂  Gerenciamento de Documentos
# =============================================================================

.PHONY: list-docs
list-docs: ## 📂  Lista os tipos de documento disponíveis em latex/
	@echo ""
	@echo "  $(BOLD)$(CYAN)📂  Tipos de Documento Disponíveis$(RESET)"
	@echo "  $(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	@for d in $(TEX_DIR)/*/; do \
		name=$$(basename $$d); \
		if [ -f "$$d/main.tex" ]; then \
			echo "  $(GREEN)✅$$(RESET) $$name"; \
		fi; \
	done
	@echo ""
	@echo "  $(YELLOW)💡  Use:$(RESET) make latex DOC=<tipo>"
	@echo ""

.PHONY: new-doc
new-doc: ## ✨  Cria um novo tipo de documento — use TYPE=nome
	@if [ -z "$(TYPE)" ]; then \
		echo ""; \
		echo "  $(RED)❌  Erro: informe o nome do tipo com TYPE=monografia$(RESET)"; \
		echo "  $(YELLOW)💡  Exemplo:$(RESET) make new-doc TYPE=monografia"; \
		echo ""; \
		exit 1; \
	fi; \
	if [ -d "$(TEX_DIR)/$(TYPE)" ]; then \
		echo ""; \
		echo "  $(RED)❌  O tipo '$(TYPE)' já existe em $(TEX_DIR)/$(TYPE)/$(RESET)"; \
		echo ""; \
		exit 1; \
	fi; \
	echo ""; \
	echo "  $(BOLD)$(CYAN)✍️  Criando novo tipo: $(TYPE)$(RESET)"; \
	echo "  $(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"; \
	mkdir -p $(TEX_DIR)/$(TYPE)/figuras $(TEX_DIR)/$(TYPE)/tabelas; \
	cp $(TEX_DIR)/tcc_artigo/main.tex $(TEX_DIR)/$(TYPE)/main.tex; \
	echo ""; \
	echo "  $(GREEN)✅  Tipo '$(TYPE)' criado em $(TEX_DIR)/$(TYPE)/$(RESET)"; \
	echo "  $(YELLOW)📝  Edite:$(RESET) latex/$(TYPE)/main.tex"; \
	echo "  $(YELLOW)▶️   Compile:$(RESET) make latex DOC=$(TYPE)"; \
	echo ""

# =============================================================================
#  🧪  Qualidade de Código
# =============================================================================

.PHONY: lint
lint: ## 🔎  Verifica estilo do código (ruff check)
	@echo ""
	@echo "  $(BOLD)$(CYAN)🔎  Analisando estilo do código...$(RESET)"
	uv run ruff check $(SCRIPTS)/ tests/
	@echo "  $(GREEN)✅  Código aprovado pelo linter!$(RESET)"
	@echo ""

.PHONY: format
format: ## ✨  Formata o código automaticamente (ruff format)
	@echo ""
	@echo "  $(BOLD)$(CYAN)✨  Formatando código...$(RESET)"
	uv run ruff format $(SCRIPTS)/ tests/
	uv run ruff check --fix $(SCRIPTS)/ tests/
	@echo "  $(GREEN)✅  Código formatado com estilo!$(RESET)"
	@echo ""

.PHONY: typecheck
typecheck: ## 🏷️   Verifica tipagem estática (mypy)
	@echo ""
	@echo "  $(BOLD)$(CYAN)🏷️   Verificando tipagem...$(RESET)"
	uv run mypy $(SCRIPTS)/
	@echo "  $(GREEN)✅  Tipagem validada!$(RESET)"
	@echo ""

.PHONY: test
test: ## 🧪  Executa testes (pytest)
	@echo ""
	@echo "  $(BOLD)$(CYAN)🧪  Executando testes...$(RESET)"
	uv run pytest -v
	@echo ""

.PHONY: check
check: lint typecheck test ## 🚥  Roda todas as verificações do CI localmente
	@echo ""
	@echo "  $(BOLD)$(GREEN)🚥  Todas as verificações (CI) passaram!$(RESET)"
	@echo ""

# =============================================================================
#  🧹  Limpeza
# =============================================================================

.PHONY: clean
clean: ## 🗑️   Remove artefatos gerados (resultados, modelos, cache)
	@echo ""
	@echo "  $(BOLD)$(YELLOW)🗑️   Limpando artefatos gerados...$(RESET)"
	rm -rf dados/processados/*.csv dados/processados/*.parquet
	rm -rf resultados/figuras/*.png resultados/figuras/*.eps
	rm -rf resultados/metricas/*.csv
	rm -rf resultados/relatorios/*
	rm -rf modelos/*.joblib modelos/*.pkl modelos/adapter_*
	rm -rf __pycache__ $(SCRIPTS)/__pycache__
	rm -rf .pytest_cache
	@echo "  $(GREEN)✅  Projeto limpo. Execute $(BOLD)make pipeline$(RESET)$(GREEN) para regenerar tudo.$(RESET)"
	@echo ""

.PHONY: clean-all
clean-all: clean latex-clean ## 💣  Limpeza total (dados + LaTeX + cache)
	@echo ""
	@echo "  $(RED)💣  Limpeza total concluída!$(RESET)"
	@echo "  $(YELLOW)⚠️   Execute $(BOLD)make setup$(RESET)$(YELLOW) e $(BOLD)make pipeline$(RESET)$(YELLOW) para reconstruir.$(RESET)"
	@echo ""

# =============================================================================
#  📋  Informações do Projeto
# =============================================================================

.PHONY: info
info: ## ℹ️   Mostra informações do ambiente
	@echo ""
	@echo "  $(BOLD)$(CYAN)ℹ️   Informações do Projeto$(RESET)"
	@echo "  $(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	@echo "  $(BOLD)📂 Projeto:$(RESET)   Repositório-Modelo para Trabalhos Acadêmicos"
	@echo "  $(BOLD)📄 Documento:$(RESET) $(DOC)"
	@echo "  $(BOLD)🐍 Python:$(RESET)    $$(uv run python --version 2>/dev/null || echo 'não instalado')"
	@echo "  $(BOLD)📦 uv:$(RESET)        $$(uv --version 2>/dev/null || echo 'não instalado')"
	@echo "  $(BOLD)📄 LaTeX:$(RESET)     $$(latexmk --version 2>/dev/null | head -1 || echo 'não instalado')"
	@echo "  $(BOLD)🌿 Git:$(RESET)       $$(git --version 2>/dev/null || echo 'não instalado')"
	@echo "  $(BOLD)📁 Branch:$(RESET)    $$(git branch --show-current 2>/dev/null || echo 'N/A')"
	@echo ""
