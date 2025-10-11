"""
音频缓冲队列管理器 - 简单测试（不依赖pytest）
"""

import asyncio
import sys
from datetime import datetime
from audio_buffer_manager import (
    AudioBufferManager,
    SentenceBuffer,
    AudioChunk,
    create_default_buffer,
    create_sentence_buffer
)


async def test_basic_operations():
    """测试基本操作"""
    print("\n测试1: 基本入队和出队...")

    buffer = AudioBufferManager(maxsize=10)

    # 创建测试音频块
    chunk = AudioChunk(
        chunk_id="chunk_001",
        audio_data=b'\x00' * 1000,
        text="测试文本"
    )

    # 入队
    success = await buffer.put(chunk)
    assert success, "入队失败"
    assert buffer.qsize() == 1, f"队列大小错误: {buffer.qsize()}"

    # 出队
    retrieved_chunk = await buffer.get()
    assert retrieved_chunk is not None, "出队失败"
    assert retrieved_chunk.chunk_id == "chunk_001", "块ID不匹配"
    assert buffer.qsize() == 0, "队列应该为空"

    print("✅ 测试1通过")


async def test_fifo_overflow():
    """测试FIFO溢出策略"""
    print("\n测试2: FIFO溢出策略...")

    buffer = AudioBufferManager(maxsize=3)

    # 填满队列
    for i in range(3):
        chunk = AudioChunk(
            chunk_id=f"chunk_{i:03d}",
            audio_data=b'\x00' * 1000,
            text=f"句子{i}"
        )
        await buffer.put(chunk)

    assert buffer.qsize() == 3, "队列应该满了"
    assert buffer.is_full(), "应该检测为满"

    # 再添加一个，应该丢弃最旧的
    new_chunk = AudioChunk(
        chunk_id="chunk_003",
        audio_data=b'\x00' * 1000,
        text="新句子"
    )
    success = await buffer.put(new_chunk)
    assert success, "入队失败"
    assert buffer.qsize() == 3, "队列大小应该保持3"
    assert buffer.dropped_chunks == 1, f"应该丢弃1个块，实际: {buffer.dropped_chunks}"

    # 验证最旧的被丢弃（chunk_000被丢弃，现在应该是chunk_001）
    first_chunk = await buffer.get()
    assert first_chunk.chunk_id == "chunk_001", f"应该是chunk_001，实际: {first_chunk.chunk_id}"

    print("✅ 测试2通过")


async def test_buffered_seconds():
    """测试缓冲时长计算"""
    print("\n测试3: 缓冲时长计算...")

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
    print(f"   缓冲时长: {buffered_seconds:.3f}秒")
    assert abs(buffered_seconds - 1.0) < 0.01, f"缓冲时长计算错误: {buffered_seconds}"

    print("✅ 测试3通过")


async def test_buffer_low_detection():
    """测试缓冲区低水位检测"""
    print("\n测试4: 缓冲区低水位检测...")

    buffer = AudioBufferManager(
        maxsize=10,
        buffer_threshold_seconds=0.5,
        sample_rate=24000
    )

    # 空队列，应该低于阈值
    assert buffer.is_buffer_low(), "空队列应该低于阈值"

    # 添加1秒音频（高于0.5秒阈值）
    chunk = AudioChunk(
        chunk_id="chunk_001",
        audio_data=b'\x00' * 48000,
        text="1秒音频",
        sample_rate=24000
    )
    await buffer.put(chunk)

    # 现在不应该低于阈值
    assert not buffer.is_buffer_low(), "1秒缓冲不应该低于0.5秒阈值"

    print("✅ 测试4通过")


async def test_sentence_buffer():
    """测试句子缓冲管理器"""
    print("\n测试5: 句子缓冲管理器...")

    sentence_buffer = create_sentence_buffer(preload_count=2)

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

    assert sentence_buffer.total_sentences == 1, "句子计数错误"

    # 获取句子
    sentence_meta = await sentence_buffer.get_next_sentence()
    assert sentence_meta is not None, "获取句子失败"
    assert sentence_meta["sentence_id"] == "sentence_001", "句子ID不匹配"
    assert sentence_meta["text"] == "第一句话", "句子文本不匹配"

    print("✅ 测试5通过")


async def test_stats():
    """测试统计信息"""
    print("\n测试6: 统计信息...")

    buffer = AudioBufferManager(maxsize=10)

    # 添加几个音频块
    for i in range(3):
        chunk = AudioChunk(
            chunk_id=f"chunk_{i:03d}",
            audio_data=b'\x00' * 1000,
            text=f"句子{i}"
        )
        await buffer.put(chunk)

    stats = buffer.get_stats()
    print(f"   统计信息: {stats}")

    assert stats["queue_size"] == 3, "队列大小错误"
    assert stats["max_size"] == 10, "最大大小错误"
    assert stats["total_chunks"] == 3, "总块数错误"
    assert stats["is_empty"] == False, "不应该为空"

    print("✅ 测试6通过")


async def test_concurrent_operations():
    """测试并发操作"""
    print("\n测试7: 并发操作...")

    buffer = AudioBufferManager(maxsize=50)

    # 并发添加音频块
    async def add_chunks():
        for i in range(30):
            chunk = AudioChunk(
                chunk_id=f"chunk_{i:03d}",
                audio_data=b'\x00' * 1000,
                text=f"句子{i}"
            )
            await buffer.put(chunk)
            await asyncio.sleep(0.001)  # 模拟间隔

    # 并发获取音频块
    async def get_chunks():
        for _ in range(30):
            await asyncio.sleep(0.002)  # 模拟播放延迟
            chunk = await buffer.get(timeout=1.0)
            if chunk:
                pass  # 成功获取

    # 同时执行
    await asyncio.gather(
        add_chunks(),
        get_chunks()
    )

    print(f"   并发后队列大小: {buffer.qsize()}")
    print("✅ 测试7通过")


async def main():
    """运行所有测试"""
    print("="*50)
    print("开始测试音频缓冲队列管理器")
    print("="*50)

    try:
        await test_basic_operations()
        await test_fifo_overflow()
        await test_buffered_seconds()
        await test_buffer_low_detection()
        await test_sentence_buffer()
        await test_stats()
        await test_concurrent_operations()

        print("\n" + "="*50)
        print("🎉 所有测试通过！")
        print("="*50)
        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
