import subprocess

query = "\dt"

ssh_command = [
    "ssh",
    "-i", "C:\\Users\\antho\\.ssh\\veklom-deploy",
    "root@5.78.135.11",
    f"docker exec llwfyzhnft87bz6brddiax1z psql -U byos -d byos_ai -c \"{query}\""
]

result = subprocess.run(ssh_command, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
