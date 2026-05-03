"""
DeepSeek API 客户端 — 支持 Chat + Embeddings
"""
import httpx
import json
import logging
from typing import AsyncIterator, Optional, List, Dict
import asyncio
import hashlib
import time

from src.config import settings

logger = logging.getLogger(__name__)

# Token bucket for rate limiting
class TokenBucket:
    """Simple async token bucket rate limiter."""

    def __init__(self, rate: int = 30, burst: int = 10):
        self.rate = rate          # tokens per minute
        self.burst = burst        # max burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate / 60.0)
            self.last_refill = now
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False

    async def wait_and_acquire(self, timeout: float = 30.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if await self.acquire():
                return True
            await asyncio.sleep(0.5)
        return False


class DeepSeekClient:
    """DeepSeek API 客户端"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        max_tokens: int = 500,
        temperature: float = 0.7
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = httpx.AsyncClient(timeout=60.0)
        self._token_bucket = TokenBucket(rate=30, burst=10)
        self._embedding_cache: Dict[str, List[float]] = {}
        self._embedding_model = "deepseek-chat"  # DeepSeek chat model supports embeddings

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_retries: int = 3
    ) -> AsyncIterator[str]:
        """
        Streaming chat with exponential backoff retry.

        Args:
            messages: Conversation history
            max_tokens: Max tokens
            temperature: Temperature
            max_retries: Retry count (3 max)

        Yields:
            Text chunks
        """
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature or self.temperature,
            "stream": True
        }

        last_error = None
        for attempt in range(max_retries):
            try:
                async with self.client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code == 429:
                        # Rate limited — wait and retry
                        retry_after = 2 ** attempt
                        logger.warning(f"DeepSeek rate limited, retrying in {retry_after}s (attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(retry_after)
                        continue

                    if response.status_code >= 500:
                        # Server error — retry
                        retry_after = 2 ** attempt
                        logger.warning(f"DeepSeek server error {response.status_code}, retrying in {retry_after}s (attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(retry_after)
                        continue

                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"DeepSeek API error: {response.status_code} - {error_text}")
                        raise Exception(f"DeepSeek API error: {response.status_code}")

                    async for line in response.aiter_lines():
                        if not line or line.strip() == "":
                            continue

                        if line.startswith("data: "):
                            data = line[6:]

                            if data == "[DONE]":
                                return

                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")

                                if content:
                                    yield content

                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse chunk: {e}")
                                continue

                    # Successfully streamed — exit retry loop
                    return

            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError,
                    ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    retry_after = 2 ** attempt
                    logger.warning(f"DeepSeek connection error, retrying in {retry_after}s (attempt {attempt+1}/{max_retries}): {e}")
                    await asyncio.sleep(retry_after)
                else:
                    logger.error(f"DeepSeek streaming failed after {max_retries} retries: {e}")
                    raise

            except Exception as e:
                logger.error(f"DeepSeek streaming error: {e}")
                raise

        if last_error:
            raise last_error

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        简化的对话接口

        Args:
            prompt: 用户输入
            system_prompt: 系统提示（可选）

        Yields:
            文本块
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        async for chunk in self.chat_stream(messages):
            yield chunk

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 256,
        temperature: float = 0.3
    ) -> dict:
        """
        Non-streaming JSON response — for structured analysis (emotion, etc.).
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }

        for attempt in range(3):
            try:
                response = await self.client.post(url, headers=headers, json=payload)
                if response.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if response.status_code >= 500:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if response.status_code != 200:
                    raise Exception(f"DeepSeek API error: {response.status_code}")

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                # Try to extract JSON from the response
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[-1].rsplit("\n```", 1)[0]
                return json.loads(content)

            except (json.JSONDecodeError, KeyError) as e:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise Exception(f"Failed to parse JSON from LLM after 3 retries: {e}")
            except (httpx.TimeoutException, httpx.ConnectError,
                    ConnectionError, TimeoutError) as e:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

        return {"neutral": 1.0}

    async def embed(self, text: str) -> List[float]:
        """
        Get embedding vector for a single text. Uses local cache to avoid duplicate API calls.

        Args:
            text: Input text

        Returns:
            Embedding vector (list of floats)
        """
        cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        # Respect rate limit
        if not await self._token_bucket.wait_and_acquire(timeout=10.0):
            logger.warning("Token bucket timeout for embeddings, returning zero vector")
            return [0.0] * 1536

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self._embedding_model,
            "input": text
        }

        for attempt in range(3):
            try:
                response = await self.client.post(url, headers=headers, json=payload)
                if response.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if response.status_code >= 500:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if response.status_code != 200:
                    raise Exception(f"Embeddings API error: {response.status_code}")

                data = response.json()
                embedding = data["data"][0]["embedding"]
                self._embedding_cache[cache_key] = embedding
                # Limit cache size
                if len(self._embedding_cache) > 500:
                    oldest = next(iter(self._embedding_cache))
                    del self._embedding_cache[oldest]
                return embedding

            except (httpx.TimeoutException, httpx.ConnectError,
                    ConnectionError, TimeoutError) as e:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.warning(f"Embeddings failed after 3 retries: {e}")
                    return [0.0] * 1536

        return [0.0] * 1536

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Batch embedding — reuses cache for individual texts.
        Falls back to sequential single-text embeddings if batch endpoint unavailable.
        """
        results = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
            if cache_key in self._embedding_cache:
                results.append(self._embedding_cache[cache_key])
            else:
                results.append(None)  # placeholder
                uncached_texts.append(text)
                uncached_indices.append(i)

        if not uncached_texts:
            return results

        # Try batch endpoint first, fall back to sequential
        for idx, text in zip(uncached_indices, uncached_texts):
            embedding = await self.embed(text)
            results[idx] = embedding

        return results

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

    def __del__(self):
        """析构函数"""
        try:
            asyncio.create_task(self.close())
        except:
            pass