import sys

if sys.version_info[0] > 2:
    from django.urls import re_path as url, include # pylint: disable=no-name-in-module
else:
    from django.conf.urls import url, include

import django

urlpatterns = [
    url(r'^admin/', django.contrib.admin.site.urls),
    url(r'^enroll/', include('enrollment.urls')),
]
