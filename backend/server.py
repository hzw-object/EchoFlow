#!/usr/bin/env python3
"""
实时语音合成服务器
支持流式 LLM 和 RealtimeTTS 实时语音合成
"""
import asyncio
import json
import logging
import sys
import os
import time
from typing import AsyncGenerator, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn

# 确保使用正确的 Python 路径
# 如果是在虚拟环境中，确保虚拟环境已激活
if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    # 在虚拟环境中
    pass
else:
    # 不在虚拟环境中，尝试查找并添加虚拟环境路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    venv_path = os.path.join(project_root, 'venv', 'lib', 'python3.9', 'site-packages')
    if os.path.exists(venv_path) and venv_path not in sys.path:
        sys.path.insert(0, venv_path)

# 添加 CosyVoice 和 Matcha-TTS 路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
cosyvoice_path = os.path.join(project_root, 'CosyVoice')
matcha_path = os.path.join(project_root, 'CosyVoice', 'third_party', 'Matcha-TTS')
if os.path.exists(cosyvoice_path) and cosyvoice_path not in sys.path:
    sys.path.insert(0, cosyvoice_path)
if os.path.exists(matcha_path) and matcha_path not in sys.path:
    sys.path.insert(0, matcha_path)

from llm_stream import LLMStreamer, DeepSeekStreamer
from realtime_tts import RealtimeTTS, EdgeTTSRealtime, PiperTTSRealtime, CosyVoiceRealtime
from config import config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EchoFlow - 实时语音合成服务")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化组件
# 如果配置了 DeepSeek API Key，则使用 DeepSeek，否则使用通用配置
if config.DEEPSEEK_API_KEY:
    logger.info("使用 DeepSeek 模型")
    llm_streamer = DeepSeekStreamer(
        api_key=config.DEEPSEEK_API_KEY,
        model=config.DEEPSEEK_MODEL,
        base_url=config.DEEPSEEK_BASE_URL,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
        system_prompt=config.LLM_SYSTEM_PROMPT,
    )
else:
    logger.info("使用通用 LLM 配置")
    llm_streamer = LLMStreamer(
        model=config.LLM_MODEL,
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
        system_prompt=config.LLM_SYSTEM_PROMPT,
    )

# 初始化 TTS 引擎
# 根据配置选择 TTS 引擎：cosyvoice（阿里通义，最佳音质）、edge（云端，音质好）、piper（本地快速）、coqui（本地）
tts_engine = None
tts_engine_name = config.TTS_ENGINE.lower()

if tts_engine_name == "cosyvoice":
    # 使用 CosyVoice（阿里巴巴通义实验室，最佳音质，超低延迟）
    try:
        tts_engine = CosyVoiceRealtime(
            model_dir=config.COSYVOICE_MODEL_DIR,
            sample_rate=config.COSYVOICE_SAMPLE_RATE,
            use_gpu=config.COSYVOICE_USE_GPU,
            speaker=config.COSYVOICE_SPEAKER,
        )
        logger.info(f"✅ CosyVoice 初始化成功: model={config.COSYVOICE_MODEL_DIR}, sample_rate={config.COSYVOICE_SAMPLE_RATE}, gpu={config.COSYVOICE_USE_GPU}, speaker={config.COSYVOICE_SPEAKER}")
    except Exception as e:
        logger.warning(f"CosyVoice 初始化失败: {e}，尝试使用 Edge-TTS")
        import traceback
        logger.debug(f"详细错误: {traceback.format_exc()}")
        tts_engine = None

if tts_engine is None and tts_engine_name == "piper":
    # 使用 Piper TTS（本地快速）
    try:
        tts_engine = PiperTTSRealtime(
            model_path=config.PIPER_MODEL_PATH,
            sample_rate=config.PIPER_SAMPLE_RATE,
            use_gpu=config.PIPER_USE_GPU,
        )
        # 验证初始化是否成功
        if tts_engine.piper_voice is None:
            logger.warning(f"Piper TTS 初始化失败：piper_voice 为 None，尝试使用 Edge-TTS")
            logger.warning(f"模型路径: {config.PIPER_MODEL_PATH}")
            tts_engine = None
        else:
            logger.info(f"✅ Piper TTS 初始化成功: model={config.PIPER_MODEL_PATH}, sample_rate={config.PIPER_SAMPLE_RATE}, gpu={config.PIPER_USE_GPU}")
    except Exception as e:
        logger.warning(f"Piper TTS 初始化失败: {e}，尝试使用 Edge-TTS")
        import traceback
        logger.debug(f"详细错误: {traceback.format_exc()}")
        tts_engine = None

if tts_engine is None and (tts_engine_name == "edge" or tts_engine_name == "piper" or tts_engine_name == "cosyvoice"):
    # 使用 Edge-TTS（云端，免费，无需下载模型）
    try:
        tts_engine = EdgeTTSRealtime(
            voice=config.EDGE_TTS_VOICE,
            rate=config.EDGE_TTS_RATE,
            pitch=config.EDGE_TTS_PITCH,
            volume=config.EDGE_TTS_VOLUME,
            use_ssml=config.EDGE_TTS_USE_SSML,
        )
        logger.info(f"使用 Edge-TTS 进行语音合成: voice={config.EDGE_TTS_VOICE}, rate={config.EDGE_TTS_RATE}, pitch={config.EDGE_TTS_PITCH}")
    except Exception as e:
        logger.warning(f"Edge-TTS 初始化失败: {e}，使用默认 TTS")
        tts_engine = None

