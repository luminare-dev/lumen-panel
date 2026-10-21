// Unit tests of the command palette: Vitest with jsdom and Testing Library.
// One worker, no file parallelism: the suite is small, and this keeps its memory use low enough
// for a small server (see docs/install.md, "Requirements").
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  root: fileURLToPath(new URL("..", import.meta.url)),
  plugins: [react()],
  test: {
    environment: "jsdom",
    include: ["island/test/**/*.test.{ts,tsx}"],
    pool: "forks",
    maxWorkers: 1,
    fileParallelism: false,
    restoreMocks: true,
    unstubGlobals: true,
  },
});
