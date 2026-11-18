from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("apps.usuarios.urls")),
    path("api/", include("apps.municipios.urls")),
    path("api/", include("apps.orcamento.urls")),
    path("api/", include("apps.fiscal.urls")),
    path("api/", include("apps.financeiro.urls")),
    path("api/", include("apps.importacao.urls")),
    path("api/", include("apps.execucao_fiscal.urls")),
    path("api/", include("apps.parametros.urls")),
    path("api/", include("apps.obrigacoes.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
