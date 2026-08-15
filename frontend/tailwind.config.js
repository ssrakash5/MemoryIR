/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        panel: "#f8fafc",
        line: "#cbd5e1",
        teal: "#0f766e",
        cobalt: "#1d4ed8",
        amber: "#b45309",
        rose: "#be123c"
      }
    }
  },
  plugins: []
};
