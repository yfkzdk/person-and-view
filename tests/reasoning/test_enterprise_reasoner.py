"""测试企业级行为推理引擎"""

import pytest
import torch
import numpy as np
from datetime import datetime
from src.reasoning import (
    EnterpriseBehaviorReasoner,
    BehaviorPattern,
    UserContext,
    Recommendation,
    RiskAssessment,
    BehaviorPatternNetwork,
    RecommendationEngine,
    RiskAssessmentNetwork
)


class TestBehaviorPattern:
    """测试行为模式数据类"""

    def test_creation(self):
        """测试创建行为模式"""
        pattern = BehaviorPattern(
            pattern_id="test_pattern_001",
            pattern_type="engagement",
            frequency=0.8,
            confidence=0.9,
            last_occurrence=datetime.now(),
            context={'emotion': 'joy'}
        )

        assert pattern.pattern_id == "test_pattern_001"
        assert pattern.pattern_type == "engagement"
        assert pattern.frequency == 0.8
        assert pattern.confidence == 0.9
        assert pattern.context['emotion'] == 'joy'


class TestUserContext:
    """测试用户上下文数据类"""

    def test_creation(self):
        """测试创建用户上下文"""
        context = UserContext(
            user_id="user_001",
            current_emotion="joy",
            emotion_intensity=0.8,
            interaction_history=[{'type': 'message'}],
            time_of_day="morning",
            day_of_week="Monday",
            session_duration=30.5,
            engagement_level=0.7,
            risk_factors=["low_engagement"]
        )

        assert context.user_id == "user_001"
        assert context.current_emotion == "joy"
        assert context.emotion_intensity == 0.8
        assert len(context.interaction_history) == 1
        assert context.time_of_day == "morning"
        assert context.engagement_level == 0.7
        assert len(context.risk_factors) == 1


class TestRecommendation:
    """测试推荐数据类"""

    def test_creation(self):
        """测试创建推荐"""
        rec = Recommendation(
            recommendation_id="rec_001",
            recommendation_type="content",
            priority=1,
            title="测试推荐",
            description="这是一个测试推荐",
            expected_impact=0.8,
            confidence=0.9,
            reasoning="基于用户行为模式",
            actions=["action1", "action2"]
        )

        assert rec.recommendation_id == "rec_001"
        assert rec.recommendation_type == "content"
        assert rec.priority == 1
        assert rec.expected_impact == 0.8
        assert len(rec.actions) == 2


class TestRiskAssessment:
    """测试风险评估数据类"""

    def test_creation(self):
        """测试创建风险评估"""
        assessment = RiskAssessment(
            risk_level="medium",
            risk_score=0.5,
            risk_factors=["low_engagement"],
            mitigation_strategies=["增加互动"],
            requires_intervention=True,
            urgency="within_24h"
        )

        assert assessment.risk_level == "medium"
        assert assessment.risk_score == 0.5
        assert len(assessment.risk_factors) == 1
        assert len(assessment.mitigation_strategies) == 1
        assert assessment.requires_intervention is True


class TestBehaviorPatternNetwork:
    """测试行为模式识别网络"""

    @pytest.fixture
    def network(self):
        return BehaviorPatternNetwork(input_dim=128, hidden_dim=256)

    def test_initialization(self, network):
        """测试初始化"""
        assert network.behavior_encoder is not None
        assert network.pattern_classifier is not None
        assert network.frequency_predictor is not None

    def test_forward_pass(self, network):
        """测试前向传播"""
        batch_size = 4
        input_dim = 128
        x = torch.randn(batch_size, input_dim)

        pattern_logits, frequency = network(x)

        assert pattern_logits.shape == (batch_size, 4)  # 4种模式类型
        assert frequency.shape == (batch_size, 1)
        assert torch.all((frequency >= 0) & (frequency <= 1))


class TestRecommendationEngine:
    """测试推荐引擎"""

    @pytest.fixture
    def engine(self):
        return RecommendationEngine(context_dim=64, num_recommendations=10)

    def test_initialization(self, engine):
        """测试初始化"""
        assert engine.context_encoder is not None
        assert engine.recommendation_generator is not None

    def test_forward_pass(self, engine):
        """测试前向传播"""
        batch_size = 2
        context_dim = 64
        context = torch.randn(batch_size, context_dim)

        recommendations = engine(context)

        assert recommendations.shape == (batch_size, 30)  # 10 recommendations * 3 values


