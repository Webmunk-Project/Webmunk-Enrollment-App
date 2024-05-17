from django.contrib import admin
from django.conf.urls import url, include
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^quicksilver/', include('quicksilver.urls')),
    url(r'^export/', include('simple_data_export.urls')),
    url(r'^enroll/', include('enrollment.urls')),
]
