"""URL configuration for config project."""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from garage import views as garage_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/register/', garage_views.register, name='register'),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('garage.urls')),
]
