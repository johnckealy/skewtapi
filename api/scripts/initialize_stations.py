from api.models import Station, HitCounter


def run():
    HitCounter.objects.create( hit_count=0 )
    Station.initialize_stations()

