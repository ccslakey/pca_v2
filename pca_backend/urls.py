from pathlib import Path

from django.contrib import admin
from django.http import FileResponse, HttpResponse
from django.urls import include, path

_INDEX = Path(__file__).resolve().parent.parent / 'frontend' / 'dist' / 'index.html'


def spa_index(request, **kwargs):
    if _INDEX.exists():
        return FileResponse(open(_INDEX, 'rb'), content_type='text/html')
    return HttpResponse(
        '<p>Frontend not built. Run <code>npm run build</code> in frontend/.</p>',
        status=404,
    )


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('players.urls')),
    path('api/', include('stats.urls')),
    path('<path:path>', spa_index),
    path('', spa_index),
]
