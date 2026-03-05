/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: '#1A1A2E',
          navy: '#16213E',
          blue: '#0F3460',
          red: '#E94560',
        }
      }
    },
  },
  plugins: [],
}
