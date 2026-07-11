import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { codeInspectorPlugin } from 'code-inspector-plugin';

const devHost = process.env.KNOWBASE_UI_DEV_HOST || "127.0.0.1";
const devPort = Number(process.env.KNOWBASE_UI_DEV_PORT || "5173");
const apiProxyTarget = process.env.KNOWBASE_API_PROXY_TARGET || "http://127.0.0.1:8000";

export default defineConfig({
  server: {
    host: devHost,
    port: devPort,
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
      "/ws": {
        target: apiProxyTarget,
        changeOrigin: true,
        ws: true,
      },
      "/health": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
  plugins: [
    codeInspectorPlugin({ 
      bundler: 'vite',
      editor: 'code',
      showSwitch: true,
      hotKeys: ["ctrlKey", "altKey"],
    }),
    react(),
  ],
});