class TestRiskAssessmentNetwork:
    """测试风险评估网络"""

    @pytest.fixture
    def network(self):
        return RiskAssessmentNetwork(input_dim=64)

    def test_initialization(self, network):
        """测试初始化"""
        assert network.risk_network is not None
        assert network.urgency_network is not None

    def test_forward_pass(self, network):
        """测试前向传播"""
        batch_size = 3
        input_dim = 64
        x = torch.randn(batch_size, input_dim)

        risk_logits, urgency_logits = network(x)

        assert risk_logits.shape == (batch_size, 4)  # 4个风险等级
        assert urgency_logits.shape == (batch_size, 3)  # 3个紧急程度


class TestEnterpriseBehaviorReasoner:
    """测试企业级行为推理引擎"""

    @pytest.fixture
    def reasoner(self):
        return EnterpriseBehaviorReasoner()

    @pytest.fixture
    def sample_context(self):
        return UserContext(
            user_id="test_user",
            current_emotion="joy",
            emotion_intensity=0.8,
            interaction_history=[
                {'type': 'message', 'content': 'test'},
                {'type': 'response', 'content': 'test'}
            ],
            time_of_day="morning",
            day_of_week="Monday",
            session_duration=25.5,
            engagement_level=0.75,
            risk_factors=[]
        )

    def test_initialization(self, reasoner):
        """测试初始化"""
        assert reasoner.pattern_network is not None
        assert reasoner.recommendation_engine is not None
        assert reasoner.risk_network is not None
        assert len(reasoner.recommendation_templates) > 0

    def test_analyze_behavior_pattern(self, reasoner, sample_context):
        """测试行为模式分析"""
        pattern = reasoner.analyze_behavior_pattern(sample_context)

        assert isinstance(pattern, BehaviorPattern)
        assert pattern.pattern_type in reasoner.PATTERN_TYPES
        assert 0 <= pattern.frequency <= 1
        assert 0 <= pattern.confidence <= 1
        assert isinstance(pattern.last_occurrence, datetime)
        assert 'emotion' in pattern.context

    def test_generate_recommendations(self, reasoner, sample_context):
        """测试生成推荐"""
        pattern = reasoner.analyze_behavior_pattern(sample_context)
        recommendations = reasoner.generate_recommendations(sample_context, pattern)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

        for rec in recommendations:
            assert isinstance(rec, Recommendation)
            assert rec.recommendation_type in ['content', 'interaction', 'intervention']
            assert 1 <= rec.priority <= 5
            assert 0 <= rec.expected_impact <= 1
            assert len(rec.actions) > 0

    def test_assess_risk(self, reasoner, sample_context):
        """测试风险评估"""
        pattern = reasoner.analyze_behavior_pattern(sample_context)
        assessment = reasoner.assess_risk(sample_context, pattern)

        assert isinstance(assessment, RiskAssessment)
        assert assessment.risk_level in reasoner.RISK_LEVELS
        assert 0 <= assessment.risk_score <= 1
        assert isinstance(assessment.risk_factors, list)
        assert isinstance(assessment.mitigation_strategies, list)
        assert isinstance(assessment.requires_intervention, bool)
        assert assessment.urgency in reasoner.URGENCY_LEVELS

    def test_high_risk_scenario(self, reasoner):
        """测试高风险场景"""
        # 创建高风险上下文
        high_risk_context = UserContext(
            user_id="risk_user",
            current_emotion="sadness",
            emotion_intensity=0.9,
            interaction_history=[],
            time_of_day="night",
            day_of_week="Monday",
            session_duration=5.0,
            engagement_level=0.1,
            risk_factors=["isolation", "negative_thoughts"]
        )

        pattern = reasoner.analyze_behavior_pattern(high_risk_context)
        assessment = reasoner.assess_risk(high_risk_context, pattern)

        # 高风险场景应该触发干预
        if assessment.risk_level in ['high', 'critical']:
            assert assessment.requires_intervention is True
            assert len(assessment.mitigation_strategies) > 0

    def test_engagement_pattern(self, reasoner):
        """测试参与模式"""
        engagement_context = UserContext(
            user_id="engaged_user",
            current_emotion="joy",
            emotion_intensity=0.8,
            interaction_history=[{'type': 'msg'} for _ in range(20)],
            time_of_day="afternoon",
            day_of_week="Wednesday",
            session_duration=45.0,
            engagement_level=0.9,
            risk_factors=[]
        )

        pattern = reasoner.analyze_behavior_pattern(engagement_context)
        recommendations = reasoner.generate_recommendations(engagement_context, pattern)

        # 高参与度应该有积极推荐
        assert len(recommendations) > 0
        assert all(isinstance(rec, Recommendation) for rec in recommendations)

    def test_avoidance_pattern(self, reasoner):
        """测试回避模式"""
        avoidance_context = UserContext(
            user_id="avoiding_user",
            current_emotion="fear",
            emotion_intensity=0.6,
            interaction_history=[],
            time_of_day="evening",
            day_of_week="Friday",
            session_duration=2.0,
            engagement_level=0.2,
            risk_factors=["avoidance"]
        )

        pattern = reasoner.analyze_behavior_pattern(avoidance_context)
        recommendations = reasoner.generate_recommendations(avoidance_context, pattern)

        # 回避模式应该有干预推荐
        assert len(recommendations) > 0

    def test_get_user_behavior_summary(self, reasoner, sample_context):
        """测试获取用户行为摘要"""
        # 分析多次行为
        for _ in range(5):
            reasoner.analyze_behavior_pattern(sample_context)

        summary = reasoner.get_user_behavior_summary(sample_context.user_id)

        assert isinstance(summary, dict)
        assert summary['total_patterns'] == 5
        assert 'pattern_distribution' in summary
        assert 'average_confidence' in summary
        assert 'average_frequency' in summary
        assert 0 <= summary['average_confidence'] <= 1
        assert 0 <= summary['average_frequency'] <= 1

    def test_empty_behavior_summary(self, reasoner):
        """测试空行为摘要"""
        summary = reasoner.get_user_behavior_summary("nonexistent_user")

        assert summary == {}

    def test_feature_extraction(self, reasoner, sample_context):
        """测试特征提取"""
        features = reasoner._extract_features(sample_context)

        assert isinstance(features, np.ndarray)
        assert features.shape == (128,)
        assert features.dtype == np.float32
        assert not np.any(np.isnan(features))

    def test_risk_feature_extraction(self, reasoner, sample_context):
        """测试风险特征提取"""
        pattern = reasoner.analyze_behavior_pattern(sample_context)
        risk_features = reasoner._extract_risk_features(sample_context, pattern)

        assert isinstance(risk_features, np.ndarray)
        assert risk_features.shape == (64,)
        assert risk_features.dtype == np.float32
        assert not np.any(np.isnan(risk_features))

    def test_priority_calculation(self, reasoner, sample_context):
        """测试优先级计算"""
        pattern = BehaviorPattern(
            pattern_id="test",
            pattern_type="risk",
            frequency=0.5,
            confidence=0.9,
            last_occurrence=datetime.now(),
            context={}
        )

        priority = reasoner._calculate_priority(pattern, sample_context)

        assert isinstance(priority, int)
        assert 1 <= priority <= 5

    def test_impact_estimation(self, reasoner, sample_context):
        """测试影响估计"""
        pattern = BehaviorPattern(
            pattern_id="test",
            pattern_type="engagement",
            frequency=0.8,
            confidence=0.9,
            last_occurrence=datetime.now(),
            context={}
        )

        impact = reasoner._estimate_impact(pattern, sample_context)

        assert isinstance(impact, float)
        assert 0 <= impact <= 1

    def test_risk_factor_identification(self, reasoner):
        """测试风险因素识别"""
        context = UserContext(
            user_id="test",
            current_emotion="sadness",
            emotion_intensity=0.9,
            interaction_history=[],
            time_of_day="night",
            day_of_week="Monday",
            session_duration=5.0,
            engagement_level=0.1,
            risk_factors=["isolation"]
        )

        pattern = BehaviorPattern(
            pattern_id="test",
            pattern_type="risk",
            frequency=0.5,
            confidence=0.8,
            last_occurrence=datetime.now(),
            context={}
        )

        risk_factors = reasoner._identify_risk_factors(context, pattern)

        assert isinstance(risk_factors, list)
        assert len(risk_factors) > 0
        assert "isolation" in risk_factors

    def test_mitigation_strategies(self, reasoner):
        """测试缓解策略生成"""
        strategies = reasoner._generate_mitigation_strategies(
            "high",
            ["low_engagement", "negative_emotion"]
        )

        assert isinstance(strategies, list)
        assert len(strategies) > 0
        assert all(isinstance(s, str) for s in strategies)

    def test_multiple_users(self, reasoner):
        """测试多用户场景"""
        contexts = [
            UserContext(
                user_id=f"user_{i}",
                current_emotion="joy",
                emotion_intensity=0.5,
                interaction_history=[],
                time_of_day="morning",
                day_of_week="Monday",
                session_duration=10.0,
                engagement_level=0.5,
                risk_factors=[]
            )
            for i in range(3)
        ]

        for context in contexts:
            pattern = reasoner.analyze_behavior_pattern(context)
            assert pattern is not None

        # 验证每个用户都有历史记录
        for i in range(3):
            summary = reasoner.get_user_behavior_summary(f"user_{i}")
            assert summary['total_patterns'] == 1
