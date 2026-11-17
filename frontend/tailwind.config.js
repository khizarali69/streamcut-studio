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
        studio: {
          bg: '#0D0F12',
          surface: '#15181E',
          card: '#1A1E26',
          border: '#272E3B',
          accent: '#6366F1', // indigo/violet
          accentHover: '#4F46E5',
          text: '#F3F4F6',
          muted: '#9CA3AF'
        }
      }
    },
  },
  plugins: [],
}
