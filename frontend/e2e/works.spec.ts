import { test, expect } from '@playwright/test';

/**
 * 作品管理 E2E 测试
 * 测试关键路径：上传作品、查看列表、查看详情
 */
test.describe('作品管理', () => {
  // 每个测试前先登录
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="username"], input[type="text"]', 'testuser');
    await page.fill('input[name="password"], input[type="password"]', 'testpass123');
    await page.click('button[type="submit"], button:has-text("登录")');
    await page.waitForURL('**/dashboard');
  });

  test('应能从仪表盘跳转到作品列表', async ({ page }) => {
    await page.goto('/dashboard');
    
    // 点击导航到作品列表
    await page.click('text=作品管理, a[href*="works"], nav >> text=作品');
    
    // 验证跳转到作品列表页
    await page.waitForURL('**/works');
    await expect(page.locator('text=作品列表, h1, [data-testid="works-title"]')).toBeVisible();
  });

  test('应能上传新作品', async ({ page }) => {
    await page.goto('/works');
    
    // 点击上传按钮
    await page.click('text=上传作品, button:has-text("上传"), a[href*="upload"]');
    
    // 验证跳转到上传页
    await page.waitForURL('**/works/upload, **/upload');
    
    // 上传文件（根据实际 UI 调整）
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('tests/fixtures/sample-image.jpg'); // 需要准备测试文件
    
    // 填写作品信息
    await page.fill('input[name="title"], input[placeholder*="标题"]', 'E2E 测试作品');
    
    // 提交
    await page.click('button:has-text("提交"), button:has-text("上传"), button[type="submit"]');
    
    // 验证上传成功（返回作品列表或显示成功消息）
    await expect(page.locator('text=上传成功, [role="alert"]')).toBeVisible({ timeout: 10000 });
  });

  test('应能在列表中查看作品', async ({ page }) => {
    await page.goto('/works');
    
    // 验证作品列表存在
    await expect(page.locator('table, [data-testid="works-table"], .works-list')).toBeVisible();
    
    // 验证有作品数据（根据实际调整）
    const rows = page.locator('tbody >> tr, .works-list >> .work-item');
    await expect(rows.first()).toBeVisible({ timeout: 5000 });
  });

  test('应能从列表点击查看作品详情', async ({ page }) => {
    await page.goto('/works');
    
    // 点击第一个作品的详情按钮或标题
    await page.click('tbody >> tr:first-child >> text=详情, tbody >> tr:first-child >> a, .work-item:first-child >> a');
    
    // 验证跳转到详情页
    await page.waitForURL('**/works/*');
    await expect(page.locator('text=作品详情, h1, [data-testid="work-detail"]')).toBeVisible();
  });
});
