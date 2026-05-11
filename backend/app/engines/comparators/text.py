"""
文本比对器

使用 SimHash + LSH 算法进行文本相似度比对
"""
import asyncio
import hashlib
import re
import time
from typing import AsyncIterator

from app.engines.comparators.base import CompareResult, ComparatorBase


class TextComparator(ComparatorBase):
    """
    文本比对器

    使用 SimHash + LSH 算法:
    1. SimHash: 将文本转换为固定长度的哈希值
    2. LSH (Locality Sensitive Hashing): 快速找到相似的哈希值
    """

    name = "text_simhash_lsh"

    def __init__(
        self,
        threshold: float = 0.8,
        hash_length: int = 64,
        fingerprint_size: int = 64,
        **kwargs,
    ):
        """
        初始化文本比对器

        Args:
            threshold: 相似度阈值
            hash_length: SimHash 长度（位数）
            fingerprint_size: 指纹大小
        """
        super().__init__(threshold, **kwargs)
        self.hash_length = hash_length
        self.fingerprint_size = fingerprint_size

        # NLTK 停用词（可选）
        self.stopwords = kwargs.get("stopwords", set())

    async def compare(self, content1: str | bytes, content2: str | bytes) -> CompareResult:
        """
        比对两个文本内容的相似度

        Args:
            content1: 第一个文本
            content2: 第二个文本

        Returns:
            CompareResult: 比对结果
        """
        start_time = time.time()

        # 确保是字符串
        text1 = self._to_text(content1)
        text2 = self._to_text(content2)

        if not text1 or not text2:
            return CompareResult(similarity=0.0, processing_time=time.time() - start_time)

        # 计算 SimHash
        hash1 = await self.compute_hash(text1)
        hash2 = await self.compute_hash(text2)

        # 计算海明距离
        hamming_distance = self._hamming_distance(hash1, hash2)

        # 计算相似度
        max_distance = self.hash_length
        similarity = 1.0 - (hamming_distance / max_distance)

        # 找出匹配的片段
        matched_segments = self._find_matched_segments(text1, text2)

        return CompareResult(
            similarity=similarity,
            details={
                "hash1": hash1,
                "hash2": hash2,
                "hamming_distance": hamming_distance,
                "text1_length": len(text1),
                "text2_length": len(text2),
            },
            matched_segments=matched_segments,
            processing_time=time.time() - start_time,
        )

    async def compute_hash(self, content: str | bytes) -> str:
        """
        计算文本的 SimHash

        Args:
            content: 文本内容

        Returns:
            str: SimHash 值（二进制字符串）
        """
        text = self._to_text(content)
        if not text:
            return "0" * self.hash_length

        # 分词
        tokens = self._tokenize(text)

        # 计算 TF
        tf = self._compute_tf(tokens)

        # 计算 IDF（简化版本）
        idf = self._compute_idf([tokens])

        # 计算每个词的哈希向量
        v = [0] * self.hash_length
        for token, tf_score in tf.items():
            token_hash = self._hash_token(token, self.hash_length)
            idf_score = idf.get(token, 1.0)

            # 加权累加
            weight = tf_score * idf_score
            for i, bit in enumerate(token_hash):
                if bit == "1":
                    v[i] += weight
                else:
                    v[i] -= weight

        # 生成 SimHash
        simhash = "".join("1" if vi > 0 else "0" for vi in v)
        return simhash

    def _to_text(self, content: str | bytes) -> str:
        """转换为字符串"""
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="ignore")
        return content

    def _tokenize(self, text: str) -> list[str]:
        """分词"""
        # 简单的分词：转小写，提取英文单词和中文
        text = text.lower()
        # 提取英文单词
        words = re.findall(r"[a-z]+", text)
        # 提取中文字符
        chinese_chars = re.findall(r"[\u4e00-\u9fff]+", text)
        for chars in chinese_chars:
            words.extend(list(chars))
        return words

    def _compute_tf(self, tokens: list[str]) -> dict[str, float]:
        """计算词频"""
        if not tokens:
            return {}

        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        # 归一化
        max_tf = max(tf.values())
        for token in tf:
            tf[token] = tf[token] / max_tf

        return tf

    def _compute_idf(self, token_lists: list[list[str]]) -> dict[str, float]:
        """计算 IDF（简化版本：假设每个文档只出现一次）"""
        idf = {}
        num_docs = len(token_lists)

        # 统计词频
        doc_freq = {}
        for tokens in token_lists:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        # 计算 IDF
        for token, df in doc_freq.items():
            idf[token] = 1.0 / (1.0 + df / num_docs)

        return idf

    def _hash_token(self, token: str, num_bits: int) -> str:
        """计算词的哈希值"""
        # 使用 MD5 哈希
        md5_hash = hashlib.md5(token.encode("utf-8")).hexdigest()
        # 转换为二进制
        binary = bin(int(md5_hash, 16))[2:].zfill(num_bits)
        return binary[:num_bits]

    def _hamming_distance(self, hash1: str, hash2: str) -> int:
        """计算海明距离"""
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

    def _find_matched_segments(self, text1: str, text2: str) -> list[dict]:
        """找出匹配的片段"""
        # 简化实现：使用滑动窗口找最长公共子串
        segments = []
        window_size = 5  # 最小匹配词数

        words1 = self._tokenize(text1)
        words2 = self._tokenize(text2)

        # 构建 n-gram 索引
        ngrams1 = {}
        for i in range(len(words1) - window_size + 1):
            ngram = " ".join(words1[i:i + window_size])
            if ngram not in ngrams1:
                ngrams1[ngram] = []
            ngrams1[ngram].append(i)

        # 查找匹配
        for i in range(len(words2) - window_size + 1):
            ngram = " ".join(words2[i:i + window_size])
            if ngram in ngrams1:
                for start1 in ngrams1[ngram]:
                    segments.append({
                        "text1_start": start1,
                        "text1_end": start1 + window_size,
                        "text2_start": i,
                        "text2_end": i + window_size,
                        "matched_text": ngram,
                    })
                break

        return segments[:10]  # 最多返回 10 个匹配片段

    async def compare_batch(
        self,
        source_text: str | bytes,
        target_texts: list[str | bytes],
    ) -> list[CompareResult]:
        """批量比对"""
        results = []
        for target in target_texts:
            result = await self.compare(source_text, target)
            results.append(result)
        return results

    async def compare_lsh(
        self,
        source_hash: str,
        target_hashes: list[str],
    ) -> AsyncIterator[tuple[int, CompareResult]]:
        """
        使用 LSH 快速比对多个哈希值

        Args:
            source_hash: 源文本的 SimHash
            target_hashes: 目标文本的 SimHash 列表

        Yields:
            (index, CompareResult): 索引和比对结果
        """
        # 分割成多个 bands
        num_bands = 8
        band_size = self.hash_length // num_bands

        source_bands = [
            source_hash[i * band_size:(i + 1) * band_size]
            for i in range(num_bands)
        ]

        for idx, target_hash in enumerate(target_hashes):
            target_bands = [
                target_hash[i * band_size:(i + 1) * band_size]
                for i in range(num_bands)
            ]

            # 计算相似的 band 数量
            similar_bands = sum(s == t for s, t in zip(source_bands, target_bands))

            # 如果有足够的相似 band，认为可能相似
            if similar_bands >= 2:
                hamming_distance = self._hamming_distance(source_hash, target_hash)
                similarity = 1.0 - (hamming_distance / self.hash_length)

                yield idx, CompareResult(
                    similarity=similarity,
                    details={
                        "similar_bands": similar_bands,
                        "total_bands": num_bands,
                    },
                )
