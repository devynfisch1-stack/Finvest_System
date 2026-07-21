import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vercel deployt von der Repo-Root aus -> kein spezieller "base"-Pfad nötig
// (anders als bei GitHub Pages, wo man /<Repo-Name>/ bräuchte).
export default defineConfig({
  plugins: [react()],
  root: __dirname,
});
