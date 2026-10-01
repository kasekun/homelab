.PHONY: help install-jdc

GREEN := \033[0;32m
RESET := \033[0m
INFO  := @printf "$(GREEN)[INFO]$(RESET) %b\n"

help:
	@echo "make install-jdc   # build jdc binary, refresh cache, set up zsh completion"

install-jdc:
	bash homelab-cli/setup.sh
