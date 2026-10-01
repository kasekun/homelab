## What is homelab?

A fork of [juftin/homelab](https://github.com/juftin/homelab) with some additional features and improvements.

**`homelab`** is a collection of services that can be deployed from your home server and accessed
securely from anywhere in the world. Everything is deployed into a single docker compose application
and managed through the convenient `jdc` command-line tool.

### Quick Start

1. Clone this repository
2. Install [direnv](https://direnv.net/) and run `direnv allow` inside the repo to put `jdc` on PATH
3. Build the CLI and set up zsh completion (requires Go):

```bash
make install-jdc
```

Walk through the setup process (i need to populate this section fully, but in a nutshell)
1. Setup traefik, duckdns, cloudflare by following this guide https://www.simplehomelab.com/traefik-v3-docker-compose-guide-2024/
  - This guide is a little frustrating, but it works.

2. Copy `.env-example` to `.env` and fill in your details:

```bash
jdc script copy-env
```

3. !important: uncomment the `LETS_ENCRYPT_ENV` line so that failed letsencrypt attempts hit the staging servers and don't get you timed out.

4. Spin up the traefik related services, and monitor the traefik logs to ensure the certificates are being issued.

```bash
jdc docker up -p traefik
jdc docker logs -s traefik
```

5. Once the certificates are being issued correctly, you can comment out the `LETS_ENCRYPT_ENV` line again.

6. Spin up the rest of the services.

```bash
jdc docker up -p all
```

or target specific services

```bash
jdc docker up -s sonarr -s radarr -s prowlarr -s plex
```

7. Run through setup of these services following guides on those services easily found elsewhere.

Note: typically if you are referencing a service from inside another container (e.g., connecting prowlarr to sonarr), the host & port is simply something like
```
host: sonarr # or sometimes host: http://sonarr
port: 8989 # found in the sonarr.yaml file -> loadbalancer.server.port: 8989
```

### Service Profiles

Each service belongs to a [docker compose profile] that can be managed independently:

- **`core`**: Base infrastructure including [traefik] reverse proxy and [OAuth] service for secure HTTPS access
- **`media`**: Media services like [Plex], [Sonarr], [Radarr], and [Ombi] for streaming and content management
- **`utilities`**: Management tools like [Watchtower] and [Portainer] for monitoring and updates
- **`miscellaneous`**: Optional services like [ChatGPT Next Web] and [LibreOffice Online]

### Common Commands

```bash
# Build the CLI (first time and after updates)
make install-jdc

# Start all services
jdc docker up

# Start just core services
jdc docker up -p core

# View logs for a specific service
jdc docker logs -s sonarr

# Update all containers in a profile
jdc docker update -p all

# List available containers
jdc docker containers

# List available profiles
jdc docker profiles

# Validate your .env file
jdc script check-env

# Check disk space
jdc script check-space

# Show help
jdc --help
jdc docker --help
jdc script --help
```

[traefik]: https://github.com/traefik/traefik
[OAuth]: https://github.com/thomseddon/traefik-forward-auth
[Plex]: https://www.plex.tv/
[Sonarr]: https://github.com/sonarr/sonarr
[Radarr]: https://github.com/Radarr/Radarr
[Ombi]: https://github.com/Ombi-app/Ombi
[ChatGPT Next Web]: https://github.com/ChatGPTNextWeb/ChatGPT-Next-Web
[Watchtower]: https://github.com/containrrr/watchtower
[LibreOffice Online]: https://www.libreoffice.org/
[Portainer]: https://github.com/portainer/portainer
[docker compose profile]: https://docs.docker.com/compose/profiles/
