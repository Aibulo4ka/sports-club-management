"""
URL configuration for memberships app API endpoints
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MembershipTypeViewSet, MembershipViewSet, PriceCalculationViewSet

# Create router for ViewSets
router = DefaultRouter()
router.register(r'types', MembershipTypeViewSet, basename='membershiptype')
router.register(r'', MembershipViewSet, basename='membership')

app_name = 'memberships'

urlpatterns = [
    # Price calculation endpoint
    path('calculate-price/', PriceCalculationViewSet.as_view({'post': 'calculate'}), name='calculate-price'),

    # Router URLs (must be last)
    path('', include(router.urls)),
]

"""
API Endpoints provided:

MembershipType:
- GET    /api/memberships/types/                  - List all membership types (admin)
- POST   /api/memberships/types/                  - Create membership type (admin)
- GET    /api/memberships/types/{id}/             - Get membership type details (admin)
- PUT    /api/memberships/types/{id}/             - Update membership type (admin)
- PATCH  /api/memberships/types/{id}/             - Partial update (admin)
- DELETE /api/memberships/types/{id}/             - Delete membership type (admin)
- GET    /api/memberships/types/catalog/          - Get catalog with prices (authenticated users)

Membership:
- GET    /api/memberships/                        - List memberships (admin: all, user: own)
- POST   /api/memberships/                        - Purchase membership (authenticated)
- GET    /api/memberships/{id}/                   - Get membership details
- PUT    /api/memberships/{id}/                   - Update membership (admin)
- PATCH  /api/memberships/{id}/                   - Partial update (admin)
- DELETE /api/memberships/{id}/                   - Suspend membership (admin)
- GET    /api/memberships/my/                     - Get current user's memberships
- GET    /api/memberships/active/                 - Get current user's active memberships
- POST   /api/memberships/{id}/suspend/           - Suspend membership (admin)
- POST   /api/memberships/{id}/activate/          - Activate membership (admin)
- POST   /api/memberships/{id}/check_visit/       - Mark visit and decrement counter

Price Calculation:
- POST   /api/memberships/calculate-price/        - Calculate price with discount
"""
