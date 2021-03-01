#!/bin/sh

set -e

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# python entry point commands go here
python manage.py migrate
python manage.py runscript initialize_stations
python manage.py runscript query_madis

exec "$@"
