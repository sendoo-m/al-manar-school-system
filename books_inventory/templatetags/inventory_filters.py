from django import template

register = template.Library()

@register.filter
def sub(value, arg):
    """طرح قيمة من أخرى"""
    try:
        return float(value or 0) - float(arg or 0)
    except (ValueError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    """ضرب قيمتين"""
    try:
        return float(value or 0) * float(arg or 0)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """قسمة قيمتين"""
    try:
        if float(arg or 0) == 0:
            return 0
        return float(value or 0) / float(arg or 0)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """حساب النسبة المئوية"""
    try:
        if float(total or 0) == 0:
            return 0
        return round((float(value or 0) / float(total or 0)) * 100, 1)
    except (ValueError, TypeError):
        return 0
