from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('documents/search/', views.index_view, name='search'),
    path('documents/<str:doc_id>/', views.detail_view, name='detail'),
    path('documents/<str:doc_id>/download/', views.download_view, name='download'),
]
