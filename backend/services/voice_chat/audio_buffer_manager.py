"""
音频缓冲队列管理器

参考py-xiaozhi和RealtimeTTS的实现，提供音频数据的缓冲和管理功能
用于优化音频播放的流畅度，减少句子间的播放延迟

设计原则:
1. 线程安全的异步队列
2. FIFO溢出策略（队列满时丢弃最旧数据）
3. 动态缓冲时长计算
4. 支持预加载机制（为后续优化预留接口）
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """音频数据块"""
    chunk_id: str
    audio_data: bytes
    text: str
    format: str = "pcm"
    sample_rate: int = 24000
    channels: int = 1
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @property
    def size(self) -> int:
        """音频数据大小（字节）"""
        return len(self.audio_data)

    @property
    def duration_seconds(self) -> float:
        """音频时长（秒）"""
        # PCM音频：bytes / (sample_rate * channels * bytes_per_sample)
        # 假设16-bit音频，bytes_per_sample = 2
        if self.format == "pcm":
            return self.size / (self.sample_rate * self.channels * 2)
        return 0.0


class AudioBufferManager:
    """
    音频缓冲队列管理器

    参考py-xiaozhi的实现：
    - 使用asyncio.Queue实现线程安全
    - 队列容量500帧（约10秒音频）
    - FIFO策略：队列满时丢弃最旧数据

    参考RealtimeTTS的实现：
    - 动态计算缓冲时长
    - 支持缓冲阈值检查
    - 提供预加载机制接口
    """

    def __init__(self,
                 maxsize: int = 500,
                 buffer_threshold_seconds: float = 0.5,
                 sample_rate: int = 24000):
        """
        初始化音频缓冲管理器

        Args:
            maxsize: 队列最大容量（帧数），默认500帧
            buffer_threshold_seconds: 缓冲阈值（秒），低于此值触发预加载
            sample_rate: 采样率，默认24kHz
        """
        self.queue = asyncio.Queue(maxsize=maxsize)
        self.maxsize = maxsize
        self.buffer_threshold_seconds = buffer_threshold_seconds
        self.sample_rate = sample_rate

        # 统计信息
        self.total_samples = 0  # 总样本数
        self.total_chunks = 0  # 总块数
        self.dropped_chunks = 0  # 丢弃的块数

        # 线程锁
        self.lock = asyncio.Lock()

        logger.info(f"✅ 音频缓冲管理器已初始化: maxsize={maxsize}, threshold={buffer_threshold_seconds}s")

    async def put(self, chunk: AudioChunk) -> bool:
        """
        安全地将音频块放入队列

        参考py-xiaozhi的_put_audio_data_safe实现：
        - 队列满时，丢弃最旧数据（FIFO）
        - 保证最新的音频数据总能进入队列

        Args:
            chunk: 音频数据块

        Returns:
            bool: 是否成功放入队列
        """
        try:
            # 尝试非阻塞放入
            self.queue.put_nowait(chunk)

            async with self.lock:
                self.total_samples += chunk.size // 2  # 16-bit音频
                self.total_chunks += 1

            logger.debug(f"✅ 音频块已入队: {chunk.chunk_id}, size={chunk.size}B, duration={chunk.duration_seconds:.2f}s")
            return True

        except asyncio.QueueFull:
            # 队列满，使用FIFO策略
            try:
                # 丢弃最旧的数据
                old_chunk = self.queue.get_nowait()

                async with self.lock:
                    self.total_samples -= old_chunk.size // 2
                    self.dropped_chunks += 1

                logger.warning(f"⚠️ 队列已满，丢弃最旧音频块: {old_chunk.chunk_id}")

                # 放入新数据
                self.queue.put_nowait(chunk)

                async with self.lock:
                    self.total_samples += chunk.size // 2
                    self.total_chunks += 1

                return True

            except Exception as e:
                logger.error(f"❌ 入队失败: {e}")
                return False

    async def get(self, timeout: Optional[float] = 0.1) -> Optional[AudioChunk]:
        """
        从队列获取音频块

        Args:
            timeout: 超时时间（秒），None表示一直等待

        Returns:
            AudioChunk: 音频块，如果队列为空且超时则返回None
        """
        try:
            if timeout is None:
                # 一直等待
                chunk = await self.queue.get()
            else:
                # 带超时等待
                chunk = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=timeout
                )

            async with self.lock:
                self.total_samples -= chunk.size // 2

            logger.debug(f"✅ 音频块已出队: {chunk.chunk_id}")
            return chunk

        except asyncio.TimeoutError:
            # 超时，队列为空
            return None
        except Exception as e:
            logger.error(f"❌ 出队失败: {e}")
            return None

    def get_buffered_seconds(self) -> float:
        """
        计算当前缓冲的音频时长（秒）

        参考RealtimeTTS的实现：
        buffered_seconds = total_samples / sample_rate

        Returns:
            float: 缓冲的秒数
        """
        if self.total_samples == 0:
            return 0.0
        return self.total_samples / self.sample_rate

    def is_buffer_low(self) -> bool:
        """
        检查缓冲区是否低于阈值

        用于触发预加载机制

        Returns:
            bool: 缓冲区是否低于阈值
        """
        buffered_seconds = self.get_buffered_seconds()
        is_low = buffered_seconds < self.buffer_threshold_seconds

        if is_low:
            logger.debug(f"⚠️ 缓冲区低于阈值: {buffered_seconds:.2f}s < {self.buffer_threshold_seconds}s")

        return is_low

    def qsize(self) -> int:
        """获取队列当前大小"""
        return self.queue.qsize()

    def is_empty(self) -> bool:
        """检查队列是否为空"""
        return self.queue.empty()

    def is_full(self) -> bool:
        """检查队列是否已满"""
        return self.queue.full()

    def clear(self):
        """清空队列"""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        self.total_samples = 0
        logger.info("🧹 音频缓冲队列已清空")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            Dict: 统计数据
        """
        return {
            "queue_size": self.qsize(),
            "max_size": self.maxsize,
            "buffered_seconds": self.get_buffered_seconds(),
            "threshold_seconds": self.buffer_threshold_seconds,
            "total_chunks": self.total_chunks,
            "dropped_chunks": self.dropped_chunks,
            "is_buffer_low": self.is_buffer_low(),
            "is_full": self.is_full(),
            "is_empty": self.is_empty(),
        }

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"AudioBufferManager("
            f"size={stats['queue_size']}/{stats['max_size']}, "
            f"buffered={stats['buffered_seconds']:.2f}s, "
            f"low={stats['is_buffer_low']})"
        )


