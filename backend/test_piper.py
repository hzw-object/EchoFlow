#!/usr/bin/env python3
"""测试 piper 导入"""
import sys
print(f"Python 路径: {sys.executable}")
print(f"Python 版本: {sys.version}")

try:
    from piper.voice import PiperVoice
    from piper.config import PiperConfig
    print("✅ piper 模块导入成功")
except ImportError as e:
    print(f"❌ piper 模块导入失败: {e}")
    print(f"Python 路径列表:")
    for p in sys.path:
        print(f"  - {p}")
