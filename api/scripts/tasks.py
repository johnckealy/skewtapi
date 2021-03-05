from celery import shared_task
from scripts.query_madis import run as run_query_madis
from celery.decorators import task



@task(name="q_madis")
def q_madis():
    run_query_madis()
