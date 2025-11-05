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
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.8"))  # 温度（更高=更随机，推荐 0.7-0.9）
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4000"))  # 最大生成 token 数（支持长文案）
    LLM_SYSTEM_PROMPT: str = os.getenv(
        "LLM_SYSTEM_PROMPT",
        "你是一个专业且友好的AI助手，擅长生成详细、结构清晰的长文案和回答。\n\n"
        "回答风格：\n"
        "- 根据问题需求调整回答长度：简单问题简短回答，复杂问题详细展开\n"
        "- 对于需要详细解释的问题，可以生成较长的文案（500-2000字）\n"
        "- 使用清晰的结构：分段、要点、层次分明\n"
        "- 语言自然流畅，既专业又易懂\n"
        "- 适当使用例子、类比来帮助理解\n\n"
        "长文案生成要点：\n"
        "- 开头简明扼要，点明主题\n"
        "- 中间逐步展开，层次清晰\n"
        "- 结尾总结要点，给出建议\n"
        "- 使用过渡词和连接词，确保连贯性\n"
        "- 避免重复啰嗦，保持信息密度\n\n"
        "语音播报优化：\n"
        "- 句子长度适中（10-30字），避免过长\n"
        "- 适当停顿，使用标点符号（。！？）分隔\n"
        "- 避免使用特殊符号和表情符号\n"
        "- 数字用中文表达（如'三个'而非'3个'）"
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
    
    # CosyVoice 配置（阿里巴巴通义实验室，最佳音质，超低延迟）
    COSYVOICE_MODEL_DIR: str = os.getenv("COSYVOICE_MODEL_DIR", "CosyVoice-300M-SFT")  # 模型目录
    COSYVOICE_USE_GPU: bool = os.getenv("COSYVOICE_USE_GPU", "true").lower() == "true"  # 是否使用 GPU（推荐）
    COSYVOICE_SAMPLE_RATE: int = int(os.getenv("COSYVOICE_SAMPLE_RATE", "22050"))  # 采样率
    COSYVOICE_SPEAKER: str = os.getenv("COSYVOICE_SPEAKER", "中文女")  # 说话人（可选：中文女、中文男等）
    
    # TTS 引擎选择
    TTS_ENGINE: str = os.getenv("TTS_ENGINE", "cosyvoice")  # 可选: "cosyvoice", "edge", "piper", "coqui"


config = Config()

