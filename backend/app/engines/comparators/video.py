"""
视频比对器

使用关键帧提取 + 图片比对进行视频相似度检测
"""
import asyncio
import hashlib
import time
from io import BytesIO
from typing import AsyncIterator

import cv2
import httpx
import numpy as np
from PIL import Image

from app.engines.comparators.base import CompareResult, ComparatorBase
from app.engines.comparators.image import ImageComparator


class VideoComparator(ComparatorBase):
    """
    视频比对器

    算法:
    1. 提取视频关键帧
    2. 对每个关键帧进行图片比对
    3. 综合评分
    """

    name = "video_keyframe"

    def __init__(
        self,
        threshold: float = 0.8,
        max_frames: int = 10,
        frame_interval: int = 5,
        **kwargs,
    ):
        """
        初始化视频比对器

        Args:
            threshold: 相似度阈值
            max_frames: 最大关键帧数量
            frame_interval: 帧间隔（秒）
            **kwargs: 其他配置参数
        """
        super().__init__(threshold, **kwargs)
        self.max_frames = max_frames
        self.frame_interval = frame_interval
        self.image_comparator = ImageComparator(
            threshold=kwargs.get("image_threshold", 0.85),
            mode=kwargs.get("image_mode", "phash"),
        )

    async def compare(self, content1: str | bytes, content2: str | bytes) -> CompareResult:
        """
        比对两个视频的相似度

        Args:
            content1: 第一个视频（URL、路径或字节数据）
            content2: 第二个视频

        Returns:
            CompareResult: 比对结果
        """
        start_time = time.time()

        try:
            # 提取关键帧
            frames1 = await self._extract_frames(content1)
            frames2 = await self._extract_frames(content2)

            if not frames1 or not frames2:
                return CompareResult(
                    similarity=0.0,
                    processing_time=time.time() - start_time,
                )

            # 两两比对关键帧
            similarities = []
            matched_segments = []

            for i, frame1 in enumerate(frames1):
                best_similarity = 0.0
                best_match_idx = 0

                for j, frame2 in enumerate(frames2):
                    sim = await self._compare_frames(frame1, frame2)
                    if sim > best_similarity:
                        best_similarity = sim
                        best_match_idx = j

                similarities.append(best_similarity)
                if best_similarity >= self.threshold:
                    matched_segments.append({
                        "frame1_index": i,
                        "frame2_index": best_match_idx,
                        "similarity": best_similarity,
                        "timestamp1": i * self.frame_interval,
                        "timestamp2": best_match_idx * self.frame_interval,
                    })

            # 计算综合相似度
            if similarities:
                # 使用加权平均
                weights = [f["similarity"] for f in matched_segments] if matched_segments else similarities
                total_similarity = sum(weights) / len(similarities)
                max_similarity = max(similarities)
                final_similarity = max_similarity * 0.6 + total_similarity * 0.4
            else:
                final_similarity = 0.0

            return CompareResult(
                similarity=final_similarity,
                details={
                    "num_frames1": len(frames1),
                    "num_frames2": len(frames2),
                    "max_similarity": max(similarities) if similarities else 0.0,
                    "avg_similarity": sum(similarities) / len(similarities) if similarities else 0.0,
                    "matched_count": len(matched_segments),
                },
                matched_segments=matched_segments,
                processing_time=time.time() - start_time,
            )

        except Exception as e:
            return CompareResult(
                similarity=0.0,
                details={"error": str(e)},
                processing_time=time.time() - start_time,
            )

    async def compute_hash(self, content: str | bytes) -> str:
        """
        计算视频的哈希值（基于关键帧的哈希）

        Args:
            content: 视频内容

        Returns:
            str: 视频哈希值
        """
        frames = await self._extract_frames(content)
        if not frames:
            return "0" * 64

        # 计算所有帧的哈希
        hashes = []
        for frame in frames[:self.max_frames]:
            frame_hash = self.image_comparator._compute_phash(frame)
            hashes.append(frame_hash)

        # 合并哈希
        combined = "".join(hashes)
        # 缩减为固定长度
        md5 = hashlib.md5(combined.encode()).hexdigest()
        return md5

    async def _extract_frames(self, content: str | bytes) -> list[np.ndarray]:
        """提取视频关键帧"""
        try:
            # 获取视频文件
            if isinstance(content, str):
                if content.startswith("http://") or content.startswith("https://"):
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.get(content)
                        response.raise_for_status()
                        video_bytes = BytesIO(response.content)
                        video_path_or_bytes = video_bytes
                else:
                    video_path_or_bytes = content
            else:
                video_path_or_bytes = BytesIO(content)

            # 打开视频
            cap = cv2.VideoCapture(video_path_or_bytes)
            if not cap.isOpened():
                return []

            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0

            # 计算采样间隔
            interval = max(1, int(self.frame_interval * fps))
            frame_indices = list(range(0, total_frames, interval))[:self.max_frames]

            # 提取帧
            frames = []
            for idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    # BGR 转 RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(frame_rgb)

            cap.release()
            return frames

        except Exception:
            return []

    async def _compare_frames(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """比对两帧图片"""
        result = await self.image_comparator.compare(frame1, frame2)
        return result.similarity

    async def extract_and_compare(
        self,
        video_content: str | bytes,
        target_frames: list[np.ndarray],
    ) -> list[tuple[int, CompareResult]]:
        """
        提取视频帧并与目标帧比对

        Args:
            video_content: 视频内容
            target_frames: 目标帧列表

        Returns:
            list[tuple[int, CompareResult]]: 每帧的比对结果
        """
        video_frames = await self._extract_frames(video_content)
        results = []

        for i, video_frame in enumerate(video_frames):
            best_result = None
            best_similarity = 0.0

            for j, target_frame in enumerate(target_frames):
                result = await self._compare_frames(video_frame, target_frame)
                if result > best_similarity:
                    best_similarity = result
                    best_result = CompareResult(
                        similarity=result,
                        details={
                            "video_frame_index": i,
                            "target_frame_index": j,
                            "timestamp": i * self.frame_interval,
                        },
                    )

            if best_result:
                results.append((i, best_result))

        return results
