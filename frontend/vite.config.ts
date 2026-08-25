import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "prompt",
      includeAssets: ["apple-touch-icon.png", "favicon.png"],
      manifest: {
        name: "Health & Fitness",
        short_name: "H&F",
        description:
          "Tu plan personalizado de peso y ejercicio, supervisado por tu entrenador.",
        lang: "es",
        start_url: "/",
        scope: "/",
        display: "standalone",
        background_color: "#F4F6F3",
        theme_color: "#F4F6F3",
        icons: [
          { src: "/pwa-192.png", sizes: "192x192", type: "image/png" },
          { src: "/pwa-512.png", sizes: "512x512", type: "image/png" },
          { src: "/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,png,svg,woff2}"],
        // The API and Django admin must never be intercepted or cached.
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//, /^\/admin/, /^\/static\//, /^\/healthz/],
      },
    }),
  ],
  define: {
    __BUILD_DATE__: JSON.stringify(new Date().toISOString().slice(0, 10)),
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  preview: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
