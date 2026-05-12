import { test, expect } from '@playwright/test';

/**
 * 登录流程 E2E 测试
 * 测试关键路径：访问首页 → 登录 → 跳转到仪表盘
 */
test.describe('登录流程', () => {
  test('应显示登录页面', async ({ page }) => {
    await page.goto('/');
    
    // 验证页面标题或登录表单存在
    await expect(page).toHaveTitle(/ScanIt|扫客/);
    await expect(page.locator('form')).toBeVisible();
  });

  test('应使用有效凭据登录', async ({ page }) => {
    await page.goto('/login');
    
    // 填写登录表单（根据实际表单字段调整）
    await page.fill('input[name="username"], input[type="text"]', 'testuser');
    await page.fill('input[name="password"], input[type="password"]', 'testpass123');
    
    // 提交表单
    await page.click('button[type="submit"], button:has-text("登录")');
    
    // 验证跳转到仪表盘（根据实际路由调整）
    await page.waitForURL('**/dashboard');
    await expect(page.locator('text=仪表盘, text=Dashboard')).toBeVisible();
  });

  test('应使用无效凭据显示错误', async ({ page }) => {
    await page.goto('/login');
    
    // 填写错误凭据
    await page.fill('input[name="username"], input[type="text"]', 'wrong');
    await page.fill('input[name="password"], input[type="password"]', 'wrong');
    
    // 提交表单
    await page.click('button[type="submit"], button:has-text("登录")');
    
    // 验证错误消息（根据实际错误提示调整）
    await expect(page.locator('text=用户名或密码错误, text=登录失败, [role="alert"]')).toBeVisible();
  });
});
