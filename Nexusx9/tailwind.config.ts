import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        nx: {
          bg:      '#04060f',
          panel:   '#070d1f',
          border:  '#0f1e3d',
          cyan:    '#00e5ff',
          blue:    '#4488ff',
          purple:  '#b44dff',
          magenta: '#ff00cc',
          gold:    '#ffcc00',
          orange:  '#ff6600',
          green:   '#00ff88',
          red:     '#ff2244',
          dim:     '#334466',
        },
      },
      fontFamily: {
        hud: ['Rajdhani', 'system-ui', 'sans-serif'],
        mono:['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow':  'pulse 3s ease-in-out infinite',
        'pulse-fast':  'pulse 0.8s ease-in-out infinite',
        'spin-slow':   'spin 8s linear infinite',
        'flicker':     'flicker 4s steps(1) infinite',
        'scan':        'scan 6s linear infinite',
      },
      keyframes: {
        flicker: {
          '0%,100%': { opacity: '1' },
          '43%':     { opacity: '0.9' },
          '44%':     { opacity: '0.4' },
          '45%':     { opacity: '1' },
        },
        scan: {
          '0%':   { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;