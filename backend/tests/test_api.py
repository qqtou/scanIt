"""
单元测试 - API 接口
"""
import pytest
from httpx import AsyncClient


class TestAuthAPI:
    """认证 API 测试"""
    
    async def test_register(self, client: AsyncClient):
        """测试用户注册"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "StrongPass123!",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "id" in data
    
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """测试重复邮箱注册"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "username": "anotheruser",
                "password": "StrongPass123!",
            },
        )
        assert response.status_code == 400
    
    async def test_login_success(self, client: AsyncClient, test_user):
        """测试登录成功"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """测试密码错误"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
    
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """测试用户不存在"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "anypassword",
            },
        )
        assert response.status_code == 401
    
    async def test_get_current_user(self, client: AsyncClient, auth_headers, test_user):
        """测试获取当前用户信息"""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username


class TestWorksAPI:
    """作品 API 测试"""
    
    async def test_list_works(self, client: AsyncClient, auth_headers, test_work):
        """测试列出作品"""
        response = await client.get(
            "/api/v1/works",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1
    
    async def test_create_work(self, client: AsyncClient, auth_headers):
        """测试创建作品"""
        response = await client.post(
            "/api/v1/works",
            headers=auth_headers,
            json={
                "title": "新作品",
                "work_type": "text",
                "content": "这是新作品的内容",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "新作品"
        assert data["work_type"] == "text"
    
    async def test_get_work(self, client: AsyncClient, auth_headers, test_work):
        """测试获取单个作品"""
        response = await client.get(
            f"/api/v1/works/{test_work.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_work.id
        assert data["title"] == test_work.title
    
    async def test_update_work(self, client: AsyncClient, auth_headers, test_work):
        """测试更新作品"""
        response = await client.put(
            f"/api/v1/works/{test_work.id}",
            headers=auth_headers,
            json={
                "title": "更新后的标题",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "更新后的标题"
    
    async def test_delete_work(self, client: AsyncClient, auth_headers, test_work):
        """测试删除作品 (软删除)"""
        response = await client.delete(
            f"/api/v1/works/{test_work.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
        
        # 再次查询应该找不到
        response = await client.get(
            f"/api/v1/works/{test_work.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404
    
    async def test_works_pagination(self, client: AsyncClient, auth_headers):
        """测试作品分页"""
        # 创建多个作品
        for i in range(15):
            await client.post(
                "/api/v1/works",
                headers=auth_headers,
                json={
                    "title": f"作品 {i}",
                    "work_type": "text",
                    "content": f"内容 {i}",
                },
            )
        
        # 测试分页
        response = await client.get(
            "/api/v1/works?page=1&page_size=10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] >= 15
        assert data["page"] == 1
        assert data["page_size"] == 10
    
    async def test_works_filter_by_type(self, client: AsyncClient, auth_headers):
        """测试按类型筛选"""
        # 创建不同类型的作品
        await client.post(
            "/api/v1/works",
            headers=auth_headers,
            json={"title": "文本作品", "work_type": "text", "content": "内容"},
        )
        await client.post(
            "/api/v1/works",
            headers=auth_headers,
            json={"title": "图片作品", "work_type": "image", "file_path": "/path"},
        )
        
        # 筛选文本类型
        response = await client.get(
            "/api/v1/works?work_type=text",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["work_type"] == "text"


class TestTasksAPI:
    """任务 API 测试"""
    
    async def test_list_tasks(self, client: AsyncClient, auth_headers, test_task):
        """测试列出任务"""
        response = await client.get(
            "/api/v1/tasks",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    async def test_create_task(self, client: AsyncClient, auth_headers, test_work):
        """测试创建检测任务"""
        response = await client.post(
            "/api/v1/tasks",
            headers=auth_headers,
            json={
                "work_id": test_work.id,
                "task_type": "detection",
                "search_engines": ["google", "bing"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["work_id"] == test_work.id
        assert data["task_type"] == "detection"
        assert "google" in data["search_engines"]
    
    async def test_create_batch_tasks(self, client: AsyncClient, auth_headers, test_work):
        """测试批量创建任务"""
        response = await client.post(
            "/api/v1/tasks/batch",
            headers=auth_headers,
            json={
                "work_ids": [test_work.id],
                "task_type": "detection",
                "search_engines": ["google"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["created_count"] >= 1
    
    async def test_get_task_progress(self, client: AsyncClient, auth_headers, test_task):
        """测试获取任务进度"""
        response = await client.get(
            f"/api/v1/tasks/{test_task.id}/progress",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "progress" in data
    
    async def test_cancel_task(self, client: AsyncClient, auth_headers, test_task):
        """测试取消任务"""
        response = await client.post(
            f"/api/v1/tasks/{test_task.id}/cancel",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"


class TestResultsAPI:
    """结果 API 测试"""
    
    async def test_list_results(self, client: AsyncClient, auth_headers, test_result):
        """测试列出检测结果"""
        response = await client.get(
            "/api/v1/results",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    async def test_results_pagination(self, client: AsyncClient, auth_headers):
        """测试结果分页"""
        response = await client.get(
            "/api/v1/results?page=1&page_size=5",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
    
    async def test_results_filter_by_risk(self, client: AsyncClient, auth_headers):
        """测试按风险等级筛选"""
        response = await client.get(
            "/api/v1/results?risk_level=high",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["risk_level"] == "high"
    
    async def test_results_filter_by_status(self, client: AsyncClient, auth_headers):
        """测试按审核状态筛选"""
        response = await client.get(
            "/api/v1/results?review_status=pending",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["review_status"] == "pending"
    
    async def test_review_result(self, client: AsyncClient, auth_headers, test_result):
        """测试审核结果"""
        response = await client.put(
            f"/api/v1/results/{test_result.id}/review",
            headers=auth_headers,
            json={
                "review_status": "confirmed",
                "review_notes": "确认侵权",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["review_status"] == "confirmed"
        assert data["review_notes"] == "确认侵权"
    
    async def test_export_results(self, client: AsyncClient, auth_headers):
        """测试导出结果"""
        response = await client.post(
            "/api/v1/results/export",
            headers=auth_headers,
            json={"format": "csv"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv"


class TestDashboardAPI:
    """仪表盘 API 测试"""
    
    async def test_get_stats(self, client: AsyncClient, auth_headers):
        """测试获取统计数据"""
        response = await client.get(
            "/api/v1/dashboard/stats",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_works" in data
        assert "total_tasks" in data
        assert "total_results" in data
    
    async def test_get_trends(self, client: AsyncClient, auth_headers):
        """测试获取趋势数据"""
        response = await client.get(
            "/api/v1/dashboard/trends",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "tasks_by_day" in data
        assert "results_by_risk" in data


# Fixtures for API tests
@pytest.fixture
async def test_result(db_session, test_user, test_task):
    """创建测试结果"""
    from app.models.result import Result, RiskLevel
    result = Result(
        task_id=test_task.id,
        user_id=test_user.id,
        risk_level=RiskLevel.HIGH,
        source_url="https://example.com",
        source_title="疑似侵权",
        source_snippet="内容",
        similarity=0.85,
    )
    db_session.add(result)
    await db_session.commit()
    await db_session.refresh(result)
    return result
