import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { fileURLToPath, URL } from "node:url";

const resolve = (p) => fileURLToPath(new URL(p, import.meta.url));

// Compiles the Svelte Flow graph into a single self-mounting JS + CSS bundle
// under docs/funding-flow/, which zensical passes through to the built site.
export default defineConfig({
  plugins: [svelte()],
  build: {
    outDir: resolve("../docs/funding-flow"),
    emptyOutDir: true,
    cssCodeSplit: false,
    lib: {
      entry: resolve("src/main.js"),
      name: "FundingFlow",
      formats: ["iife"],
      fileName: () => "funding-flow.js",
    },
    rollupOptions: {
      output: { assetFileNames: "funding-flow.[ext]" },
    },
  },
});
