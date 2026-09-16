import { test, expect, type Page } from '@playwright/test';

const BASE = 'http://localhost:5173';

async function gotoStart(page: Page) {
  await page.goto(BASE);
  await page.waitForSelector('.start-title', { timeout: 10000 });
}

test('시작 화면: Paychecker와 대상 설명, 카드 4개 표시', async ({ page }) => {
  await gotoStart(page);

  await expect(page.locator('.start-title')).toHaveText('Paychecker');
  await expect(page.locator('.start-sub')).toHaveText('내 월급, 어디가 달라졌을까요?');
  await expect(page.locator('.start-desc')).toHaveText(
    '한국어 명세서가 낯선 이주노동자를 위한 급여 확인'
  );

  await expect(page.locator('.start-choice-card')).toHaveCount(4);

  await expect(page.locator('.start-choice-title').first()).toHaveText('월급 못 받음');
  await expect(page.locator('.start-choice-desc').first()).toHaveText(
    '받기로 한 월급이 들어오지 않았어요.'
  );

  await expect(page.locator('.start-choice-card').nth(1)).toHaveText([
    '적거나 달라짐',
    '금액이 바뀌어서 확인하고 싶은 경우',
  ]);
  await expect(page.locator('.start-choice-card').nth(2)).toHaveText([
    '명세서 이해',
    '항목이 여러 개일 때 어떤 게 대응되는지 보는 경우',
  ]);
  await expect(page.locator('.start-choice-card').nth(3)).toHaveText([
    '직접 입력',
    '버튼 대신 직접 항목을 입력하고 싶은 경우',
  ]);
});

test('시작 화면: 카드 클릭 시 기존 선택 동작 연결', async ({ page }) => {
  await gotoStart(page);

  const first = page.locator('.start-choice-card').first();
  await first.click();
  await expect(first).toHaveClass(/selected/);
  await expect(page.locator('.start-choice-card').first()).toBeVisible();

  await page.locator('.start-choice-card').nth(1).click();
  await expect(page.locator('.start-choice-card').first()).not.toHaveClass(/selected/);
  await expect(page.locator('.start-choice-card').nth(1)).toHaveClass(/selected/);
});

test('입력 화면: 항목 추가 버튼 크기/스타일', async ({ page }) => {
  await gotoStart(page);
  await page.locator('.start-choice-card').last().click();
  await page.waitForSelector('.input-title', { timeout: 10000 });

  const addBtn = page.locator('.add-row-btn-fixed').first();
  const box = await addBtn.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.height).toBe(44);
  expect(box!.width).toBeGreaterThanOrEqual(32);
  expect(box!.width).toBeLessThanOrEqual(360);

  const style = await addBtn.evaluate((el) => getComputedStyle(el));
  expect(style.backgroundColor).toBe('rgb(255, 255, 255)');
  expect(style.borderTopWidth).toBe('1px');
  expect(style.borderTopColor).toBe('rgb(215, 221, 226)');
  expect(style.borderRadius).toBe('8px');
  expect(style.color).toBe('rgb(27, 36, 43)');
});

test('입력 화면: 각 목록 아래 항목 추가 버튼 유지, 입력 후 비교 가능', async ({ page }) => {
  await gotoStart(page);
  await page.locator('.start-choice-card').last().click();
  await page.waitForSelector('.input-title', { timeout: 10000 });

  const beforeName = page.locator('.input-field').first();
  await beforeName.fill('식대');
  await page.locator('.input-field').nth(1).fill('월 식대');
  await page.locator('.input-field').nth(2).fill('50000');

  await page.locator('.add-row-btn-fixed').first().click();

  const afterName = page.locator('.input-field').nth(4);
  await afterName.fill('식대');
  await page.locator('.input-field').nth(5).fill('월 식대');
  await page.locator('.input-field').nth(6).fill('70000');

  await page.locator('.add-row-btn-fixed').last().click();
  await page.locator('.primary-btn').first().click();

  await page.waitForSelector('.result-title', { timeout: 20000 });
  await expect(page.locator('.result-title')).toHaveText('비교 결과');
});

