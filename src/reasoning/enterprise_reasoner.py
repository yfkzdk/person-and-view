"""企业级行为推理引擎"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import torch
import torch.nn as nn
import numpy as np
from collections import defaultdict


@dataclass
class BehaviorPattern:
    """行为模式"""
    pattern_id: str
    pattern_type: str  # engagement, avoidance, preference, risk
    frequency: float
    confidence: float
    last_occurrence: datetime
    context: Dict[str, any] = field(default_factory=dict)


@dataclass
class UserContext:
    """用户上下文"""
    user_id: str
    current_emotion: str
    emotion_intensity: float
    interaction_history: List[Dict]
    time_of_day: str  # morning, afternoon, evening, night
    day_of_week: str
    session_duration: float  # minutes
    engagement_level: float  # 0.0 - 1.0
    risk_factors: List[str] = field(default_factory=list)


@dataclass
class Recommendation:
    """推荐"""
    recommendation_id: str
    recommendation_type: str  # content, interaction, intervention
    priority: int  # 1-5, 1最高
    title: str
    description: str
    expected_impact: float  # 0.0 - 1.0
    confidence: float
    reasoning: str
    actions: List[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    """风险评估"""
    risk_level: str  # low, medium, high, critical
    risk_score: float  # 0.0 - 1.0
    risk_factors: List[str]
    mitigation_strategies: List[str]
    requires_intervention: bool
    urgency: str  # immediate, within_24h, within_week


class BehaviorPatternNetwork(nn.Module):
    """行为模式识别网络"""

    def __init__(self, input_dim: int = 128, hidden_dim: int = 256):
        super().__init__()

        # 行为编码器
        self.behavior_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2)
        )

        # 模式分类器
        self.pattern_classifier = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 4)  # 4种模式类型
        )

        # 频率预测器
        self.frequency_predictor = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """前向传播"""
        encoded = self.behavior_encoder(x)
        pattern_logits = self.pattern_classifier(encoded)
        frequency = self.frequency_predictor(encoded)
        return pattern_logits, frequency


class RecommendationEngine(nn.Module):
    """推荐引擎"""

    def __init__(self, context_dim: int = 64, num_recommendations: int = 10):
        super().__init__()

        # 上下文编码器
        self.context_encoder = nn.Sequential(
            nn.Linear(context_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64)
        )

        # 推荐生成器
        self.recommendation_generator = nn.Sequential(
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Linear(128, num_recommendations * 3)  # type, priority, impact
        )

    def forward(self, context: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        encoded = self.context_encoder(context)
        recommendations = self.recommendation_generator(encoded)
        return recommendations


class RiskAssessmentNetwork(nn.Module):
    """风险评估网络"""

    def __init__(self, input_dim: int = 64):
        super().__init__()

        # 风险评估网络
        self.risk_network = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 4)  # 4个风险等级
        )

        # 紧急程度评估
        self.urgency_network = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 3)  # 3个紧急程度
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """前向传播"""
        risk_logits = self.risk_network(x)
        urgency_logits = self.urgency_network(x)
        return risk_logits, urgency_logits


class EnterpriseBehaviorReasoner:
    """企业级行为推理引擎"""

    PATTERN_TYPES = ['engagement', 'avoidance', 'preference', 'risk']
    RISK_LEVELS = ['low', 'medium', 'high', 'critical']
    URGENCY_LEVELS = ['immediate', 'within_24h', 'within_week']
    TIME_PERIODS = ['morning', 'afternoon', 'evening', 'night']

    def __init__(self):
        self.pattern_network = BehaviorPatternNetwork()
        self.recommendation_engine = RecommendationEngine()
        self.risk_network = RiskAssessmentNetwork()

        # 行为历史记录
        self.behavior_history: Dict[str, List[BehaviorPattern]] = defaultdict(list)

        # 推荐模板
        self.recommendation_templates = {
            'engagement': [
                {
                    'type': 'content',
                    'title': '增加互动内容',
                    'description': '基于用户参与模式，推荐更多互动性内容',
                    'actions': ['推送互动问题', '提供个性化内容', '增加游戏化元素']
                },
                {
                    'type': 'interaction',
                    'title': '主动关怀',
                    'description': '用户表现出高参与度，适合深度互动',
                    'actions': ['发起深度对话', '提供专业建议', '分享相关资源']
                }
            ],
            'avoidance': [
                {
                    'type': 'intervention',
                    'title': '降低互动压力',
                    'description': '检测到回避行为，需要调整互动策略',
                    'actions': ['减少推送频率', '简化交互流程', '提供轻松话题']
                }
            ],
            'preference': [
                {
                    'type': 'content',
                    'title': '个性化推荐',
                    'description': '基于用户偏好提供定制内容',
                    'actions': ['推荐偏好主题', '调整内容风格', '优化呈现方式']
                }
            ],
            'risk': [
                {
                    'type': 'intervention',
                    'title': '风险干预',
                    'description': '检测到潜在风险，需要及时干预',
                    'actions': ['提供支持资源', '引导专业帮助', '持续关注状态']
                }
            ]
        }

    def analyze_behavior_pattern(
        self,
        user_context: UserContext
    ) -> BehaviorPattern:
        """分析行为模式"""
        # 构建特征向量
        features = self._extract_features(user_context)
        features_tensor = torch.FloatTensor(features).unsqueeze(0)

        # 网络推理
        with torch.no_grad():
            pattern_logits, frequency = self.pattern_network(features_tensor)

        # 解析结果
        pattern_probs = torch.softmax(pattern_logits, dim=-1)
        pattern_idx = torch.argmax(pattern_probs, dim=-1).item()
        confidence = pattern_probs[0, pattern_idx].item()

        pattern_type = self.PATTERN_TYPES[pattern_idx]

        # 创建行为模式
        pattern = BehaviorPattern(
            pattern_id=f"pattern_{datetime.now().timestamp()}",
            pattern_type=pattern_type,
            frequency=frequency.item(),
            confidence=confidence,
            last_occurrence=datetime.now(),
            context={
                'emotion': user_context.current_emotion,
                'time_of_day': user_context.time_of_day,
                'engagement_level': user_context.engagement_level
            }
        )

        # 记录历史
        self.behavior_history[user_context.user_id].append(pattern)

        return pattern

    def generate_recommendations(
        self,
        user_context: UserContext,
        behavior_pattern: BehaviorPattern
    ) -> List[Recommendation]:
        """生成推荐"""
        recommendations = []

        # 获取推荐模板
        templates = self.recommendation_templates.get(behavior_pattern.pattern_type, [])

        for idx, template in enumerate(templates):
            # 计算优先级和影响
            priority = self._calculate_priority(behavior_pattern, user_context)
            expected_impact = self._estimate_impact(behavior_pattern, user_context)

            recommendation = Recommendation(
                recommendation_id=f"rec_{datetime.now().timestamp()}_{idx}",
                recommendation_type=template['type'],
                priority=priority,
                title=template['title'],
                description=template['description'],
                expected_impact=expected_impact,
                confidence=behavior_pattern.confidence,
                reasoning=f"基于{behavior_pattern.pattern_type}模式，置信度{behavior_pattern.confidence:.2f}",
                actions=template['actions']
            )

            recommendations.append(recommendation)

        # 按优先级排序
        recommendations.sort(key=lambda r: r.priority)

        return recommendations

    def assess_risk(
        self,
        user_context: UserContext,
        behavior_pattern: BehaviorPattern
    ) -> RiskAssessment:
        """评估风险"""
        # 构建风险特征
        risk_features = self._extract_risk_features(user_context, behavior_pattern)
        risk_tensor = torch.FloatTensor(risk_features).unsqueeze(0)

        # 网络推理
        with torch.no_grad():
            risk_logits, urgency_logits = self.risk_network(risk_tensor)

        # 解析结果
        risk_probs = torch.softmax(risk_logits, dim=-1)
        urgency_probs = torch.softmax(urgency_logits, dim=-1)

        risk_idx = torch.argmax(risk_probs, dim=-1).item()
        urgency_idx = torch.argmax(urgency_probs, dim=-1).item()

        risk_level = self.RISK_LEVELS[risk_idx]
        risk_score = risk_probs[0, risk_idx].item()
        urgency = self.URGENCY_LEVELS[urgency_idx]

        # 识别风险因素
        risk_factors = self._identify_risk_factors(user_context, behavior_pattern)

        # 生成缓解策略
        mitigation_strategies = self._generate_mitigation_strategies(risk_level, risk_factors)

        # 判断是否需要干预
        requires_intervention = risk_level in ['high', 'critical']

        return RiskAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            risk_factors=risk_factors,
            mitigation_strategies=mitigation_strategies,
            requires_intervention=requires_intervention,
            urgency=urgency if requires_intervention else 'within_week'
        )

    def _extract_features(self, context: UserContext) -> np.ndarray:
        """提取特征向量"""
        features = []

        # 情绪特征
        emotion_map = {
            'joy': 0.8, 'sadness': 0.2, 'anger': 0.1,
            'fear': 0.3, 'surprise': 0.6, 'neutral': 0.5
        }
        features.append(emotion_map.get(context.current_emotion, 0.5))
        features.append(context.emotion_intensity)

        # 时间特征
        time_map = {'morning': 0.25, 'afternoon': 0.5, 'evening': 0.75, 'night': 1.0}
        features.append(time_map.get(context.time_of_day, 0.5))

        # 参与度
        features.append(context.engagement_level)

        # 会话时长（归一化）
        features.append(min(context.session_duration / 60.0, 1.0))

        # 交互历史长度（归一化）
        features.append(min(len(context.interaction_history) / 100.0, 1.0))

        # 风险因素数量（归一化）
        features.append(min(len(context.risk_factors) / 5.0, 1.0))

        # 填充到128维
        while len(features) < 128:
            features.append(0.0)

        return np.array(features[:128], dtype=np.float32)

    def _extract_risk_features(
        self,
        context: UserContext,
        pattern: BehaviorPattern
    ) -> np.ndarray:
        """提取风险特征"""
        features = []

        # 行为模式特征
        pattern_map = {'engagement': 0.8, 'avoidance': 0.2, 'preference': 0.6, 'risk': 0.1}
        features.append(pattern_map.get(pattern.pattern_type, 0.5))
        features.append(pattern.confidence)
        features.append(pattern.frequency)

        # 用户上下文特征
        features.append(context.emotion_intensity)
        features.append(context.engagement_level)
        features.append(len(context.risk_factors))

        # 填充到64维
        while len(features) < 64:
            features.append(0.0)

        return np.array(features[:64], dtype=np.float32)

    def _calculate_priority(
        self,
        pattern: BehaviorPattern,
        context: UserContext
    ) -> int:
        """计算优先级"""
        # 基础优先级
        base_priority = {
            'risk': 1,
            'avoidance': 2,
            'engagement': 3,
            'preference': 4
        }

        priority = base_priority.get(pattern.pattern_type, 5)

        # 根据置信度调整
        if pattern.confidence > 0.8:
            priority = max(1, priority - 1)

        # 根据情绪强度调整
        if context.emotion_intensity > 0.7:
            priority = max(1, priority - 1)

        return priority

    def _estimate_impact(
        self,
        pattern: BehaviorPattern,
        context: UserContext
    ) -> float:
        """估计影响"""
        # 基础影响
        base_impact = {
            'engagement': 0.8,
            'avoidance': 0.6,
            'preference': 0.7,
            'risk': 0.9
        }

        impact = base_impact.get(pattern.pattern_type, 0.5)

        # 根据参与度调整
        impact *= (0.5 + 0.5 * context.engagement_level)

        # 根据置信度调整
        impact *= pattern.confidence

        return min(impact, 1.0)

    def _identify_risk_factors(
        self,
        context: UserContext,
        pattern: BehaviorPattern
    ) -> List[str]:
        """识别风险因素"""
        risk_factors = []

        # 情绪风险
        if context.current_emotion in ['sadness', 'anger', 'fear']:
            if context.emotion_intensity > 0.7:
                risk_factors.append(f"高强度{context.current_emotion}情绪")

        # 参与度风险
        if context.engagement_level < 0.3:
            risk_factors.append("低参与度")

        # 行为模式风险
        if pattern.pattern_type == 'avoidance':
            risk_factors.append("回避行为模式")

        if pattern.pattern_type == 'risk':
            risk_factors.append("风险行为模式")

        # 已有风险因素
        risk_factors.extend(context.risk_factors)

        return risk_factors

    def _generate_mitigation_strategies(
        self,
        risk_level: str,
        risk_factors: List[str]
    ) -> List[str]:
        """生成缓解策略"""
        strategies = []

        if risk_level == 'low':
            strategies.append("持续观察用户状态")
            strategies.append("提供常规支持")

        elif risk_level == 'medium':
            strategies.append("增加互动频率")
            strategies.append("提供个性化关怀")
            strategies.append("引导积极活动")

        elif risk_level == 'high':
            strategies.append("立即启动干预流程")
            strategies.append("提供专业支持资源")
            strategies.append("通知相关人员")

        elif risk_level == 'critical':
            strategies.append("紧急干预")
            strategies.append("联系专业机构")
            strategies.append("24小时持续关注")

        # 针对特定风险因素的策略
        for factor in risk_factors:
            if '情绪' in factor:
                strategies.append("情绪疏导")
            if '参与度' in factor:
                strategies.append("提升互动吸引力")
            if '回避' in factor:
                strategies.append("降低压力，建立信任")

        return list(set(strategies))  # 去重

    def get_user_behavior_summary(self, user_id: str) -> Dict:
        """获取用户行为摘要"""
        patterns = self.behavior_history.get(user_id, [])

        if not patterns:
            return {}

        # 统计模式分布
        pattern_counts = defaultdict(int)
        for pattern in patterns:
            pattern_counts[pattern.pattern_type] += 1

        # 计算平均置信度
        avg_confidence = np.mean([p.confidence for p in patterns])

        # 计算平均频率
        avg_frequency = np.mean([p.frequency for p in patterns])

        # 最近模式
        recent_pattern = patterns[-1] if patterns else None

        return {
            'total_patterns': len(patterns),
            'pattern_distribution': dict(pattern_counts),
            'average_confidence': avg_confidence,
            'average_frequency': avg_frequency,
            'recent_pattern_type': recent_pattern.pattern_type if recent_pattern else None,
            'recent_confidence': recent_pattern.confidence if recent_pattern else None
        }