if tts_engine is None:
    # 使用 Coqui TTS（默认后备方案）
    try:
        tts_engine = RealtimeTTS(
            model_name=config.TTS_MODEL,
            sample_rate=config.TTS_SAMPLE_RATE,
            use_gpu=config.TTS_USE_GPU,
        )
        logger.info(f"使用 Coqui TTS 进行语音合成: model={config.TTS_MODEL}, sample_rate={config.TTS_SAMPLE_RATE}, gpu={config.TTS_USE_GPU}")
    except Exception as e:
        logger.error(f"所有 TTS 引擎初始化失败: {e}")
        raise


@app.get("/")
async def root():
    """健康检查端点"""
    return {"status": "ok", "message": "EchoFlow 实时语音合成服务运行中"}


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket 端点：实时语音合成
    客户端发送文本，服务器返回音频流
    """
    await websocket.accept()
    logger.info("WebSocket 连接已建立")

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "text":
                user_text = message.get("text", "")
                print(f"\n{'='*80}")
                print(f"📝 收到用户输入: {user_text[:50]}...")
                print(f"{'='*80}\n")
                
                # 记录接收消息的时间（用于计算首字延迟）
                receive_time = int(time.time() * 1000)
                
                # 累积 LLM 生成的完整文本
                llm_full_response = []
                chunk_count = 0
                
                # 流式 LLM 处理（低延迟模式）
                first_text_chunk = True
                try:
                    async for text_chunk in llm_streamer.stream(user_text):
                        if text_chunk:
                            # 累积文本块
                            llm_full_response.append(text_chunk)
                            chunk_count += 1
                            
                            # 记录首字延迟（发送第一个文本块的时间）
                            if first_text_chunk:
                                # 计算首字延迟（从接收消息到生成第一个文本块）
                                first_text_time = int(time.time() * 1000)
                                first_text_latency = first_text_time - receive_time
                                
                                # 发送首字延迟标记（包含服务器端计算的首字延迟）
                                await websocket.send_json({
                                    "type": "first_text",
                                    "timestamp": first_text_time,
                                    "receive_time": receive_time,
                                    "latency": first_text_latency
                                })
                                first_text_chunk = False
                            
                            # RealtimeTTS 生成音频（立即发送，不等待完整句子）
                            audio_chunk_count = 0
                            async for audio_chunk in tts_engine.synthesize_stream(text_chunk):
                                # 立即发送音频数据到客户端（降低延迟）
                                audio_chunk_count += 1
                                await websocket.send_bytes(audio_chunk)
                                logger.debug(f"📤 已发送音频块 #{audio_chunk_count}: {len(audio_chunk)} 字节")
                                # 不添加延迟，让数据流尽快传输
                            
                            if audio_chunk_count > 0:
                                logger.info(f"✅ 文本块合成完成，共发送 {audio_chunk_count} 个音频块")
                
                except Exception as llm_error:
                    print(f"❌ LLM 生成过程中发生错误: {llm_error}")
                    import traceback
                    traceback.print_exc()
                
                # 记录 LLM 完整生成结果（一定要执行，即使有错误）
                full_response_text = "".join(llm_full_response)
                
                print("\n" + "=" * 80)
                print(f"✅ LLM 生成完成")
                print(f"📊 统计信息:")
                print(f"   - 文本块数: {chunk_count}")
                print(f"   - 总字符数: {len(full_response_text)}")
                print(f"   - 总字数: {len(full_response_text.replace(' ', ''))}")
                print(f"👤 用户输入:")
                print(f"   {user_text}")
                print(f"🤖 LLM 完整回复:")
                # 按行显示，更易读
                if len(full_response_text) <= 500:
                    print(f"   {full_response_text}")
                else:
                    print(f"   {full_response_text[:500]}...")
                    print(f"   [... 省略 {len(full_response_text) - 500} 字符 ...]")
                print("=" * 80 + "\n")
                
                # 发送结束标记
                await websocket.send_json({"type": "end"})
                
            elif message.get("type") == "close":
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket 连接已断开")
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        await websocket.close(code=1011, reason=str(e))


@app.post("/api/chat")
async def http_chat(request: dict):
    """
    HTTP 端点：流式语音合成（Server-Sent Events）
    用于不支持 WebSocket 的场景
    """
    user_text = request.get("text", "")
    
    async def generate_audio_stream():
        """生成音频流"""
        try:
            # 流式 LLM 处理
            async for text_chunk in llm_streamer.stream(user_text):
                if text_chunk:
                    # RealtimeTTS 生成音频
                    async for audio_chunk in tts_engine.synthesize_stream(text_chunk):
                        # 将音频数据编码为 base64 或直接发送二进制
                        yield audio_chunk
        except Exception as e:
            logger.error(f"生成音频流错误: {e}")
    
    return StreamingResponse(
        generate_audio_stream(),
        media_type="audio/mpeg",
        headers={
            "Content-Type": "audio/mpeg",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=config.HOST,
        port=config.PORT,
        log_level="info",
        reload=config.DEBUG
    )

