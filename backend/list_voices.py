"""列出可用的 Edge-TTS 中文语音"""
import asyncio
import edge_tts

async def list_chinese_voices():
    """列出所有中文语音"""
    voices = await edge_tts.list_voices()
    chinese_voices = [v for v in voices if 'zh-CN' in v['Locale']]
    
    print("=" * 60)
    print("可用的中文语音列表（Edge-TTS）")
    print("=" * 60)
    print()
    
    # 按性别分类
    female_voices = [v for v in chinese_voices if v['Gender'] == 'Female']
    male_voices = [v for v in chinese_voices if v['Gender'] == 'Male']
    
    print("🎙️  女声（推荐用于情感表达）：")
    print("-" * 60)
    for v in female_voices:
        name = v.get('ShortName', v.get('Name', 'Unknown'))
        friendly = v.get('FriendlyName', v.get('LocalName', name))
        print(f"  {name:30} - {friendly}")
    
    print()
    print("🎤 男声：")
    print("-" * 60)
    for v in male_voices:
        name = v.get('ShortName', v.get('Name', 'Unknown'))
        friendly = v.get('FriendlyName', v.get('LocalName', name))
        print(f"  {name:30} - {friendly}")
    
    print()
    print("=" * 60)
    print("推荐语音（自然、有情感）：")
    print("  zh-CN-XiaoxiaoNeural     - 晓晓（年轻女声，活泼）")
    print("  zh-CN-XiaoyiNeural       - 晓伊（年轻女声，温柔）")
    print("  zh-CN-XiaohanNeural      - 晓涵（年轻女声，甜美）")
    print("  zh-CN-XiaomoNeural       - 晓墨（年轻女声，知性）")
    print("  zh-CN-XiaoxuanNeural     - 晓萱（年轻女声，活泼）")
    print("  zh-CN-XiaoruiNeural      - 晓睿（年轻女声，温柔）")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(list_chinese_voices())

