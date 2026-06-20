const runtimeDefaults = {
  NODE_ENV: "production",
  UACP_BOX_NAME: "uacp-pillar-council",
  UACP_RUNTIME_MODE: "pillar_council",
  UACP_WORKER_GROUP: "pillar_council",
  UACP_ARCHIVE_WRITE_REQUIRED: "true",
};

for (const [key, value] of Object.entries(runtimeDefaults)) {
  if (!process.env[key]) {
    process.env[key] = value;
  }
}

await import("../../server.ts");
