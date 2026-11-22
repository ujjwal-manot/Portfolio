// Vite config for the read-only EdgeSense-130 console, serving project results files under /repo without write access.
import fs from "node:fs";
import path from "node:path";
import react from "@vitejs/plugin-react";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

function readOnlyRepoPlugin(repoRoot: string): Plugin {
  const allowed = /^\/projects\/[a-z0-9_]+\/results\/[A-Za-z0-9_.\-/]+$/;
  const serve = (reqUrl: string | undefined, res: import("node:http").ServerResponse, next: () => void) => {
    if (!reqUrl || !reqUrl.startsWith("/repo/")) return next();
    const rel = decodeURIComponent(reqUrl.slice("/repo".length).split("?")[0]);
    if (!allowed.test(rel) || rel.includes("..")) {
      res.statusCode = 403;
      res.end("forbidden");
      return;
    }
    const target = path.resolve(repoRoot, rel.slice(1));
    if (!target.startsWith(repoRoot) || !fs.existsSync(target) || !fs.statSync(target).isFile()) {
      res.statusCode = 404;
      res.end("not found");
      return;
    }
    res.setHeader("Content-Type", target.endsWith(".json") ? "application/json" : "text/plain; charset=utf-8");
    fs.createReadStream(target).pipe(res);
  };
  return {
    name: "edgesense-readonly-repo",
    configureServer(server) {
      server.middlewares.use((req, res, next) => serve(req.url, res, next));
    },
    configurePreviewServer(server) {
      server.middlewares.use((req, res, next) => serve(req.url, res, next));
    },
  };
}

export default defineConfig({
  plugins: [react(), readOnlyRepoPlugin(path.resolve(__dirname, ".."))],
  server: { fs: { allow: [".."] } },
  test: { environment: "node" },
});
