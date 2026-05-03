"""
文本清理工具 - 过滤 emoji 和情绪文字
"""
import re


def clean_text_for_tts(text: str) -> str:
    """
    清理文本，移除不适合朗读的内容

    Args:
        text: 原始文本

    Returns:
        清理后的文本
    """
    # 移除常见的 emoji（使用明确的Unicode码点）
    emojis_to_remove = [
        '\U0001F600', '\U0001F601', '\U0001F602', '\U0001F603', '\U0001F604',
        '\U0001F605', '\U0001F606', '\U0001F607', '\U0001F608', '\U0001F609',
        '\U0001F60A', '\U0001F60B', '\U0001F60C', '\U0001F60D', '\U0001F60E',
        '\U0001F60F', '\U0001F618', '\U0001F619', '\U0001F61A', '\U0001F61B',
        '\U0001F61C', '\U0001F61D', '\U0001F61E', '\U0001F61F', '\U0001F620',
        '\U0001F621', '\U0001F622', '\U0001F623', '\U0001F624', '\U0001F625',
        '\U0001F626', '\U0001F627', '\U0001F628', '\U0001F629', '\U0001F62A',
        '\U0001F62B', '\U0001F62C', '\U0001F62D', '\U0001F62E', '\U0001F62F',
        '\U0001F630', '\U0001F631', '\U0001F632', '\U0001F633', '\U0001F634',
        '\U0001F635', '\U0001F636', '\U0001F637', '\U0001F638', '\U0001F639',
        '\U0001F63A', '\U0001F63B', '\U0001F63C', '\U0001F63D', '\U0001F63E',
        '\U0001F63F', '\U0001F640', '\U0001F641', '\U0001F642', '\U0001F643',
        '\U0001F644', '\U0001F645', '\U0001F646', '\U0001F647', '\U0001F648',
        '\U0001F649', '\U0001F64A', '\U0001F64B', '\U0001F64C', '\U0001F64D',
        '\U0001F64E', '\U0001F64F',
    ]

    for emoji in emojis_to_remove:
        text = text.replace(emoji, '')

    # 移除 markdown 格式符号
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold** -> bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # *italic* -> italic
    text = re.sub(r'`([^`]+)`', r'\1', text)  # `code` -> code

    # 移除多余的空格和换行
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    return text


def should_skip_for_tts(text: str) -> bool:
    """
    判断文本是否应该完全跳过（不朗读）

    Args:
        text: 文本内容

    Returns:
        True 表示跳过，False 表示朗读
    """
    # 纯 emoji 或符号
    cleaned = clean_text_for_tts(text)
    return len(cleaned.strip()) == 0