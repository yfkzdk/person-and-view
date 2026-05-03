"""集成测试 - 端到端系统测试"""

import pytest
import torch
import numpy as np
from datetime import datetime
from src.personalization import DeepUserProfiler
from src.skills import MultiRoleSystem
from src.emotion import MultimodalEmotionDetector, EmotionState
from src.reasoning import EnterpriseBehaviorReasoner, UserContext


class TestEndToEndFlow:
    """端到端流程测试"""

    @pytest.fixture
    def profiler(self):
        return DeepUserProfiler()

    @pytest.fixture
    def role_system(self):
        return MultiRoleSystem()

    @pytest.fixture
    def emotion_detector(self):
        return MultimodalEmotionDetector()

    @pytest.fixture
    def reasoner(self):
        return EnterpriseBehaviorReasoner()

    def test_complete_user_interaction_flow(
        self,
        profiler,
        role_system,
        emotion_detector,
        reasoner
    ):
        """测试完整的用户交互流程"""
        # 1. 用户输入
        user_input = "我今天很开心，想听一个有趣的故事"

        # 2. 情绪检测
        emotion = emotion_detector.detect(text=user_input)
        assert isinstance(emotion, EmotionState)
        assert emotion.type in ['joy', 'neutral', 'surprise']

        # 3. 用户画像分析
        profile = profiler.analyze_user_input(user_input)
        assert 'voice_preference' in profile
        assert 'language_style' in profile

        # 4. 角色选择
        role = role_system.select_role(user_input, profile)
        assert role is not None
        assert role.id in ['storyteller', 'mentor', 'companion', 'expert', 'friend']

        # 5. 行为推理
        context = UserContext(
            user_id="test_user",
            current_emotion=emotion.type,
            emotion_intensity=emotion.intensity,
            interaction_history=[{'input': user_input}],
            time_of_day="afternoon",
            day_of_week="Monday",
            session_duration=5.0,
            engagement_level=0.8,
            risk_factors=[]
        )

        pattern = reasoner.analyze_behavior_pattern(context)
        assert pattern is not None

        # 6. 生成推荐
        recommendations = reasoner.generate_recommendations(context, pattern)
        assert len(recommendations) > 0

        # 7. 风险评估
        assessment = reasoner.assess_risk(context, pattern)
        assert assessment is not None

        print(f"\n端到端流程测试结果:")
        print(f"  情绪: {emotion.type} ({emotion.intensity:.2f})")
        print(f"  角色: {role.name}")
        print(f"  行为模式: {pattern.pattern_type}")
        print(f"  推荐数量: {len(recommendations)}")
        print(f"  风险等级: {assessment.risk_level}")

    def test_negative_emotion_flow(
        self,
        profiler,
        role_system,
        emotion_detector,
        reasoner
    ):
        """测试负面情绪处理流程"""
        user_input = "我很伤心，感觉什么都不顺利"

        # 情绪检测
        emotion = emotion_detector.detect(text=user_input)
        assert emotion.type in ['sadness', 'fear', 'anger']

        # 角色选择（应该选择支持性角色）
        profile = profiler.analyze_user_input(user_input)
        role = role_system.select_role(user_input, profile)

        # 行为推理
        context = UserContext(
            user_id="sad_user",
            current_emotion=emotion.type,
            emotion_intensity=emotion.intensity,
            interaction_history=[{'input': user_input}],
            time_of_day="evening",
            day_of_week="Friday",
            session_duration=2.0,
            engagement_level=0.3,
            risk_factors=["negative_mood"]
        )

        pattern = reasoner.analyze_behavior_pattern(context)
        assessment = reasoner.assess_risk(context, pattern)

        # 负面情绪应该触发更高的风险关注
        print(f"\n负面情绪流程测试:")
        print(f"  情绪: {emotion.type} ({emotion.intensity:.2f})")
        print(f"  风险等级: {assessment.risk_level}")
        print(f"  需要干预: {assessment.requires_intervention}")

    def test_multi_turn_conversation(
        self,
        profiler,
        role_system,
        emotion_detector,
        reasoner
    ):
        """测试多轮对话流程"""
        conversation = [
            "你好，我想聊聊天",
            "今天过得怎么样？",
            "我很开心，因为今天完成了一个重要项目",
            "能给我讲个故事吗？",
            "太棒了，我很喜欢这个故事！"
        ]

        emotions = []
        roles = []
        patterns = []

        for user_input in conversation:
            # 情绪检测
            emotion = emotion_detector.detect(text=user_input)
            emotions.append(emotion)

            # 用户画像更新
            profile = profiler.analyze_user_input(user_input)

            # 角色选择
            role = role_system.select_role(user_input, profile)
            roles.append(role)

            # 行为分析
            context = UserContext(
                user_id="multi_turn_user",
                current_emotion=emotion.type,
                emotion_intensity=emotion.intensity,
                interaction_history=[{'input': user_input}],
                time_of_day="afternoon",
                day_of_week="Wednesday",
                session_duration=len(conversation) * 2.0,
                engagement_level=0.7,
                risk_factors=[]
            )

            pattern = reasoner.analyze_behavior_pattern(context)
            patterns.append(pattern)

        # 验证对话流程
        assert len(emotions) == len(conversation)
        assert len(roles) == len(conversation)
        assert len(patterns) == len(conversation)

        # 获取行为摘要
        summary = reasoner.get_user_behavior_summary("multi_turn_user")
        assert summary['total_patterns'] == len(conversation)

        print(f"\n多轮对话测试:")
        print(f"  对话轮数: {len(conversation)}")
        print(f"  情绪变化: {[e.type for e in emotions]}")
        print(f"  主要角色: {max(set([r.id for r in roles]), key=[r.id for r in roles].count)}")
        print(f"  平均置信度: {summary['average_confidence']:.2f}")


