from django.urls import path
from . import views
from .views import daily_report_view, monthly_report_view

app_name = 'report'
urlpatterns = [
    path('daily-report/', daily_report_view, name='daily_report'),
    path('monthly-report/', monthly_report_view, name='monthly_report'),
    path('installments-unpaid/', views.installments_unpaid_report, name='installments_unpaid_report'),
    path('expenses/', views.expenses_report, name='expenses_report'),
]
