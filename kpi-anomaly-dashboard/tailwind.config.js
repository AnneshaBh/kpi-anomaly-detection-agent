module.exports = {
  content: ['./src/**/*.{js,jsx}', './index.html'],
  theme: {
    extend: {
      colors: {
        high:    '#C00000',
        medium:  '#E8A000',
        low:     '#107C41',
        grey:    '#767676',
        risk:    '#C00000',
        upside:  '#107C41',
        pbi:     '#0078D4',
        surface: '#FFFFFF',
        page:    '#F3F2F1',
        border:  '#E0E0E0',
        ink:     '#252423',
        muted:   '#605E5C',
      },
      fontFamily: {
        sans: ['Segoe UI', 'system-ui', 'sans-serif'],
      },
    },
  },
}
