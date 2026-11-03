import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      colors: {
        canvas: "#f2f6f5",
        panel: "#ffffff",
        panelMuted: "#e8efed",
        borderSoft: "rgba(16,52,48,0.12)",
        ink: "#112f2c",
        muted: "#4c6260",
        success: "#1b7a4b",
        warning: "#9a5b07",
        danger: "#b0372b",
        info: "#0e7468",
        infoSoft: "#d9efeb",
        onAccent: "#ffffff",
      },
      boxShadow: {
        console: "0 1px 2px rgba(16,52,48,0.06), 0 8px 24px -12px rgba(16,52,48,0.12)",
      },
    },
  },
  plugins: [],
};

export default config;
