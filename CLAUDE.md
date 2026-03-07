# CLAUDE.md - Homelab Onboarding

## What
This is a Docker-based homelab setup for managing self-hosted services (media, networking, utilities).
- **Stack**: Docker Compose, Bash.
- **Management**: Custom CLI tool `jdc` (wraps `docker compose`).
- **Structure**:
  - `apps/*.yaml`: Individual service definitions (imported by main `docker-compose.yaml`).
  - `appdata/`: Persistent storage for containers.
  - `jdc/`: Source for the management tool.
  - `secrets/`: Sensitive data files.

## How to Work
**Always use the `jdc` wrapper** instead of raw `docker compose` commands. It handles profiles and paths.

### Common Commands
- **Start/Update**: `./jdc/bin/jdc up [service_name] ` or `-p [profile]` (e.g., `core`, `media`).
- **Logs**: `./jdc/bin/jdc logs [service_name]`
- **Status**: `./jdc/bin/jdc ps`
- **List Services**: `./jdc/bin/jdc containers`
- **List Profiles**: `./jdc/bin/jdc profiles`

### Configuration
- Modify services in `apps/<service>.yaml`.
- Main orchestration is in `docker-compose.yaml` (defines networks, includes apps).
- Env vars are loaded from `.env` (ensure it exists if deploying).

### Development
- No formal test suite. Validation involves running `jdc config` or starting the service.
- If editing `jdc` script itself, test with shell commands.

