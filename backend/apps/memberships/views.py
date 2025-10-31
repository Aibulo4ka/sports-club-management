"""
API views for memberships app (REST API)
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import MembershipType, Membership, MembershipStatus
from .serializers import (
    MembershipTypeSerializer, MembershipTypeWithPriceSerializer,
    MembershipSerializer, MembershipCreateSerializer,
    MembershipUpdateSerializer, PriceCalculationSerializer
)


class MembershipTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for MembershipType CRUD operations (admin only)

    Provides:
    - list: GET /api/memberships/types/
    - create: POST /api/memberships/types/
    - retrieve: GET /api/memberships/types/{id}/
    - update: PUT/PATCH /api/memberships/types/{id}/
    - destroy: DELETE /api/memberships/types/{id}/
    """
    queryset = MembershipType.objects.all()
    serializer_class = MembershipTypeSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'duration_days']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'duration_days', 'created_at']
    ordering = ['price']

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def catalog(self, request):
        """
        Get catalog of active membership types with prices calculated for current user
        GET /api/memberships/types/catalog/
        """
        # Get active membership types
        active_types = self.queryset.filter(is_active=True)

        # Get client if user is authenticated
        client = None
        if hasattr(request.user, 'profile') and hasattr(request.user.profile, 'client'):
            client = request.user.profile.client

        # Serialize with price calculation
        serializer = MembershipTypeWithPriceSerializer(
            active_types,
            many=True,
            context={'client': client}
        )

        return Response(serializer.data)


class MembershipViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Membership operations

    Provides:
    - list: GET /api/memberships/ (admin: all, user: own)
    - create: POST /api/memberships/ (purchase membership)
    - retrieve: GET /api/memberships/{id}/
    - update: PUT/PATCH /api/memberships/{id}/ (admin only)
    - destroy: DELETE /api/memberships/{id}/ (admin only - soft delete)
    """
    queryset = Membership.objects.select_related(
        'client__profile__user', 'membership_type'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'membership_type']
    ordering_fields = ['start_date', 'end_date', 'purchased_at']
    ordering = ['-purchased_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return MembershipCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MembershipUpdateSerializer
        return MembershipSerializer

    def get_queryset(self):
        """
        Filter queryset:
        - Admin sees all memberships
        - Regular users see only their own memberships
        """
        if self.request.user.is_staff:
            return self.queryset

        # Regular users see only their own memberships
        if hasattr(self.request.user, 'profile') and hasattr(self.request.user.profile, 'client'):
            return self.queryset.filter(client=self.request.user.profile.client)

        return Membership.objects.none()

    def perform_destroy(self, instance):
        """
        Soft delete: set status to SUSPENDED instead of deleting
        (preserves data integrity for payments, analytics)
        """
        instance.status = MembershipStatus.SUSPENDED
        instance.save()

    @action(detail=False, methods=['get'])
    def my(self, request):
        """
        Get current user's memberships
        GET /api/memberships/my/
        """
        if not hasattr(request.user, 'profile') or not hasattr(request.user.profile, 'client'):
            return Response(
                {'error': '>;L7>20B5;L =5 O2;O5BAO :;85=B><'},
                status=status.HTTP_400_BAD_REQUEST
            )

        client = request.user.profile.client
        memberships = self.queryset.filter(client=client)

        serializer = self.get_serializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get current user's active memberships
        GET /api/memberships/active/
        """
        if not hasattr(request.user, 'profile') or not hasattr(request.user.profile, 'client'):
            return Response(
                {'error': '>;L7>20B5;L =5 O2;O5BAO :;85=B><'},
                status=status.HTTP_400_BAD_REQUEST
            )

        client = request.user.profile.client
        today = timezone.now().date()

        # Get active memberships that are not expired
        active_memberships = self.queryset.filter(
            client=client,
            status=MembershipStatus.ACTIVE,
            end_date__gte=today
        )

        serializer = self.get_serializer(active_memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def suspend(self, request, pk=None):
        """
        Suspend membership (admin only)
        POST /api/memberships/{id}/suspend/
        """
        membership = self.get_object()
        membership.status = MembershipStatus.SUSPENDED
        membership.save()

        serializer = self.get_serializer(membership)
        return Response({
            'message': '1>=5<5=B ?@8>AB0=>2;5=',
            'membership': serializer.data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def activate(self, request, pk=None):
        """
        Activate suspended membership (admin only)
        POST /api/memberships/{id}/activate/
        """
        membership = self.get_object()

        # Check if not expired
        if membership.end_date < timezone.now().date():
            return Response(
                {'error': '52>7<>6=> 0:B828@>20BL 8AB5:H89 01>=5<5=B'},
                status=status.HTTP_400_BAD_REQUEST
            )

        membership.status = MembershipStatus.ACTIVE
        membership.save()

        serializer = self.get_serializer(membership)
        return Response({
            'message': '1>=5<5=B 0:B828@>20=',
            'membership': serializer.data
        })

    @action(detail=True, methods=['post'])
    def check_visit(self, request, pk=None):
        """
        Check if membership allows a visit and decrement visits_remaining
        POST /api/memberships/{id}/check_visit/

        Used by staff to mark a client's visit
        """
        membership = self.get_object()

        # Check if membership is active
        if membership.status != MembershipStatus.ACTIVE:
            return Response(
                {'error': f'1>=5<5=B =5 0:B825=. !B0BCA: {membership.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if not expired
        today = timezone.now().date()
        if membership.end_date < today:
            # Auto-expire
            membership.status = MembershipStatus.EXPIRED
            membership.save()
            return Response(
                {'error': '1>=5<5=B 8ABQ:'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check visits remaining (if limited)
        if membership.visits_remaining is not None:
            if membership.visits_remaining <= 0:
                return Response(
                    {'error': 'AG5@?0= ;8<8B ?>A5I5=89'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Decrement visits
            membership.visits_remaining -= 1
            membership.save()

        serializer = self.get_serializer(membership)
        return Response({
            'message': '>A5I5=85 70AG8B0=>',
            'membership': serializer.data,
            'visits_remaining': membership.visits_remaining
        })


class PriceCalculationViewSet(viewsets.ViewSet):
    """
    ViewSet for calculating membership prices with discounts

    Provides:
    - POST /api/memberships/calculate-price/ - Calculate price preview
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """
        Calculate price for a membership with discount
        POST /api/memberships/calculate-price/

        Body:
        {
            "membership_type_id": 1,
            "client_id": 5
        }
        """
        serializer = PriceCalculationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Calculate pricing
        pricing_info = serializer.calculate()

        return Response(pricing_info)
