import { defineConfig } from "vite";
import preact from "@preact/preset-vite";
import { resolve } from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [preact()],
  build: {
    lib: {
      entry: resolve(__dirname, "src/index.tsx"),
      name: "PortfolioChatbot",
      fileName: "chatbot",
      formats: ["iife"],
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
        // Single-file output
        assetFileNames: "chatbot.[ext]",
      },
    },
    // Optimize for production
    minify: "terser",
    terserOptions: {
      compress: {
        drop_console: true,
      },
    },
  },
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
});
