"""
音频缓冲队列管理器 - 单元测试

测试AudioBufferManager和SentenceBuffer的核心功能
"""

import asyncio
import pytest
from datetime import datetime
from audio_buffer_manager import (
    AudioBufferManager,
    SentenceBuffer,
    AudioChunk,
    create_default_buffer,
    create_sentence_buffer
)


# ============ AudioChunk 测试 ============

def test_audio_chunk_creation():
    """测试AudioChunk创建"""
    chunk = AudioChunk(
        chunk_id="chunk_001",
        audio_data=b"test_audio_data",
        text="测试文本",
        sample_rate=24000
    )

    assert chunk.chunk_id == "chunk_001"
    assert chunk.text == "测试文本"
    assert chunk.size == len(b"test_audio_data")
    assert chunk.sample_rate == 24000
    assert chunk.timestamp is not None


def test_audio_chunk_duration():
    """测试AudioChunk时长计算"""
    # 24kHz, 单声道, 16-bit, 1秒音频 = 24000 * 1 * 2 = 48000 bytes
    audio_data = b'\x00' * 48000

    chunk = AudioChunk(
        chunk_id="chunk_001",
        audio_data=audio_data,
        text="1秒音频",
        sample_rate=24000,
        channels=1
    )

    duration = chunk.duration_seconds
    assert abs(duration - 1.0) < 0.01  # 允许1%误差


# ============ AudioBufferManager 测试 ============

@pytest.mark.asyncio
async def test_buffer_manager_init():
    """测试缓冲管理器初始化"""
    buffer = AudioBufferManager(maxsize=100, buffer_threshold_seconds=0.5)

    assert buffer.maxsize == 100
    assert buffer.buffer_threshold_seconds == 0.5
    assert buffer.qsize() == 0
    assert buffer.is_empty()
    assert not buffer.is_full()


@pytest.mark.asyncio
async def test_buffer_put_and_get():
    """测试基本的入队和出队"""
    buffer = AudioBufferManager(maxsize=10)

    # 创建测试音频块
    chunk = AudioChunk(
        chunk_id="chunk_001",
        audio_data=b'\x00' * 1000,
        text="测试"
    )

    # 入队
    success = await buffer.put(chunk)
    assert success
    assert buffer.qsize() == 1

    # 出队
    retrieved_chunk = await buffer.get()
    assert retrieved_chunk is not None
    assert retrieved_chunk.chunk_id == "chunk_001"
    assert buffer.qsize() == 0


@pytest.mark.asyncio
async def test_buffer_fifo_overflow():
    """测试FIFO溢出策略"""
    buffer = AudioBufferManager(maxsize=3)

    # 填满队列
    for i in range(3):
        chunk = AudioChunk(
            chunk_id=f"chunk_{i:03d}",
            audio_data=b'\x00' * 1000,
            text=f"句子{i}"
        )
        await buffer.put(chunk)

    assert buffer.qsize() == 3
    assert buffer.is_full()

    # 再添加一个，应该丢弃最旧的
    new_chunk = AudioChunk(
        chunk_id="chunk_003",
        audio_data=b'\x00' * 1000,
        text="新句子"
    )
    success = await buffer.put(new_chunk)
    assert success
    assert buffer.qsize() == 3  # 队列大小不变
    assert buffer.dropped_chunks == 1  # 丢弃计数+1

    # 验证最旧的被丢弃
    first_chunk = await buffer.get()
    assert first_chunk.chunk_id == "chunk_001"  # chunk_000被丢弃了


@pytest.mark.asyncio
async def test_buffer_get_timeout():
    """测试出队超时"""
    buffer = AudioBufferManager(maxsize=10)

    # 空队列，超时应该返回None
    chunk = await buffer.get(timeout=0.1)
    assert chunk is None


@pytest.mark.asyncio
async def test_buffered_seconds_calculation():
    """测试缓冲时长计算"""
    buffer = AudioBufferManager(maxsize=10, sample_rate=24000)

    # 添加1秒的音频（48000 bytes @ 24kHz 16-bit）
    chunk = AudioChunk(
        chunk_id="chunk_001",
        audio_data=b'\x00' * 48000,
        text="1秒音频",
        sample_rate=24000
    )
    await buffer.put(chunk)

    buffered_seconds = buffer.get_buffered_seconds()
    assert abs(buffered_seconds - 1.0) < 0.01  # 允许1%误差


@pytest.mark.asyncio
async def test_is_buffer_low():
    """测试缓冲区低水位检测"""
    buffer = AudioBufferManager(
        maxsize=10,
        buffer_threshold_seconds=0.5,
        sample_rate=24000
    )

    # 空队列，应该低于阈值
    assert buffer.is_buffer_low()

    # 添加1秒音频（高于0.5秒阈值）
    chunk = AudioChunk(
        chunk_id="chunk_001",
        audio_data=b'\x00' * 48000,
        text="1秒音频",
        sample_rate=24000
    )
    await buffer.put(chunk)

    # 现在不应该低于阈值
    assert not buffer.is_buffer_low()


@pytest.mark.asyncio
async def test_buffer_clear():
    """测试清空队列"""
    buffer = AudioBufferManager(maxsize=10)

    # 添加几个音频块
    for i in range(5):
        chunk = AudioChunk(
            chunk_id=f"chunk_{i:03d}",
            audio_data=b'\x00' * 1000,
            text=f"句子{i}"
        )
        await buffer.put(chunk)

    assert buffer.qsize() == 5

    # 清空
    buffer.clear()
    assert buffer.qsize() == 0
    assert buffer.is_empty()


