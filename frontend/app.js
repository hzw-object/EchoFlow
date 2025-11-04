/**
 * EchoFlow 前端应用
 * 实时语音合成客户端
 */

class EchoFlowClient {
    constructor() {
        this.ws = null;
        this.audioContext = null;
        this.audioQueue = [];
        this.isPlaying = false;
        this.currentSource = null;
        this.audioChunks = [];  // 累积音频块
        
        // DOM 元素
        this.userInput = document.getElementById('user-input');
        this.sendBtn = document.getElementById('send-btn');
        this.stopBtn = document.getElementById('stop-btn');
        this.clearBtn = document.getElementById('clear-btn');
        this.status = document.getElementById('status');
        this.connectionStatus = document.getElementById('connection-status');
        this.statusDot = document.querySelector('.status-dot');
        this.audioPlayer = document.getElementById('audio-player');
        this.audioInfo = document.getElementById('audio-info');
        this.logContainer = document.getElementById('log-container');
        
        // 延迟统计
        this.latencyStats = {
            sendTime: null,
            firstTextTime: null,
            firstAudioTime: null,
            endTime: null
        };
        this.firstTextLatencyEl = document.getElementById('first-text-latency');
        this.firstAudioLatencyEl = document.getElementById('first-audio-latency');
        this.totalLatencyEl = document.getElementById('total-latency');
        
        // 初始化
        this.init();
    }
    
    init() {
        // 初始化音频上下文
        this.initAudioContext();
        
        // 绑定事件
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.stopBtn.addEventListener('click', () => this.stop());
        this.clearBtn.addEventListener('click', () => this.clear());
        
        // Enter 键发送（Shift+Enter 换行）
        this.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // 连接 WebSocket
        this.connect();
    }
    
