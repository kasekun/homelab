.PHONY: build completion-zsh

GREEN := \033[0;32m
BLUE  := \033[0;34m
RESET := \033[0m
INFO  := @printf "$(GREEN)[INFO]$(RESET) %b\n"

build:
	go build -o jdc .
	$(INFO) "built $(BLUE)homelab-cli/jdc$(RESET)"

# Writes zsh completion to ~/.zshrc_jdc_completion via `jdc self completion zsh`.
# Enable with: source ~/.zshrc_jdc_completion
completion-zsh: build
	./jdc self completion zsh > "$(HOME)/.zshrc_jdc_completion"
	$(INFO) "completion written to $(BLUE)~/.zshrc_jdc_completion$(RESET)"
