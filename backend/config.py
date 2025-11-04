"""
配置文件
从环境变量读取配置
"""
import os
from typing import Optional
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Config:
    """应用配置"""
    
    # LLM 配置
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.9"))  # 提高温度，使回答更自然、有变化
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    LLM_SYSTEM_PROMPT: str = os.getenv(
        "LLM_SYSTEM_PROMPT",
        "你是一个真实、自然的朋友，用口语化的方式聊天。"
        "回答要有人情味：可以用'嗯'、'啊'、'哦'等语气词，适当使用'呢'、'吧'、'呀'等助词。"
        "语速自然，3-5句话，避免书面语和官方腔调。"
        "可以适当使用感叹号、问号表达情感，但不要过度。"
        "像真实的人在思考、停顿、组织语言，让对话更自然流畅。"
    )
    
    # DeepSeek 配置（如果使用 DeepSeek）
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    # TTS 配置
    TTS_MODEL: Optional[str] = os.getenv("TTS_MODEL", "tts_models/zh-CN/baker/tacotron2-DDC-GST")
    TTS_USE_GPU: bool = os.getenv("TTS_USE_GPU", "false").lower() == "true"
    TTS_SAMPLE_RATE: int = int(os.getenv("TTS_SAMPLE_RATE", "22050"))
    
    # 服务器配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Edge-TTS 配置（可选）
    EDGE_TTS_VOICE: str = os.getenv("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    EDGE_TTS_RATE: str = os.getenv("EDGE_TTS_RATE", "+5%")  # 语速（默认稍快，更自然）
    EDGE_TTS_PITCH: str = os.getenv("EDGE_TTS_PITCH", "+3Hz")  # 音调（默认稍高，更有活力）
    EDGE_TTS_VOLUME: str = os.getenv("EDGE_TTS_VOLUME", "+0%")  # 音量
    EDGE_TTS_USE_SSML: bool = os.getenv("EDGE_TTS_USE_SSML", "true").lower() == "true"  # 是否启用情感检测
    
    # Piper TTS 配置（本地快速TTS）
    # 如果没有配置，尝试自动查找模型文件
    _default_piper_model = os.path.join(os.path.dirname(__file__), "model", "zh_CN-huayan-medium.onnx")
    _default_piper_model_alt = os.path.join(os.path.dirname(__file__), "models", "zh_CN-huayan-medium.onnx")
    _piper_model_path = os.getenv("PIPER_MODEL_PATH")
    if _piper_model_path is None:
        # 尝试自动查找
        if os.path.exists(_default_piper_model):
            _piper_model_path = "model/zh_CN-huayan-medium.onnx"  # 相对路径
        elif os.path.exists(_default_piper_model_alt):
            _piper_model_path = "models/zh_CN-huayan-medium.onnx"
    PIPER_MODEL_PATH: Optional[str] = _piper_model_path
    PIPER_USE_GPU: bool = os.getenv("PIPER_USE_GPU", "false").lower() == "true"  # 是否使用 GPU
    PIPER_SAMPLE_RATE: int = int(os.getenv("PIPER_SAMPLE_RATE", "22050"))  # 采样率
    
    # TTS 引擎选择
    TTS_ENGINE: str = os.getenv("TTS_ENGINE", "piper")  # 可选: "piper", "edge", "coqui"


config = Config()

