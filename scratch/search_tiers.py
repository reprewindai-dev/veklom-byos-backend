import re
import glob

files = glob.glob("frontend/static/control-plane-next/_next/static/chunks/*.js")
for f in files:
    content = open(f, "r", encoding="utf-8").read()
    if "founding" in content or "standard" in content or "regulated" in content or "starter" in content:
        print("MATCH:", f)
        # print some snippet
        for m in re.finditer(r"(.{0,100}(founding|standard|regulated|starter).{0,100})", content):
            print("  ->", m.group(0)[:200])
            break