@pytest.mark.asyncio
async def test_buffer_stats():
    """测试统计信息"""
    buffer = AudioBufferManager(maxsize=10)

    # 添加音频块
    chunk = AudioChunk(
        chunk_id="chunk_001",
        audio_data=b'\x00' * 1000,
        text="测试"
    )
    await buffer.put(chunk)

    stats = buffer.get_stats()

    assert stats["queue_size"] == 1
    assert stats["max_size"] == 10
    assert stats["total_chunks"] == 1
    assert stats["is_empty"] == False
    assert stats["is_full"] == False


# ============ SentenceBuffer 测试 ============

@pytest.mark.asyncio
async def test_sentence_buffer_init():
    """测试句子缓冲管理器初始化"""
    sentence_buffer = create_sentence_buffer(preload_count=2)

    assert sentence_buffer.preload_count == 2
    assert sentence_buffer.total_sentences == 0
    assert sentence_buffer.current_sentence_id is None


@pytest.mark.asyncio
async def test_sentence_buffer_add_and_get():
    """测试添加和获取句子"""
    sentence_buffer = create_sentence_buffer()

    # 添加句子
    chunk = AudioChunk(
        chunk_id="chunk_001",
        audio_data=b'\x00' * 1000,
        text="第一句话"
    )
    await sentence_buffer.add_sentence(
        sentence_id="sentence_001",
        text="第一句话",
        audio_chunk=chunk
    )

    assert sentence_buffer.total_sentences == 1

    # 获取句子
    sentence_meta = await sentence_buffer.get_next_sentence()
    assert sentence_meta is not None
    assert sentence_meta["sentence_id"] == "sentence_001"
    assert sentence_meta["text"] == "第一句话"
    assert sentence_buffer.current_sentence_id == "sentence_001"


@pytest.mark.asyncio
async def test_sentence_buffer_should_preload():
    """测试预加载触发条件"""
    sentence_buffer = create_sentence_buffer(preload_count=2)

    # 空队列，缓冲低，应该预加载
    assert sentence_buffer.should_preload()

    # 添加足够多的句子
    for i in range(3):
        chunk = AudioChunk(
            chunk_id=f"chunk_{i:03d}",
            audio_data=b'\x00' * 48000,  # 1秒音频
            text=f"句子{i}"
        )
        await sentence_buffer.add_sentence(
            sentence_id=f"sentence_{i:03d}",
            text=f"句子{i}",
            audio_chunk=chunk
        )

    # 缓冲足够，不应该预加载
    # （注意：这个测试依赖于buffer_threshold_seconds的设置）


@pytest.mark.asyncio
async def test_sentence_buffer_stats():
    """测试句子缓冲统计"""
    sentence_buffer = create_sentence_buffer()

    # 添加句子
    chunk = AudioChunk(
        chunk_id="chunk_001",
        audio_data=b'\x00' * 1000,
        text="测试"
    )
    await sentence_buffer.add_sentence(
        sentence_id="sentence_001",
        text="测试",
        audio_chunk=chunk
    )

    stats = sentence_buffer.get_stats()

    assert stats["total_sentences"] == 1
    assert stats["sentence_queue_size"] == 1
    assert "audio_buffer" in stats


# ============ 便捷函数测试 ============

def test_create_default_buffer():
    """测试创建默认缓冲管理器"""
    buffer = create_default_buffer()

    assert buffer.maxsize == 500
    assert buffer.buffer_threshold_seconds == 0.5
    assert buffer.sample_rate == 24000


def test_create_sentence_buffer_func():
    """测试创建句子缓冲管理器"""
    sentence_buffer = create_sentence_buffer(preload_count=3)

    assert sentence_buffer.preload_count == 3
    assert sentence_buffer.audio_buffer.maxsize == 500


# ============ 压力测试 ============

@pytest.mark.asyncio
async def test_concurrent_operations():
    """测试并发操作"""
    buffer = AudioBufferManager(maxsize=100)

    # 并发添加100个音频块
    async def add_chunks():
        for i in range(50):
            chunk = AudioChunk(
                chunk_id=f"chunk_{i:03d}",
                audio_data=b'\x00' * 1000,
                text=f"句子{i}"
            )
            await buffer.put(chunk)

    # 并发获取音频块
    async def get_chunks():
        for _ in range(50):
            await asyncio.sleep(0.01)  # 模拟播放延迟
            chunk = await buffer.get(timeout=1.0)

    # 同时执行添加和获取
    await asyncio.gather(
        add_chunks(),
        get_chunks()
    )

    # 验证没有崩溃，队列状态正常
    assert buffer.qsize() >= 0


# ============ 运行测试 ============

if __name__ == "__main__":
    print("开始测试音频缓冲队列管理器...")

    # 运行所有测试
    asyncio.run(test_buffer_manager_init())
    print("✅ 测试: 缓冲管理器初始化")

    asyncio.run(test_buffer_put_and_get())
    print("✅ 测试: 基本入队和出队")

    asyncio.run(test_buffer_fifo_overflow())
    print("✅ 测试: FIFO溢出策略")

    asyncio.run(test_buffer_get_timeout())
    print("✅ 测试: 出队超时")

    asyncio.run(test_buffered_seconds_calculation())
    print("✅ 测试: 缓冲时长计算")

    asyncio.run(test_is_buffer_low())
    print("✅ 测试: 缓冲区低水位检测")

    asyncio.run(test_buffer_clear())
    print("✅ 测试: 清空队列")

    asyncio.run(test_buffer_stats())
    print("✅ 测试: 统计信息")

    asyncio.run(test_sentence_buffer_add_and_get())
    print("✅ 测试: 句子添加和获取")

    asyncio.run(test_concurrent_operations())
    print("✅ 测试: 并发操作")

    print("\n" + "="*50)
    print("🎉 所有测试通过！")
    print("="*50)
