"""
比对器基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CompareResult:
    """比对结果"""

    similarity: float  # 0.0 - 1.0
    details: dict | None = None  # 详细比对信息
    matched_regions: list[dict] | None = None  # 匹配区域（图片/视频）
    matched_segments: list[dict] | None = None  # 匹配片段（视频）
    processing_time: float = 0.0  # 处理时间（秒）

    def __post_init__(self):
        """确保 similarity 在 0.0-1.0 范围内"""
        self.similarity = max(0.0, min(1.0, self.similarity))


class ComparatorBase(ABC):
    """比对器基类"""

    name: str = "base"

    def __init__(self, threshold: float = 0.8, **kwargs):
        """
        初始化比对器

        Args:
            threshold: 相似度阈值，超过该阈值认为是相似
            **kwargs: 其他配置参数
        """
        self.threshold = threshold
        self.config = kwargs

    @abstractmethod
    async def compare(self, content1: str | bytes, content2: str | bytes) -> CompareResult:
        """
        比对两个内容

        Args:
            content1: 第一个内容（可以是 URL、文本或文件路径）
            content2: 第二个内容

        Returns:
            CompareResult: 比对结果
        """
        raise NotImplementedError

    @abstractmethod
    async def compute_hash(self, content: str | bytes) -> str:
        """
        计算内容的哈希值（用于快速比对）

        Args:
            content: 内容

        Returns:
            str: 哈希值
        """
        raise NotImplementedError

    def is_similar(self, result: CompareResult) -> bool:
        """判断是否相似"""
        return result.similarity >= self.threshold

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(threshold={self.threshold})>"
