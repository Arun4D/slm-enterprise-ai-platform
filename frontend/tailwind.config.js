export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#111827',
        panel: '#1f2937',
        accent: '#22c55e'
      },
      boxShadow: {
        soft: '0 12px 40px rgba(15,23,42,0.15)'
      }
    }
  },
  plugins: []
};
