#!/usr/bin/env bash
# Idempotent setup script for the jdc CLI.
# No sudo required — binary stays in homelab-cli/, PATH via direnv.

set -euo pipefail

GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[0;33m"
RESET="\033[0m"

info() {
  printf "${GREEN}[INFO]${RESET} %b\n" "$1"
}

action() {
  printf "${YELLOW}[ACTION]${RESET} %b\n" "$1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_BIN="${SCRIPT_DIR}/jdc"
COMPLETION_FILE="${HOME}/.zshrc_jdc_completion"
ZSHRC_FILE="${HOME}/.zshrc"

# --- 0. Check Go is available ---
if ! command -v go >/dev/null 2>&1; then
  printf "${YELLOW}[ERROR]${RESET} go not found on PATH.\n"
  printf "Install Go from https://go.dev/dl/ then re-run this script.\n"
  exit 1
fi

# --- 1. Build binary ---
info "Building ${BLUE}homelab-cli/jdc${RESET}..."
make -C "${SCRIPT_DIR}" build

# --- 2. Refresh cache ---
info "Refreshing ${BLUE}.jdc-cache.json${RESET}..."
"${TARGET_BIN}" self refresh

# --- 3. Generate zsh completion ---
"${TARGET_BIN}" self completion zsh > "${COMPLETION_FILE}"
info "Completion script written to ${BLUE}${COMPLETION_FILE}${RESET}"

# --- 4. Idempotently source completion in ~/.zshrc ---
# The source line is wrapped in a zsh guard so sourcing ~/.zshrc from bash
# (e.g. during direnv or manual testing) does not trigger `compdef: command not found`.
touch "${ZSHRC_FILE}"
SOURCE_LINE="[[ -n \"\$ZSH_VERSION\" ]] && source ${COMPLETION_FILE}"
if awk -v line="${SOURCE_LINE}" 'BEGIN{found=0} $0==line{found=1} END{exit !found}' "${ZSHRC_FILE}"; then
  info "Completion source line already present in ${BLUE}${ZSHRC_FILE}${RESET}; skipping"
else
  # Remove any old unguarded source line from a previous install
  if grep -qF "source ${COMPLETION_FILE}" "${ZSHRC_FILE}" 2>/dev/null; then
    grep -vF "source ${COMPLETION_FILE}" "${ZSHRC_FILE}" > "${ZSHRC_FILE}.tmp" && mv "${ZSHRC_FILE}.tmp" "${ZSHRC_FILE}"
    info "Replaced old unguarded source line in ${BLUE}${ZSHRC_FILE}${RESET}"
  fi
  echo "${SOURCE_LINE}" >> "${ZSHRC_FILE}"
  info "Appended zsh-guarded source line to ${BLUE}${ZSHRC_FILE}${RESET}"
fi

# --- 5. Verify jdc is resolvable (expects direnv to be active) ---
if command -v jdc >/dev/null 2>&1; then
  info "jdc is resolvable at ${BLUE}$(command -v jdc)${RESET}"
else
  action "jdc is not yet on PATH. Run: ${BLUE}direnv allow${RESET} (or restart your shell)"
fi

action "To enable completion, restart your shell or run: ${BLUE}source ~/.zshrc${RESET} (in zsh)"
