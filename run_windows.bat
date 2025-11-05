@echo off
chcp 65001 >nul
echo ========================================
echo   EchoFlow Windows 一键启动脚本
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到 Python！请先安装: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查 Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到 Git！请先安装: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM 创建虚拟环境（如果不存在）
if not exist venv (
    echo [1/4] 创建虚拟环境...
    python -m venv venv
    echo ✅ 虚拟环境创建完成
    echo.
)

REM 激活虚拟环境
echo [2/4] 激活虚拟环境...
call venv\Scripts\activate.bat
echo.

REM 安装依赖（如果 requirements.txt 存在）
if exist requirements.txt (
    echo [3/4] 检查并安装依赖...
    pip install -q -r requirements.txt
    echo ✅ 依赖安装完成
    echo.
)

REM 克隆 CosyVoice（如果不存在）
if not exist CosyVoice (
    echo 检测到 CosyVoice 未安装，开始下载...
    echo 这可能需要几分钟（约 11GB）...
    git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
    if %errorlevel% neq 0 (
        echo ❌ CosyVoice 下载失败！
        pause
        exit /b 1
    )
    
    cd CosyVoice
    git lfs install
    git lfs pull
    pip install -q -r requirements.txt
    cd ..
    echo ✅ CosyVoice 安装完成
    echo.
)

REM 创建 .env（如果不存在）
if not exist .env (
    echo 创建配置文件...
    (
        echo TTS_ENGINE=cosyvoice
        echo COSYVOICE_MODEL_DIR=CosyVoice/pretrained_models/CosyVoice-300M-SFT
        echo COSYVOICE_USE_GPU=true
        echo OPENAI_API_KEY=your_api_key_here
        echo LLM_MODEL=gpt-3.5-turbo
    ) > .env
    echo ⚠️  请编辑 .env 文件配置 OPENAI_API_KEY
    echo.
)

REM 启动服务
echo [4/4] 启动服务...
echo.
echo ========================================
echo   🚀 服务启动中...
echo ========================================
echo.
echo 📊 访问地址: http://localhost:8000
echo 💡 按 Ctrl+C 停止服务
echo.

set TTS_ENGINE=cosyvoice
set COSYVOICE_MODEL_DIR=%cd%\CosyVoice\pretrained_models\CosyVoice-300M-SFT
set COSYVOICE_USE_GPU=true
set PYTHONPATH=%cd%\CosyVoice;%cd%

python backend\server.py

echo.
echo 服务已停止
pause

