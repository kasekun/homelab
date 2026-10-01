# CLAUDE.md - Homelab Onboarding

## What
This is a Docker-based homelab setup for managing self-hosted services (media, networking, utilities).
- **Stack**: Docker Compose, Go, Bash.
- **Management**: Custom CLI tool `jdc` (Go binary, wraps `docker compose`). Source in `homelab-cli/`.
- **Structure**:
  - `apps/*.yaml`: Individual service definitions (imported by main `docker-compose.yaml`).
  - `appdata/`: Persistent storage for containers.
  - `homelab-cli/`: Go source for the `jdc` CLI (compiled binary at `homelab-cli/jdc`).
  - `jdc/scripts/`: Shell scripts invoked by `jdc script` subcommands (UFW, traefik, etc.).
  - `scripts/`: Additional maintenance scripts (backup, vpn check, create-databases).
  - `secrets/`: Sensitive data files.

## How to Work
**Always use the `jdc` wrapper** instead of raw `docker compose` commands. It handles profiles and paths.

### Install / Build
```bash
make install-jdc   # build binary, refresh cache, set up zsh completion
```
Requires Go. The binary is written to `homelab-cli/jdc` and put on PATH via direnv (`direnv allow`).

### Common Commands
- **Start/Update**: `jdc docker up [-s service...] [-p profile]`
- **Logs**: `jdc docker logs -s sonarr`
- **Status**: `jdc docker ps`
- **List Services**: `jdc docker containers`
- **List Profiles**: `jdc docker profiles`
- **Update services**: `jdc docker update -p core`
- **Stop**: `jdc docker stop -s sonarr`
- **Remove**: `jdc docker remove -s sonarr`
- **Full teardown**: `jdc docker down`

### Script Commands
- **Check env**: `jdc script check-env`
- **Check disk**: `jdc script check-space`
- **Copy env**: `jdc script copy-env [-y]`
- **Init homelab**: `jdc script init-homelab -y`
- **UFW setup**: `jdc script ufw-setup -y`
- **Traefik ACME**: `jdc script traefik-acme -y`

### Configuration
- Modify services in `apps/<service>.yaml`.
- Main orchestration is in `docker-compose.yaml` (defines networks, includes apps).
- Env vars are loaded from `.env` (ensure it exists if deploying).

### Development
- No formal test suite. Validation involves running `jdc docker config` or starting the service.
- If editing Go source in `homelab-cli/`, rebuild with `make -C homelab-cli build` then `jdc self refresh`.
- Tab completion reads from `.jdc-cache.json` (repo root, gitignored). Refresh with `jdc self refresh`.
