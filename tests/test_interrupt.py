"""
打断处理器测试
"""
import pytest
import asyncio
from src.vad.interrupt_handler import InterruptHandler, VADInterruptException


@pytest.mark.asyncio
async def test_interrupt_handler_creation():
    """测试打断处理器创建"""
    handler = InterruptHandler()
    assert handler.is_interrupted() is False


@pytest.mark.asyncio
async def test_trigger_interrupt():
    """测试触发打断"""
    handler = InterruptHandler()

    handler.trigger_interrupt()
    assert handler.is_interrupted() is True


@pytest.mark.asyncio
async def test_clear_interrupt():
    """测试清除打断"""
    handler = InterruptHandler()

    handler.trigger_interrupt()
    handler.clear_interrupt()
    assert handler.is_interrupted() is False


@pytest.mark.asyncio
async def test_check_and_raise():
    """测试检查并抛出异常"""
    handler = InterruptHandler()

    # 未打断时不应抛出异常
    await handler.check_and_raise()

    # 打断时应抛出异常
    handler.trigger_interrupt()
    with pytest.raises(VADInterruptException):
        await handler.check_and_raise()


@pytest.mark.asyncio
async def test_with_interrupt_context():
    """测试打断上下文管理器"""
    handler = InterruptHandler()

    async with handler.interrupt_context():
        assert handler.is_interrupted() is False
        # 模拟打断
        handler.trigger_interrupt()

    # 退出上下文后应清除打断
    assert handler.is_interrupted() is False


@pytest.mark.asyncio
async def test_cancel_task():
    """测试取消任务"""
    handler = InterruptHandler()

    # 创建一个长时间运行的任务
    async def long_task():
        await asyncio.sleep(10)

    task = asyncio.create_task(long_task())

    # 取消任务
    await handler.cancel_task(task)

    # 任务应该被取消
    assert task.cancelled() or task.done()
