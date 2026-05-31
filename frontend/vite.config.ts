import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "node:path";

// Veklom Workspace — frontend lives inside veklom-byos-backend.
// - Source in /src, build output → /static/workspace (mounted by FastAPI as /workspace).
// - `@/...` resolves to /src for clean imports.
// - Base is "./" so the same build serves under any prefix.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  base: process.env.VITE_BASE ?? "./",
  build: {
    outDir: "./static/workspace",
    emptyOutDir: true,
    assetsDir: "assets",
    target: "es2022",
    sourcemap: false,
    chunkSizeWarningLimit: 900,
  },
  server: {
    host: true,
    port: 5173,
    strictPort: false,
    proxy: {
      // Proxy /api/* during dev so the frontend talks to the local FastAPI
      // backend without CORS noise. Set VITE_VEKLOM_API_BASE to override.
      "/api": {
        target: process.env.VITE_DEV_BACKEND ?? "http://localhost:8000",
        changeOrigin: true,
      },
      "/health": { target: process.env.VITE_DEV_BACKEND ?? "http://localhost:8000", changeOrigin: true },
    },
  },
});
