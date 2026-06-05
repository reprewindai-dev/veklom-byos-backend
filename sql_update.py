import subprocess

sql = """
UPDATE vendors SET 
  stripe_account_id = '',
  onboarding_complete = false,
  status = 'pending'
WHERE user_id = '3f9a04b6-3630-457a-92a7-0243a4473aa9';
"""

process = subprocess.Popen(
    ['ssh', '-i', r'C:\Users\antho\.ssh\veklom-deploy', '-o', 'StrictHostKeyChecking=no', 'root@5.78.135.11', 'docker exec -i llwfyzhnft87bz6brddiax1z psql -U byos -d byos_ai -t'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)
out, err = process.communicate(input=sql.encode('utf-8'))
print("OUT:", out.decode('utf-8'))
if err:
    print("ERR:", err.decode('utf-8'))
