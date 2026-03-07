#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RADARR_DB="${ROOT_DIR}/appdata/radarr/radarr.db"
SONARR_DB="${ROOT_DIR}/appdata/sonarr/sonarr.db"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"
RADARR_BAK="${RADARR_DB}.bak.${TIMESTAMP}"
SONARR_BAK="${SONARR_DB}.bak.${TIMESTAMP}"

warn() {
  echo "WARNING: $*"
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

confirm_step() {
  local prompt="$1"
  read -r -p "${prompt} [y/N]: " reply
  case "${reply}" in
    [yY]|[yY][eE][sS]) return 0 ;;
    *) return 1 ;;
  esac
}

require_cmd() {
  local cmd="$1"
  command -v "${cmd}" >/dev/null 2>&1 || die "Required command not found: ${cmd}"
}

# Returns 0 (true) if the named container is currently running, 1 if not.
container_running() {
  local name="$1"
  docker ps --filter "name=^/${name}$" --filter "status=running" -q | grep -q .
}

assert_containers_stopped() {
  local running=()
  container_running radarr && running+=(radarr)
  container_running sonarr && running+=(sonarr)
  if [[ ${#running[@]} -gt 0 ]]; then
    echo >&2
    warn "Container(s) still running: ${running[*]}"
    warn "Writing to a live SQLite DB can corrupt it."
    warn "Stop the containers first (Step 1) before running any SQL steps."
    die "Aborting to prevent DB corruption."
  fi
}

print_counts() {
  echo
  echo "Current DB counters"
  echo "-------------------"
  echo "Radarr movies with files: $(sqlite3 "${RADARR_DB}" "SELECT COUNT(*) FROM Movies WHERE MovieFileId != 0;")"
  echo "Radarr movies without files: $(sqlite3 "${RADARR_DB}" "SELECT COUNT(*) FROM Movies WHERE MovieFileId = 0;")"
  echo "Sonarr episodes with files: $(sqlite3 "${SONARR_DB}" "SELECT COUNT(*) FROM Episodes WHERE EpisodeFileId != 0;")"
  echo "Sonarr monitored episodes without files: $(sqlite3 "${SONARR_DB}" "SELECT COUNT(*) FROM Episodes WHERE EpisodeFileId = 0 AND Monitored = 1;")"
  echo
}

require_cmd sqlite3
require_cmd cp

[[ -f "${ROOT_DIR}/jdc/bin/jdc" ]] || die "Could not find jdc at ${ROOT_DIR}/jdc/bin/jdc"
[[ -f "${RADARR_DB}" ]] || die "Could not find ${RADARR_DB}"
[[ -f "${SONARR_DB}" ]] || die "Could not find ${SONARR_DB}"

cat <<'EOF'
=========================================================
 ARR DISK-FAILURE RESET SCRIPT (RADARR + SONARR)
=========================================================

This script can:
  1) Stop radarr and sonarr containers
  2) Create timestamped DB backups
  3) Mark all media files as missing in both apps
  4) Clear grab/import history in both apps
  5) Start containers again

Each step asks for confirmation with default No [y/N].
If you press Enter, the step is skipped.

EOF

warn "Run this only after replacing a failed media disk."
warn "SQL writes are destructive. Backups are strongly recommended."

print_counts

if confirm_step "Step 1/7: Stop radarr and sonarr containers?"; then
  (cd "${ROOT_DIR}" && ./jdc/bin/jdc down radarr sonarr)
else
  echo "Skipped stopping containers."
fi

if confirm_step "Step 2/7: Backup radarr.db to ${RADARR_BAK}?"; then
  cp "${RADARR_DB}" "${RADARR_BAK}"
  echo "Created ${RADARR_BAK}"
else
  echo "Skipped radarr backup."
fi

if confirm_step "Step 3/7: Backup sonarr.db to ${SONARR_BAK}?"; then
  cp "${SONARR_DB}" "${SONARR_BAK}"
  echo "Created ${SONARR_BAK}"
else
  echo "Skipped sonarr backup."
fi

if confirm_step "Step 4/7: Reset Radarr file state (set all movies to missing)?"; then
  assert_containers_stopped
  sqlite3 "${RADARR_DB}" <<'EOF'
BEGIN TRANSACTION;
DELETE FROM MovieFiles;
DELETE FROM MetadataFiles;
DELETE FROM SubtitleFiles;
DELETE FROM ExtraFiles;
UPDATE Movies SET MovieFileId = 0;
COMMIT;
EOF
  echo "Radarr file state reset completed."
else
  echo "Skipped Radarr file reset."
fi

if confirm_step "Step 5/7: Reset Sonarr file state (set all episodes to missing)?"; then
  assert_containers_stopped
  sqlite3 "${SONARR_DB}" <<'EOF'
BEGIN TRANSACTION;
DELETE FROM EpisodeFiles;
DELETE FROM MetadataFiles;
DELETE FROM SubtitleFiles;
DELETE FROM ExtraFiles;
UPDATE Episodes SET EpisodeFileId = 0;
COMMIT;
EOF
  echo "Sonarr file state reset completed."
else
  echo "Skipped Sonarr file reset."
fi

if confirm_step "Step 6/7: Clear Radarr + Sonarr history tables?"; then
  assert_containers_stopped
  sqlite3 "${RADARR_DB}" <<'EOF'
BEGIN TRANSACTION;
DELETE FROM History;
DELETE FROM DownloadHistory;
COMMIT;
EOF
  sqlite3 "${SONARR_DB}" <<'EOF'
BEGIN TRANSACTION;
DELETE FROM History;
DELETE FROM DownloadHistory;
COMMIT;
EOF
  echo "History tables cleared."
else
  echo "Skipped history cleanup."
fi

if confirm_step "Step 7/7: Start radarr and sonarr containers?"; then
  (cd "${ROOT_DIR}" && ./jdc/bin/jdc up radarr sonarr)
else
  echo "Skipped starting containers."
fi

print_counts

cat <<'EOF'
Next steps in UI:
  - Sonarr: Wanted -> Missing -> Search All
  - Radarr: Wanted -> Missing -> Search All

Note:
  - Unmonitored items are not searched automatically.
EOF
