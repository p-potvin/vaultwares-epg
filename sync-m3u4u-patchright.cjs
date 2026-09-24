const os = require('node:os');
const path = require('node:path');
const { chromium } = require('C:/Users/Administrator/Desktop/Prom-King/qa-automation/node_modules/patchright');

const profile = process.env.M3U4U_CHROME_USER_DATA_DIR || path.join(os.homedir(), 'AppData', 'Local', 'VaultWares', 'M3U4UAutomation', 'ChromeProfile');
const playlistId = process.env.M3U4U_PLAYLIST_ID || '744895';
const timeout = Number.parseInt(process.env.M3U4U_TIMEOUT_MS || '120000', 10);
const postSyncWaitMs = Number.parseInt(process.env.M3U4U_POST_SYNC_WAIT_MS || '45000', 10);
const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';

function log(message) {
  process.stdout.write(`${new Date().toISOString()} ${message}\n`);
}

async function main() {
  if (!Number.isSafeInteger(timeout) || timeout < 10_000 || timeout > 120_000) {
    throw new Error('M3U4U_TIMEOUT_MS must be between 10000 and 120000');
  }
  if (!Number.isSafeInteger(postSyncWaitMs) || postSyncWaitMs < 5_000 || postSyncWaitMs > 60_000) {
    throw new Error('M3U4U_POST_SYNC_WAIT_MS must be between 5000 and 60000');
  }
  log('opening the dedicated Chrome profile');
  const context = await chromium.launchPersistentContext(profile, { executablePath: chrome, headless: false, args: ['--profile-directory=Default'], viewport: null, timeout });
  try {
    const page = context.pages()[0] || await context.newPage();
    await page.goto('https://m3u4u.com/playlists', { waitUntil: 'domcontentloaded', timeout });
    if (page.url().includes('/login')) throw new Error('m3u4u profile is signed out');
    await page.locator('button.bulk-sync-btn').waitFor({ state: 'visible', timeout });
    log('m3u4u playlists table loaded');
    const row = page.locator(`.ag-row[row-id="${playlistId}"]`);
    await row.waitFor({ state: 'visible', timeout });
    await row.getByRole('checkbox').check({ timeout });
    if (process.env.M3U4U_DRY_RUN === '1') {
      log(`playlist ${playlistId} is selectable (dry run)`);
      return;
    }
    const response = page.waitForResponse(r => r.url().includes('/api/playlists/bulk-sync') && r.request().method() === 'POST', { timeout });
    await page.getByRole('button', { name: 'Sync Selected Playlists' }).click({ timeout });
    log('first sync click completed; waiting for confirmation dialog');
    const confirmation = page.locator('button.confirm-ok, [data-action="confirm-ok"], [data-testid="confirm-ok"], #confirm-ok, .confirm-ok').first();
    try {
      await confirmation.waitFor({ state: 'visible', timeout });
    } catch (error) {
      const visibleButtons = await page.locator('[role="dialog"] button:visible, .modal button:visible, .swal2-popup button:visible').allTextContents();
      throw new Error(`m3u4u confirmation control did not appear; visible dialog buttons: ${JSON.stringify(visibleButtons)}`);
    }
    log('confirmation dialog appeared; submitting the second sync click');
    await confirmation.click({ timeout });
    const syncResponse = await response;
    if (!syncResponse.ok()) throw new Error(`m3u4u rejected playlist sync (HTTP ${syncResponse.status()})`);
    log(`playlist sync accepted (HTTP ${syncResponse.status()})`);
    log(`keeping the page open for ${postSyncWaitMs / 1000}s while m3u4u completes post-sync work`);
    await page.waitForTimeout(postSyncWaitMs);
    log('post-sync wait completed');
  } finally { await context.close(); }
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
