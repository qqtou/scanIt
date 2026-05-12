import { test, expect } from '@playwright/test';

/**
 * 仪表盘页面 E2E 测试
 * 测试关键路径：查看统计、快速操作
 */
test.describe('仪表盘页面', () => {
  // 每个测试前先登录（实际项目中应使用登录态复用）
  test.beforeEach(async ({ page }) => {
    // 跳转到登录页并登录
    await page.goto('/login');
    await page.fill('input[name="username"], input[type="text"]', 'testuser');
    await page.fill('input[name="password"], input[type="password"]', 'testpass123');
    await page.click('button[type="submit"], button:has-text("登录")');
    await page.waitForURL('**/dashboard');
  });

  test('应显示关键统计信息', async ({ page }) => {
    await page.goto('/dashboard');
    
    // 验证统计卡片存在（根据实际 UI 调整选择器）
    await expect(page.locator('text=作品总数, [data-testid="stat-works"]')).toBeVisible();
    await expect(page.locator('text=检测任务, [data-testid="stat-tasks"]')).toBeVisible();
    await expect(page.locator('text=发现侵权, [data-testid="stat-results"]')).toBeVisible();
  });

  test('应显示快速操作按钮', async ({ page }) => {
    await page.goto('/dashboard');
    
    // 验证快速操作（根据实际 UI 调整）
    await expect(page.locator('text=上传作品, button:has-text("上传")')).toBeVisible();
    await expect(page.locator('text=新建检测, button:has-text("检测")')).toBeVisible();
  });

  test('点击上传作品应跳转到上传页', async ({ page }) => {
    await page.goto('/dashboard');
    
    // 点击上传按钮
    await page.click('text=上传作品, button:has-text("上传")');
    
    // 验证跳转（根据实际路由调整）
    await page.waitForURL('**/works/upload, **/upload');
  });
});
