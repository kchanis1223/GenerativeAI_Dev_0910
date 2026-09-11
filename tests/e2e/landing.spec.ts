import { expect, test } from '@playwright/test'

test('기존 바다·로고·물고기 랜딩에서 바다가 갈라지는 전환으로 배차 화면에 진입한다', async ({
  page,
}) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Badaro', exact: true })).toBeVisible()
  await expect(page.locator('main a')).toHaveCount(1)
  await expect(page.locator('.fish-scene')).toHaveCount(3)
  await expect(page.locator('.water-photo')).toBeVisible()
  expect(
    await page
      .locator('.water-photo')
      .evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0),
  ).toBe(true)
  await expect(page.getByRole('link', { name: '바다로 워크스페이스 입장' })).toHaveCSS(
    'font-family',
    /SSRO WaterDrop/,
  )
  await page.clock.install()
  await page.getByRole('link', { name: '바다로 워크스페이스 입장' }).click()
  await expect(page.locator('.ocean-transition')).toBeVisible()
  await page.clock.runFor(1400)
  await expect(page).toHaveURL('/workspace')
  await expect(page.locator('.ocean-transition')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '배송 배차', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '배차 요청', exact: true })).toHaveCSS(
    'font-family',
    /JayeonSans/,
  )
  await page.getByRole('link', { name: 'Badaro 메인 페이지' }).click()
  await expect(page).toHaveURL('/')
  await expect(page.locator('.water-photo')).toBeVisible()
  expect(errors).toEqual([])
})

test('모바일 랜딩은 화면을 채우며 모션 감소 설정에서 키보드로 즉시 진입한다', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  expect(
    await page.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      height: document.documentElement.scrollHeight,
    })),
  ).toEqual({ width: 390, height: 844 })
  await expect(page.locator('.landing animate')).toHaveCount(0)
  await expect(page.locator('.water-photo')).toHaveCSS('animation-name', 'none')
  await expect(page.locator('.badaro-wordmark')).toHaveCSS('filter', 'none')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: '바다로 워크스페이스 입장' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL('/workspace')
  await expect(page.locator('.ocean-transition')).toHaveCount(0)
})
