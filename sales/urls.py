from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.query_view, name='query'),
    path('process/', views.process_query, name='process_query'),
]


