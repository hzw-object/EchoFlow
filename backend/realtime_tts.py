"""
RealtimeTTS 实时语音合成模块
每生成一小段文本就立即转换为音频
"""
import asyncio
import logging
import io
from typing import AsyncGenerator, Optional
import numpy as np

try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logging.warning("TTS 库未安装，将使用模拟模式")

logger = logging.getLogger(__name__)


class RealtimeTTS:
    """实时语音合成引擎"""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        output_format: str = "wav",
        sample_rate: int = 22050,
        use_gpu: bool = False,
    ):
        """
        初始化 RealtimeTTS
        
        Args:
            model_name: TTS 模型名称（如 "tts_models/zh-CN/baker/tacotron2-DDC-GST"）
            output_format: 输出音频格式（wav, mp3 等）
            sample_rate: 采样率
            use_gpu: 是否使用 GPU
        """
        self.output_format = output_format
        self.sample_rate = sample_rate
        self.use_gpu = use_gpu
        self.tts = None
        
        if TTS_AVAILABLE:
            try:
                # 默认使用中文 TTS 模型
                if model_name is None:
                    model_name = "tts_models/zh-CN/baker/tacotron2-DDC-GST"
                
                self.tts = TTS(model_name=model_name, gpu=use_gpu)
                logger.info(f"RealtimeTTS 初始化完成: model={model_name}")
            except Exception as e:
                logger.error(f"TTS 模型加载失败: {e}，将使用模拟模式")
                self.tts = None
        else:
            logger.warning("TTS 库未安装，使用模拟模式")
    
    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        流式合成语音
        
        Args:
            text: 待合成的文本
            
        Yields:
            audio_chunk: 音频数据块（bytes）
        """
        if not text or not text.strip():
            return
        
        try:
            if self.tts is None:
                # 模拟模式：生成静音音频
                async for chunk in self._generate_silence(len(text)):
                    yield chunk
                return
            
            # 在线程池中执行 TTS（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            
            # 生成音频
            audio_data = await loop.run_in_executor(
                None,
                self._synthesize_sync,
                text
            )
            
            # 将音频数据转换为 WAV 格式并分块发送
            wav_data = self._float32_to_wav(audio_data)
            
            # 分块发送（每块约 2 秒）
            chunk_size = self.sample_rate * 2 * 2  # 16-bit = 2 bytes per sample
            for i in range(0, len(wav_data), chunk_size):
                chunk = wav_data[i:i + chunk_size]
                yield chunk
                
                # 添加小延迟，模拟实时生成
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"TTS 合成错误: {e}")
            # 生成静音作为后备
            async for chunk in self._generate_silence(len(text)):
                yield chunk
    
    def _float32_to_wav(self, audio_data: np.ndarray) -> bytes:
        """
        将 float32 音频数据转换为 WAV 格式
        
        Args:
            audio_data: float32 格式的音频数据
            
        Returns:
            wav_data: WAV 格式的音频数据（bytes）
        """
        import struct
        import wave
        import io
        
        # 转换为 16-bit PCM
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        # 创建 WAV 文件内存对象
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        return wav_buffer.getvalue()
    
    def _synthesize_sync(self, text: str) -> np.ndarray:
        """
        同步合成语音（在后台线程中执行）
        
        Args:
            text: 待合成的文本
            
        Returns:
            audio_data: 音频数据（numpy array）
        """
        try:
            # 使用 TTS 模型生成音频
            wav = self.tts.tts(text=text)
            
            # 确保是 numpy array
            if isinstance(wav, list):
                wav = np.array(wav)
            
            # 归一化到 [-1, 1] 范围
            if wav.dtype != np.float32:
                wav = wav.astype(np.float32)
            
            # 归一化
            if wav.max() > 1.0 or wav.min() < -1.0:
                wav = wav / (np.abs(wav).max() + 1e-8)
            
            return wav
            
        except Exception as e:
            logger.error(f"TTS 同步合成错误: {e}")
            # 返回静音
            return np.zeros(int(self.sample_rate * 0.5), dtype=np.float32)
    
    async def _generate_silence(self, text_length: int) -> AsyncGenerator[bytes, None]:
        """生成静音音频（用于模拟）"""
        # 根据文本长度生成相应时长的静音
        duration = min(text_length * 0.1, 5.0)  # 最多 5 秒
        samples = int(self.sample_rate * duration)
        silence = np.zeros(samples, dtype=np.float32)
        
        # 转换为 WAV 格式
        wav_data = self._float32_to_wav(silence)
        
        # 分块发送
        chunk_size = self.sample_rate * 2 * 2  # 16-bit = 2 bytes per sample
        for i in range(0, len(wav_data), chunk_size):
            chunk = wav_data[i:i + chunk_size]
            yield chunk
            await asyncio.sleep(0.1)


# 使用 Edge-TTS 的替代实现（可选）
class EdgeTTSRealtime(RealtimeTTS):
    """使用 Edge-TTS 的实时语音合成（微软 Edge TTS，免费）"""
    
    def __init__(
        self,
        voice: str = "zh-CN-XiaoxiaoNeural",
        rate: str = "+5%",  # 语速：-50% 到 +100%（默认稍快，更自然）
        pitch: str = "+3Hz",  # 音调：-50Hz 到 +50Hz（默认稍高，更有活力）
        volume: str = "+0%",  # 音量：-50% 到 +100%
        use_ssml: bool = True,  # 是否使用 SSML 增强情感
    ):
        """
        初始化 Edge-TTS
        
        Args:
            voice: 语音名称（推荐：zh-CN-XiaoxiaoNeural, zh-CN-XiaoyiNeural, zh-CN-XiaohanNeural）
            rate: 语速（-50% 到 +100%，例如 "+10%"）
            pitch: 音调（-50Hz 到 +50Hz，例如 "+5Hz"）
            volume: 音量（-50% 到 +100%，例如 "+10%"）
            use_ssml: 是否使用 SSML 标签增强情感表达
        """
        try:
            import edge_tts
            self.edge_tts = edge_tts
            self.voice = voice
            self.rate = rate
            self.pitch = pitch
            self.volume = volume
            self.use_ssml = use_ssml
            self.sample_rate = 24000  # Edge-TTS 默认采样率
            super().__init__()
            logger.info(f"Edge-TTS 初始化完成: voice={voice}, rate={rate}, pitch={pitch}, use_ssml={use_ssml}")
        except ImportError:
            logger.error("edge-tts 未安装，请运行: pip install edge-tts")
            raise
    
    def _detect_emotion_and_adjust_rate(self, text: str) -> str:
        """
        根据文本情感自动调整语速和音调参数
        
        Args:
            text: 原始文本
            
        Returns:
            rate: 调整后的语速参数
        """
        import re
        
        # 兴奋/高兴的词汇 - 稍微加快语速
        excited_patterns = [
            r'！', r'!', r'太好了', r'太棒了', r'真棒', r'太赞',
            r'开心', r'高兴', r'兴奋', r'激动', r'惊喜', r'哇'
        ]
        
        # 疑问/好奇的词汇 - 正常语速
        question_patterns = [
            r'？', r'\?', r'为什么', r'怎么', r'如何', r'什么', r'哪里'
        ]
        
        # 检测情感并调整参数
        if any(re.search(p, text) for p in excited_patterns):
            return "+8%"  # 兴奋时稍微加快
        elif any(re.search(p, text) for p in question_patterns):
            return "+3%"  # 疑问时稍微放慢
        else:
            return "+5%"  # 默认稍快，更自然
    
    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        流式合成语音（Edge-TTS 原生支持流式）
        
        Args:
            text: 待合成的文本
            
        Yields:
            audio_chunk: 音频数据块（bytes）
        """
        if not text or not text.strip():
            return
        
        try:
            import wave
            import io
            
            # 根据文本情感自动调整语速
            dynamic_rate = self._detect_emotion_and_adjust_rate(text) if self.use_ssml else self.rate
            
            # Edge-TTS 原生支持流式输出
            # 使用优化的参数：稍快的语速、稍高的音调，使语音更自然有情感
            communicate = self.edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=dynamic_rate,
                pitch=self.pitch,
                volume=self.volume
            )
            
            # 平衡延迟和连贯性：适当大小的音频块
            first_chunk = True
            wav_header = None
            audio_data = b""
            min_chunk_size = 24000  # 提高到约1秒的音频（24kHz, 16-bit），确保连贯性
            first_chunk_min_size = 8000  # 第一个块至少0.3秒，确保语音连贯
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    if first_chunk:
                        # 第一个块包含 WAV 头
                        wav_header = chunk["data"][:44]  # WAV 头通常是 44 字节
                        first_audio = chunk["data"][44:]  # 音频数据
                        
                        # 第一个音频块：确保有足够大小以保持连贯性
                        if len(first_audio) > 0:
                            if len(first_audio) >= first_chunk_min_size:
                                # 第一个块足够大，发送
                                yield wav_header + first_audio[:first_chunk_min_size]
                                audio_data = first_audio[first_chunk_min_size:]
                            else:
                                # 第一个块较小，累积到最小大小再发送
                                audio_data = first_audio
                                wav_header = wav_header  # 保留头
                                first_chunk = False
                                continue
                        
                        wav_header = None  # 只在第一个块发送头
                        first_chunk = False
                    else:
                        audio_data += chunk["data"]
                    
                    # 当累积足够数据时，分块发送（确保块大小合适）
                    while len(audio_data) >= min_chunk_size:
                        yield audio_data[:min_chunk_size]
                        audio_data = audio_data[min_chunk_size:]
            
            # 发送剩余数据（如果有WAV头，先发送头）
            if audio_data:
                if wav_header:
                    yield wav_header + audio_data
                else:
                    yield audio_data
                    
        except Exception as e:
            logger.error(f"Edge-TTS 合成错误: {e}")
            # 生成静音作为后备
            async for chunk in self._generate_silence(len(text)):
                yield chunk
    
    def _synthesize_sync(self, text: str) -> np.ndarray:
        """使用 Edge-TTS 同步合成（用于兼容性）"""
        import asyncio
        import wave
        import io
        
        async def _async_synthesize():
            communicate = self.edge_tts.Communicate(text, self.voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            # 将 WAV 数据转换为 numpy array
            wav_file = wave.open(io.BytesIO(audio_data))
            frames = wav_file.readframes(wav_file.getnframes())
            audio_array = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            return audio_array
        
        return asyncio.run(_async_synthesize())


# 使用 Piper TTS 的本地实现（快速，本地部署）
class PiperTTSRealtime(RealtimeTTS):
    """使用 Piper TTS 的本地实时语音合成（极速，本地部署）"""
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        sample_rate: int = 22050,
        use_gpu: bool = False,
    ):
        """
        初始化 Piper TTS
        
        Args:
            model_path: Piper 模型文件路径（.onnx 文件，包含 .json 配置文件）
            sample_rate: 采样率（Piper 通常为 22050）
            use_gpu: 是否使用 GPU（需要 onnxruntime-gpu）
        """
        self.sample_rate = sample_rate
        self.use_gpu = use_gpu
        self.model_path = model_path
        self.model = None
        self.config = None
        self.use_piper_command = False
        
        import os
        
        # 如果没有提供模型路径，使用默认路径或尝试自动下载
        if model_path is None:
            # 尝试从环境变量或默认位置获取（支持 models 和 model 目录）
            default_model_1 = os.path.join(os.path.dirname(__file__), "model", "zh_CN-huayan-medium.onnx")
            default_model_2 = os.path.join(os.path.dirname(__file__), "models", "zh_CN-huayan-medium.onnx")
            if os.path.exists(default_model_1):
                model_path = default_model_1
            elif os.path.exists(default_model_2):
                model_path = default_model_2
            else:
                logger.warning(f"未找到 Piper 模型，请下载模型到: {default_model_1} 或 {default_model_2}")
                logger.info("模型下载地址: https://huggingface.co/rhasspy/piper-voices/tree/main/zh/zh_CN/huayan/medium")
                model_path = None
        
        self.model_path = model_path
        self.piper_voice = None
        # 注意：在 __init__ 中不能创建 asyncio.Lock()，因为它需要事件循环
        # 将在首次使用时创建
        self._synthesis_lock = None
        
        # 尝试使用 piper-tts Python 包
        if model_path:
            try:
                from piper.voice import PiperVoice
                from piper.config import PiperConfig
                import onnxruntime as ort
                import json
                import os
                from pathlib import Path
                
                # 保存 ort 引用，以便后续使用
                self.ort = ort
                
                # 处理相对路径：如果路径是相对路径，转换为绝对路径
                if not os.path.isabs(model_path):
                    # 尝试相对于当前文件目录
                    base_dir = os.path.dirname(__file__)
                    abs_model_path = os.path.join(base_dir, model_path)
                    if os.path.exists(abs_model_path):
                        model_path = abs_model_path
                    # 如果还是相对路径且不存在，尝试相对于当前工作目录
                    elif not os.path.exists(model_path):
                        # 保持原路径，让后续代码处理错误
                        pass
                
                # 加载配置文件
                config_path = model_path.replace('.onnx', '.onnx.json')
                if not os.path.exists(config_path):
                    raise FileNotFoundError(f"配置文件未找到: {config_path}，模型路径: {model_path}")
                
                # 确保模型文件存在
                if not os.path.exists(model_path):
                    raise FileNotFoundError(f"模型文件未找到: {model_path}")
                
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
                
                # 创建 PiperConfig
                piper_config = PiperConfig.from_dict(config_dict)
                
                # 设置执行提供者
                # Mac 上使用 CoreMLExecutionProvider，其他平台使用 CUDAExecutionProvider
                # 注意：CoreML 在某些情况下可能导致段错误，如果遇到问题可以禁用
                if use_gpu:
                    # 尝试使用 GPU 加速
                    available_providers = ort.get_available_providers()
                    if 'CUDAExecutionProvider' in available_providers:
                        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                        logger.info("使用 CUDA GPU 加速")
                    elif 'CoreMLExecutionProvider' in available_providers:
                        # Mac 上的 GPU 加速
                        # 警告：CoreML 可能导致段错误，如果遇到问题可以禁用
                        use_coreml = os.getenv("PIPER_USE_COREML", "true").lower() == "true"
                        if use_coreml:
                            providers = ['CoreMLExecutionProvider', 'CPUExecutionProvider']
                            logger.info("使用 CoreML GPU 加速（Mac）")
                        else:
                            providers = ['CPUExecutionProvider']
                            logger.info("CoreML 已禁用（可能不稳定），使用 CPU")
                    else:
                        logger.warning("未找到 GPU 提供者，使用 CPU")
                        providers = ['CPUExecutionProvider']
                else:
                    providers = ['CPUExecutionProvider']
                    logger.debug("使用 CPU 执行")
                
                # 创建 ONNX 会话
                sess_options = ort.SessionOptions()
                sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                session = ort.InferenceSession(
                    model_path,
                    sess_options=sess_options,
                    providers=providers
                )
                
                # 创建 PiperVoice 实例
                self.piper_voice = PiperVoice(session, piper_config)
                
                # 更新采样率
                if hasattr(piper_config, 'sample_rate') and piper_config.sample_rate:
                    self.sample_rate = piper_config.sample_rate
                
                logger.info(f"使用 piper-tts Python 包加载模型: model={model_path}, sample_rate={self.sample_rate}")
                
            except ImportError as e:
                logger.warning(f"piper-tts 包未正确安装: {e}")
                logger.warning("请安装: pip install piper-tts")
                self.piper_voice = None
            except Exception as e:
                logger.error(f"Piper 模型加载失败: {e}")
                import traceback
                logger.debug(f"详细错误信息: {traceback.format_exc()}")
                self.piper_voice = None
        
        super().__init__()
    
    def _load_model(self, model_path: str):
        """加载 Piper ONNX 模型"""
        import json
        import os
        
        # 加载模型配置文件
        config_path = model_path.replace('.onnx', '.onnx.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            logger.warning(f"未找到配置文件: {config_path}，使用默认配置")
            self.config = {
                "audio": {
                    "sample_rate": self.sample_rate
                }
            }
        
        # 设置执行提供者
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if self.use_gpu else ['CPUExecutionProvider']
        
        # 加载 ONNX 模型
        sess_options = self.ort.SessionOptions()
        sess_options.graph_optimization_level = self.ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.model = self.ort.InferenceSession(
            model_path,
            sess_options=sess_options,
            providers=providers
        )
        
        # 更新采样率
        if self.config and 'audio' in self.config:
            self.sample_rate = self.config['audio'].get('sample_rate', self.sample_rate)
    
    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        流式合成语音（Piper 本地快速合成）
        
        Args:
            text: 待合成的文本
            
        Yields:
            audio_chunk: 音频数据块（bytes）
        """
        if not text or not text.strip():
            return
        
        try:
            # 初始化锁（如果还没有）
            if self._synthesis_lock is None:
                self._synthesis_lock = asyncio.Lock()
            
            # 使用锁保护，防止并发访问导致段错误
            async with self._synthesis_lock:
                loop = asyncio.get_event_loop()
                
                # 优先使用 piper-tts Python 包
                if self.piper_voice is not None:
                    logger.debug(f"使用 piper-tts Python 包合成: {text[:50]}")
                    audio_data = await loop.run_in_executor(
                        None,
                        self._synthesize_sync_piper,
                        text
                    )
                elif self.use_piper_command:
                    # 使用 piper 命令（后备方案）
                    logger.debug(f"使用 piper 命令合成: {text[:50]}")
                    audio_data = await loop.run_in_executor(
                        None,
                        self._synthesize_sync_command,
                        text
                    )
                elif self.model is not None:
                    # 使用 ONNX 推理（原始方法，不推荐）
                    logger.debug(f"使用 ONNX 推理合成: {text[:50]}")
                    audio_data = await loop.run_in_executor(
                        None,
                        self._synthesize_sync_onnx,
                        text
                    )
                else:
                    # 如果所有方法都不可用，记录详细信息并抛出异常
                    logger.error(f"Piper TTS 未正确初始化:")
                    logger.error(f"  - piper_voice: {self.piper_voice is not None}")
                    logger.error(f"  - use_piper_command: {self.use_piper_command}")
                    logger.error(f"  - model: {self.model is not None}")
                    logger.error(f"  - model_path: {self.model_path}")
                    raise RuntimeError(
                        f"Piper TTS 未正确初始化。piper_voice={self.piper_voice is not None}, "
                        f"use_piper_command={self.use_piper_command}, model={self.model is not None}. "
                        f"请确保 piper-tts 包已安装：pip install piper-tts"
                    )
                
                # 将音频数据转换为 WAV 格式（在锁内完成）
                wav_data = self._float32_to_wav(audio_data)
            
            # 在锁外发送音频块，避免阻塞
            
            # 分块发送（每块约 0.5-1 秒，降低延迟）
            chunk_size = self.sample_rate * 1 * 2  # 16-bit = 2 bytes per sample, 1秒
            for i in range(0, len(wav_data), chunk_size):
                chunk = wav_data[i:i + chunk_size]
                if chunk:
                    yield chunk
                    # Piper 本地合成很快，不需要额外延迟
                    await asyncio.sleep(0.01)
                    
        except Exception as e:
            logger.error(f"Piper TTS 合成错误: {e}")
            # 生成静音作为后备
            async for chunk in self._generate_silence(len(text)):
                yield chunk
    
    def _synthesize_sync_onnx(self, text: str) -> np.ndarray:
        """
        使用 ONNX 模型同步合成语音
        
        Args:
            text: 待合成的文本
            
        Returns:
            audio_data: 音频数据（numpy array）
        """
        if self.model is None:
            raise ValueError("模型未加载")
        
        # Piper 模型需要文本编码
        # 这里需要根据 Piper 的文本编码方式处理
        # 简化处理：直接使用文本
        try:
            # 获取模型输入输出名称
            input_name = self.model.get_inputs()[0].name
            input_length_name = self.model.get_inputs()[1].name if len(self.model.get_inputs()) > 1 else None
            
            # 文本预处理（简化版，实际需要根据 Piper 的具体要求）
            # Piper 通常需要音素序列，这里简化处理
            text_encoded = self._encode_text(text)
            
            # 准备输入
            inputs = {
                input_name: text_encoded
            }
            if input_length_name:
                inputs[input_length_name] = np.array([len(text_encoded)], dtype=np.int64)
            
            # 推理
            outputs = self.model.run(None, inputs)
            
            # 获取音频输出（通常是第一个输出）
            audio_data = outputs[0]
            
            # 确保是 numpy array 并归一化
            if isinstance(audio_data, list):
                audio_data = np.array(audio_data)
            
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # 归一化到 [-1, 1] 范围
            if audio_data.max() > 1.0 or audio_data.min() < -1.0:
                audio_data = audio_data / (np.abs(audio_data).max() + 1e-8)
            
            # 如果是一维数组，确保是单声道
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            return audio_data
            
        except Exception as e:
            logger.error(f"ONNX 推理错误: {e}")
            # 返回静音
            return np.zeros(int(self.sample_rate * 0.5), dtype=np.float32)
    
    def _encode_text(self, text: str) -> np.ndarray:
        """
        编码文本为模型输入格式
        注意：这是简化版本，实际 Piper 模型可能需要音素序列
        
        Args:
            text: 输入文本
            
        Returns:
            encoded: 编码后的文本数组
        """
        # 简化处理：将文本转换为字符ID
        # 实际 Piper 模型可能需要更复杂的编码
        # 这里使用 UTF-8 编码作为示例
        text_bytes = text.encode('utf-8')
        text_array = np.frombuffer(text_bytes, dtype=np.uint8).astype(np.int64)
        return text_array.reshape(1, -1)  # 添加 batch 维度
    
    def _synthesize_sync_command(self, text: str) -> np.ndarray:
        """
        使用 piper 命令同步合成（后备方案）
        
        Args:
            text: 待合成的文本
            
        Returns:
            audio_data: 音频数据（numpy array）
        """
        import subprocess
        import tempfile
        import os
        
        if self.model_path is None:
            raise ValueError("未指定 Piper 模型路径")
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_wav = tmp_file.name
        
        try:
            # 调用 piper 命令
            cmd = [
                'piper',
                '--model', self.model_path,
                '--output_file', tmp_wav
            ]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate(input=text.encode('utf-8'))
            
            if process.returncode != 0:
                raise RuntimeError(f"Piper 命令执行失败: {stderr.decode()}")
            
            # 读取生成的音频文件
            import wave
            with wave.open(tmp_wav, 'rb') as wav_file:
                frames = wav_file.readframes(wav_file.getnframes())
                audio_array = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            
            return audio_array
            
        finally:
            # 清理临时文件
            if os.path.exists(tmp_wav):
                os.unlink(tmp_wav)
    
    def _preprocess_text_for_natural_speech(self, text: str) -> str:
        """
        预处理文本，使其更适合自然语音合成
        
        Args:
            text: 原始文本
            
        Returns:
            processed_text: 处理后的文本
        """
        import re
        
        # 在标点符号后添加适当停顿（让语音更自然）
        # 句号、问号、感叹号后添加较长停顿
        text = re.sub(r'([。！？])\s*', r'\1，', text)
        # 逗号后添加短暂停顿
        text = re.sub(r'([，、])\s*', r'\1', text)
        
        # 在语气词后添加短暂停顿，让语音更自然
        text = re.sub(r'([嗯啊哦哎])\s*', r'\1，', text)
        
        # 确保问句有适当的语调变化
        text = re.sub(r'([^？])\?', r'\1？', text)
        
        # 处理长句，适当添加停顿
        # 在较长的句子中（超过20字），在合适的位置添加逗号
        def add_pauses(match):
            sentence = match.group(0)
            if len(sentence) > 20:
                # 在"的"、"了"、"呢"等词后适当添加停顿
                sentence = re.sub(r'([的呢了])([^，。！？])', r'\1，\2', sentence, count=1)
            return sentence
        
        # 处理句子内的停顿
        text = re.sub(r'[^，。！？]+', add_pauses, text)
        
        return text
    
    def _synthesize_sync_piper(self, text: str) -> np.ndarray:
        """
        使用 piper-tts Python 包同步合成语音（优化版：更自然）
        
        Args:
            text: 待合成的文本
            
        Returns:
            audio_data: 音频数据（numpy array）
        """
        if self.piper_voice is None:
            raise ValueError("PiperVoice 未初始化")
        
        try:
            # 预处理文本，使其更自然
            processed_text = self._preprocess_text_for_natural_speech(text)
            
            # 使用 PiperVoice 合成语音
            # 注意：Piper 的 synthesize 方法可能支持 SynthesisConfig
            from piper.config import SynthesisConfig
            
            # 创建合成配置，调整参数使语音更自然
            synthesis_config = SynthesisConfig(
                length_scale=1.0,  # 长度缩放（1.0 = 正常速度，>1.0 = 更慢，<1.0 = 更快）
                noise_scale=0.667,  # 噪声缩放（控制音质和自然度）
                noise_w_scale=0.8  # 噪声权重（控制音质和自然度）
            )
            
            # 使用配置合成，添加错误处理
            try:
                audio_chunks = list(self.piper_voice.synthesize(processed_text, syn_config=synthesis_config))
            except Exception as synth_error:
                # 如果合成失败，尝试不使用配置
                logger.warning(f"使用配置合成失败: {synth_error}，尝试默认方法")
                audio_chunks = list(self.piper_voice.synthesize(processed_text))
            
            if not audio_chunks:
                raise ValueError("未生成音频数据")
            
            # 合并所有音频块
            audio_arrays = [chunk.audio_float_array for chunk in audio_chunks]
            audio_data = np.concatenate(audio_arrays)
            
            # 确保是 float32 格式
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # 归一化到 [-1, 1] 范围
            if audio_data.max() > 1.0 or audio_data.min() < -1.0:
                audio_data = audio_data / (np.abs(audio_data).max() + 1e-8)
            
            # 添加轻微的音频处理，使语音更自然
            # 轻微的音量变化（模拟真实说话的音量波动）
            audio_length = len(audio_data)
            if audio_length > 0:
                # 创建一个轻微的音量包络，模拟自然说话
                envelope = np.ones(audio_length, dtype=np.float32)
                # 在开头和结尾添加淡入淡出
                fade_length = min(int(self.sample_rate * 0.01), audio_length // 10)  # 10ms 淡入淡出
                if fade_length > 0:
                    fade_in = np.linspace(0.8, 1.0, fade_length)
                    fade_out = np.linspace(1.0, 0.8, fade_length)
                    envelope[:fade_length] = fade_in
                    envelope[-fade_length:] = fade_out
                    
                    # 应用包络
                    audio_data = audio_data * envelope
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Piper Voice 合成错误: {e}")
            # 返回静音
            return np.zeros(int(self.sample_rate * 0.5), dtype=np.float32)
    
    def _synthesize_sync(self, text: str) -> np.ndarray:
        """同步合成语音（兼容接口）"""
        if self.piper_voice is not None:
            return self._synthesize_sync_piper(text)
        elif self.model is not None:
            return self._synthesize_sync_onnx(text)
        else:
            return self._synthesize_sync_command(text)

