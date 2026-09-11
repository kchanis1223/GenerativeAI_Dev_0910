import { expect, test } from '@playwright/test'

test('로고와 역할별 진입 버튼을 표시하고 본사물류운영자 화면으로 전환한다', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Badaro', exact: true })).toBeVisible()
  await expect(page.locator('main a')).toHaveCount(2)
  await expect(page.locator('.fish-scene')).toHaveCount(0)
  await expect(page.locator('.water-photo')).toBeVisible()
  expect(
    await page
      .locator('.water-photo')
      .evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0),
  ).toBe(true)
  await expect(page.getByRole('link', { name: '본사물류운영자 페이지 진입' })).toHaveCSS(
    'font-family',
    /JayeonSans/,
  )
  const entry = page.getByRole('link', { name: '본사물류운영자 페이지 진입' })
  const bounds = (await entry.boundingBox())!
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2)
  await expect(entry).toHaveCSS('animation-play-state', 'paused')
  await page.clock.install()
  await page.getByRole('link', { name: '본사물류운영자 페이지 진입' }).click()
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
  await expect(page.locator('.role-entry').first()).toHaveCSS('animation-name', 'none')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: '점주님 페이지 진입' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: '본사물류운영자 페이지 진입' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL('/workspace')
  await expect(page.locator('.ocean-transition')).toHaveCount(0)
})

test('점주님 진입은 별도 등록 준비 화면으로 연결된다', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await page.getByRole('link', { name: '점주님 페이지 진입' }).click()
  await expect(page).toHaveURL('/owner')
  await expect(page.getByRole('heading', { name: '점주님 페이지', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: '차량 등록', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: '배송정보 등록', exact: true })).toBeVisible()
  await page.getByRole('link', { name: '진입 화면으로', exact: true }).click()
  await page.getByRole('link', { name: '본사물류운영자 페이지 진입' }).click()
  await expect(page.getByRole('link', { name: '본사물류운영자 전용', exact: true })).toBeVisible()
  await expect(page.getByText('목업 모드', { exact: true })).toHaveCount(0)
})
