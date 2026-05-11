"""
比对器

导出所有比对器
"""
from app.engines.comparators.base import CompareResult, ComparatorBase
from app.engines.comparators.text import TextComparator
from app.engines.comparators.image import ImageComparator
from app.engines.comparators.video import VideoComparator

__all__ = [
    "ComparatorBase",
    "CompareResult",
    "TextComparator",
    "ImageComparator",
    "VideoComparator",
]