class TestSystemIntegration:
    """系统集成测试"""

    @pytest.fixture
    def complete_system(self):
        return {
            'profiler': DeepUserProfiler(),
            'role_system': MultiRoleSystem(),
            'emotion_detector': MultimodalEmotionDetector(),
            'reasoner': EnterpriseBehaviorReasoner()
        }

    def test_emotion_role_integration(self, complete_system):
        """测试情绪检测与角色系统集成"""
        emotion_detector = complete_system['emotion_detector']
        role_system = complete_system['role_system']
        profiler = complete_system['profiler']

        # 测试不同情绪对应的角色选择
        test_cases = [
            ("我很开心！", "joy"),
            ("我很难过", "sadness"),
            ("我很生气！", "anger"),
            ("我有点害怕", "fear")
        ]

        for text, expected_emotion in test_cases:
            emotion = emotion_detector.detect(text=text)
            profile = profiler.analyze_user_input(text)
            role = role_system.select_role(text, profile)

            assert role is not None
            print(f"情绪 {emotion.type} -> 角色 {role.name}")

    def test_profiler_reasoner_integration(self, complete_system):
        """测试画像引擎与推理引擎集成"""
        profiler = complete_system['profiler']
        reasoner = complete_system['reasoner']
        emotion_detector = complete_system['emotion_detector']

        # 分析用户输入
        user_inputs = [
            "我喜欢听故事",
            "我更喜欢轻松的对话",
            "我需要专业的建议"
        ]

        for user_input in user_inputs:
            # 画像分析
            profile = profiler.analyze_user_input(user_input)

            # 情绪检测
            emotion = emotion_detector.detect(text=user_input)

            # 构建上下文
            context = UserContext(
                user_id="integration_user",
                current_emotion=emotion.type,
                emotion_intensity=emotion.intensity,
                interaction_history=[{'input': user_input}],
                time_of_day="morning",
                day_of_week="Tuesday",
                session_duration=10.0,
                engagement_level=0.6,
                risk_factors=[]
            )

            # 行为推理
            pattern = reasoner.analyze_behavior_pattern(context)
            recommendations = reasoner.generate_recommendations(context, pattern)

            assert len(recommendations) > 0
            print(f"输入: {user_input}")
            print(f"  画像: {profile['language_style']['formality']}")
            print(f"  模式: {pattern.pattern_type}")
            print(f"  推荐数: {len(recommendations)}")

    def test_full_pipeline_performance(self, complete_system):
        """测试完整管道性能"""
        import time

        profiler = complete_system['profiler']
        role_system = complete_system['role_system']
        emotion_detector = complete_system['emotion_detector']
        reasoner = complete_system['reasoner']

        user_input = "测试性能的输入文本"

        # 测量总处理时间
        start_time = time.time()

        # 执行完整流程
        emotion = emotion_detector.detect(text=user_input)
        profile = profiler.analyze_user_input(user_input)
        role = role_system.select_role(user_input, profile)

        context = UserContext(
            user_id="perf_user",
            current_emotion=emotion.type,
            emotion_intensity=emotion.intensity,
            interaction_history=[{'input': user_input}],
            time_of_day="afternoon",
            day_of_week="Monday",
            session_duration=5.0,
            engagement_level=0.7,
            risk_factors=[]
        )

        pattern = reasoner.analyze_behavior_pattern(context)
        recommendations = reasoner.generate_recommendations(context, pattern)
        assessment = reasoner.assess_risk(context, pattern)

        end_time = time.time()
        processing_time = (end_time - start_time) * 1000  # 毫秒

        print(f"\n性能测试:")
        print(f"  总处理时间: {processing_time:.2f}ms")
        print(f"  情绪检测: ✓")
        print(f"  用户画像: ✓")
        print(f"  角色选择: ✓")
        print(f"  行为推理: ✓")
        print(f"  推荐生成: ✓")
        print(f"  风险评估: ✓")

        # 性能要求：总处理时间应小于500ms
        assert processing_time < 500, f"处理时间过长: {processing_time:.2f}ms"


