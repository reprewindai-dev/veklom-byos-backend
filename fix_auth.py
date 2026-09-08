import re

with open('backend/apps/api/routers/auth.py', 'r', encoding='utf-8') as f:
    text = f.read()

pattern = r'return f\"\"\"<!doctype html>.*?</script>\n</body>\n</html>\"\"\"'

def replacer(m):
    s = m.group(0)
    s = s.replace('return f\"\"\"<!doctype html>', 'return \"\"\"<!doctype html>')
    s = s.replace('{{', '{').replace('}}', '}')
    s = s.replace('</html>\"\"\"', '</html>\"\"\".replace(\"{encoded}\", encoded)')
    return s

new_text = re.sub(pattern, replacer, text, flags=re.DOTALL)

with open('backend/apps/api/routers/auth.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print('Replaced!')
