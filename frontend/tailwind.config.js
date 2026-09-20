/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx}",
    "./src/components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#064E3B",
        secondary: "#047857",
        accent: "#10B981",
        mint: "#ECFDF5",
        slate: "#F8FAFC",
        card: "#FFFFFF",
        text: "#0F172A",
        muted: "#64748B",
        border: "#E2E8F0",
        blue: "#2563EB",
        purple: "#7C3AED",
        orange: "#F59E0B",
        red: "#DC2626",
      },
      boxShadow: {
        soft: "0 10px 30px rgba(15, 23, 42, 0.08)",
      },
      borderRadius: {
        panel: "22px",
      },
    },
  },
  plugins: [],
};
