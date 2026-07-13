import os

config = """http:
  routers:
    veklom:
      entryPoints:
        - http
        - https
      rule: "Host(`veklom.com`) || Host(`www.veklom.com`) || Host(`api.veklom.com`)"
      service: veklom
      tls:
        certResolver: letsencrypt
  services:
    veklom:
      loadBalancer:
        servers:
          - url: "http://n13gp1nhrcdp0hvazvbnlxru-213557155694:80"
"""
with open("/data/coolify/proxy/dynamic/veklom.yaml", "w") as f:
    f.write(config)
print("Config written successfully.")
