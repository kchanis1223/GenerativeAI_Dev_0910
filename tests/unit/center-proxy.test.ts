import { afterEach, expect, test, vi } from 'vitest'
import { createServer, type ViteDevServer } from 'vite'
import { centerApiProxy } from '../../vite.config'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

let server: ViteDevServer | undefined
let cacheDir: string | undefined
afterEach(async () => {
  await server?.close()
  if (cacheDir) await rm(cacheDir, { recursive: true, force: true })
})
async function start(key: string, upstream = vi.fn<typeof fetch>()) {
  cacheDir = await mkdtemp(join(tmpdir(), 'badaro-proxy-test-'))
  server = await createServer({
    configFile: false,
    cacheDir,
    optimizeDeps: { noDiscovery: true, include: [] },
    plugins: [centerApiProxy(key, upstream)],
    server: { host: '127.0.0.1', port: 0 },
  })
  await server.listen()
  const address = server.httpServer!.address()
  if (!address || typeof address === 'string') throw new Error('Server address missing')
  return { url: `http://127.0.0.1:${address.port}/api/tms/centerList`, upstream }
}

test('키 누락 시 외부 호출 없이 설정 오류를 반환한다', async () => {
  const { url, upstream } = await start('')
  const response = await fetch(url)
  expect(response.status).toBe(503)
  expect(await response.json()).toEqual({ code: 'TMS_KEY_MISSING' })
  expect(upstream).not.toHaveBeenCalled()
})

test('서버에서만 키를 추가하고 조회 응답을 반환한다', async () => {
  const body = { resultCode: '200', resultCount: 0, resultMessage: 'success', resultData: [] }
  const upstream = vi.fn<typeof fetch>().mockResolvedValue(Response.json(body))
  const { url } = await start('test-server-key', upstream)
  expect(await (await fetch(url)).json()).toEqual(body)
  expect(upstream).toHaveBeenCalledWith(
    'https://apis.openapi.sk.com/tms/centerList?appKey=test-server-key',
    expect.objectContaining({
      headers: { Accept: 'application/json' },
      redirect: 'error',
    }),
  )
})

test('다른 출처, 메서드, 쿼리 요청은 외부로 전달하지 않는다', async () => {
  const { url, upstream } = await start('test-server-key')
  expect((await fetch(url, { headers: { Origin: 'https://example.com' } })).status).toBe(403)
  expect((await fetch(url, { method: 'POST' })).status).toBe(405)
  expect((await fetch(`${url}?appKey=client-key`)).status).toBe(404)
  expect(upstream).not.toHaveBeenCalled()
})

test('키를 포함한 응답과 외부 오류 본문은 브라우저로 전달하지 않는다', async () => {
  const upstream = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(Response.json({ message: 'test-server-key' }))
    .mockResolvedValueOnce(new Response('test-server-key', { status: 401 }))
  const { url } = await start('test-server-key', upstream)
  const leaked = await fetch(url)
  expect(leaked.status).toBe(502)
  expect(await leaked.text()).not.toContain('test-server-key')
  const unauthorized = await fetch(url)
  expect(unauthorized.status).toBe(401)
  expect(await unauthorized.text()).not.toContain('test-server-key')
})
