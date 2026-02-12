/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          pink: '#F5C6C6',
          'pink-light': '#FDE8E8',
          'pink-dark': '#E8A0A0',
          gold: '#C9A96E',
          'gold-light': '#E8D5A8',
          'gold-dark': '#A88B4A',
          cream: '#FFF9F5',
          charcoal: '#2D2D2D',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Playfair Display', 'serif'],
      },
    },
  },
  plugins: [],
}
