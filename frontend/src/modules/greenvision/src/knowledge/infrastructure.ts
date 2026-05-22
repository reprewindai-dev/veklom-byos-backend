export const INFRASTRUCTURE_MAP = {
  veklom: {
    ip: "5.78.135.11",
    name: "veklom-prod-1",
    ssh: "ssh -F NUL -i ~/.ssh/veklom-deploy root@5.78.135.11",
    coolify: {
      app: "veklom-api",
      project: "veklom",
      dashboard: "http://5.78.135.11:8000"
    },
    services: ["Postgres", "Redis", "Ollama (veklom-ollama / qwen2.5:0.5b)"]
  },
  co2router: {
    ip: "5.78.153.146",
    name: "co2routerengine-prod-1",
    ssh: "ssh -F NUL -i ~/.ssh/veklom-deploy root@5.78.153.146",
    coolify: {
      app: "ecobe-engine",
      project: "ecobe",
      dashboard: "http://5.78.153.146:8000"
    },
    services: ["Postgres", "Redis"]
  },
  network: {
    frontend: "veklom.com",
    api: "api.veklom.com",
    engine: "engine.veklom.com",
    marketplace: "veklom.dev"
  }
};
