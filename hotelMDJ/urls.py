"""Root URL configuration for the Hotel MDJ project.

Two presentation layers are mounted over the same business core:

* ``/``        -> server-rendered pages (``web`` app)
* ``/api/v1/`` -> JSON REST API (``reservation.api``)

The API is versioned from day one so that a future API Gateway can route
``/api/v1/*`` to this service while a ``/api/v2/*`` is rolled out alongside it.
"""

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # POST /i18n/setlang/ (name "set_language"): stores the chosen language in
    # a cookie and redirects back to the page given in ``next``.
    path("i18n/", include("django.conf.urls.i18n")),
    path("api/v1/", include("reservation.api.urls")),
    path("", include("web.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
