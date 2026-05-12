import { test, expect } from '@playwright/test';

/**
 * 检测任务 E2E 测试
 * 测试关键路径：创建任务、查看列表、查看结果
 */
test.describe('检测任务', () => {
  // 每个测试前先登录
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="username"], input[type="text"]', 'testuser');
    await page.fill('input[name="password"], input[type="password"]', 'testpass123');
    await page.click('button[type="submit"], button:has-text("登录")');
    await page.waitForURL('**/dashboard');
  });

  test('应能从仪表盘跳转到任务列表', async ({ page }) => {
    await page.goto('/dashboard');
    
    // 点击导航到任务列表
    await page.click('text=检测任务, a[href*="tasks"], nav >> text=任务');
    
    // 验证跳转到任务列表页
    await page.waitForURL('**/tasks');
    await expect(page.locator('text=检测任务列表, h1, [data-testid="tasks-title"]')).toBeVisible();
  });

  test('应能创建新检测任务', async ({ page }) => {
    await page.goto('/tasks');
    
    // 点击创建任务按钮
    await page.click('text=新建任务, button:has-text("新建"), button:has-text("创建")');
    
    // 验证跳转到创建任务页
    await page.waitForURL('**/tasks/create, **/tasks/new');
    
    // 选择作品（根据实际 UI 调整）
    await page.click('[data-testid="select-work"], select[name="work_id"]');
    await page.selectOption('select[name="work_id"]', { index: 1 });
    
    // 选择检测类型
    await page.check('input[name="content_type"][value="image"], input[value="image"]');
    
    // 提交任务
    await page.click('button[type="submit"], button:has-text("提交"), button:has-text("创建")');
    
    // 验证创建成功（返回任务列表或显示成功消息）
    await expect(page.locator('text=任务创建成功, [role="alert"]')).toBeVisible({ timeout: 10000 });
  });

  test('应能在列表中查看任务', async ({ page }) => {
    await page.goto('/tasks');
    
    // 验证任务列表存在
    await expect(page.locator('table, [data-testid="tasks-table"], .tasks-list')).toBeVisible();
    
    // 验证有任务数据（根据实际调整）
    const rows = page.locator('tbody >> tr, .tasks-list >> .task-item');
    await expect(rows.first()).toBeVisible({ timeout: 5000 });
  });

  test('应能从列表点击查看任务详情', async ({ page }) => {
    await page.goto('/tasks');
    
    // 点击第一个任务的详情按钮或标题
    await page.click('tbody >> tr:first-child >> text=详情, tbody >> tr:first-child >> a, .task-item:first-child >> a');
    
    // 验证跳转到详情页
    await page.waitForURL('**/tasks/*');
    await expect(page.locator('text=任务详情, h1, [data-testid="task-detail"]')).toBeVisible();
  });

  test('应能在任务详情页查看检测结果', async ({ page }) => {
    // 先跳转到某个任务详情页
    await page.goto('/tasks');
    await page.click('tbody >> tr:first-child >> a, .task-item:first-child >> a');
    await page.waitForURL('**/tasks/*');
    
    // 验证检测结果区域（根据实际 UI 调整）
    await expect(page.locator('text=检测结果, [data-testid="detection-results"]')).toBeVisible({ timeout: 10000 });
    
    // 验证有相似度分数或匹配结果
    await expect(page.locator('text=相似度, .similarity-score')).toBeVisible();
  });
});
