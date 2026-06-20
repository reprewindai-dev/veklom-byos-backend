const runtimeDefaults = {
  NODE_ENV: "production",
  UACP_BOX_NAME: "uacp-builder-systems",
  UACP_RUNTIME_MODE: "builder_systems",
  UACP_WORKER_GROUP: "builder_systems",
  UACP_ARCHIVE_WRITE_REQUIRED: "true",
};

for (const [key, value] of Object.entries(runtimeDefaults)) {
  if (!process.env[key]) {
    process.env[key] = value;
  }
}

await import("../../server.ts");
