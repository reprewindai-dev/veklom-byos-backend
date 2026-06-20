const runtimeDefaults = {
  NODE_ENV: "production",
  UACP_BOX_NAME: "uacp-growth-sales",
  UACP_RUNTIME_MODE: "growth_sales",
  UACP_WORKER_GROUP: "growth_sales",
  UACP_ARCHIVE_WRITE_REQUIRED: "true",
};

for (const [key, value] of Object.entries(runtimeDefaults)) {
  if (!process.env[key]) {
    process.env[key] = value;
  }
}

await import("../../server.ts");
