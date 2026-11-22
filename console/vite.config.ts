// Vite config for the read-only EdgeSense-130 console, exposing project results, tracking sessions, and paper comparisons under /repo.
import fs from "node:fs";
import path from "node:path";
import react from "@vitejs/plugin-react";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

function readOnlyRepoPlugin(repoRoot: string): Plugin {
  const allowed = [
    /^\/projects\/[a-z0-9_]+\/results\/[A-Za-z0-9_.\-/]+$/,
    /^\/projects\/[a-z0-9_]+\/[a-z0-9_/]+\.svg$/,
    /^\/tracking\/sessions\.csv$/,
    /^\/compare_with_papers\/published\.json$/,
  ];
  const contentType = (p: string) =>
    p.endsWith(".json")
      ? "application/json"
      : p.endsWith(".svg")
        ? "image/svg+xml"
        : p.endsWith(".raw")
          ? "application/octet-stream"
          : "text/plain; charset=utf-8";
  const serve = (req: import("node:http").IncomingMessage, res: import("node:http").ServerResponse, next: () => void) => {
    const reqUrl = req.url;
    if (!reqUrl || !reqUrl.startsWith("/repo/")) return next();
    if (req.method !== "GET" && req.method !== "HEAD") {
      res.statusCode = 405;
      res.end("read-only");
      return;
    }
    const rel = decodeURIComponent(reqUrl.slice("/repo".length).split("?")[0]);
    if (rel === "/manifest") {
      const manifest: Record<string, { raw: string[]; svg: string[] }> = {};
      const projDir = path.join(repoRoot, "projects");
      if (fs.existsSync(projDir)) {
        for (const name of fs.readdirSync(projDir)) {
          const resDir = path.join(projDir, name, "results");
          const raw = fs.existsSync(resDir) ? fs.readdirSync(resDir).filter((f) => f.endsWith(".raw")) : [];
          const svg = fs.existsSync(resDir) ? fs.readdirSync(resDir).filter((f) => f.endsWith(".svg")) : [];
          manifest[name] = { raw, svg };
        }
      }
      res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify(manifest));
      return;
    }
    if (!allowed.some((rx) => rx.test(rel)) || rel.includes("..")) {
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
    res.setHeader("Content-Type", contentType(target));
    fs.createReadStream(target).pipe(res);
  };
  return {
    name: "edgesense-readonly-repo",
    configureServer(server) {
      server.middlewares.use((req, res, next) => serve(req, res, next));
    },
    configurePreviewServer(server) {
      server.middlewares.use((req, res, next) => serve(req, res, next));
    },
  };
}

export default defineConfig({
  plugins: [react(), readOnlyRepoPlugin(path.resolve(__dirname, ".."))],
  server: { fs: { allow: [".."] } },
  test: { environment: "node" },
});
