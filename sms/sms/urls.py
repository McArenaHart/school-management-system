from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("people/", include(("people.urls", "people"), namespace="people")),
    path("comms/", include(("comms.urls", "comms"), namespace="comms")),
    path("academics/", include(("academics.urls", "academics"), namespace="academics")),
    path("finance/", include(("finance.urls", "finance"), namespace="finance")),
    path("reports/", include(("reports.urls", "reports"), namespace="reports")),
    path("rbac/", include(("rbac.urls", "rbac"), namespace="rbac")),
    path("registrar/", include(("registrar.urls", "registrar"), namespace="registrar")),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
