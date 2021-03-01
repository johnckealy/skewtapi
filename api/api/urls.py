from django.urls import path, re_path
from api.views import RadiosondeAPIView, AvailableAPIView, NearestAPIView 


urlpatterns = [
    path('available/', AvailableAPIView.as_view(), name="available-sondes"),
    re_path('sondes/$', RadiosondeAPIView.as_view(), name="get-sonde"),
    re_path('nearest/$', NearestAPIView.as_view(), name="nearest-sonde"),
] 