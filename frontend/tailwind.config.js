/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Sora", "sans-serif"],
        body: ["Plus Jakarta Sans", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      colors: {
        surface: {
          DEFAULT: "rgb(var(--surface-rgb) / <alpha-value>)",
          elevated: "rgb(var(--surface-elevated-rgb) / <alpha-value>)",
          card: "rgb(var(--surface-card-rgb) / <alpha-value>)",
        },
        accent: {
          cyan: "rgb(var(--accent-cyan-rgb) / <alpha-value>)",
          blue: "rgb(var(--accent-blue-rgb) / <alpha-value>)",
          violet: "rgb(var(--accent-violet-rgb) / <alpha-value>)",
          emerald: "rgb(var(--accent-emerald-rgb) / <alpha-value>)",
          rose: "rgb(var(--accent-rose-rgb) / <alpha-value>)",
          amber: "rgb(var(--accent-amber-rgb) / <alpha-value>)",
        },
        fintech: {
          border: "rgb(var(--fintech-border-rgb) / <alpha-value>)",
          glow: "rgb(var(--fintech-glow-rgb) / <alpha-value>)",
        },
        theme: {
          DEFAULT: "rgb(var(--text-primary-rgb) / <alpha-value>)",
          muted: "rgb(var(--text-muted-rgb) / <alpha-value>)",
          inverse: "rgb(var(--text-inverse-rgb) / <alpha-value>)",
          bg: {
            DEFAULT: "rgb(var(--bg-primary-rgb) / <alpha-value>)",
            muted: "rgb(var(--bg-secondary-rgb) / <alpha-value>)",
          },
          border: "rgb(var(--border-base-rgb) / <alpha-value>)",
        },
      },
      animation: {
        "fade-in": "fadeIn 0.5s ease-out forwards",
        "slide-up": "slideUp 0.5s ease-out forwards",
        "pulse-glow": "pulseGlow 2s ease-in-out infinite",
        "shimmer": "shimmer 2s linear infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 20px rgba(59, 130, 246, 0.15)" },
          "50%": { boxShadow: "0 0 40px rgba(59, 130, 246, 0.3)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      backgroundImage: {
        "grid-pattern":
          "linear-gradient(to right, rgba(148,163,184,0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(148,163,184,0.05) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};
