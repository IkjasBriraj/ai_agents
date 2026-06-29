/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ibm: {
          blue: "#0f62fe",
          dark: "#161616",
          gray: {
            10: "#f4f4f4",
            20: "#e0e0e0",
            80: "#393939",
            90: "#262626",
            100: "#161616",
          }
        }
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      }
    },
  },
  plugins: [],
}
