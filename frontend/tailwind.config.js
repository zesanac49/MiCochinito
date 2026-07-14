/** Sistema de diseño neomórfico (doc 06 §3). Tokens de color, sombras y radios. */
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#E8ECF1',
        'surface-raised': '#EDF1F6',
        'text-primary': '#1F2430',
        'text-secondary': '#5A6478',
        accent: '#047857',
        'accent-soft': '#D1E7DF',
        danger: '#B4232C',
        warning: '#B45309',
      },
      boxShadow: {
        nm: '9px 9px 18px rgba(163,177,198,.55), -9px -9px 18px rgba(255,255,255,.9)',
        'nm-sm': '5px 5px 10px rgba(163,177,198,.5), -5px -5px 10px rgba(255,255,255,.85)',
        'nm-in': 'inset 6px 6px 12px rgba(163,177,198,.55), inset -6px -6px 12px rgba(255,255,255,.9)',
        'nm-well': 'inset 2px 2px 5px rgba(163,177,198,.35), inset -2px -2px 5px rgba(255,255,255,.7)',
      },
      borderRadius: { nm: '1.25rem', 'nm-sm': '0.875rem' },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      transitionDuration: { nm: '140ms' },
    },
  },
  plugins: [],
}
