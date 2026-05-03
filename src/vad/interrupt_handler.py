"""
打断处理器
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Optional


class VADInterruptException(Exception):
    """VAD 打断异常"""
    pass


class InterruptHandler:
    """打断处理器"""

    def __init__(self):
        """初始化打断处理器"""
        self._interrupted = False
        self._lock = asyncio.Lock()

    def is_interrupted(self) -> bool:
        """
        检查是否被打断

        Returns:
            是否被打断
        """
        return self._interrupted

    def trigger_interrupt(self):
        """触发打断"""
        self._interrupted = True

    def clear_interrupt(self):
        """清除打断状态"""
        self._interrupted = False

    async def check_and_raise(self):
        """
        检查打断状态，如果被打断则抛出异常

        Raises:
            VADInterruptException: 如果被打断
        """
        async with self._lock:
            if self._interrupted:
                raise VADInterruptException("User interrupted")

    @asynccontextmanager
    async def interrupt_context(self):
        """
        打断上下文管理器

        用法:
            async with handler.interrupt_context():
                # 执行任务
                await some_task()
        """
        try:
            self.clear_interrupt()
            yield self
        finally:
            self.clear_interrupt()

    async def cancel_task(self, task: Optional[asyncio.Task]):
        """
        取消任务

        Args:
            task: 要取消的任务
        """
        if task is None or task.done():
            return

        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass
