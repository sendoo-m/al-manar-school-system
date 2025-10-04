# treasury_management/templatetags/treasury_filters.py
from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def add_days(date, days):
    """إضافة أيام للتاريخ"""
    try:
        return date + timedelta(days=days)
    except:
        return date

@register.filter
def sum_amounts(expenses):
    """جمع المبالغ"""
    try:
        return sum(expense.amount for expense in expenses)
    except:
        return 0

@register.filter
def sum_field(data_list, field_name):
    """جمع حقل معين من قائمة"""
    try:
        return sum(item[field_name] for item in data_list)
    except:
        return 0

@register.filter
def remove_param(query_string, param_name):
    """إزالة معامل من query string"""
    try:
        from urllib.parse import parse_qs, urlencode
        params = parse_qs(query_string)
        params.pop(param_name, None)
        return urlencode(params, doseq=True)
    except:
        return query_string

@register.filter
def mul(value, arg):
    """ضرب قيمتين"""
    try:
        return float(value) * float(arg)
    except:
        return 0
