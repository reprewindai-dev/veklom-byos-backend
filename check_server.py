import subprocess

def run_ssh(command):
    ssh_command = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-i", "C:\\Users\\antho\\.ssh\\veklom-deploy",
        "root@5.78.135.11",
        command
    ]
    result = subprocess.run(ssh_command, capture_output=True, text=True)
    return result.stdout, result.stderr

print("Checking disk space...")
stdout, stderr = run_ssh("df -h")
print("STDOUT:\n", stdout)
print("STDERR:\n", stderr)

print("\nChecking docker containers...")
stdout, stderr = run_ssh("docker ps")
print("STDOUT:\n", stdout)
print("STDERR:\n", stderr)

print("\nChecking Coolify logs (last 50 lines)...")
stdout, stderr = run_ssh("docker logs --tail 50 coolify")
print("STDOUT:\n", stdout)
print("STDERR:\n", stderr)
