"""命名实体识别测试"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from src.nlp.ner_extractor import NERExtractor


def test_extractor_initialization():
    """测试提取器初始化"""
    extractor = NERExtractor()
    assert extractor is not None


def test_extractor_extract_person():
    """测试人名提取"""
    extractor = NERExtractor()
    text = "张三和李四一起去北京旅游"
    entities = extractor.extract(text)
    assert isinstance(entities, list)
    person_entities = [e for e in entities if e['type'] == 'PERSON']
    assert len(person_entities) > 0


def test_extractor_extract_location():
    """测试地名提取"""
    extractor = NERExtractor()
    text = "我想去北京和上海旅游"
    entities = extractor.extract(text)
    location_entities = [e for e in entities if e['type'] == 'LOCATION']
    assert len(location_entities) > 0


def test_extractor_extract_organization():
    """测试机构名提取"""
    extractor = NERExtractor()
    text = "他在阿里巴巴和腾讯工作过"
    entities = extractor.extract(text)
    org_entities = [e for e in entities if e['type'] == 'ORGANIZATION']
    assert len(org_entities) > 0


def test_extractor_empty_input():
    """测试空输入"""
    extractor = NERExtractor()
    entities = extractor.extract("")
    assert entities == []


def test_extractor_none_input():
    """测试None输入"""
    extractor = NERExtractor()
    entities = extractor.extract(None)
    assert entities == []
