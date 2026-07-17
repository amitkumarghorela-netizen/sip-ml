import type { Config } from "tailwindcss"
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#667eea", dark: "#764ba2" },
        bull:  "#16a34a",
        bear:  "#dc2626",
        side:  "#d97706",
        rec:   "#2563eb",
      },
    },
  },
  plugins: [],
}
export default config
