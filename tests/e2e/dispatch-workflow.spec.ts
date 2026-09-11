import { expect, test, type Page } from '@playwright/test'

async function prepare(page: Page, center = '성수센터') {
  await page.goto('/workspace')
  await page.getByRole('radio', { name: `${center} 선택`, exact: true }).check()
  await page.getByRole('button', { name: '주문 등록/선택', exact: true }).click()
  await page.getByRole('button', { name: '주문 전체 선택', exact: true }).click()
  await page.getByRole('button', { name: '차량 선택', exact: true }).click()
  await page.getByRole('button', { name: '가능 차량 전체 선택', exact: true }).click()
  await page.getByRole('button', { name: '배차 조건 설정', exact: true }).click()
  await page.getByRole('button', { name: '배차 요청 확인', exact: true }).click()
}

test('센터→주문→차량→조건→요청→계산→결과→차량 상세 순서로 진행한다', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto('/workspace')
  await expect(page.getByRole('button', { name: '주문 등록/선택', exact: true })).toBeDisabled()
  await expect(
    page.getByRole('navigation', { name: '배차 진행 단계' }).getByRole('button'),
  ).toHaveCount(8)
  await prepare(page)
  await expect(page.locator('.workflow-review')).toContainText('성수센터')
  await expect(page.locator('.workflow-review')).toContainText('8건')
  await expect(page.locator('.workflow-review')).toContainText('5대')
  await page.getByRole('button', { name: '배차 요청하기', exact: true }).click()
  await expect(page.getByRole('heading', { name: '6. 계산 중', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '배차 요청하기', exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '7. 배차 결과 확인', exact: true })).toBeVisible()
  await expect(page.locator('.dispatch-totals')).toContainText('7')
  await expect(page.locator('.unassigned')).toContainText('인천 미배차 예제')
  await page.screenshot({ path: 'test-results/workflow-result-desktop.png', fullPage: true })
  await page.getByRole('button', { name: '차량별 배송 상세 확인', exact: true }).click()
  await expect(page.getByRole('heading', { name: /^8\./ })).toBeVisible()
  await expect(page.getByRole('img', { name: '배송 순서 직선 경로도' })).toBeVisible()
  await expect(page.locator('.delivery-stops li').first()).toContainText('도착')
  await page.getByRole('button', { name: 'API 탐색', exact: true }).click()
  await page.getByRole('button', { name: '배송 준비', exact: true }).click()
  await expect(page.getByRole('heading', { name: /^8\./ })).toBeVisible()
  await page
    .getByRole('navigation', { name: '배차 진행 단계' })
    .getByRole('button', { name: /01/ })
    .click()
  await page.getByRole('radio', { name: '을지로센터 선택', exact: true }).check()
  await expect(page.getByRole('status')).toContainText('이전 결과를 초기화')
  await expect(
    page.getByRole('navigation', { name: '배차 진행 단계' }).getByRole('button', { name: /07/ }),
  ).toBeDisabled()
  expect(errors).toEqual([])
})

test('주문 등록을 선택에 반영하고 이전 단계·보조 메뉴 이동 후에도 선택을 유지한다', async ({
  page,
}) => {
  await page.goto('/workspace')
  await page.getByRole('radio', { name: '을지로센터 선택', exact: true }).check()
  await page.getByRole('button', { name: '주문 등록/선택', exact: true }).click()
  await expect(page.getByRole('button', { name: '차량 선택', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: '주문 등록·관리', exact: true }).click()
  await page.getByRole('button', { name: '등록', exact: true }).click()
  await page.getByLabel('orderName').fill('오늘 신규 주문')
  await page.getByRole('button', { name: '저장', exact: true }).click()
  await expect(
    page.getByRole('checkbox', { name: '오늘 신규 주문 선택', exact: true }),
  ).toBeVisible()
  await page.getByRole('checkbox', { name: '오늘 신규 주문 선택', exact: true }).check()
  await page.getByRole('button', { name: '차량 선택', exact: true }).click()
  await expect(
    page.getByRole('checkbox', { name: '정비 대기 차량 선택', exact: true }),
  ).toBeDisabled()
  await expect(page.getByRole('button', { name: '배차 조건 설정', exact: true })).toBeDisabled()
  await page.getByRole('checkbox', { name: '12가1234 선택', exact: true }).check()
  await page.getByRole('button', { name: '이전 단계', exact: true }).click()
  await expect(
    page.getByRole('checkbox', { name: '오늘 신규 주문 선택', exact: true }),
  ).toBeChecked()
  await page.getByRole('button', { name: '차량 정보', exact: true }).click()
  const vehicle = page.locator('.tms-records > li').filter({ hasText: '12가1234' })
  await vehicle.getByRole('button', { name: '수정', exact: true }).click()
  await page.getByLabel('inputYn').selectOption('0')
  await page.getByRole('button', { name: '저장', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('성공')
  await page.getByRole('button', { name: '배송 준비', exact: true }).click()
  await page.getByRole('button', { name: '차량 선택', exact: true }).click()
  await expect(page.getByRole('checkbox', { name: '12가1234 선택', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: '배차 조건 설정', exact: true })).toBeDisabled()
})

test('모바일에서 경로 제외로 배차하고 새 배송을 준비한다', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await prepare(page)
  await page.getByRole('button', { name: '이전 단계', exact: true }).click()
  await page.getByLabel('경로 데이터', { exact: true }).selectOption('N')
  await page.getByRole('button', { name: '배차 요청 확인', exact: true }).click()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
  await page.screenshot({ path: 'test-results/workflow-review-mobile.png', fullPage: true })
  await page.getByRole('button', { name: '배차 요청하기', exact: true }).click()
  await expect(page.getByRole('heading', { name: '7. 배차 결과 확인', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '차량별 배송 상세 확인', exact: true }).click()
  await expect(page.getByText('경로 데이터 제외로 요청하여 배송 순서만 표시합니다.')).toBeVisible()
  await expect(page.locator('.route-diagram')).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
  await page.getByRole('button', { name: '새 배송 준비', exact: true }).click()
  await expect(page.getByRole('heading', { name: '1. 센터 선택', exact: true })).toBeVisible()
  await expect(page.getByRole('radio', { checked: true })).toHaveCount(0)
})
