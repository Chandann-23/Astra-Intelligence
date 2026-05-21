import { test, expect } from '@playwright/test';

test.describe('Astra Intelligence Homepage', () => {
  test('should load the homepage with correct title', async ({ page }) => {
    await page.goto('/');
    
    // Check title
    await expect(page).toHaveTitle(/ASTRA/);
    
    // Check main heading
    const heading = page.locator('h1', { hasText: 'Astra Engine' });
    await expect(heading).toBeVisible();
  });

  test('should have a functional chat input', async ({ page }) => {
    await page.goto('/');
    
    // Find the input field
    const chatInput = page.getByPlaceholder('Initialize research sequence...');
    await expect(chatInput).toBeVisible();
    
    // Verify it accepts input
    await chatInput.fill('Test search query');
    await expect(chatInput).toHaveValue('Test search query');
    
    // Find the execute button
    const executeButton = page.locator('button', { hasText: 'Execute' });
    await expect(executeButton).toBeVisible();
  });

  test('should display engine insights panel', async ({ page }) => {
    await page.goto('/');
    
    // Check for the Engine Insights panel header
    const engineInsights = page.getByText('ENGINE_INSIGHTS');
    await expect(engineInsights).toBeVisible();
    
    // Check for RAG pipeline status
    const ragPipelineStatus = page.getByText('RAG Pipeline Status');
    await expect(ragPipelineStatus).toBeVisible();
  });
});
