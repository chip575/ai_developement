import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_BACKEND_URL || 'http://127.0.0.1:8765'
  return {
    plugins: [vue()],
    server: {
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
          configure(proxy) {
            // FastAPI checks Origin on POST; the local development proxy is same-origin to it.
            proxy.on('proxyReq', (proxyReq, request) => {
              if (request.headers.origin) proxyReq.setHeader('Origin', new URL(target).origin)
            })
          },
        },
      },
    },
    test: { environment: 'jsdom', restoreMocks: true },
  }
})
