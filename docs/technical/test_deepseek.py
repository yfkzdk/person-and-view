"""
测试 DeepSeek API 配置
"""
import asyncio
import sys
import os

# 设置 UTF-8 编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目路径
sys.path.insert(0, "O:\\AII\\app\\voices")

# 加载环境变量
from dotenv import load_dotenv
load_dotenv("O:\\AII\\app\\voices\\.env")

from src.config import settings
from src.llm.deepseek_client import DeepSeekClient


async def test_deepseek():
    """测试 DeepSeek API"""
    print("="*60)
    print("🧪 测试 DeepSeek API 配置")
    print("="*60)
    print()

    # 检查配置
    print(f"📋 LLM Provider: {settings.LLM_PROVIDER}")
    print(f"🔑 API Key: {settings.DEEPSEEK_API_KEY[:20]}..." if settings.DEEPSEEK_API_KEY else "❌ 未设置")
    print(f"🌐 Base URL: {settings.DEEPSEEK_BASE_URL}")
    print(f"🤖 Model: {settings.DEEPSEEK_MODEL}")
    print()

    # 创建客户端
    client = DeepSeekClient(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        model=settings.DEEPSEEK_MODEL,
        max_tokens=100,
        temperature=0.7
    )

    try:
        print("💬 发送测试消息: 你好，请简单介绍一下你自己")
        print()
        print("📝 响应:")
        print("-" * 60)

        # 流式生成
        full_response = []
        async for chunk in client.chat("你好，请简单介绍一下你自己"):
            print(chunk, end="", flush=True)
            full_response.append(chunk)

        print()
        print("-" * 60)
        print()
        print(f"✅ 测试成功！共生成 {len(''.join(full_response))} 个字符")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_deepseek())