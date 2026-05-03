"""
对话管理器 - 整合所有组件实现完整对话功能

整合：
- 角色卡片系统
- 记忆系统
- 情绪感知
- LLM生成
- TTS语音合成
- 高级蒸馏功能
"""
import asyncio
from typing import AsyncIterator, Dict, Optional, List
import logging
import copy

from src.models.character_card import CharacterCard, CharacterCardManager
from src.memory.smart_memory import SmartMemorySystem
from src.emotion.emotion_aware_dialogue import EmotionAwareResponder, EmotionState
from src.llm.llm_router import LLMRouter
from src.llm.context_manager import ContextManager
from src.models.llm_config import LLMConfig
from src.tts.tts_streamer import get_tts_audio, get_tts_format
from src.tts.voice_profile_manager import VoiceProfileManager
from src.config import settings
from src.utils.advanced_person_distiller import AdvancedPersonDistiller, SelfMemory, PersonaLayer
from src.vad.interrupt_handler import VADInterruptException
from src.conversation.conversation_state import ConversationStateMachine, ConversationPhase
from src.memory.knowledge_graph import KnowledgeGraph, MultiKnowledgeGraph

logger = logging.getLogger(__name__)


class DialogueManager:
    """
    对话管理器 - 统一管理所有对话组件
    """

    def __init__(
        self,
        character_name: str = "小云",
        enable_memory: bool = True,
        enable_emotion: bool = True,
        enable_tts: bool = True,
        use_multi_kg: bool = False
    ):
        """
        初始化对话管理器

        Args:
            character_name: 角色名称
            enable_memory: 是否启用记忆系统
            enable_emotion: 是否启用情绪感知
            enable_tts: 是否启用语音合成
        """
        # 1. 加载角色
        self.character_manager = CharacterCardManager()
        self.character_manager.create_default_characters()
        self.character = self.character_manager.get_card(character_name)

        if not self.character:
            raise ValueError(f"Character '{character_name}' not found")

        # 2. 初始化记忆系统
        self.enable_memory = enable_memory
        if enable_memory:
            self.memory = SmartMemorySystem(
                max_short_term_turns=30,
                storage_dir=f"memory/{character_name}",
                auto_save=settings.MEMORY_AUTO_SAVE
            )
            self.memory.load_from_file()
        else:
            self.memory = None

        # 3. Emotion-aware responder (with LLM client for real analysis)
        self.enable_emotion = enable_emotion
        self.emotion_responder = None
        if enable_emotion:
            self.emotion_responder = EmotionAwareResponder(self.character)

        # 4. LLM router
        llm_config = LLMConfig(
            api_key=settings.DEEPSEEK_API_KEY,
            model_name=settings.DEEPSEEK_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE
        )
        context_manager = ContextManager()
        self.llm_router = LLMRouter(config=llm_config, context_manager=context_manager)
        self.llm_router.set_person_profile(self.character)

        # Wire LLM client into emotion responder for LLM-based analysis
        if self.emotion_responder:
            self.emotion_responder.llm_client = self.llm_router.client

        # 5. TTS - 使用统一接口，根据配置自动选择 Edge TTS 或 CosyVoice
        self.enable_tts = enable_tts

        # 6. 声音配置 - 根据角色自动匹配
        self.voice_profile_manager = VoiceProfileManager()
        self.voice_profile = self.voice_profile_manager.get_profile_for_character(character_name)

        # 当前情绪状态
        self.current_emotion: Optional[EmotionState] = None

        # 高级蒸馏器
        self.advanced_distiller = AdvancedPersonDistiller()

        # 7. 对话状态机 — 带快照和回滚
        self.state_machine = ConversationStateMachine()
        # Wire state machine to context manager and memory for rollback
        self.state_machine.context_manager = context_manager
        if self.memory:
            self.state_machine.memory_system = self.memory

        # 8. 知识图谱 — 网状角色知识激活
        self.use_multi_kg = use_multi_kg
        if use_multi_kg:
            self.knowledge_graph = MultiKnowledgeGraph(character_name)
        else:
            self.knowledge_graph = KnowledgeGraph(character_name)

        # 9. 语义记忆 — wire embedding and summarize functions
        if self.memory:
            client = self.llm_router.client

            async def embed_fn(text: str):
                return await client.embed(text)

            async def summarize_fn(prompt: str):
                msgs = [{"role": "user", "content": prompt}]
                try:
                    result = await client.chat_json(msgs, max_tokens=256, temperature=0.3)
                    return result.get("summary", result.get("content", ""))
                except Exception:
                    response = ""
                    async for chunk in client.chat_stream(msgs, max_tokens=256, temperature=0.3):
                        response += chunk
                    return response

            self.memory.set_embed_fn(embed_fn)
            self.memory.set_summarize_fn(summarize_fn)

        logger.info(f"DialogueManager initialized with character: {character_name}, voice: {self.voice_profile.get('name', 'default')}")

    async def chat(
        self,
        user_input: str,
        return_audio: bool = False,
        interrupt_handler=None,
        settings: Optional[Dict] = None
    ) -> AsyncIterator[Dict]:
        """
        处理用户输入并生成回复

        Args:
            user_input: 用户输入
            return_audio: 是否返回音频
            settings: 动态设置 dict（来自前端设置面板），可覆盖 temperature/max_tokens 等

        Yields:
            消息字典 {"type": "text/audio/emotion", "content": ...}
        """
        try:
            # 0. State: input received
            self.state_machine.transition(ConversationPhase.LISTENING)
            self.state_machine.update_topic(user_input)

            # 1. Emotion analysis (LLM-based multi-dimensional weights)
            self.state_machine.transition(ConversationPhase.UNDERSTANDING)
            emotion_context = None
            if self.enable_emotion and self.emotion_responder:
                try:
                    emotion_weights = await self.emotion_responder.analyze_emotion_weights(user_input)
                    # Determine primary emotion from weights
                    primary = max(emotion_weights, key=emotion_weights.get)
                    self.current_emotion = EmotionState(
                        primary_emotion=primary,
                        intensity=max(emotion_weights.values()),
                        secondary_emotions=sorted(
                            [k for k, v in emotion_weights.items() if v > 0.1 and k != primary],
                            key=lambda k: emotion_weights[k], reverse=True
                        )
                    )
                except Exception:
                    # Fallback to keyword
                    self.current_emotion = self.emotion_responder.analyze_user_emotion(user_input)
                    emotion_weights = self.emotion_responder._state_to_weights(self.current_emotion)

                yield {
                    "type": "emotion",
                    "emotion": self.current_emotion.primary_emotion,
                    "intensity": self.current_emotion.intensity,
                    "weights": emotion_weights
                }

                # Lightweight emotion context (NOT replacing system prompt)
                emotion_context = self.emotion_responder.get_emotion_aware_prompt(
                    user_input, self.current_emotion
                )

            # 2. Memory context
            memory_context = None
            if self.enable_memory and self.memory:
                memory_context = await self.memory.get_relevant_context(user_input)

                if memory_context:
                    yield {
                        "type": "memory_context",
                        "content": memory_context[:200] + "..."
                    }

            # 2.5 Knowledge graph activation — 网状角色知识 (支持单/多图谱)
            knowledge_context = None
            if self.knowledge_graph:
                # Sync disabled nodes from settings
                if settings:
                    disabled = settings.get("knowledge", {}).get("disabled_nodes", [])
                    if disabled:
                        self.knowledge_graph.set_disabled_nodes(disabled)
                activated = self.knowledge_graph.activate(user_input)
                if activated:
                    if self.use_multi_kg:
                        knowledge_context = self.knowledge_graph.get_context(activated)
                    else:
                        knowledge_context = self.knowledge_graph.get_context(activated)

            # Combine emotion + memory + knowledge into one context string (capped)
            combined_context = None
            context_parts = []
            if emotion_context:
                context_parts.append(emotion_context)
            if memory_context:
                context_parts.append(memory_context)
            if knowledge_context:
                context_parts.append(knowledge_context)
            if context_parts:
                combined_context = "\n".join(context_parts)
                # Use settings context_chars if available, else default 800
                max_ctx_chars = 800
                if settings:
                    max_ctx_chars = settings.get("memory", {}).get("context_chars", 800)
                if len(combined_context) > max_ctx_chars:
                    combined_context = combined_context[:max_ctx_chars] + "…"

            # 3. LLM streaming generation
            self.state_machine.transition(ConversationPhase.RESPONDING)
            full_response = []

            # Apply settings overrides for temperature / max_tokens
            llm_temperature = None
            llm_max_tokens = None
            if settings:
                char_settings = settings.get("character", {})
                if "temperature" in char_settings:
                    llm_temperature = char_settings["temperature"]
                resp_len = char_settings.get("response_length", "medium")
                len_map = {"short": 300, "medium": 800, "long": 2000}
                llm_max_tokens = len_map.get(resp_len, 800)

            async for chunk in self.llm_router.chat(
                user_input,
                context=combined_context,
                temperature=llm_temperature,
                max_tokens=llm_max_tokens
            ):
                if interrupt_handler and interrupt_handler.is_interrupted():
                    yield {"type": "interrupted"}
                    raise VADInterruptException("User interrupted")

                full_response.append(chunk)

                yield {
                    "type": "text_chunk",
                    "content": chunk,
                    "is_final": False
                }

            # 标记文本完成
            full_text = "".join(full_response)
            yield {
                "type": "text_chunk",
                "content": "",
                "is_final": True
            }

            # 4. TTS语音合成 - 使用角色绑定的声音配置
            if return_audio and self.enable_tts:
                self.state_machine.transition(ConversationPhase.SPEAKING)
                audio_format = get_tts_format()
                voice = self.voice_profile.get("voice") if self.voice_profile else None
                rate = self.voice_profile.get("rate") if self.voice_profile else None
                pitch = self.voice_profile.get("pitch") if self.voice_profile else None
                style = self.voice_profile.get("style") if self.voice_profile else None

                async for audio_chunk in get_tts_audio(full_text, voice=voice, rate=rate, pitch=pitch, style=style):
                    if interrupt_handler and interrupt_handler.is_interrupted():
                        yield {"type": "interrupted"}
                        raise VADInterruptException("User interrupted")

                    yield {
                        "type": "audio",
                        "data": audio_chunk,
                        "format": audio_format,
                        "is_final": False
                    }

                # 标记音频完成
                yield {
                    "type": "audio",
                    "data": b"",
                    "format": audio_format,
                    "is_final": True
                }

            # 5. 存入记忆
            if self.enable_memory and self.memory:
                await self.memory.process_interaction(user_input, full_text)
                # Trigger auto-summary compression as background task
                asyncio.create_task(self._maybe_compress_history())

            # 6. 返回完整回复
            self.state_machine.transition(ConversationPhase.IDLE)
            yield {
                "type": "complete",
                "user_input": user_input,
                "response": full_text,
                "emotion": self.current_emotion.primary_emotion if self.current_emotion else None
            }

        except VADInterruptException:
            # Rollback to last stable state, preserving pending input
            self.state_machine.rollback(pending_input=user_input)
            self.state_machine.clear_interrupt()
            raise  # Re-raise for server to handle
        except Exception as e:
            logger.error(f"Dialogue error: {e}")
            self.state_machine.transition(ConversationPhase.IDLE)
            yield {
                "type": "error",
                "message": str(e)
            }

    async def _maybe_compress_history(self):
        """Compress old conversation turns into summaries when threshold exceeded."""
        if not self.enable_memory or not self.memory:
            return
        if not self.memory._summarize_fn:
            return
        try:
            await self.memory.compress_history(self.memory._summarize_fn)
        except Exception as e:
            logger.warning(f"Background history compression failed: {e}")

    def switch_character(self, character_name: str) -> bool:
        """
        切换角色（同时更新声音配置）

        Args:
            character_name: 新角色名称

        Returns:
            是否成功
        """
        character = self.character_manager.get_card(character_name)
        if not character:
            return False

        self.character = character
        self.llm_router.set_person_profile(character)

        # 重新初始化情绪感知
        if self.enable_emotion:
            self.emotion_responder = EmotionAwareResponder(character)
            if hasattr(self, 'llm_router'):
                self.emotion_responder.llm_client = self.llm_router.client

        # 切换声音配置
        self.voice_profile = self.voice_profile_manager.get_profile_for_character(character_name)

        # 清空记忆（保留旧记忆到文件，新角色新记忆）
        if self.enable_memory and self.memory:
            self.memory.save_all()

        if self.enable_memory:
            self.memory = SmartMemorySystem(
                max_short_term_turns=30,
                storage_dir=f"memory/{character_name}",
                auto_save=settings.MEMORY_AUTO_SAVE
            )
            self.memory.load_from_file()

        logger.info(f"Switched to character: {character_name}, voice: {self.voice_profile.get('name', 'default')}")
        return True

    def get_character_info(self) -> Dict:
        """获取当前角色信息"""
        return {
            "name": self.character.name,
            "description": self.character.description,
            "personality": self.character.personality,
            "tags": self.character.tags
        }

    def save_state(self):
        """保存状态"""
        if self.enable_memory and self.memory:
            self.memory.save_all()

        self.character_manager.save_card(self.character.name)

    def clear_conversation(self):
        """清空当前对话"""
        if self.enable_memory and self.memory:
            self.memory.clear_short_term()

        self.llm_router.reset_context()

    def distill_from_chat_history(
        self,
        chat_messages: List[Dict],
        basic_info: Optional[Dict] = None
    ) -> str:
        """
        从聊天记录蒸馏角色特征

        Args:
            chat_messages: 聊天记录 [{"time": "...", "content": "...", "emotion": "..."}]
            basic_info: 基本信息 {"age": 25, "mbti": "INTJ", "zodiac": "摩羯座"}

        Returns:
            生成的系统提示词
        """
        # 使用高级蒸馏器
        self_memory, persona = self.advanced_distiller.distill_from_chat_history(
            name=self.character.name,
            role=self.character.description,
            chat_messages=chat_messages,
            basic_info=basic_info or {}
        )

        # 生成系统提示词
        system_prompt = self.advanced_distiller.generate_system_prompt(
            self_memory,
            persona
        )

        # 更新LLM的系统提示词
        self.llm_router.context_manager.set_system_prompt(system_prompt)

        # 保存到角色卡片
        self.character.system_prompt = system_prompt
        self.character.custom_fields["self_memory"] = self_memory.to_dict()
        self.character.custom_fields["persona"] = persona.to_dict()

        logger.info(f"Character distilled from {len(chat_messages)} messages")

        return system_prompt


