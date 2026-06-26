import subprocess

command = "docker exec coolify-redis redis-cli -a sGIiZY2X4GYzwZXBlTcxauAAqmjnGmZhobHjjhbQjMc= config set stop-writes-on-bgsave-error no"

ssh_command = [
    "ssh",
    "-o", "StrictHostKeyChecking=no",
    "-i", "C:\\Users\\antho\\.ssh\\veklom-deploy",
    "root@5.78.135.11",
    command
]

result = subprocess.run(ssh_command, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