class TestErrorHandling:
    """错误处理测试"""

    @pytest.fixture
    def system(self):
        return {
            'profiler': DeepUserProfiler(),
            'role_system': MultiRoleSystem(),
            'emotion_detector': MultimodalEmotionDetector(),
            'reasoner': EnterpriseBehaviorReasoner()
        }

    def test_empty_input_handling(self, system):
        """测试空输入处理"""
        emotion_detector = system['emotion_detector']
        profiler = system['profiler']

        # 空文本
        emotion = emotion_detector.detect(text="")
        assert emotion is not None

        profile = profiler.analyze_user_input("")
        assert profile is not None

    def test_long_input_handling(self, system):
        """测试长输入处理"""
        emotion_detector = system['emotion_detector']
        profiler = system['profiler']

        # 生成超长文本
        long_text = "测试" * 1000

        emotion = emotion_detector.detect(text=long_text)
        assert emotion is not None

        profile = profiler.analyze_user_input(long_text)
        assert profile is not None

    def test_special_characters_handling(self, system):
        """测试特殊字符处理"""
        emotion_detector = system['emotion_detector']
        profiler = system['profiler']

        special_text = "!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/~`"

        emotion = emotion_detector.detect(text=special_text)
        assert emotion is not None

        profile = profiler.analyze_user_input(special_text)
        assert profile is not None

    def test_concurrent_users(self, system):
        """测试并发用户处理"""
        reasoner = system['reasoner']
        emotion_detector = system['emotion_detector']

        # 模拟多个用户同时使用
        users = [f"user_{i}" for i in range(10)]

        for user_id in users:
            emotion = emotion_detector.detect(text=f"用户{user_id}的输入")

            context = UserContext(
                user_id=user_id,
                current_emotion=emotion.type,
                emotion_intensity=emotion.intensity,
                interaction_history=[],
                time_of_day="morning",
                day_of_week="Monday",
                session_duration=5.0,
                engagement_level=0.5,
                risk_factors=[]
            )

            pattern = reasoner.analyze_behavior_pattern(context)
            assert pattern is not None

        # 验证每个用户都有独立的历史记录
        for user_id in users:
            summary = reasoner.get_user_behavior_summary(user_id)
            assert summary['total_patterns'] == 1


