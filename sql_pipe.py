import subprocess

sql = """
DO $$
DECLARE
    existing_ws_id VARCHAR;
BEGIN
    SELECT id INTO existing_ws_id FROM workspaces LIMIT 1;

    INSERT INTO users (id, email, hashed_password, full_name, role, status, workspace_id)
    VALUES (
        '9a4ad4be-ca03-470a-adc6-56b63fee7261',
        'studiogradekits@gmail.com',
        'scrypt:38df9074f0b69763ae480d81e0fd8692:d97d290a6cadbbabdf5374257c7caf0d015bf760497f446744cd42df89e0962f22d81336df1fdf56c198f2834fcb98ee798c796e19f98dda2514a0963a6d3064',
        'BigCappo',
        'USER',
        'ACTIVE',
        existing_ws_id
    ) ON CONFLICT (email) DO NOTHING;
END $$;
"""

process = subprocess.Popen(
    ['ssh', '-i', r'C:\Users\antho\.ssh\veklom-deploy', '-o', 'StrictHostKeyChecking=no', 'root@5.78.135.11', 'docker exec -i llwfyzhnft87bz6brddiax1z psql -U byos -d byos_ai'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)
out, err = process.communicate(input=sql.encode('utf-8'))
print("OUT:", out.decode('utf-8'))
print("ERR:", err.decode('utf-8'))
