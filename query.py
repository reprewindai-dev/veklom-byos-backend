import subprocess
import json

def run_ssh(cmd):
    return subprocess.check_output(
        ['ssh', '-i', r'C:\Users\antho\.ssh\veklom-deploy', '-o', 'StrictHostKeyChecking=no', 'root@5.78.135.11', cmd]
    ).decode('utf-8')

# Get the studiogradekits user from barbankz
query = "SELECT row_to_json(users) FROM users WHERE email='studiogradekits@gmail.com';"
print("Extracting...")
out = run_ssh(f"echo \"{query}\" > /tmp/query.sql && docker exec -i myq30kt1h6wg0p8w3e9facxm psql -U barbankz -d barbankz -t < /tmp/query.sql")
print("Data:", out)

# Also delete test users from byos_ai
delete_query = "DELETE FROM users WHERE email LIKE '%example%' OR email LIKE '%test%' OR email LIKE '%smoke%' OR email LIKE '%mailnull%';"
print("Deleting fake users from byos_ai...")
del_out = run_ssh(f"echo \"{delete_query}\" > /tmp/del.sql && docker exec -i llwfyzhnft87bz6brddiax1z psql -U byos -d byos_ai < /tmp/del.sql")
print("Delete out:", del_out)