class SentenceBuffer:
    """
    句子级别的缓冲管理器

    在AudioBufferManager的基础上，提供句子级别的缓冲管理
    用于支持逐句播放和预加载
    """

    def __init__(self,
                 audio_buffer: AudioBufferManager,
                 preload_count: int = 2):
        """
        初始化句子缓冲管理器

        Args:
            audio_buffer: 底层音频缓冲管理器
            preload_count: 预加载句子数量（为后续优化预留）
        """
        self.audio_buffer = audio_buffer
        self.preload_count = preload_count

        # 句子队列（存储句子级别的元数据）
        self.sentence_queue = asyncio.Queue()

        # 当前播放状态
        self.current_sentence_id: Optional[str] = None
        self.total_sentences = 0

        logger.info(f"✅ 句子缓冲管理器已初始化: preload_count={preload_count}")

    async def add_sentence(self,
                          sentence_id: str,
                          text: str,
                          audio_chunk: AudioChunk):
        """
        添加一个句子到缓冲区

        Args:
            sentence_id: 句子ID
            text: 句子文本
            audio_chunk: 音频数据块
        """
        # 添加到音频缓冲
        await self.audio_buffer.put(audio_chunk)

        # 添加句子元数据
        await self.sentence_queue.put({
            "sentence_id": sentence_id,
            "text": text,
            "chunk_id": audio_chunk.chunk_id,
            "timestamp": datetime.now(),
        })

        self.total_sentences += 1

        logger.info(f"✅ 句子已加入缓冲: {sentence_id} - '{text}'")

    async def get_next_sentence(self) -> Optional[Dict[str, Any]]:
        """
        获取下一个句子

        Returns:
            Dict: 句子元数据，如果没有则返回None
        """
        try:
            sentence_meta = await asyncio.wait_for(
                self.sentence_queue.get(),
                timeout=0.1
            )

            self.current_sentence_id = sentence_meta["sentence_id"]
            return sentence_meta

        except asyncio.TimeoutError:
            return None

    def should_preload(self) -> bool:
        """
        检查是否应该预加载下一句

        判断逻辑：
        1. 音频缓冲区低于阈值
        2. 句子队列未满

        Returns:
            bool: 是否应该预加载
        """
        # 为后续优化预留接口
        should_load = (
            self.audio_buffer.is_buffer_low() and
            self.sentence_queue.qsize() < self.preload_count
        )

        if should_load:
            logger.debug("💡 应该预加载下一句")

        return should_load

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "audio_buffer": self.audio_buffer.get_stats(),
            "sentence_queue_size": self.sentence_queue.qsize(),
            "total_sentences": self.total_sentences,
            "current_sentence_id": self.current_sentence_id,
            "should_preload": self.should_preload(),
        }


# 便捷函数
def create_default_buffer() -> AudioBufferManager:
    """创建默认配置的音频缓冲管理器"""
    return AudioBufferManager(
        maxsize=500,
        buffer_threshold_seconds=0.5,
        sample_rate=24000
    )


def create_sentence_buffer(preload_count: int = 2) -> SentenceBuffer:
    """创建默认配置的句子缓冲管理器"""
    audio_buffer = create_default_buffer()
    return SentenceBuffer(audio_buffer, preload_count)
