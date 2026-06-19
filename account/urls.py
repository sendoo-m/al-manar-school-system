from django.urls import path
from . import views

app_name = 'account'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('change_password/', views.change_password, name='change_password'),
    path('password_change_done/', views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('view_profile/', views.view_profile, name='view_profile'),
    path('logout/', views.custom_logout, name='logout'),
    path('heartbeat/', views.heartbeat, name='heartbeat'),  # ← جديد

]

# from django.urls import path
# from django.contrib.auth.views import LoginView
# from . import views
# from django.contrib.auth.views import LogoutView

# app_name = 'account'

# urlpatterns = [
#     path('signup/', views.signup, name='signup'),
#     path('login/', views.login_view, name='login'),
#     path('change_password/', views.change_password, name='change_password'),
#     path('password_change_done/', views.PasswordChangeDoneView.as_view(), name='password_change_done'),
#     path('view_profile/', views.view_profile, name='view_profile'),
    
# ]