class TestDataConsistency:
    """数据一致性测试"""

    @pytest.fixture
    def system(self):
        return {
            'profiler': DeepUserProfiler(),
            'role_system': MultiRoleSystem(),
            'emotion_detector': MultimodalEmotionDetector(),
            'reasoner': EnterpriseBehaviorReasoner()
        }

    def test_emotion_consistency(self, system):
        """测试情绪检测一致性"""
        emotion_detector = system['emotion_detector']

        # 相同输入应该产生相似的情绪结果
        text = "我很开心"
        emotions = [emotion_detector.detect(text=text) for _ in range(5)]

        # 所有情绪类型应该一致
        emotion_types = [e.type for e in emotions]
        assert len(set(emotion_types)) == 1

    def test_profile_consistency(self, system):
        """测试画像一致性"""
        profiler = system['profiler']

        text = "我喜欢听故事"
        profiles = [profiler.analyze_user_input(text) for _ in range(3)]

        # 画像应该保持一致
        for profile in profiles:
            assert 'voice_preference' in profile
            assert 'language_style' in profile

    def test_role_selection_consistency(self, system):
        """测试角色选择一致性"""
        role_system = system['role_system']
        profiler = system['profiler']

        text = "给我讲个故事"
        profile = profiler.analyze_user_input(text)

        roles = [role_system.select_role(text, profile) for _ in range(5)]

        # 相同输入应该选择相同角色
        role_ids = [r.id for r in roles]
        assert len(set(role_ids)) == 1


class TestSystemHealth:
    """系统健康检查"""

    def test_all_modules_importable(self):
        """测试所有模块可导入"""
        from src.personalization import DeepUserProfiler
        from src.skills import MultiRoleSystem, RoleManager
        from src.emotion import MultimodalEmotionDetector
        from src.reasoning import EnterpriseBehaviorReasoner

        assert DeepUserProfiler is not None
        assert MultiRoleSystem is not None
        assert RoleManager is not None
        assert MultimodalEmotionDetector is not None
        assert EnterpriseBehaviorReasoner is not None

    def test_all_models_initializable(self):
        """测试所有模型可初始化"""
        profiler = DeepUserProfiler()
        role_system = MultiRoleSystem()
        emotion_detector = MultimodalEmotionDetector()
        reasoner = EnterpriseBehaviorReasoner()

        assert profiler is not None
        assert role_system is not None
        assert emotion_detector is not None
        assert reasoner is not None

    def test_memory_usage(self):
        """测试内存使用"""
        import sys

        profiler = DeepUserProfiler()
        role_system = MultiRoleSystem()
        emotion_detector = MultimodalEmotionDetector()
        reasoner = EnterpriseBehaviorReasoner()

        # 检查对象大小
        profiler_size = sys.getsizeof(profiler)
        role_system_size = sys.getsizeof(role_system)
        emotion_detector_size = sys.getsizeof(emotion_detector)
        reasoner_size = sys.getsizeof(reasoner)

        print(f"\n内存使用:")
        print(f"  DeepUserProfiler: {profiler_size} bytes")
        print(f"  MultiRoleSystem: {role_system_size} bytes")
        print(f"  MultimodalEmotionDetector: {emotion_detector_size} bytes")
        print(f"  EnterpriseBehaviorReasoner: {reasoner_size} bytes")

        # 内存使用应该在合理范围内
        assert profiler_size < 10000  # 10KB
        assert role_system_size < 10000
        assert emotion_detector_size < 10000
        assert reasoner_size < 10000
