# SkewT API

This is the Django REST FRAMEWORK backend for [skewt.org](skewt.org). It can produce upper atmosphere profiles 
of temperature, wind, and dewpoint temperature from radiosonde balloons all around the world. 

There are just three endpoints to api.skewt.org: 

Find the nearest radiosonde station to the specified latitude/longitude:

`https://api.skewt.org/api/nearest/?lat=51.5068&lon=-0.09078`

Return a list of all available radiosonde profiles:

`https://api.skewt.org/api/available`


Return the data for a particular station, based on the WMO identification number

`https://api.skewt.org/api/sondes/?wmo_id=03005`