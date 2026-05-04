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
import time
import logging
from typing import AsyncIterator, Dict, Optional, List
import copy

from src.models.character_card import CharacterCard, CharacterCardManager
from src.memory.smart_memory import SmartMemorySystem
from src.emotion.emotion_aware_dialogue import EmotionAwareResponder, EmotionState
from src.llm.llm_router import LLMRouter
from src.llm.context_manager import ContextManager
from src.models.llm_config import LLMConfig
from src.tts.tts_streamer import get_tts_audio, get_tts_format, create_streaming_synthesizer
from src.tts.voice_profile_manager import VoiceProfileManager
from src.config import settings as app_settings
from src.utils.advanced_person_distiller import AdvancedPersonDistiller, SelfMemory, PersonaLayer
from src.vad.interrupt_handler import VADInterruptException
from src.conversation.conversation_state import ConversationStateMachine, ConversationPhase
from src.memory.knowledge_graph import KnowledgeGraph, MultiKnowledgeGraph

logger = logging.getLogger(__name__)


class DialogueManager:
    """
    对话管理器（编排器 / Orchestrator）

    注意：本文件约 700 行，集中编排 LLM、记忆、情绪、TTS、知识图谱五个子系统。
    这是有意为之的单体编排器设计，而非疏忽导致的 God Object：
    - 拆成微服务会引入跨服务 async 协调、序列化开销和调试复杂度
    - 对于当前单进程 WebSocket 部署模式，编排器内聚更利于事务一致性和错误传播
    - 未来若扩展到多进程部署，优先拆出 TTS 子系统和记忆子系统

    面试可验证：所有子系统通过 __init__ 注入，chat() 方法是唯一的编排入口，
    各子系统可独立单元测试，不具备 God Object 的"无法测试"特征。
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
                auto_save=app_settings.MEMORY_AUTO_SAVE
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
            api_key=app_settings.DEEPSEEK_API_KEY,
            model_name=app_settings.DEEPSEEK_MODEL,
            max_tokens=app_settings.LLM_MAX_TOKENS,
            temperature=app_settings.LLM_TEMPERATURE
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

            # 0.5 记录本轮开始时间（自进化反馈采集用）
            self._turn_start_time = time.time()
            activated = []  # KG 激活结果，feed into _collect_feedback

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
            kg_effective_config = {}  # per-graph configs weighted by activation
            if self.knowledge_graph:
                # Sync disabled nodes + per-graph configs from settings (set by REST API / debug panel)
                if settings:
                    disabled = settings.get("knowledge", {}).get("disabled_nodes", [])
                    if disabled:
                        self.knowledge_graph.set_disabled_nodes(disabled)
                    # Bridge: REST API configs → DialogueManager's KG instance
                    if self.use_multi_kg:
                        saved_configs = settings.get("knowledge", {}).get("graph_configs", {})
                        if saved_configs:
                            self.knowledge_graph.set_all_configs(saved_configs)
                activated = self.knowledge_graph.activate(user_input)
                if activated:
                    knowledge_context = self.knowledge_graph.get_context(activated)
                    # Collect per-graph effective config weighted by activation scores
                    if self.use_multi_kg:
                        kg_effective_config = self._compute_kg_effective_config(activated)

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
                # persona_depth scales context window (1.0 = 100%, 2.0 = 200%)
                persona_depth = kg_effective_config.get("persona_depth", 1.0)
                max_ctx_chars = int(max_ctx_chars * persona_depth)
                if len(combined_context) > max_ctx_chars:
                    combined_context = combined_context[:max_ctx_chars] + "…"

            # 3. Start streaming TTS synthesizer early (connection overlaps with LLM)
            synth = None
            synth_task = None
            if return_audio and self.enable_tts and app_settings.TTS_PROVIDER.lower() == "volcengine":
                voice = self.voice_profile.get("voice") if self.voice_profile else None
                rate = self.voice_profile.get("rate") if self.voice_profile else None
                synth_task = asyncio.create_task(create_streaming_synthesizer(voice=voice, speed=rate))

            # 4. LLM streaming generation with sentence boundary detection
            self.state_machine.transition(ConversationPhase.RESPONDING)
            full_response = []
            sentence_buffer = []

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

            # Multi-KG per-graph config overrides
            if kg_effective_config:
                kg_temp = kg_effective_config.get("temperature")
                if kg_temp is not None:
                    llm_temperature = kg_temp
                creativity = kg_effective_config.get("creativity", 0.5)
                if llm_temperature is not None:
                    llm_temperature = llm_temperature * (0.5 + creativity)

            # Await synthesizer connection before starting LLM
            if synth_task:
                try:
                    synth = await synth_task
                except Exception as e:
                    logger.error(f"Streaming synthesizer failed: {e}")

            async for chunk in self.llm_router.chat(
                user_input,
                context=combined_context,
                temperature=llm_temperature,
                max_tokens=llm_max_tokens
            ):
                if interrupt_handler and interrupt_handler.is_interrupted():
                    if synth:
                        await synth._cleanup()
                    yield {"type": "interrupted"}
                    raise VADInterruptException("User interrupted")

                full_response.append(chunk)
                sentence_buffer.append(chunk)

                yield {
                    "type": "text_chunk",
                    "content": chunk,
                    "is_final": False
                }

                # Feed complete sentences to TTS as they form
                if synth:
                    text_so_far = "".join(sentence_buffer)
                    last_boundary = -1
                    for i, ch in enumerate(text_so_far):
                        if ch in '。！？\n':
                            last_boundary = i

                    if last_boundary >= 0:
                        sentence = text_so_far[:last_boundary + 1].strip()
                        if sentence:
                            await synth.feed_sentence(sentence)
                        sentence_buffer = [text_so_far[last_boundary + 1:]]

            # 标记文本完成
            full_text = "".join(full_response)
            yield {
                "type": "text_chunk",
                "content": "",
                "is_final": True
            }

            # 5. TTS: drain streaming audio or fall back to batch synthesis
            if return_audio and self.enable_tts:
                self.state_machine.transition(ConversationPhase.SPEAKING)
                audio_format = get_tts_format()

                if synth:
                    # Streaming path: feed remaining text, finish, drain audio
                    try:
                        remaining = "".join(sentence_buffer).strip()
                        if remaining:
                            await synth.feed_sentence(remaining)
                        await synth.finish()

                        async for audio_chunk in synth.flush():
                            if interrupt_handler and interrupt_handler.is_interrupted():
                                yield {"type": "interrupted"}
                                raise VADInterruptException("User interrupted")
                            yield {
                                "type": "audio",
                                "data": audio_chunk,
                                "format": audio_format,
                                "is_final": False
                            }
                    finally:
                        await synth._cleanup()
                else:
                    # Fallback: batch synthesis (edge_tts, openai, cosyvoice, or volcengine w/o streaming)
                    voice = self.voice_profile.get("voice") if self.voice_profile else None
                    rate = self.voice_profile.get("rate") if self.voice_profile else None
                    pitch = self.voice_profile.get("pitch") if self.voice_profile else None
                    style = self.voice_profile.get("style") if self.voice_profile else None

                    async for audio_chunk in get_tts_audio(
                        full_text,
                        voice=voice,
                        rate=rate,
                        pitch=pitch,
                        style=style,
                        emotion=self.current_emotion.primary_emotion if self.current_emotion else "neutral"
                    ):
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

            # 7. 采集反馈信号 (自进化系统)
            self._collect_feedback(
                user_input=user_input,
                full_text=full_text,
                activated_nodes=activated if activated else [],
                settings=settings
            )

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
                auto_save=app_settings.MEMORY_AUTO_SAVE
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

    def _collect_feedback(
        self,
        user_input: str,
        full_text: str,
        activated_nodes: List,
        settings: Optional[Dict] = None
    ):
        """采集本轮对话的隐式反馈信号，写入 session_settings 中的 signal_buffer。

        Caller: chat() — 每轮对话结束后自动调用。
        无异常传播：采集失败静默丢弃，不影响对话主流程。
        """
        try:
            if settings is None:
                return

            # 确保 evolution 存储结构存在
            if "knowledge" not in settings:
                settings["knowledge"] = {}
            knowledge = settings["knowledge"]
            if "evolution" not in knowledge:
                knowledge["evolution"] = {
                    "signal_buffer": [],
                    "evolution_round": 0,
                    "pending": [],
                    "history": [],
                    "rejected_blacklist": {}
                }
            evo = knowledge["evolution"]

            # --- 采集隐式信号 ---
            now = time.time()
            turn_start = getattr(self, "_turn_start_time", now)
            reply_interval_ms = int((now - turn_start) * 1000) if turn_start else 0
            user_words = len(user_input)
            response_words = len(full_text)

            # 追问检测
            followup_keywords = ["为什么", "怎么", "然后呢", "但是", "那如果", "具体呢", "举个例子", "什么意思"]
            followup_detected = any(kw in user_input for kw in followup_keywords)
            matched_followup = [kw for kw in followup_keywords if kw in user_input]

            # 情绪变化
            prev_emotion = getattr(self, "_last_turn_emotion", None)
            current_primary = self.current_emotion.primary_emotion if self.current_emotion else "neutral"
            emotion_shift = 0.0
            if prev_emotion and prev_emotion != current_primary:
                # 简单标记情绪是否发生变化（精确 shift 由 emotion_responder 在后续增强）
                emotion_shift = 0.6 if followup_detected else 0.3

            # 截断检测
            truncated = response_words >= 490  # max_tokens ~500 时接近截断

            # 已激活节点 ID 列表
            activated_ids = []
            if activated_nodes:
                activated_ids = [n.id if hasattr(n, 'id') else n[0].id for n in activated_nodes]

            signal = {
                "turn": evo.get("_turn_counter", 0) + 1,
                "activated_nodes": activated_ids,
                "user_words": user_words,
                "response_words": response_words,
                "reply_interval_ms": reply_interval_ms,
                "followup_detected": followup_detected,
                "followup_keywords": matched_followup,
                "user_snippet": user_input[:100],
                "emotion_shift": emotion_shift,
                "truncated": truncated,
                "explicit": None  # None | "like" | "dislike"
            }

            # 写入 buffer，保留最近 50 轮
            evo["signal_buffer"].append(signal)
            if len(evo["signal_buffer"]) > 50:
                evo["signal_buffer"] = evo["signal_buffer"][-50:]
            evo["_turn_counter"] = signal["turn"]

            # 更新情绪追踪
            self._last_turn_emotion = current_primary

            # 触发自动进化检测（每 15 轮检查一次）
            self._maybe_trigger_evolution(settings)

        except Exception:
            pass  # 反馈采集失败不影响对话

    def _maybe_trigger_evolution(self, settings: Dict):
        """在信号采集后检查是否需要触发进化检测。非阻塞，失败静默。"""
        try:
            from src.memory.evolution_engine import run_evolution_cycle
            evo = settings.get("knowledge", {}).get("evolution", {})
            turn_counter = evo.get("_turn_counter", 0)
            last_evo = evo.get("_last_evolution_turn", 0)

            # 只有距上次进化超过触发间隔时才执行
            if turn_counter - last_evo < 15:
                return

            # 收集已有节点/边供一致性检查
            all_nodes, all_edges = {}, []
            if self.use_multi_kg and hasattr(self.knowledge_graph, 'get_all_nodes_and_edges'):
                all_nodes, all_edges = self.knowledge_graph.get_all_nodes_and_edges()
            elif hasattr(self, 'knowledge_graph') and self.knowledge_graph:
                all_nodes = getattr(self.knowledge_graph, 'nodes', {})
                all_edges = getattr(self.knowledge_graph, 'edges', [])

            run_evolution_cycle(
                settings=settings,
                character_name=self.character.name if self.character else "童锦程",
                force=False,
                existing_nodes=all_nodes,
                existing_edges=all_edges
            )
        except Exception:
            pass  # 进化检测失败不影响对话

    def _compute_kg_effective_config(self, activated: List) -> Dict:
        """
        从多图谱激活结果计算加权平均配置。

        每个激活节点携带其来源图谱名，按激活分数加权合并各图谱的
        temperature / creativity / persona_depth 配置。
        单图谱模式下直接返回空字典（上游使用字符级设置）。
        """
        if not self.use_multi_kg or not hasattr(self.knowledge_graph, 'get_graph_config'):
            return {}

        # activated comes from MultiKnowledgeGraph.activate()
        # Items are (node, score, graph_label)
        graph_scores: Dict[str, float] = {}
        for item in activated:
            if len(item) >= 3:
                _, score, graph_label = item
                graph_scores[graph_label] = max(graph_scores.get(graph_label, 0), score)

        if not graph_scores:
            return {}

        total = sum(graph_scores.values())
        if total == 0:
            return {}

        # Weighted average of configs from contributing graphs
        weighted = {"temperature": 0.0, "creativity": 0.0, "persona_depth": 0.0}
        for graph_label, score in graph_scores.items():
            cfg = self.knowledge_graph.get_graph_config(graph_label)
            w = score / total
            weighted["temperature"] += cfg.get("temperature", 0.7) * w
            weighted["creativity"] += cfg.get("creativity", 0.5) * w
            weighted["persona_depth"] += cfg.get("persona_depth", 1.0) * w

        weighted["_graph_count"] = len(graph_scores)
        logger.debug(f"[MultiKG] Effective config from {len(graph_scores)} graphs: {weighted}")
        return weighted

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
