from django.urls import path
from rest_framework.routers import DefaultRouter

from .copilot_views import copilot_agui, copilot_tool, copilot_tools
from .views import PlayerViewSet

router = DefaultRouter()
router.register(r'players', PlayerViewSet, basename='player')

urlpatterns = [
    path('copilot/tools/', copilot_tools),
    path('copilot/tool/', copilot_tool),
    path('copilot/agui/', copilot_agui),
    *router.urls,
]
