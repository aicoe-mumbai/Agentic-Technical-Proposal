import { defineConfig, Plugin } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// Custom plugin to handle SPA routing for /analyze/*.pdf paths
const spaFallbackForAnalyzePdf: Plugin = {
  name: 'spa-fallback-for-analyze-pdf',
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      if (req.url && req.url.startsWith('/analyze/') && req.url.includes('.pdf')) {
        req.url = '/index.html'; // Rewrite to root, react-router will handle the route
      }
      next();
    });
  },
};

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [
    react(),
    mode === 'development' &&
    componentTagger(),
    mode === 'development' && spaFallbackForAnalyzePdf,
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
