import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "favicon.ico"],
      manifest: {
        name: "Wealth VN - Quản lý tài sản",
        short_name: "Wealth VN",
        description: "Phần mềm quản lý tài sản đầu tư tại Việt Nam",
        // Matches the default "clean-slate" theme primary color (#3B82F6)
        // and the favicon gradient start color.
        theme_color: "#3B82F6",
        background_color: "#0f172a",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png", purpose: "any" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png", purpose: "any" },
          { src: "pwa-maskable-512x512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
          { src: "apple-touch-icon.png", sizes: "180x180", type: "image/png", purpose: "any" },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        // SPA: mọi route không khớp tài nguyên tĩnh đều fallback về index.html
        navigateFallback: "index.html",
        // Không cache các lời gọi API qua service worker
        navigateFallbackDenylist: [/^\/api\//],
        // Kiểm soát cập nhật service worker: đợi kích hoạt thủ công
        skipWaiting: false,
        clientsClaim: true,
        runtimeCaching: [
          {
            // API GET: ưu tiên mạng, timeout 5s, cache 30 entry / 5 phút
            urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
            handler: "NetworkFirst",
            method: "GET",
            options: {
              cacheName: "api-cache",
              networkTimeoutSeconds: 5,
              expiration: {
                maxEntries: 30,
                maxAgeSeconds: 5 * 60,
              },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Tài nguyên tĩnh (JS/CSS/fonts): StaleWhileRevalidate
            urlPattern: ({ request }) =>
              request.destination === "script" ||
              request.destination === "style" ||
              request.destination === "font",
            handler: "StaleWhileRevalidate",
            options: {
              cacheName: "assets-cache",
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Hình ảnh: CacheFirst, 60 entry / 30 ngày
            urlPattern: ({ request }) => request.destination === "image",
            handler: "CacheFirst",
            options: {
              cacheName: "image-cache",
              expiration: {
                maxEntries: 60,
                maxAgeSeconds: 30 * 24 * 60 * 60,
              },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
    }),
  ],
  server: {
    host: "0.0.0.0",
    port: 5173,
    allowedHosts: true,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});

// Biểu tượng PWA (pwa-192x192.png, pwa-512x512.png, pwa-maskable-512x512.png,
// apple-touch-icon.png) được tạo bằng `npm run gen-icons` từ favicon.svg.
