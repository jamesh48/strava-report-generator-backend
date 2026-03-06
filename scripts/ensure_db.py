#!/usr/bin/env python
"""Creates the application database if it does not exist. Runs before Django."""
import os
import sys

import psycopg2
from psycopg2 import sql

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
    print(f'Created database "{db_name}"')
else:
    print(f'Database "{db_name}" already exists')
cur.close()
conn.close()
