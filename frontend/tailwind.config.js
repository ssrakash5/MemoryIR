/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a12",
        ink: "#f5f6fa",
        panel: "#13141f",
        panel2: "#191b29",
        line: "#262a3d",
        teal: "#6d5ef8",
        cobalt: "#6d5ef8",
        amber: "#f5b942",
        rose: "#f04a53",
        emerald: "#2fd480"
      }
    }
  },
  plugins: []
};
