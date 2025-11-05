"""
API views for accounts app (REST API)
"""

from rest_framework import generics, status, viewsets, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend
from .models import Profile, Client, Trainer
from .serializers import (
    RegisterSerializer, ProfileSerializer,
    ClientSerializer, ClientCreateSerializer, ClientUpdateSerializer,
    TrainerSerializer
)


class RegisterView(generics.CreateAPIView):
    """
    Register a new user (client)
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class LogoutView(APIView):
    """
    Logout user (blacklist JWT token)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            # TODO: Add JWT token to blacklist
            return Response({"detail": "Успешный выход"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveAPIView):
    """
    Get current user's profile
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user.profile


class ProfileUpdateView(generics.UpdateAPIView):
    """
    Update current user's profile
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user.profile


class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Client CRUD operations (admin only)

    Provides:
    - list: GET /api/clients/
    - create: POST /api/clients/
    - retrieve: GET /api/clients/{id}/
    - update: PUT/PATCH /api/clients/{id}/
    - destroy: DELETE /api/clients/{id}/
    """
    queryset = Client.objects.select_related('profile__user').all()
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['profile__user__first_name', 'profile__user__last_name', 'profile__user__email', 'profile__phone']
    ordering_fields = ['profile__created_at', 'profile__user__first_name']
    ordering = ['-profile__created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ClientCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ClientUpdateSerializer
        return ClientSerializer

    def perform_destroy(self, instance):
        """
        Soft delete: deactivate user instead of deleting
        (preserves data integrity for payments, bookings)
        """
        instance.profile.user.is_active = False
        instance.profile.user.save()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate deactivated client"""
        client = self.get_object()
        client.profile.user.is_active = True
        client.profile.user.save()
        return Response({'status': 'Клиент активирован'})

    @action(detail=False, methods=['get'])
    def students(self, request):
        """Get list of student clients"""
        students = self.queryset.filter(is_student=True)
        serializer = self.get_serializer(students, many=True)
        return Response(serializer.data)


class TrainerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Trainer CRUD operations (admin only)
    """
    queryset = Trainer.objects.select_related('profile__user').filter(is_active=True)
    serializer_class = TrainerSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['profile__user__first_name', 'profile__user__last_name', 'specialization']

    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        """Get trainer's schedule"""
        trainer = self.get_object()
        # TODO: Implement schedule retrieval (Sprint 3)
        return Response({'message': 'Schedule feature coming in Sprint 3'})
