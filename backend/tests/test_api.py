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
            "/api/auth/register",
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
            "/api/auth/register",
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
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """测试密码错误"""
        response = await client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
    
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """测试用户不存在"""
        response = await client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "anypassword",
            },
        )
        assert response.status_code == 401
    
    async def test_get_current_user(self, client: AsyncClient, auth_headers, test_user):
        """测试获取当前用户信息"""
        response = await client.get(
            "/api/auth/me",
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
            "/api/works",
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
            "/api/works",
            headers=auth_headers,
            json={
                "title": "新作品",
                "content_type": "text",
                "content_url": "https://example.com/new",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "新作品"
    
    async def test_get_work(self, client: AsyncClient, auth_headers, test_work):
        """测试获取单个作品"""
        response = await client.get(
            f"/api/works/{test_work.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_work.id)
        assert data["title"] == test_work.title


class TestTasksAPI:
    """任务 API 测试"""
    
    async def test_list_tasks(self, client: AsyncClient, auth_headers, test_task):
        """测试列出任务"""
        response = await client.get(
            "/api/tasks",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    async def test_create_task(self, client: AsyncClient, auth_headers, test_work):
        """测试创建检测任务"""
        response = await client.post(
            "/api/tasks",
            headers=auth_headers,
            json={
                "work_id": str(test_work.id),
                "keywords": ["test", "demo"],
                "search_engines": ["google", "bing"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["work_id"] == str(test_work.id)


class TestResultsAPI:
    """结果 API 测试"""
    
    async def test_list_results(self, client: AsyncClient, auth_headers, test_result):
        """测试列出检测结果"""
        response = await client.get(
            "/api/results",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


# Fixtures for API tests - test_result now provided by conftest.py
