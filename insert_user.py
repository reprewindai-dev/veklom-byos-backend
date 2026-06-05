import subprocess
import json

def run_ssh_with_input(cmd, stdin_data):
    process = subprocess.Popen(
        ['ssh', '-i', r'C:\Users\antho\.ssh\veklom-deploy', '-o', 'StrictHostKeyChecking=no', 'root@5.78.135.11', cmd],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    out, err = process.communicate(input=stdin_data.encode('utf-8'))
    return out.decode('utf-8') + err.decode('utf-8')

user_data = {
    "id": "9a4ad4be-ca03-470a-adc6-56b63fee7261",
    "email": "studiogradekits@gmail.com",
    "password_hash": "scrypt:38df9074f0b69763ae480d81e0fd8692:d97d290a6cadbbabdf5374257c7caf0d015bf760497f446744cd42df89e0962f22d81336df1fdf56c198f2834fcb98ee798c796e19f98dda2514a0963a6d3064",
    "display_name": "BigCappo",
    "role": "artist",
    "plan": "beta",
    "access_status": "active",
    "moderation_status": "good_standing",
    "terms_accepted_at": "2026-05-28T10:05:47.951",
    "acceptable_use_accepted_at": "2026-05-28T10:05:47.951",
    "privacy_accepted_at": "2026-05-28T10:05:47.951",
    "last_known_ip": "142.114.104.212",
    "created_at": "2026-05-28T10:05:47.952313",
    "updated_at": "2026-05-28T16:14:02.141"
}

remote_py = f"""
import asyncio
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://byos:WZk0WzseaPma1_KsJ53Nr7OgMUhnk9EV@llwfyzhnft87bz6brddiax1z:5432/byos_ai')
with engine.begin() as conn:
    conn.execute(text(\"\"\"
    INSERT INTO users (id, email, password_hash, display_name, role, status, terms_accepted_at, acceptable_use_accepted_at, privacy_accepted_at, created_at, updated_at)
    VALUES (
        '{user_data['id']}',
        '{user_data['email']}',
        '{user_data['password_hash']}',
        '{user_data['display_name']}',
        'vendor',
        'active',
        '{user_data['terms_accepted_at']}',
        '{user_data['acceptable_use_accepted_at']}',
        '{user_data['privacy_accepted_at']}',
        '{user_data['created_at']}',
        '{user_data['updated_at']}'
    ) ON CONFLICT (email) DO NOTHING;
    \"\"\"))
    print("User inserted!")
"""

print("Running...")
out = run_ssh_with_input("cat > /tmp/insert.py && docker exec -i n13gp1nhrcdp0hvazvbnlxru-213557155694 python /tmp/insert.py", remote_py)
print("Done:", out)
