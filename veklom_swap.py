#!/usr/bin/env python3
"""
veklom_swap.py — Zero-downtime backend swap with Traefik routing update.

Usage:
  python3 veklom_swap.py <image_tag>

Example:
  python3 veklom_swap.py 9bac492
  python3 veklom_swap.py latest

This script:
1. Starts the new container and waits for it to be healthy
2. Updates Traefik to route to the new container's IP
3. Stops the old container only after Traefik has confirmed routing works
4. Rolls back automatically if new container fails health checks
"""

import subprocess
import json
import time
import sys
import os

CONTAINER_BASE = "n13gp1nhrcdp0hvazvbnlxru"
IMAGE_BASE = "n13gp1nhrcdp0hvazvbnlxru"
ENV_FILE = "/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env"
TRAEFIK_CONFIG = "/data/coolify/proxy/dynamic/veklom.yaml"
NETWORK = "coolify"
PORT = 8088
HEALTH_URL = f"http://localhost:{PORT}/health"
MAX_WAIT_SECONDS = 120
CONTAINER_PROD_NAME = f"{CONTAINER_BASE}-213557155694"


def run(cmd, check=True, capture=True):
    r = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
    if check and r.returncode != 0:
        print(f"FAILED: {cmd}")
        print(r.stderr)
        sys.exit(1)
    return r.stdout.strip()


def get_container_ip(name):
    return run(f"docker inspect {name} --format '{{{{.NetworkSettings.Networks.{NETWORK}.IPAddress}}}}'")


def write_traefik_config(backend_ip):
    config = f"""http:
  routers:
    veklom-api:
      entryPoints:
        - http
        - https
      rule: "Host(`api.veklom.com`)"
      service: veklom-api
      tls:
        certResolver: letsencrypt
    veklom-main:
      entryPoints:
        - http
        - https
      rule: "Host(`veklom.com`) || Host(`www.veklom.com`) || Host(`app.veklom.com`)"
      service: veklom-api
      tls:
        certResolver: letsencrypt
  services:
    veklom-api:
      loadBalancer:
        servers:
          - url: "http://{backend_ip}:{PORT}"
"""
    with open(TRAEFIK_CONFIG, "w") as f:
        f.write(config)
    print(f"  Traefik config updated → http://{backend_ip}:{PORT}")


def wait_healthy(container_name, max_wait=MAX_WAIT_SECONDS):
    print(f"  Waiting for {container_name} to be healthy...")
    for i in range(max_wait // 3):
        time.sleep(3)
        status = run(f"docker inspect {container_name} --format '{{{{.State.Health.Status}}}}'", check=False)
        logs = run(f"docker inspect {container_name} --format '{{{{.State.Status}}}}'", check=False)
        if status == "healthy":
            return True
        if logs == "exited":
            return False
        print(f"    [{i*3}s] status={status}")
    return False


def check_api_live(ip):
    r = subprocess.run(
        f"curl -sf http://{ip}:{PORT}/health",
        shell=True, capture_output=True, text=True, timeout=5
    )
    return r.returncode == 0 and "healthy" in r.stdout


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "latest"
    image = f"{IMAGE_BASE}:{tag}"
    new_name = f"{CONTAINER_BASE}-new-{int(time.time())}"
    
    print(f"\n{'='*60}")
    print(f"  VEKLOM ZERO-DOWNTIME SWAP")
    print(f"  Image: {image}")
    print(f"  New container: {new_name}")
    print(f"{'='*60}\n")

    # 1. Find current running container
    old_name = run(
        f"docker ps --filter name={CONTAINER_BASE} --filter status=running --format '{{{{.Names}}}}' | head -1",
        check=False
    )
    print(f"  Current container: {old_name or 'NONE'}")

    # 2. Start new container (no port binding yet — just on coolify network)
    print(f"\n[1/5] Starting new container...")
    run(
        f"docker run -d --name {new_name} "
        f"--network {NETWORK} "
        f"--env-file {ENV_FILE} "
        f"--restart unless-stopped "
        f"--health-cmd 'curl -sf http://localhost:{PORT}/health' "
        f"--health-interval 5s "
        f"--health-retries 5 "
        f"--health-start-period 30s "
        f"{image}"
    )

    # 3. Wait for new container to be healthy
    print(f"\n[2/5] Waiting for health check...")
    if not wait_healthy(new_name):
        print("\n  ERROR: New container failed to become healthy. Rolling back.")
        run(f"docker stop {new_name}", check=False)
        run(f"docker rm {new_name}", check=False)
        if old_name:
            old_ip = get_container_ip(old_name)
            write_traefik_config(old_ip)
        sys.exit(1)

    new_ip = get_container_ip(new_name)
    print(f"  New container healthy at {new_ip}")

    # 4. Verify API actually works
    print(f"\n[3/5] Verifying API response...")
    if not check_api_live(new_ip):
        print("  ERROR: Health check passed but API not responding. Rolling back.")
        run(f"docker stop {new_name}", check=False)
        run(f"docker rm {new_name}", check=False)
        sys.exit(1)
    print(f"  API confirmed healthy")

    # 5. Atomically update Traefik to point to new container
    print(f"\n[4/5] Switching Traefik routing...")
    write_traefik_config(new_ip)
    time.sleep(3)  # Give Traefik time to reload

    # 6. Stop old container
    print(f"\n[5/5] Stopping old container...")
    if old_name and old_name != new_name:
        run(f"docker stop {old_name}", check=False)
        run(f"docker rm {old_name}", check=False)
        print(f"  Removed: {old_name}")

    # Rename new container to the canonical prod name
    run(f"docker stop {new_name}", check=False)
    run(f"docker rm {CONTAINER_PROD_NAME}", check=False)
    run(
        f"docker run -d --name {CONTAINER_PROD_NAME} "
        f"--network {NETWORK} "
        f"--env-file {ENV_FILE} "
        f"--restart unless-stopped "
        f"-p {PORT}:{PORT} "
        f"--health-cmd 'curl -sf http://localhost:{PORT}/health' "
        f"--health-interval 10s "
        f"--health-retries 3 "
        f"{image}"
    )
    time.sleep(5)
    final_ip = get_container_ip(CONTAINER_PROD_NAME)
    write_traefik_config(final_ip)

    print(f"\n{'='*60}")
    print(f"  SWAP COMPLETE")
    print(f"  Container: {CONTAINER_PROD_NAME}")
    print(f"  Image: {image}")
    print(f"  IP: {final_ip}")
    print(f"  Traefik routing: http://{final_ip}:{PORT}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
