from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard_view, name='index'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('login/verify/', views.session_login_api, name='login_verify'),
    path('logout/', views.logout_view, name='logout'),
    path('api/session-login/', views.session_login_api, name='session_login_api'),
    path('documents/create/', views.document_create_view, name='document_create'),
    path('documents/<str:doc_id>/edit/', views.document_edit_view, name='document_edit'),
    path('documents/<str:doc_id>/delete/', views.document_delete_view, name='document_delete'),
    path('documents/<str:doc_id>/restore/', views.document_restore_view, name='document_restore'),
]
