import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Veklom palette — sovereign / control-plane vibe
        bg: {
          900: "#070A12",
          800: "#0B0F1A",
          700: "#111726",
          600: "#1A2236",
        },
        ink: {
          50: "#F5F7FB",
          200: "#C7CEDC",
          400: "#8892AB",
          600: "#5A6480",
        },
        brand: {
          400: "#ffc425",
          500: "#ffb800",
          600: "#e69d00",
          700: "#b37a00",
        },
        accent: {
          green: "#3EE7A2",
          amber: "#FFB547",
          red: "#FF5C7A",
          violet: "#A78BFA",
        },
        border: {
          DEFAULT: "#1F2A40",
          strong: "#2A3A5C",
        },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Inter", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        card: "0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 24px -8px rgba(0,0,0,0.6)",
      },
    },
  },
  plugins: [],
};
export default config;
