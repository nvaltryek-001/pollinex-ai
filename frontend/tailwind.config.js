/** @type {import('tailwindcss').Config} */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["class"],
  theme: {
    extend: {
      colors: {
        paper: v("paper"),
        surface: v("surface"),
        raised: v("raised"),
        ink: v("ink"),
        muted: v("muted"),
        line: v("line"),
        leaf: v("leaf"),
        pollen: v("pollen"),
        petal: v("petal"),
        alert: v("alert"),
        sky: v("sky"),
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: { card: "0 1px 0 rgb(var(--line) / 1), 0 8px 24px -16px rgb(0 0 0 / 0.25)" },
      keyframes: { rise: { from: { opacity: 0, transform: "translateY(6px)" }, to: { opacity: 1, transform: "none" } } },
      animation: { rise: "rise .35s ease-out both" },
    },
  },
  plugins: [],
};
