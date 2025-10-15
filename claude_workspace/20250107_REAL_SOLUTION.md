# 真正的解决方案

## 问题本质

**当前逻辑**：
```python
TEXT1到达 → 创建句子1 (is_complete=False)
AUDIO累积...
TEXT2到达 → 标记句子1完成 (is_complete=True) ← 延迟在这里！
         → 创建句子2 (is_complete=False)
```

**问题**：句子1必须等TEXT2到达才能播放！

---

## 解决方案：收到足够音频就标记完成

**策略**：
- TEXT到达时创建句子（不变）
- AUDIO累积时检查：如果累积了足够长的音频（比如500ms），就标记当前句子完成
- 不等下一个TEXT

**实现**：

```python
def append_audio_chunk(self, audio_data: AudioData):
    # ... 现有解码逻辑不变 ...

    # 🚀 新增：检查当前句子是否已有足够音频可播放
    if self._sentences and not self._sentences[-1]["is_complete"]:
        current_sentence = self._sentences[-1]
        audio_duration = (len(self._pcm_chunks) - current_sentence["start_chunk"]) * 0.04  # 每帧40ms

        # 如果累积了500ms以上音频，标记可播放
        if audio_duration >= 0.5:  # 500ms
            current_sentence["end_chunk"] = len(self._pcm_chunks)
            current_sentence["is_complete"] = True
            logger.info(f"🚀 音频累积足够，标记句子可播放: {audio_duration:.1f}s")
```

**优势**：
- ✅ 不破坏句子创建逻辑（TEXT仍然创建句子）
- ✅ 音频累积到500ms就可以播放
- ✅ 不依赖下一个TEXT
- ✅ 句子边界仍然由TEXT定义（历史记录正确）

**风险**：
- ⚠️ 如果TEXT晚于500ms到达，句子切分可能不准（但概率低）
