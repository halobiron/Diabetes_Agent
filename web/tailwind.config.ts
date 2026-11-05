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
        canvas: "#f2f5fb",
        panel: "#ffffff",
        panelMuted: "#e7e9f5",
        borderSoft: "rgba(40,30,110,0.12)",
        ink: "#1c1a3a",
        muted: "#55527a",
        success: "#1b7a4b",
        warning: "#9a5b07",
        danger: "#b0372b",
        info: "#4b3fa8",
        infoSoft: "#e7e4f8",
        onAccent: "#ffffff",
      },
      boxShadow: {
        console: "0 1px 2px rgba(40,30,110,0.06), 0 8px 24px -12px rgba(40,30,110,0.12)",
      },
    },
  },
  plugins: [],
};

export default config;
