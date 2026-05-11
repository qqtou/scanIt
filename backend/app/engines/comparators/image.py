"""
图片比对器

使用 pHash (Perceptual Hash) + CNN 特征比对
"""
import asyncio
import hashlib
import time
from io import BytesIO

import cv2
import httpx
import numpy as np
from PIL import Image

from app.engines.comparators.base import CompareResult, ComparatorBase


class ImageComparator(ComparatorBase):
    """
    图片比对器

    支持两种比对模式:
    1. pHash: 感知哈希，适合快速比对
    2. CNN: 使用预训练 CNN 模型，适合精确比对
    """

    name = "image_phash_cnn"

    def __init__(
        self,
        threshold: float = 0.85,
        mode: str = "phash",
        **kwargs,
    ):
        """
        初始化图片比对器

        Args:
            threshold: 相似度阈值
            mode: 比对模式 ("phash", "cnn", "hybrid")
            **kwargs: 其他配置参数
        """
        super().__init__(threshold, **kwargs)
        self.mode = mode
        self.hash_size = kwargs.get("hash_size", 8)  # pHash 大小
        self.image_size = kwargs.get("image_size", 224)  # CNN 输入大小

    async def compare(self, content1: str | bytes, content2: str | bytes) -> CompareResult:
        """
        比对两个图片的相似度

        Args:
            content1: 第一个图片（URL、路径或字节数据）
            content2: 第二个图片

        Returns:
            CompareResult: 比对结果
        """
        start_time = time.time()

        try:
            # 加载图片
            img1 = await self._load_image(content1)
            img2 = await self._load_image(content2)

            if img1 is None or img2 is None:
                return CompareResult(
                    similarity=0.0,
                    processing_time=time.time() - start_time,
                )

            # 根据模式选择比对方法
            if self.mode == "phash":
                similarity, details = await self._compare_phash(img1, img2)
            elif self.mode == "cnn":
                similarity, details = await self._compare_cnn(img1, img2)
            else:  # hybrid
                sim1, det1 = await self._compare_phash(img1, img2)
                sim2, det2 = await self._compare_cnn(img1, img2)
                # 加权平均
                similarity = sim1 * 0.4 + sim2 * 0.6
                details = {**det1, **det2}

            return CompareResult(
                similarity=similarity,
                details=details,
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
        计算图片的 pHash

        Args:
            content: 图片内容

        Returns:
            str: pHash 值
        """
        img = await self._load_image(content)
        if img is None:
            return "0" * (self.hash_size * self.hash_size)

        # 计算 pHash
        img_hash = self._compute_phash(img)
        return img_hash

    async def _load_image(self, content: str | bytes) -> np.ndarray | None:
        """加载图片"""
        try:
            if isinstance(content, str):
                # URL 或文件路径
                if content.startswith("http://") or content.startswith("https://"):
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(content)
                        response.raise_for_status()
                        image = Image.open(BytesIO(response.content))
                else:
                    image = Image.open(content)
            else:
                # 字节数据
                image = Image.open(BytesIO(content))

            # 转换为 RGB
            if image.mode != "RGB":
                image = image.convert("RGB")

            # 转换为 numpy 数组
            return np.array(image)

        except Exception:
            return None

    def _compute_phash(self, img: np.ndarray) -> str:
        """
        计算感知哈希 (pHash)

        算法:
        1. 缩小尺寸 (去除高频细节)
        2. 转为灰度
        3. 计算 DCT
        4. 取低频部分
        5. 计算均值
        6. 生成哈希
        """
        # 缩小尺寸
        size = self.hash_size * 4
        img_resized = cv2.resize(img, (size, size), interpolation=cv2.INTER_CUBIC)

        # 转为灰度
        if len(img_resized.shape) == 3:
            gray = cv2.cvtColor(img_resized, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_resized

        # 计算 DCT
        dct = cv2.dct(gray.astype(np.float64))
        dct_cropped = dct[:self.hash_size, :self.hash_size]

        # 计算均值
        mean = dct_cropped.mean()

        # 生成哈希
        hash_str = ""
        for i in range(self.hash_size):
            for j in range(self.hash_size):
                if dct_cropped[i, j] > mean:
                    hash_str += "1"
                else:
                    hash_str += "0"

        return hash_str

    def _hamming_distance(self, hash1: str, hash2: str) -> int:
        """计算海明距离"""
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

    async def _compare_phash(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
    ) -> tuple[float, dict]:
        """使用 pHash 比对"""
        hash1 = self._compute_phash(img1)
        hash2 = self._compute_phash(img2)

        distance = self._hamming_distance(hash1, hash2)
        max_distance = len(hash1)
        similarity = 1.0 - (distance / max_distance)

        return similarity, {
            "hash1": hash1,
            "hash2": hash2,
            "hamming_distance": distance,
            "mode": "phash",
        }

    async def _compare_cnn(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
    ) -> tuple[float, dict]:
        """使用 CNN 特征比对"""
        # 提取特征
        features1 = await self._extract_cnn_features(img1)
        features2 = await self._extract_cnn_features(img2)

        if features1 is None or features2 is None:
            return 0.0, {"error": "Failed to extract CNN features", "mode": "cnn"}

        # 计算余弦相似度
        similarity = self._cosine_similarity(features1, features2)

        return similarity, {
            "features1_norm": float(np.linalg.norm(features1)),
            "features2_norm": float(np.linalg.norm(features2)),
            "mode": "cnn",
        }

    async def _extract_cnn_features(self, img: np.ndarray) -> np.ndarray | None:
        """提取 CNN 特征"""
        try:
            import torch
            import torchvision.transforms as transforms
            from torchvision import models

            # 加载预训练模型（使用 MobileNetV2 轻量级）
            model = models.mobilenet_v2(pretrained=True)
            model.eval()

            # 预处理
            transform = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((self.image_size, self.image_size)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ])

            # 转换图片
            img_tensor = transform(img).unsqueeze(0)

            # 提取特征
            with torch.no_grad():
                features = model.features(img_tensor)
                features = features.mean(dim=[2, 3])  # Global average pooling

            return features.squeeze().numpy()

        except ImportError:
            # 如果没有 torch，使用简单的颜色直方图
            return self._extract_color_histogram(img)
        except Exception:
            return None

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def _extract_color_histogram(self, img: np.ndarray) -> np.ndarray:
        """提取颜色直方图（备用方案）"""
        # 转为灰度
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        else:
            gray = img

        # 计算直方图
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten()
        hist = hist / hist.sum()  # 归一化

        return hist

    async def find_similar_regions(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
    ) -> list[dict]:
        """
        找出两张图片中相似的区域

        Args:
            img1: 第一张图片
            img2: 第二张图片

        Returns:
            list[dict]: 相似区域列表
        """
        regions = []

        # 缩放到相同大小
        size = (256, 256)
        img1_resized = cv2.resize(img1, size, interpolation=cv2.INTER_CUBIC)
        img2_resized = cv2.resize(img2, size, interpolation=cv2.INTER_CUBIC)

        # 转换为灰度
        gray1 = cv2.cvtColor(img1_resized, cv2.COLOR_RGB2GRAY) if len(img1_resized.shape) == 3 else img1_resized
        gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_RGB2GRAY) if len(img2_resized.shape) == 3 else img2_resized

        # 使用 SIFT 特征匹配
        try:
            sift = cv2.SIFT_create()
            kp1, desc1 = sift.detectAndCompute(gray1, None)
            kp2, desc2 = sift.detectAndCompute(gray2, None)

            if desc1 is None or desc2 is None:
                return regions

            # 暴力匹配
            bf = cv2.BFMatcher()
            matches = bf.knnMatch(desc1, desc2, k=2)

            # 应用 Lowe's ratio test
            good_matches = []
            for m, n in matches:
                if m.distance < 0.75 * n.distance:
                    good_matches.append(m)

            # 提取匹配点
            for match in good_matches[:10]:
                pt1 = kp1[match.queryIdx].pt
                pt2 = kp2[match.trainIdx].pt
                regions.append({
                    "x1": int(pt1[0]),
                    "y1": int(pt1[1]),
                    "x2": int(pt2[0]),
                    "y2": int(pt2[1]),
                    "distance": float(match.distance),
                })

        except Exception:
            pass

        return regions
