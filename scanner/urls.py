from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    
    # API endpoints
    path('api/login/', views.api_login, name='api_login'),
    path('api/chips/', views.api_chips, name='api_chips'),
    path('api/chips/<str:code>/check/', views.api_check_chip, name='api_check_chip'),
    path('api/chips/<str:code>/delete/', views.api_delete_chip, name='api_delete_chip'),
    path('api/prices/', views.api_prices, name='api_prices'),
    path('api/history/', views.api_history, name='api_history'),
    path('api/history/clear/', views.api_clear_history, name='api_clear_history'),
    path('api/users/', views.api_users, name='api_users'),
    path('api/users/<str:username>/delete/', views.api_delete_user, name='api_delete_user'),
    path('api/stats/', views.api_stats, name='api_stats'),
]
