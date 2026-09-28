import { test, expect } from '@playwright/test';

test('has title and dashboard element', async ({ page }) => {
  // We navigate to the index page
  await page.goto('/');

  // Wait for the app to finish loading state (skeleton will disappear)
  // We can look for the 'NET WORTH' label to appear
  await expect(page.locator('text=NET WORTH')).toBeVisible();

  // The title should be WealthOS or Dashboard
  await expect(page).toHaveTitle(/WealthOS/i);
});
