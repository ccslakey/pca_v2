from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import BattingSeasonViewSet, meta, PitchingSeasonViewSet

router = DefaultRouter()
router.register(r'batting', BattingSeasonViewSet, basename='batting')
router.register(r'pitching', PitchingSeasonViewSet, basename='pitching')

urlpatterns = router.urls + [
    path('meta/', meta, name='meta'),
]
