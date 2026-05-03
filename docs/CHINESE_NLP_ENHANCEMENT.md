# 中文NLP增强模块文档

## 概述

本文档描述了中文NLP增强模块的实现，包括分词、情感分析、命名实体识别、文本分类和文本增强。

## 核心模块

### 1. 中文分词器 (ChineseTokenizer)

**功能：**
- 中文分词（精确模式、全模式、搜索引擎模式）
- 词性标注
- 关键词提取
- 自定义词典

**使用方法：**
```python
from src.nlp import ChineseTokenizer

tokenizer = ChineseTokenizer()

# 分词
tokens = tokenizer.cut("我爱自然语言处理")

# 词性标注
tagged = tokenizer.pos_tag("我爱自然语言处理")

# 提取关键词
keywords = tokenizer.extract_keywords(text, top_k=5)

# 添加自定义词
tokenizer.add_word("自然语言处理")
```

### 2. 情感分析器 (SentimentAnalyzer)

**功能：**
- 情感极性分析（正面/负面/中性）
- 情感强度评分
- 情感词提取

**使用方法：**
```python
from src.nlp import SentimentAnalyzer

analyzer = SentimentAnalyzer()

result = analyzer.analyze("今天天气真好")
# {'polarity': 'positive', 'confidence': 0.8, 'score': 0.6}

words = analyzer.get_sentiment_words("我很开心")
# {'positive': ['开心'], 'negative': []}
```

### 3. 命名实体识别器 (NERExtractor)

**功能：**
- 人名识别
- 地名识别
- 机构名识别

**使用方法：**
```python
from src.nlp import NERExtractor

extractor = NERExtractor()

entities = extractor.extract("张三去北京旅游")
# [{'text': '张三', 'type': 'PERSON', 'start': 0, 'end': 2}, ...]
```

### 4. 文本分类器 (TextClassifier)

**功能：**
- 意图识别
- 主题分类

**使用方法：**
```python
from src.nlp import TextClassifier

classifier = TextClassifier()

intent = classifier.classify_intent("我想听故事")
# 'story'

topic = classifier.classify_topic("今天天气怎么样")
# 'weather'
```

### 5. 文本增强器 (TextEnhancer)

**功能：**
- 关键短语提取
- 文本摘要
- 文本纠错

**使用方法：**
```python
from src.nlp import TextEnhancer

enhancer = TextEnhancer()

phrases = enhancer.extract_key_phrases(text)
summary = enhancer.summarize(text, max_length=50)
corrected = enhancer.correct_text(text)
```

## 性能指标

- **分词速度**: ~1000 chars/s
- **情感分析**: < 50ms
- **NER提取**: < 100ms
- **文本分类**: < 10ms

## 依赖库

- jieba - 中文分词
- re - 正则表达式