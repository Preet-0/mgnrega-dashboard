from django.contrib import admin
from django.urls import path
from dashboard import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Main pages
    path('', views.index, name='index'),
    path('district/<str:district_code>/', views.district_detail, name='district_detail'),

    # API endpoints
    path('api/district/<str:district_code>/records/', views.district_records_api, name='district_records_api'),
    path('api/save-records/<str:district_code>/', views.save_records, name='save_records'),
]
