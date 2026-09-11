import { expect, test } from '@playwright/test'

test('사진과 전역 폰트를 표시하고 로고를 눌러 워크스페이스에 이동한다', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Badaro', exact: true })).toBeVisible()
  await expect(page.locator('.sidebar')).toHaveCount(0)
  await expect(page.locator('main a')).toHaveCount(1)
  await page.evaluate(() => document.fonts.ready)
  expect(await page.evaluate(() => document.fonts.check('16px "SSRO WaterDrop"'))).toBe(true)
  expect(
    await page
      .locator('.water-photo')
      .evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0),
  ).toBe(true)
  await expect(page.locator('h1 .badaro-logo')).toBeVisible()
  expect(
    await page
      .locator('h1 .badaro-logo')
      .evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0),
  ).toBe(true)
  await expect(page.getByRole('link', { name: '바다로 워크스페이스 입장' })).toHaveCSS(
    'font-family',
    /SSRO WaterDrop/,
  )
  await page.getByRole('link', { name: '바다로 워크스페이스 입장' }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  await expect(page.locator('.ocean-transition')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '1. 센터 선택', exact: true })).toBeVisible()
  await page.evaluate(() => document.fonts.ready)
  expect(await page.evaluate(() => document.fonts.check('16px JayeonSans'))).toBe(true)
  await expect(page.getByRole('searchbox')).toHaveCSS('font-family', /JayeonSans/)
  await expect(page.locator('.brand .badaro-logo')).toBeVisible()
  await page.getByRole('button', { name: '동작 흐름', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace\/flow$/)
  await page.reload()
  await expect(page.getByRole('heading', { name: '눈으로 확인하는 동작 흐름' })).toBeVisible()
  await page.goBack()
  await expect(page).toHaveURL(/\/workspace$/)
  await expect(page.locator('.ocean-transition')).toHaveCount(0)
  await page.getByRole('link', { name: 'Badaro 메인 페이지' }).click()
  await expect(page).toHaveURL(/\/$/)
  expect(errors).toEqual([])
})

test('모바일 메인은 스크롤 없이 표시되며 모션 감소 설정을 따른다', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await expect(page.getByRole('link', { name: '바다로 워크스페이스 입장' })).toBeVisible()
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
  await expect(page).toHaveURL(/\/workspace$/)
  await expect(page.locator('.ocean-transition')).toHaveCount(0)
})
