import subprocess

ssh_command = [
    "ssh",
    "-i", "C:\\Users\\antho\\.ssh\\veklom-deploy",
    "root@5.78.135.11",
    """
    cd /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru
    git pull origin main
    docker build -t veklom-local:latest .
    docker stop n13gp1nhrcdp0hvazvbnlxru-213557155694 || true
    docker rm n13gp1nhrcdp0hvazvbnlxru-213557155694 || true
    docker run -d \
      --name n13gp1nhrcdp0hvazvbnlxru-213557155694 \
      --network coolify \
      --env-file /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env \
      --restart unless-stopped \
      -p 8088:8088 \
      veklom-local:latest
    """
]

result = subprocess.run(ssh_command, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
