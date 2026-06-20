const runtimeDefaults = {
  NODE_ENV: "production",
  UACP_BOX_NAME: "uacp-vendor-network",
  UACP_RUNTIME_MODE: "vendor_network",
  UACP_WORKER_GROUP: "vendor_network",
  UACP_ARCHIVE_WRITE_REQUIRED: "true",
};

for (const [key, value] of Object.entries(runtimeDefaults)) {
  if (!process.env[key]) {
    process.env[key] = value;
  }
}

await import("../../server.ts");
