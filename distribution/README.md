# Release distribution

This directory defines the complete platform runtime. It pulls immutable application images from GitHub Container Registry and binds dashboards to loopback; Cloudflare Tunnel is the intended public ingress.

```bash
cp distribution/.env.example distribution/.env
# Replace every placeholder and use commit-SHA image tags.
scripts/proxmox/deploy.sh --check-only
scripts/proxmox/deploy.sh
```

Do not commit `distribution/.env`. See [the Proxmox deployment runbook](../docs/PROXMOX_DEPLOYMENT.md) for VM preparation, secure publication, backups, and updates.
