"""
单元测试 - 数据模型
"""
import pytest
import uuid
from datetime import datetime, timezone

from app.models.user import User, UserRole
from app.models.work import Work, ContentType
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.result import Result, RiskLevel


class TestUserModel:
    """用户模型测试"""
    
    async def test_create_user(self, db_session):
        """测试创建用户"""
        user = User(
            email="new@example.com",
            username="newuser",
            hashed_password="hashed_password",
            role="user",
        )
        db_session.add(user)
        await db_session.commit()
        
        assert user.id is not None
        assert user.email == "new@example.com"
        assert user.username == "newuser"
        assert user.role == "user"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.created_at is not None
    
    async def test_user_default_values(self, db_session):
        """测试用户默认值"""
        user = User(
            email="default@example.com",
            username="defaultuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        
        assert user.role == "user"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.api_quota == 100
        assert user.api_used == 0
    
    async def test_user_admin_role(self, db_session):
        """测试管理员用户"""
        user = User(
            email="admin@example.com",
            username="admin",
            hashed_password="hashed_password",
            role="admin",
        )
        db_session.add(user)
        await db_session.commit()
        
        assert user.role == "admin"


class TestWorkModel:
    """作品模型测试"""
    
    async def test_create_text_work(self, db_session, test_user):
        """测试创建文本作品"""
        work = Work(
            user_id=test_user.id,
            title="测试文本作品",
            content_type="text",
            content_url="https://example.com/text",
            content_hash="abc123def456",
        )
        db_session.add(work)
        await db_session.commit()
        
        assert work.id is not None
        assert work.title == "测试文本作品"
        assert work.content_type == "text"
        assert work.content_url == "https://example.com/text"
        assert work.content_hash == "abc123def456"
    
    async def test_create_image_work(self, db_session, test_user):
        """测试创建图片作品"""
        work = Work(
            user_id=test_user.id,
            title="测试图片作品",
            content_type="image",
            content_url="https://example.com/image.jpg",
            mime_type="image/jpeg",
        )
        db_session.add(work)
        await db_session.commit()
        
        assert work.id is not None
        assert work.content_type == "image"
        assert work.mime_type == "image/jpeg"
    
    async def test_create_video_work(self, db_session, test_user):
        """测试创建视频作品"""
        work = Work(
            user_id=test_user.id,
            title="测试视频作品",
            content_type="video",
            content_url="https://example.com/video.mp4",
            mime_type="video/mp4",
            content_size=1024000,
        )
        db_session.add(work)
        await db_session.commit()
        
        assert work.id is not None
        assert work.content_type == "video"
        assert work.content_size == 1024000


class TestTaskModel:
    """任务模型测试"""
    
    async def test_create_detection_task(self, db_session, test_user, test_work):
        """测试创建检测任务"""
        task = Task(
            user_id=test_user.id,
            work_id=test_work.id,
            title="检测任务",
            status="pending",
            search_engines=["google", "bing"],
        )
        db_session.add(task)
        await db_session.commit()
        
        assert task.id is not None
        assert task.status == "pending"
        assert "google" in task.search_engines
        assert "bing" in task.search_engines
    
    async def test_task_status_transitions(self, db_session, test_user, test_work):
        """测试任务状态转换"""
        task = Task(
            user_id=test_user.id,
            work_id=test_work.id,
            status="pending",
        )
        db_session.add(task)
        await db_session.commit()
        
        # PENDING -> RUNNING
        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        await db_session.commit()
        assert task.status == "running"
        assert task.started_at is not None
        
        # RUNNING -> COMPLETED
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        task.progress = 100
        await db_session.commit()
        assert task.status == "completed"
        assert task.completed_at is not None


class TestResultModel:
    """结果模型测试"""
    
    async def test_create_result(self, db_session, test_user, test_task, test_work):
        """测试创建检测结果"""
        result = Result(
            task_id=test_task.id,
            user_id=test_user.id,
            work_id=test_work.id,
            risk_level="high",
            source_url="https://example.com/infringing",
            source_title="疑似侵权内容",
            source_snippet="这是疑似侵权的文本内容",
            similarity_score=0.95,
            content_type="text",
            search_engine="google",
        )
        db_session.add(result)
        await db_session.commit()
        
        assert result.id is not None
        assert result.risk_level == "high"
        assert result.similarity_score == 0.95
    
    async def test_result_risk_levels(self, db_session, test_user, test_task, test_work):
        """测试不同风险等级"""
        risk_levels = ["high", "medium", "low", "safe"]
        for i, risk_level in enumerate(risk_levels):
            result = Result(
                task_id=test_task.id,
                user_id=test_user.id,
                work_id=test_work.id,
                risk_level=risk_level,
                source_url=f"https://example.com/result_{i}",
                source_title=f"结果 {risk_level}",
                source_snippet="内容",
                similarity_score=0.5,
                content_type="text",
                search_engine="google",
            )
            db_session.add(result)
        
        await db_session.commit()


# Pytest fixture for test_work and test_task
@pytest.fixture
async def test_work(db_session, test_user):
    """创建测试作品"""
    work = Work(
        user_id=test_user.id,
        title="测试作品",
        content_type="text",
        content_url="https://example.com/test",
        content_hash="testhash123",
    )
    db_session.add(work)
    await db_session.commit()
    await db_session.refresh(work)
    return work


@pytest.fixture
async def test_task(db_session, test_user, test_work):
    """创建测试任务"""
    task = Task(
        user_id=test_user.id,
        work_id=test_work.id,
        status="pending",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task
