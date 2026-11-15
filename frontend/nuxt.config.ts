export default defineNuxtConfig({
  devtools: { enabled: false },
  typescript: {
    strict: true,
    typeCheck: false,
  },
  ssr: true,
  css: ['~/assets/css/main.css'],
  nitro: {
    routeRules: {
      '/api/**': {
        proxy: `${process.env.BACKEND_URL || 'http://backend:8000'}/api/**`,
      },
    },
  },
  runtimeConfig: {
    public: {
      apiBase: '/api/v1',
    },
  },
})
