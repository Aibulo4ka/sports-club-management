"""
Custom template filters for markdown rendering
"""
from django import template
from django.utils.safestring import mark_safe
import markdown2

register = template.Library()


@register.filter(name='markdown')
def markdown_format(text):
    """
    Конвертирует Markdown текст в HTML с поддержкой таблиц и extras
    """
    if not text:
        return ''

    # Используем markdown2 с расширениями для таблиц, списков и т.д.
    html = markdown2.markdown(
        text,
        extras=[
            'tables',           # Поддержка таблиц
            'fenced-code-blocks',  # Блоки кода ```
            'strike',           # Зачёркнутый текст
            'task_list',        # Чекбоксы [ ] и [x]
            'cuddled-lists',    # Лучшая обработка списков
            'header-ids',       # ID для заголовков
        ]
    )

    return mark_safe(html)
