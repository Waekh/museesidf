/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        cream: "#FAFAF8",
        ink: "#1C1C1C",
        ocre: "#C4973A",
        "ocre-dark": "#A67C2A",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ['"Playfair Display"', "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};
