// Playwright quick check for wage-doc-compare-ui
const { chromium } = require('/c/Users/click/AppData/Local/hermes/hermes-agent/node_modules/playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const base = 'http://localhost:5173';
  const screenshots = [];

  const take = async (name) => {
    const path = `C:/Users/click/upstage_mabc/frontend/screenshots/${name}.png`;
    await page.screenshot({ path, fullPage: true });
    screenshots.push({ name, path });
  };

  const text = (sel) => page.locator(sel).textContent();
  const has = async (sel) => (await page.locator(sel).count()) > 0;

  try {
    await page.goto(base, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    await take('start-1440');

    const startTitle = await text('.start-title');
    console.log('start title:', startTitle);
    const cards = await page.locator('.start-choice-card').count();
    console.log('start cards:', cards);

    await page.setViewportSize({ width: 390, height: 900 });
    await page.waitForTimeout(400);
    await take('start-390');

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(400);
    await page.locator('.start-choice-card').first().click();
    await page.waitForTimeout(600);
    await take('input-1440-after-choice');

    const inputTitle = await text('.input-title');
    console.log('input title:', inputTitle);
    const addBtns = await page.locator('.add-row-btn-fixed').count();
    console.log('add btns:', addBtns);

    const nameInput = page.locator('.input-field').first();
    await nameInput.fill('식대');
    await page.locator('.input-field').nth(1).fill('월 식대');
    await page.locator('.input-field').nth(2).fill('50000');
    await page.locator('.input-field').nth(3).fill('0');

    const addBefore = page.locator('.add-row-btn-fixed').first();
    await addBefore.click();
    await page.waitForTimeout(350);

    const afterName = page.locator('.input-field').nth(4);
    await afterName.fill('식대');
    await page.locator('.input-field').nth(5).fill('월 식대');
    await page.locator('.input-field').nth(6).fill('70000');
    await page.locator('.input-field').nth(7).fill('0');

    const addAfter = page.locator('.add-row-btn-fixed').last();
    await addAfter.click();
    await page.waitForTimeout(350);
    await take('input-filled-1440');

    await page.locator('.primary-btn').first().click();
    await page.waitForTimeout(2500);
    await take('result-1440');

    const resultTitle = await text('.result-title');
    console.log('result title:', resultTitle);
    const backLink = await has('.result-back-link');
    console.log('back link present:', backLink);
    const detailsOpen = await has('.request-info-details');
    console.log('details present:', detailsOpen);
    const explainBtn = await has('.explain-primary-btn');
    console.log('explain button present:', explainBtn);

    const amounts = await page.locator('.side-amount').allTextContents();
    console.log('side amounts:', amounts);

    await page.locator('.result-back-link').click();
    await page.waitForTimeout(500);
    await take('input-after-back-1440');

    await page.locator('.primary-btn').first().click();
    await page.waitForTimeout(2500);
    await take('result-1440-recompare');

    const reamounts = await page.locator('.side-amount').allTextContents();
    console.log('recompare side amounts:', reamounts);
  } catch (e) {
    console.error('check failed:', e && e.message);
  }

  await browser.close();
  console.log('screenshots:', screenshots.map(s => s.path));
})();
