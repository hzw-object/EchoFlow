# EchoFlow - 实时语音合成系统

一个基于流式 LLM 和 RealtimeTTS 的实时语音合成系统，支持边生成边播放。

## 功能特性

- 🚀 **流式 LLM 处理**：支持 GPT、Qwen、vLLM 等模型
- 🎙️ **实时语音合成**：文本生成后立即转换为语音
- 📡 **WebSocket 通信**：实时音频流传输
- 🎵 **边播边听**：音频流边生成边播放，无需等待

## 系统架构

```
用户输入文字
    ↓
流式 LLM（GPT/Qwen/vLLM）
    ↓ 按 token 逐步输出文本
RealtimeTTS
    ↓ 每生成一小段就推送音频块
WebSocket / HTTP Stream
    ↓
前端接收音频流边播边听
```

## 安装依赖

### 后端依赖

```bash
pip install -r requirements.txt
```

### TTS 模型（可选）

如果需要使用 TTS 库：

```bash
pip install TTS
```

或者使用 Edge-TTS（免费）：

```bash
pip install edge-tts
```

## 配置

### 环境变量

创建 `.env` 文件：

```env
# LLM 配置（选择一种方式）

# 方式1：使用 DeepSeek（推荐）
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# 方式2：使用 OpenAI
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# 方式3：使用 Qwen/vLLM（本地部署）
# LLM_MODEL=qwen
# OPENAI_BASE_URL=http://localhost:8000/v1

# 通用 LLM 参数
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# TTS 配置
TTS_MODEL=tts_models/zh-CN/baker/tacotron2-DDC-GST
TTS_USE_GPU=false
TTS_SAMPLE_RATE=22050
```

## 运行

### 启动后端服务

```bash
cd backend
python server.py
```

服务将在 `http://localhost:8000` 启动。

### 启动前端

使用任意 HTTP 服务器，例如：

```bash
cd frontend
python -m http.server 8080
```

或使用 nginx、Apache 等。

然后在浏览器中访问 `http://localhost:8080`。

## 使用说明

1. 在输入框中输入要转换为语音的文字
2. 点击"发送"按钮
3. 系统会：
   - 通过流式 LLM 逐步生成文本
   - 每生成一小段文本就立即转换为语音
   - 通过 WebSocket 实时推送音频流
   - 前端边接收边播放

## API 接口

### WebSocket 接口

`ws://localhost:8000/ws/chat`

**客户端发送：**
```json
{
  "type": "text",
  "text": "用户输入的文本"
}
```

**服务器返回：**
- 音频数据（二进制 Blob）
- 结束标记：`{"type": "end"}`

### HTTP 接口

`POST /api/chat`

**请求：**
```json
{
  "text": "用户输入的文本"
}
```

**响应：**
- 音频流（audio/mpeg）

## 项目结构

```
EchoFlow/
├── backend/
│   ├── __init__.py
│   ├── server.py          # 主服务器
│   ├── llm_stream.py      # 流式 LLM 接口
│   └── realtime_tts.py    # 实时语音合成
├── frontend/
│   ├── index.html         # 前端页面
│   ├── style.css          # 样式
│   └── app.js             # 前端逻辑
├── requirements.txt       # Python 依赖
└── README.md             # 说明文档
```

## 扩展

### 使用不同的 LLM

#### 使用 DeepSeek（推荐）

在 `backend/.env` 文件中配置：

```env
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-chat
```

系统会自动检测并使用 DeepSeek。

#### 代码中使用 DeepSeek

```python
from llm_stream import DeepSeekStreamer

llm_streamer = DeepSeekStreamer(
    api_key="your-api-key",
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1"
)
```

#### 使用其他 LLM

```python
# 使用 Qwen
llm_streamer = QwenLLMStreamer(base_url="http://localhost:8000/v1")

# 使用 vLLM
llm_streamer = VLLMStreamer(base_url="http://localhost:8000/v1")
```

### 使用不同的 TTS

修改 `backend/realtime_tts.py`：

```python
# 使用 Edge-TTS
tts_engine = EdgeTTSRealtime(voice="zh-CN-XiaoxiaoNeural")
```

## 许可证

MIT License