    initAudioContext() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.log('音频上下文初始化成功', 'info');
        } catch (e) {
            this.log('音频上下文初始化失败: ' + e.message, 'error');
        }
    }
    
    connect() {
        const wsUrl = `ws://${window.location.hostname}:8000/ws/chat`;
        this.log(`正在连接到: ${wsUrl}`, 'info');
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            this.log('WebSocket 连接已建立', 'info');
            this.updateConnectionStatus('connected');
            this.status.textContent = '已连接，等待输入...';
        };
        
        this.ws.onmessage = (event) => {
            if (event.data instanceof Blob) {
                // 累积音频数据块
                this.audioChunks.push(event.data);
            } else if (typeof event.data === 'string') {
                // 接收 JSON 消息
                try {
                    const message = JSON.parse(event.data);
                    if (message.type === 'first_text') {
                        // 计算首字延迟
                        if (this.latencyStats.sendTime) {
                            const clientTimestamp = Date.now();
                            // 使用服务器端计算的延迟（更准确）
                            // 服务器端延迟 = 从服务器收到消息到生成第一个文本块的时间
                            const serverLatency = message.latency || 0;
                            
                            // 客户端总延迟 = 从客户端发送到客户端收到的时间
                            const clientTotalLatency = clientTimestamp - this.latencyStats.sendTime;
                            
                            // 网络延迟 ≈ 客户端总延迟 - 服务器端延迟
                            const networkLatency = clientTotalLatency - serverLatency;
                            
                            // 显示首字延迟（客户端视角：从发送到收到第一个文本块）
                            this.latencyStats.firstTextTime = clientTimestamp;
                            this.updateLatency('first-text', clientTotalLatency);
                            this.log(`首字延迟: ${clientTotalLatency}ms (服务器处理: ${serverLatency}ms, 网络: ${networkLatency}ms)`, 'info');
                        }
                    } else if (message.type === 'end') {
                        // 处理累积的音频块
                        if (this.audioChunks.length > 0) {
                            this.handleAccumulatedAudio();
                            this.audioChunks = [];  // 清空累积的块
                        }
                        
                        // 计算总延迟
                        if (this.latencyStats.sendTime) {
                            this.latencyStats.endTime = Date.now();
                            const totalLatency = this.latencyStats.endTime - this.latencyStats.sendTime;
                            this.updateLatency('total', totalLatency);
                        }
                        
                        this.log('音频流结束', 'info');
                        this.status.textContent = '播放完成';
                        this.sendBtn.disabled = false;
                        this.stopBtn.disabled = true;
                    }
                } catch (e) {
                    this.log('解析消息失败: ' + e.message, 'error');
                }
            }
        };
        
        this.ws.onerror = (error) => {
            this.log('WebSocket 错误: ' + error, 'error');
            this.updateConnectionStatus('error');
        };
        
        this.ws.onclose = () => {
            this.log('WebSocket 连接已关闭', 'warning');
            this.updateConnectionStatus('disconnected');
            
            // 尝试重连
            setTimeout(() => {
                if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
                    this.log('尝试重新连接...', 'info');
                    this.connect();
                }
            }, 3000);
        };
    }
    
    updateConnectionStatus(status) {
        this.statusDot.className = 'status-dot';
        
        switch (status) {
            case 'connected':
                this.statusDot.classList.add('connected');
                this.connectionStatus.querySelector('span:last-child').textContent = '已连接';
                break;
            case 'connecting':
                this.statusDot.classList.add('connecting');
                this.connectionStatus.querySelector('span:last-child').textContent = '连接中...';
                break;
            case 'error':
                this.statusDot.classList.add('error');
                this.connectionStatus.querySelector('span:last-child').textContent = '连接错误';
                break;
            default:
                this.connectionStatus.querySelector('span:last-child').textContent = '未连接';
        }
    }
    
    sendMessage() {
        const text = this.userInput.value.trim();
        
        if (!text) {
            this.log('请输入文字', 'warning');
            return;
        }
        
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            this.log('WebSocket 未连接', 'error');
            this.connect();
            return;
        }
        
        // 记录发送时间
        this.latencyStats.sendTime = Date.now();
        this.latencyStats.firstTextTime = null;
        this.latencyStats.firstAudioTime = null;
        this.latencyStats.endTime = null;
        
        // 清空累积的音频块
        this.audioChunks = [];
        
        // 重置延迟显示
        this.firstTextLatencyEl.textContent = '-';
        this.firstAudioLatencyEl.textContent = '-';
        this.totalLatencyEl.textContent = '-';
        
        // 发送消息
        const message = {
            type: 'text',
            text: text
        };
        
        this.ws.send(JSON.stringify(message));
        
        this.log(`发送: ${text.substring(0, 50)}...`, 'info');
        this.status.textContent = '正在生成音频...';
        this.sendBtn.disabled = true;
        this.stopBtn.disabled = false;
        
        // 清空之前的音频
        this.audioQueue = [];
        this.stopAudio();
    }
    
    async handleAccumulatedAudio() {
        try {
            if (this.audioChunks.length === 0) {
                return;
            }
            
            // 记录首音延迟（第一次收到音频）
            if (!this.latencyStats.firstAudioTime && this.latencyStats.sendTime) {
                this.latencyStats.firstAudioTime = Date.now();
                const firstAudioLatency = this.latencyStats.firstAudioTime - this.latencyStats.sendTime;
                this.updateLatency('first-audio', firstAudioLatency);
                this.log(`首音延迟: ${firstAudioLatency}ms`, 'info');
            }
            
            // 合并所有音频块
            const combinedBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
            const arrayBuffer = await combinedBlob.arrayBuffer();
            
            // 解码音频数据
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
            
            // 播放音频
            this.playAudio(audioBuffer);
            
            // 更新音频信息
            const duration = audioBuffer.duration.toFixed(2);
            const sampleRate = audioBuffer.sampleRate;
            this.audioInfo.textContent = `采样率: ${sampleRate}Hz, 时长: ${duration}s`;
            
        } catch (e) {
            this.log('处理音频数据失败: ' + e.message, 'error');
            console.error('音频解码错误详情:', e);
            
            // 如果解码失败，尝试使用 Audio 元素播放
            if (this.audioChunks.length > 0) {
                const combinedBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                const audioUrl = URL.createObjectURL(combinedBlob);
                this.audioPlayer.src = audioUrl;
            }
        }
    }
    
    async handleAudioData(audioBlob) {
        // 这个方法现在只用于累积，实际处理在 handleAccumulatedAudio
        // 保留以兼容旧代码
    }
    
    updateLatency(type, latencyMs) {
        const latency = Math.round(latencyMs);
        const latencyText = latency < 1000 ? `${latency}ms` : `${(latency / 1000).toFixed(2)}s`;
        
        // 根据延迟设置颜色
        let color = '#4caf50'; // 绿色（快）
        if (latency > 2000) {
            color = '#f44336'; // 红色（慢）
        } else if (latency > 1000) {
            color = '#ff9800'; // 橙色（中等）
        }
        
        switch (type) {
            case 'first-text':
                this.firstTextLatencyEl.textContent = latencyText;
                this.firstTextLatencyEl.style.color = color;
                break;
            case 'first-audio':
                this.firstAudioLatencyEl.textContent = latencyText;
                this.firstAudioLatencyEl.style.color = color;
                break;
            case 'total':
                this.totalLatencyEl.textContent = latencyText;
                this.totalLatencyEl.style.color = color;
                break;
        }
    }
    
    playAudio(audioBuffer) {
        if (!this.audioContext) {
            return;
        }
        
        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.audioContext.destination);
        
        // 如果当前正在播放，将新音频加入队列
        if (this.isPlaying) {
            this.audioQueue.push(source);
        } else {
            this.startPlaying(source);
        }
    }
    
    startPlaying(source) {
        this.isPlaying = true;
        this.currentSource = source;
        
        source.onended = () => {
            this.currentSource = null;
            
            // 播放队列中的下一个音频
            if (this.audioQueue.length > 0) {
                const nextSource = this.audioQueue.shift();
                this.startPlaying(nextSource);
            } else {
                this.isPlaying = false;
            }
        };
        
        source.start(0);
    }
    
    stopAudio() {
        if (this.currentSource) {
            this.currentSource.stop();
            this.currentSource = null;
        }
        
        this.audioQueue = [];
        this.isPlaying = false;
    }
    
    stop() {
        this.stopAudio();
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'close' }));
        }
        
        this.status.textContent = '已停止';
        this.sendBtn.disabled = false;
        this.stopBtn.disabled = true;
        this.log('已停止播放', 'info');
    }
    
    clear() {
        this.userInput.value = '';
        this.stop();
        this.log('已清空', 'info');
    }
    
    log(message, type = 'info') {
        const time = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        logEntry.innerHTML = `<span class="log-time">[${time}]</span>${message}`;
        
        this.logContainer.appendChild(logEntry);
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
        
        // 限制日志条目数量
        while (this.logContainer.children.length > 100) {
            this.logContainer.removeChild(this.logContainer.firstChild);
        }
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new EchoFlowClient();
});

