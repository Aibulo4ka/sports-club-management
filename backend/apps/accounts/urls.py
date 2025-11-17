"""
API URL configuration for accounts app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

app_name = 'accounts'

# Create router for ViewSets
router = DefaultRouter()
router.register(r'clients', views.ClientViewSet, basename='client')
router.register(r'trainers', views.TrainerViewSet, basename='trainer')

urlpatterns = [
    # JWT Authentication
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile-detail'),
    path('profile/update/', views.ProfileUpdateView.as_view(), name='profile-update'),

    # Include router URLs for ViewSets
    path('', include(router.urls)),
]
