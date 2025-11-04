"""
流式 LLM 接口
支持 GPT/Qwen/vLLM 等模型
"""
import asyncio
import logging
from typing import AsyncGenerator, Optional
import openai
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMStreamer:
    """流式 LLM 文本生成器"""
    
    def __init__(
        self,
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ):
        """
        初始化 LLM 流式生成器
        
        Args:
            model: 模型名称（支持 OpenAI API 或兼容接口）
            api_key: API 密钥
            base_url: API 基础 URL（用于 Qwen/vLLM 等）
            temperature: 温度参数（0.8-0.9 更自然）
            max_tokens: 最大 token 数
            system_prompt: 系统提示词，用于引导模型生成更自然的回答
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        
        # 初始化 OpenAI 客户端（兼容 OpenAI API 格式）
        self.client = AsyncOpenAI(
            api_key=api_key or "dummy-key",
            base_url=base_url or "https://api.openai.com/v1"
        )
        
        logger.info(f"LLMStreamer 初始化完成: model={model}, base_url={base_url}, temperature={temperature}")
    
    def _get_default_system_prompt(self) -> str:
        """获取默认系统提示词（简洁版，降低延迟）"""
        return (
            "用自然、口语化的方式回答，像朋友聊天。"
            "简洁明了，3-5句话，避免书面语。"
            "可以用语气词（嗯、啊）让回答更亲切。"
        )
    
    async def stream(self, user_input: str) -> AsyncGenerator[str, None]:
        """
        流式生成文本
        
        Args:
            user_input: 用户输入的文本
            
        Yields:
            text_chunk: 文本片段
        """
        try:
            # 构建消息，包含系统提示词
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_input}
            ]
            
            # 流式调用 LLM
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            
            # 逐步生成文本，平衡延迟和连贯性
            buffer = ""
            first_chunk = True  # 标记是否为第一个 chunk
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    buffer += content
                    
                    # 优化策略：第一个 chunk 也需要足够的上下文，确保语音连贯
                    # 但不要等待太久，平衡延迟和连贯性
                    if first_chunk and len(buffer) >= 8:  # 从3提高到8，确保有足够上下文
                        # 优先在标点处分割，如果没有则发送
                        has_punctuation = any(p in buffer for p in ['，', ',', '。', '.', '！', '!', '？', '?'])
                        if has_punctuation:
                            # 找到最近的标点分割
                            for punct in ['，', ',', '。', '.', '！', '!', '？', '?']:
                                if punct in buffer:
                                    idx = buffer.rfind(punct) + 1
                                    if idx >= 5:  # 确保至少5个字符
                                        yield buffer[:idx]
                                        buffer = buffer[idx:]
                                        first_chunk = False
                                        break
                            if first_chunk:  # 如果还没发送，继续等待
                                continue
                        else:
                            # 没有标点，但已经有足够字符，发送
                            yield buffer
                            buffer = ""
                            first_chunk = False
                            continue
                    
                    # 智能分割：优先在句子结束处分割，确保语音连贯
                    sentence_endings = ['。', '！', '？', '；', '\n']
                    english_endings = ['. ', '! ', '? ', '.\n', '!\n', '?\n']
                    
                    # 检查是否有句子结束标记（确保句子完整）
                    found_ending = False
                    for ending in sentence_endings:
                        if ending in buffer and len(buffer) >= 5:  # 提高到5，确保有足够上下文
                            # 找到句子结束，在结束处分割
                            idx = buffer.rfind(ending) + len(ending)
                            if idx > 0:
                                yield buffer[:idx]
                                buffer = buffer[idx:]
                                found_ending = True
                                break
                    
                    # 如果没有中文标点，检查英文标点
                    if not found_ending:
                        for ending in english_endings:
                            if ending in buffer and len(buffer) >= 8:  # 提高到8
                                idx = buffer.rfind(ending) + len(ending)
                                if idx > 0:
                                    yield buffer[:idx]
                                    buffer = buffer[idx:]
                                    found_ending = True
                                    break
                    
                    # 如果缓冲区太长且没有找到结束标记，在短语分隔符处分割
                    if not found_ending and len(buffer) >= 30:  # 提高到30，减少分割频率
                        # 优先在逗号、顿号等位置分割（确保短语完整）
                        for separator in ['，', ',', '、', '；', ';']:
                            if separator in buffer[10:]:  # 至少保留10个字符
                                idx = buffer.rfind(separator, 10) + 1
                                if idx > 10:
                                    yield buffer[:idx]
                                    buffer = buffer[idx:]
                                    break
                        else:
                            # 如果找不到合适的分割点，等待更多字符
                            if len(buffer) >= 40:  # 提高到40
                                yield buffer
                                buffer = ""
            
            # 发送剩余的文本
            if buffer:
                yield buffer
                
        except Exception as e:
            logger.error(f"LLM 流式生成错误: {e}")
            # 如果 LLM 调用失败，返回原始输入（用于测试）
            yield user_input
    
    def _split_text_intelligently(self, text: str, min_chunk_size: int = 10) -> list[str]:
        """
        智能分割文本，确保每个片段都是完整的句子
        
        Args:
            text: 待分割的文本
            min_chunk_size: 最小片段大小
            
        Returns:
            文本片段列表
        """
        chunks = []
        current_chunk = ""
        
        # 按句子分割
        sentence_endings = ['。', '！', '？', '.', '!', '?', '\n']
        
        for char in text:
            current_chunk += char
            if char in sentence_endings and len(current_chunk) >= min_chunk_size:
                chunks.append(current_chunk)
                current_chunk = ""
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks


# 示例：使用 Qwen 或 vLLM 的配置
class QwenLLMStreamer(LLMStreamer):
    """Qwen 模型流式生成器"""
    
    def __init__(self, base_url: str = "http://localhost:8000/v1"):
        super().__init__(
            model="qwen",
            base_url=base_url,
            api_key="dummy-key"
        )


class VLLMStreamer(LLMStreamer):
    """vLLM 模型流式生成器"""
    
    def __init__(self, base_url: str = "http://localhost:8000/v1"):
        super().__init__(
            model="vllm-model",
            base_url=base_url,
            api_key="dummy-key"
        )


class DeepSeekStreamer(LLMStreamer):
    """DeepSeek 模型流式生成器"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com/v1",
        temperature: float = 0.8,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ):
        """
        初始化 DeepSeek 流式生成器
        
        Args:
            api_key: DeepSeek API 密钥
            model: 模型名称（deepseek-chat, deepseek-chat-v1 等）
            base_url: API 基础 URL
            temperature: 温度参数（0.8-0.9 更自然）
            max_tokens: 最大 token 数
            system_prompt: 系统提示词
        """
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        )
        logger.info(f"DeepSeek 流式生成器初始化完成: model={model}, temperature={temperature}")

