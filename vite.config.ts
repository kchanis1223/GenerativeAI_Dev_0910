import { defineConfig, loadEnv, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'

// Development only: credentials stay in the Vite process, never in client code.
export function centerApiProxy(appKey: string, request: typeof fetch = fetch): Plugin {
  return {
    name: 'tms-center-api',
    configureServer(server) {
      server.middlewares.use('/api/tms/centerList', async (req, res) => {
        res.setHeader('Content-Type', 'application/json; charset=utf-8')
        res.setHeader('Cache-Control', 'no-store')
        const fail = (status: number, code: string) => {
          res.statusCode = status
          res.end(JSON.stringify({ code }))
        }
        if (req.url !== '/' && req.url !== '') return fail(404, 'NOT_FOUND')
        if (req.method !== 'GET') {
          res.setHeader('Allow', 'GET')
          return fail(405, 'METHOD_NOT_ALLOWED')
        }
        // Reject cross-origin requests before attaching the server credential.
        if (
          (req.headers.origin && req.headers.origin !== `http://${req.headers.host}`) ||
          req.headers['sec-fetch-site'] === 'cross-site'
        )
          return fail(403, 'FORBIDDEN')
        if (!appKey) return fail(503, 'TMS_KEY_MISSING')
        try {
          // B-02 verified query authentication; never log this upstream URL.
          const upstream = new URL('https://apis.openapi.sk.com/tms/centerList')
          upstream.searchParams.set('appKey', appKey)
          const response = await request(upstream.toString(), {
            headers: { Accept: 'application/json' },
            signal: AbortSignal.timeout(7000),
            redirect: 'error',
          })
          if (!response.ok)
            return fail(
              response.status === 401 || response.status === 403 ? 401 : 502,
              'TMS_UPSTREAM_ERROR',
            )
          const body: unknown = await response.json()
          // Do not relay headers or an upstream message that might echo credentials.
          const encoded = JSON.stringify(body)
          if (encoded.includes(appKey) || encoded.includes(encodeURIComponent(appKey)))
            return fail(502, 'TMS_INVALID_RESPONSE')
          res.end(encoded)
        } catch {
          fail(502, 'TMS_UPSTREAM_ERROR')
        }
      })
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), ['TMAP_', 'TMS_'])
  const agentEnv = loadEnv(mode, `${process.cwd()}/agent`, ['TMAP_', 'TMS_'])
  return {
    plugins: [
      vue(),
      centerApiProxy(
        env.TMS_APP_KEY || agentEnv.TMS_APP_KEY || env.TMAP_APP_KEY || agentEnv.TMAP_APP_KEY || '',
      ),
    ],
    server: {
      proxy: {
        '/api/agent': {
          target: 'http://127.0.0.1:8000',
          rewrite: (path) => path.replace(/^\/api\/agent/, '').replace(/^\/chat$/, '/api/chat'),
        },
      },
    },
  }
})
