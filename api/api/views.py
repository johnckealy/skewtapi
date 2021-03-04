from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.shortcuts import render
from decimal import Decimal as d

from api.models import Radiosonde, Haversine
from api.serializers import RadiosondeSerializer, AvailableSerializer
from rest_framework.generics import get_object_or_404



class RadiosondeAPIView(APIView):
    def get(self, request):
        if request.method == 'GET':
            sonde = Radiosonde.objects.get(wmo_id=request.GET['wmo_id'])
            serializer = RadiosondeSerializer(sonde)
        return Response(serializer.data) 



class AvailableAPIView(APIView):
    def get(self, request):
        if request.method == 'GET':
            sondes = Radiosonde.objects.all()
            serializer = AvailableSerializer(sondes, many=True)
        return Response(serializer.data) 



class NearestAPIView(APIView):
    def get(self, request):
        if request.method == 'GET':
            lat = d(request.GET['lat'])
            lon = d(request.GET['lon'])
            available = Radiosonde.objects.filter(sonde_validtime__gt=(timezone.now() - timezone.timedelta(days=1)))
            latlon = {'lat': lat, 'lon': lon}
            if available:
                nearest = Haversine.closest(available, latlon)
                serializer = RadiosondeSerializer(nearest)
            else:
                return Response({ 'message': 'No Sondes less than 1 day old are available.' })
        return Response(serializer.data)


