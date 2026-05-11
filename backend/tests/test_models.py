"""
单元测试 - 数据模型
"""
import pytest
from datetime import datetime
from sqlalchemy import select

from app.models.user import User
from app.models.work import Work, WorkType
from app.models.task import Task, TaskStatus, TaskType
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
        assert user.is_deleted is False
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
        assert user.is_deleted is False
        assert user.quota_monthly == 100
        assert user.quota_used_monthly == 0
    
    async def test_user_soft_delete(self, db_session):
        """测试用户软删除"""
        user = User(
            email="delete@example.com",
            username="deleteuser",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        await db_session.commit()
        
        # 软删除
        user.is_deleted = True
        await db_session.commit()
        
        # 查询应该找不到
        result = await db_session.execute(
            select(User).where(User.email == "delete@example.com")
        )
        found_user = result.scalar_one_or_none()
        assert found_user is None


class TestWorkModel:
    """作品模型测试"""
    
    async def test_create_text_work(self, db_session, test_user):
        """测试创建文本作品"""
        work = Work(
            user_id=test_user.id,
            title="测试文本作品",
            work_type=WorkType.TEXT,
            content="这是测试文本内容",
            simhash="abc123",
        )
        db_session.add(work)
        await db_session.commit()
        
        assert work.id is not None
        assert work.title == "测试文本作品"
        assert work.work_type == WorkType.TEXT
        assert work.content == "这是测试文本内容"
        assert work.simhash == "abc123"
    
    async def test_create_image_work(self, db_session, test_user):
        """测试创建图片作品"""
        work = Work(
            user_id=test_user.id,
            title="测试图片作品",
            work_type=WorkType.IMAGE,
            file_path="/uploads/image.jpg",
            phash="def456",
        )
        db_session.add(work)
        await db_session.commit()
        
        assert work.id is not None
        assert work.work_type == WorkType.IMAGE
        assert work.file_path == "/uploads/image.jpg"
        assert work.phash == "def456"
    
    async def test_create_video_work(self, db_session, test_user):
        """测试创建视频作品"""
        work = Work(
            user_id=test_user.id,
            title="测试视频作品",
            work_type=WorkType.VIDEO,
            file_path="/uploads/video.mp4",
            duration=120,
            frame_count=3600,
        )
        db_session.add(work)
        await db_session.commit()
        
        assert work.id is not None
        assert work.work_type == WorkType.VIDEO
        assert work.duration == 120
        assert work.frame_count == 3600


class TestTaskModel:
    """任务模型测试"""
    
    async def test_create_detection_task(self, db_session, test_user, test_work):
        """测试创建检测任务"""
        task = Task(
            user_id=test_user.id,
            work_id=test_work.id,
            task_type=TaskType.DETECTION,
            status=TaskStatus.PENDING,
            search_engines=["google", "bing"],
        )
        db_session.add(task)
        await db_session.commit()
        
        assert task.id is not None
        assert task.task_type == TaskType.DETECTION
        assert task.status == TaskStatus.PENDING
        assert "google" in task.search_engines
        assert "bing" in task.search_engines
    
    async def test_task_status_transitions(self, db_session, test_user, test_work):
        """测试任务状态转换"""
        task = Task(
            user_id=test_user.id,
            work_id=test_work.id,
            task_type=TaskType.DETECTION,
            status=TaskStatus.PENDING,
        )
        db_session.add(task)
        await db_session.commit()
        
        # PENDING -> RUNNING
        task.status = TaskStatus.RUNNING
        await db_session.commit()
        assert task.status == TaskStatus.RUNNING
        
        # RUNNING -> COMPLETED
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        await db_session.commit()
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None


class TestResultModel:
    """结果模型测试"""
    
    async def test_create_result(self, db_session, test_user, test_task):
        """测试创建检测结果"""
        result = Result(
            task_id=test_task.id,
            user_id=test_user.id,
            risk_level=RiskLevel.HIGH,
            source_url="https://example.com",
            source_title="疑似侵权内容",
            source_snippet="这是疑似侵权的文本内容",
            similarity=0.95,
            matched_content="疑似侵权内容",
            metadata={"engine": "google", "rank": 1},
        )
        db_session.add(result)
        await db_session.commit()
        
        assert result.id is not None
        assert result.risk_level == RiskLevel.HIGH
        assert result.similarity == 0.95
        assert result.metadata["engine"] == "google"
    
    async def test_result_risk_levels(self, db_session, test_user, test_task):
        """测试不同风险等级"""
        for risk_level in RiskLevel:
            result = Result(
                task_id=test_task.id,
                user_id=test_user.id,
                risk_level=risk_level,
                source_url=f"https://example.com/{risk_level.value}",
                source_title=f"结果 {risk_level.value}",
                source_snippet="内容",
                similarity=0.5,
            )
            db_session.add(result)
        
        await db_session.commit()
        
        # 查询所有结果
        from sqlalchemy import select
        results = await db_session.execute(select(Result))
        found_results = results.scalars().all()
        
        assert len(found_results) == len(RiskLevel)


# Pytest fixture for test_work and test_task
@pytest.fixture
async def test_work(db_session, test_user):
    """创建测试作品"""
    work = Work(
        user_id=test_user.id,
        title="测试作品",
        work_type=WorkType.TEXT,
        content="测试内容",
        simhash="test123",
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
        task_type=TaskType.DETECTION,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task