test('결과 화면: 항목별 금액 32px/700, 관련 자료/참고 문구 영역, 요청ID/버전 접기, 뒤로가기, 강조 버튼', async ({ page }) => {
  await gotoStart(page);
  await page.locator('.start-choice-card').last().click();
  await page.waitForSelector('.input-title', { timeout: 10000 });

  await page.locator('.input-field').first().fill('식대');
  await page.locator('.input-field').nth(1).fill('월 식대');
  await page.locator('.input-field').nth(2).fill('50000');

  await page.locator('.add-row-btn-fixed').first().click();

  await page.locator('.input-field').nth(4).fill('식대');
  await page.locator('.input-field').nth(5).fill('월 식대');
  await page.locator('.input-field').nth(6).fill('70000');

  await page.locator('.add-row-btn-fixed').last().click();
  await page.locator('.primary-btn').first().click();
  await page.waitForSelector('.result-title', { timeout: 20000 });

  const beforeAmount = page.locator('.side-amount').first();
  const afterAmount = page.locator('.side-amount').nth(1);
  expect(beforeAmount).toBeVisible();
  expect(afterAmount).toBeVisible();

  await expect(page.locator('.result-back-link')).toBeVisible();
  await expect(page.locator('.request-info-details')).toBeVisible();
  await expect(page.locator('.explain-primary-btn')).toBeVisible();

  await expect(page.locator('.explain-primary-btn')).toHaveText('차이 설명과 질문 만들기');

  const related = page.locator('.meta-label').first();
  await expect(related).toHaveText('관련 자료');

  const ref = page.locator('.meta-label').last();
  await expect(ref).toHaveText('참고 문구');
});

test('결과 화면: 요청 ID/버전 접기 동작과 뒤로가기', async ({ page }) => {
  await gotoStart(page);
  await page.locator('.start-choice-card').last().click();
  await page.waitForSelector('.input-title', { timeout: 10000 });

  await page.locator('.input-field').first().fill('식대');
  await page.locator('.input-field').nth(1).fill('월 식대');
  await page.locator('.input-field').nth(2).fill('50000');
  await page.locator('.add-row-btn-fixed').first().click();

  await page.locator('.input-field').nth(4).fill('식대');
  await page.locator('.input-field').nth(5).fill('월 식대');
  await page.locator('.input-field').nth(6).fill('70000');
  await page.locator('.add-row-btn-fixed').last().click();
  await page.locator('.primary-btn').first().click();
  await page.waitForSelector('.result-title', { timeout: 20000 });

  const details = page.locator('.request-info-details');
  await expect(details).toHaveAttribute('open');

  const infoValue = page.locator('.info-value').first();
  await expect(infoValue).toBeVisible();

  await page.locator('.result-back-link').click();
  await page.waitForSelector('.input-title', { timeout: 10000 });
  await expect(page.locator('.input-title')).toBeVisible();
});

test('입력 화면: 수정 후 재비교 흐름', async ({ page }) => {
  await gotoStart(page);
  await page.locator('.start-choice-card').last().click();
  await page.waitForSelector('.input-title', { timeout: 10000 });

  await page.locator('.input-field').first().fill('식대');
  await page.locator('.input-field').nth(1).fill('월 식대');
  await page.locator('.input-field').nth(2).fill('50000');
  await page.locator('.add-row-btn-fixed').first().click();

  await page.locator('.input-field').nth(4).fill('식대');
  await page.locator('.input-field').nth(5).fill('월 식대');
  await page.locator('.input-field').nth(6).fill('70000');
  await page.locator('.add-row-btn-fixed').last().click();
  await page.locator('.primary-btn').first().click();
  await page.waitForSelector('.result-title', { timeout: 20000 });

  await expect(page.locator('.side-amount').first()).toBeVisible();
  await expect(page.locator('.side-amount').nth(1)).toBeVisible();

  await page.locator('.result-back-link').click();
  await page.waitForSelector('.input-title', { timeout: 10000 });

  await page.locator('.input-field').nth(6).fill('80000');
  await page.locator('.primary-btn').first().click();
  await page.waitForSelector('.result-title', { timeout: 20000 });

  const afterAmount = page.locator('.side-amount').nth(1);
  const text = await afterAmount.textContent();
  expect(text).toContain('80000');
});

test('화면 크기: 390px 캡처', async ({ page }) => {
  await gotoStart(page);
  await page.setViewportSize({ width: 390, height: 900 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'screenshots/start-390.png', fullPage: true });
  await expect(page.locator('.start-title')).toBeVisible();
});

test('화면 크기: 1440px 캡처', async ({ page }) => {
  await gotoStart(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'screenshots/start-1440.png', fullPage: true });
  await expect(page.locator('.start-title')).toBeVisible();
});
