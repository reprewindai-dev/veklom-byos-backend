import subprocess

command = "python3 -c \"import re; filepath = '/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env'; content = open(filepath).read(); content = re.sub(r'GITHUB_CLIENT_ID=.*', 'GITHUB_CLIENT_ID=Iv23liPqr3V9FPknhwIn', content); content = re.sub(r'GITHUB_CLIENT_SECRET=.*', 'GITHUB_CLIENT_SECRET=\\'3f6e8c5433e3b0c1de5a8be350f466dd6ce2a808\\'', content); open(filepath, 'w').write(content); print('SUCCESS')\""

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
