from rest_framework.routers import DefaultRouter
from .views import BattingSeasonViewSet, PitchingSeasonViewSet

router = DefaultRouter()
router.register(r'batting', BattingSeasonViewSet, basename='batting')
router.register(r'pitching', PitchingSeasonViewSet, basename='pitching')

urlpatterns = router.urls
