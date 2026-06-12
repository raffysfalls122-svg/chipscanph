from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),

    # API endpoints
    path('api/login/', views.api_login, name='api_login'),
    path('api/chips/', views.api_chips, name='api_chips'),
    path('api/stats/', views.api_stats, name='api_stats'),
    path('api/scan/history/', views.api_scan_history, name='api_scan_history'),
    path('api/scan/image/', views.api_scan_image, name='api_scan_image'),
    path('api/chips/<str:code>/upload-image/', views.api_chip_upload_image, name='api_chip_upload_image'),
    path('api/prices/', views.api_prices, name='api_prices'),
    path('api/history/', views.api_history, name='api_history'),
    path('api/history/clear/', views.api_history_clear, name='api_history_clear'),
    path('api/chips/<str:code>/delete/', views.api_delete_chip, name='api_delete_chip'),
    path('api/users/', views.api_users, name='api_users'),
    path('api/users/<str:username>/delete/', views.api_delete_user, name='api_delete_user'),
    path('api/chips/<str:code>/check/', views.api_check_chip, name='api_check_chip'),
    path('api/approvals/submit/', views.api_submit_approval, name='api_submit_approval'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/approvals/', views.api_approvals_list, name='api_approvals_list'),
    path('api/approvals/<int:req_id>/action/', views.api_approval_action, name='api_approval_action'),

    # Camera streaming endpoints (shared for mobile and desktop)
    path('camera/stream/', views.stream_camera, name='stream_camera'),
    path('api/camera/capture/', views.api_camera_capture, name='api_camera_capture'),
]
