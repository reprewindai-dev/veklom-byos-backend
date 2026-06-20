const runtimeDefaults = {
  NODE_ENV: "production",
  UACP_BOX_NAME: "uacp-operations-intake",
  UACP_RUNTIME_MODE: "operations_intake",
  UACP_WORKER_GROUP: "operations_intake",
  UACP_ARCHIVE_WRITE_REQUIRED: "true",
};

for (const [key, value] of Object.entries(runtimeDefaults)) {
  if (!process.env[key]) {
    process.env[key] = value;
  }
}

await import("../../server.ts");