# 使用示例
async def example_dialogue():
    """对话示例"""
    # 创建对话管理器
    dialogue = DialogueManager(
        character_name="小云",
        enable_memory=True,
        enable_emotion=True,
        enable_tts=False  # 示例中不启用TTS
    )

    print("=" * 80)
    print(f"对话系统已启动 - 当前角色: {dialogue.character.name}")
    print("=" * 80)

    # 获取角色信息
    info = dialogue.get_character_info()
    print(f"角色: {info['name']}")
    print(f"描述: {info['description']}")
    print(f"性格: {info['personality']}")
    print("=" * 80)

    # 对话
    user_inputs = [
        "你好",
        "我最近感觉很焦虑",
        "我喜欢打篮球"
    ]

    for user_input in user_inputs:
        print(f"\n用户: {user_input}")
        print(f"{dialogue.character.name}: ", end="", flush=True)

        async for message in dialogue.chat(user_input):
            if message["type"] == "text_chunk" and not message["is_final"]:
                print(message["content"], end="", flush=True)
            elif message["type"] == "emotion":
                print(f"\n[情绪: {message['emotion']}]", end=" ")

        print()

    # 保存状态
    dialogue.save_state()
    print("\n✅ 对话已保存")


if __name__ == "__main__":
    asyncio.run(example_dialogue())
