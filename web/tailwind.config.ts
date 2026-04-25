import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx,mdx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0B132B",
        paper: "#FAFAFC",
        muted: "#6C757D",
        // ROTI palette: cool → warm.
        roti: {
          50: "#E5F8FA",
          100: "#B5E9EE",
          300: "#5DC9D6",
          500: "#0FA3B1",
          700: "#0B7B86",
          accent: "#F7A072",
          warn: "#E63946",
        },
      },
      fontFamily: {
        display: ["'Inter Display'", "Inter", "system-ui", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
      },
      maxWidth: {
        prose: "65ch",
      },
      backgroundImage: {
        "grid-dark":
          "linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};

export default config;
