"""命名实体识别器 - 使用规则和词典进行NER"""

from typing import Any, Dict, List, Optional
import re


class NERExtractor:
    """
    命名实体识别器

    使用规则和词典进行简单的命名实体识别
    支持实体类型: PERSON, LOCATION, ORGANIZATION
    参考HanLP MSRA标注集的实体类型定义
    """

    # 常见姓氏
    SURNAMES = {
        '张', '王', '李', '赵', '刘', '陈', '杨', '黄', '周', '吴',
        '徐', '孙', '马', '朱', '胡', '郭', '何', '林', '罗', '高'
    }

    # 常见地名后缀
    LOCATION_SUFFIXES = {
        '市', '省', '县', '区', '镇', '村', '山', '河', '湖', '海',
        '岛', '江', '路', '街', '道', '城', '州', '国'
    }

    # 常见机构名后缀
    ORG_SUFFIXES = {
        '公司', '集团', '企业', '银行', '大学', '学院', '医院',
        '研究所', '研究院', '中心', '机构', '组织', '协会'
    }

    # 知名机构
    KNOWN_ORGS = {
        '阿里巴巴', '腾讯', '百度', '华为', '小米', '京东', '字节跳动',
        '美团', '滴滴', '快手', '网易', '新浪', '搜狐'
    }

    # 知名地名
    KNOWN_LOCATIONS = {
        '北京', '上海', '广州', '深圳', '杭州', '南京', '武汉', '成都',
        '西安', '重庆', '天津', '苏州', '长沙', '郑州', '青岛', '大连'
    }

    def __init__(self):
        """初始化提取器"""
        pass

    def extract(self, text: Optional[str]) -> List[Dict[str, Any]]:
        """
        提取命名实体

        Args:
            text: 输入文本

        Returns:
            List[Dict]: 实体列表，每个实体包含text, type, start, end
        """
        if not text or not text.strip():
            return []

        entities: List[Dict[str, Any]] = []

        # 提取人名
        entities.extend(self._extract_persons(text))

        # 提取地名
        entities.extend(self._extract_locations(text))

        # 提取机构名
        entities.extend(self._extract_organizations(text))

        # 去重：相同位置的实体只保留最长的
        entities = self._deduplicate(entities)

        # 按位置排序
        entities.sort(key=lambda x: x['start'])

        return entities

    def _extract_persons(self, text: str) -> List[Dict[str, Any]]:
        """提取人名"""
        entities: List[Dict[str, Any]] = []

        # 简单规则：姓氏 + 1-2个字
        for i, char in enumerate(text):
            if char in self.SURNAMES:
                # 检查后面1-2个字（2字名和3字名）
                for length in [2, 3]:
                    if i + length <= len(text):
                        name = text[i:i + length]
                        # 简单验证：不是地名或机构名
                        if name not in self.KNOWN_LOCATIONS and name not in self.KNOWN_ORGS:
                            entities.append({
                                'text': name,
                                'type': 'PERSON',
                                'start': i,
                                'end': i + length
                            })

        return entities

    def _extract_locations(self, text: str) -> List[Dict[str, Any]]:
        """提取地名"""
        entities: List[Dict[str, Any]] = []

        # 已知地名
        for loc in self.KNOWN_LOCATIONS:
            start = 0
            while True:
                start = text.find(loc, start)
                if start == -1:
                    break
                entities.append({
                    'text': loc,
                    'type': 'LOCATION',
                    'start': start,
                    'end': start + len(loc)
                })
                start += len(loc)

        # 基于后缀的地名识别
        for suffix in self.LOCATION_SUFFIXES:
            pattern = rf'[一-龥]{{2,4}}{suffix}'
            matches = re.finditer(pattern, text)
            for match in matches:
                loc = match.group()
                entities.append({
                    'text': loc,
                    'type': 'LOCATION',
                    'start': match.start(),
                    'end': match.end()
                })

        return entities

    def _extract_organizations(self, text: str) -> List[Dict[str, Any]]:
        """提取机构名"""
        entities: List[Dict[str, Any]] = []

        # 已知机构
        for org in self.KNOWN_ORGS:
            start = 0
            while True:
                start = text.find(org, start)
                if start == -1:
                    break
                entities.append({
                    'text': org,
                    'type': 'ORGANIZATION',
                    'start': start,
                    'end': start + len(org)
                })
                start += len(org)

        # 基于后缀的机构名识别
        for suffix in self.ORG_SUFFIXES:
            pattern = rf'[一-龥]{{2,6}}{suffix}'
            matches = re.finditer(pattern, text)
            for match in matches:
                org = match.group()
                entities.append({
                    'text': org,
                    'type': 'ORGANIZATION',
                    'start': match.start(),
                    'end': match.end()
                })

        return entities

    def _deduplicate(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        去重：对于重叠的实体，保留最长的

        Args:
            entities: 实体列表

        Returns:
            List[Dict]: 去重后的实体列表
        """
        if not entities:
            return []

        # 按起始位置排序，长度长的优先
        entities.sort(key=lambda x: (x['start'], -(x['end'] - x['start'])))

        result: List[Dict[str, Any]] = []
        for entity in entities:
            # 检查是否与已选实体重叠
            overlap = False
            for existing in result:
                if (entity['start'] >= existing['start'] and
                        entity['start'] < existing['end']):
                    overlap = True
                    break
                if (entity['end'] > existing['start'] and
                        entity['end'] <= existing['end']):
                    overlap = True
                    break

            if not overlap:
                result.append(entity)

        return result
