import os

PLAYBOOKUX_SNIPPET = '''
<!-- PlaybookUX -->
<script>
  (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
  new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
  j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
  'https://cdn.playbookux.com/snippet/REPLACE_ME_PLAYBOOKUX_KEY'+dl;f.parentNode.insertBefore(j,f);
  })(window,document,'script','dataLayer','REPLACE_ME_PLAYBOOKUX_KEY');
</script>
'''

TERMLY_SNIPPET = '''
<!-- Termly Compliance Badge -->
<script
  type="text/javascript"
  src="https://app.termly.io/resource-blocker/REPLACE_ME_TERMLY_ID"
></script>
'''

def inject_head(path, snippet):
    if not os.path.exists(path):
        print(f"Skipping {path}, not found.")
        return
        
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if "REPLACE_ME_PLAYBOOKUX_KEY" in content:
        print(f"Skipping {path}, PlaybookUX already injected.")
        return
        
    content = content.replace("</head>", snippet + "</head>")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Injected PlaybookUX into {path}")

def inject_body(path, snippet):
    if not os.path.exists(path):
        print(f"Skipping {path}, not found.")
        return
        
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if "REPLACE_ME_TERMLY_ID" in content:
        print(f"Skipping {path}, Termly already injected.")
        return
        
    content = content.replace("</body>", snippet + "</body>")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Injected Termly into {path}")

# Run injections
inject_head('C:/Users/antho/.windsurf/veklom-byos-backend/frontend/landing/index.html', PLAYBOOKUX_SNIPPET)
inject_head('C:/Users/antho/.windsurf/veklom-byos-backend/frontend/static/auth.html', PLAYBOOKUX_SNIPPET)
inject_head('C:/Users/antho/.windsurf/veklom-byos-backend/frontend/static/workspace/index.html', PLAYBOOKUX_SNIPPET)

inject_body('C:/Users/antho/.windsurf/veklom-byos-backend/frontend/landing/index.html', TERMLY_SNIPPET)
