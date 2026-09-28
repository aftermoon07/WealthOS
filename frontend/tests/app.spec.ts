import { test, expect } from '@playwright/test';

test('has title and dashboard element', async ({ page }) => {
  // Mock the /api/dashboard endpoint to return dummy data
  await page.route('/api/dashboard', async route => {
    const json = {
      summary: { net_worth: '10000', total_assets: '10000', total_liabilities: '0', savings_rate: '25.0', portfolio_value: '5000' },
      top_spending_categories: [],
      anomaly_count: 0,
      recent_anomalies: [],
      goals: [],
      net_worth_history: [],
      market_data_source: 'DEMO'
    };
    await route.fulfill({ json });
  });

  // We navigate to the index page
  await page.goto('/');

  // Wait for the app to finish loading state (skeleton will disappear)
  // We can look for the 'NET WORTH' label to appear
  await expect(page.locator('text=NET WORTH')).toBeVisible();

  // The title should be WealthOS or Dashboard
  await expect(page).toHaveTitle(/WealthOS/i);
});
