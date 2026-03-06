import os

import psycopg2
from psycopg2 import sql
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Creates the application database if it does not exist'

    def handle(self, *args, **options):
        db_name = os.environ.get('DB_NAME', 'strava_report')
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            port=os.environ.get('DB_PORT', 5432),
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASSWORD', ''),
            dbname='postgres',
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute('SELECT 1 FROM pg_database WHERE datname = %s', [db_name])
        if not cur.fetchone():
            cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(db_name)))
            self.stdout.write(self.style.SUCCESS(f'Created database "{db_name}"'))
        else:
            self.stdout.write(f'Database "{db_name}" already exists')
        cur.close()
        conn.close()
