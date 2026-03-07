import time
import os
import requests

from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from .models import Activity, StravaToken, UserSettings

STRAVA_TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"
STRAVA_ATHLETE_URL = "https://www.strava.com/api/v3/athlete"


def get_access_token(athlete_id: str) -> str:
    token = StravaToken.objects.get(athlete_id=athlete_id)

    if time.time() > token.expires_at:
        return _refresh_token(token)

    return token.access_token


def _refresh_token(token: StravaToken) -> str:
    response = requests.post(STRAVA_TOKEN_URL, data={
        'client_id': os.environ['STRAVA_CLIENT_ID'],
        'client_secret': os.environ['STRAVA_CLIENT_SECRET'],
        'grant_type': 'refresh_token',
        'refresh_token': token.refresh_token,
    })
    response.raise_for_status()
    data = response.json()

    token.access_token = data['access_token']
    token.refresh_token = data['refresh_token']
    token.expires_at = data['expires_at']
    token.save()

    return token.access_token


def exchange_token(code: str) -> str:
    response = requests.post(STRAVA_TOKEN_URL, data={
        'client_id': os.environ['STRAVA_CLIENT_ID'],
        'client_secret': os.environ['STRAVA_CLIENT_SECRET'],
        'code': code,
        'grant_type': 'authorization_code',
    })
    response.raise_for_status()
    data = response.json()

    athlete_id = str(data['athlete']['id'])
    StravaToken.objects.update_or_create(
        athlete_id=athlete_id,
        defaults={
            'access_token': data['access_token'],
            'refresh_token': data['refresh_token'],
            'expires_at': data['expires_at'],
        }
    )
    return athlete_id


def fetch_athlete_stats(athlete_id: str) -> dict:
    access_token = get_access_token(athlete_id)
    response = requests.get(
        f"https://www.strava.com/api/v3/athletes/{athlete_id}/stats/",
        headers={'Authorization': f'Bearer {access_token}'},
    )
    response.raise_for_status()
    return response.json()


SUPPORTED_TYPES = {'Run', 'Ride', 'Walk', 'Swim'}


def _fetch_strava_activities(access_token: str, page: int = 1) -> list:
    response = requests.get(
        'https://www.strava.com/api/v3/activities',
        headers={'Authorization': f'Bearer {access_token}'},
        params={'page': page, 'per_page': 200},
    )
    response.raise_for_status()
    data = response.json()
    if len(data) == 200:
        return data + _fetch_strava_activities(access_token, page + 1)
    return data


def add_all_activities(athlete_id: str) -> list:
    access_token = get_access_token(athlete_id)
    activities = _fetch_strava_activities(access_token)
    activities = [a for a in activities if a.get('type') in SUPPORTED_TYPES]

    objs = [
        Activity(
            athlete_id=athlete_id,
            activity_id=a['id'],
            name=a['name'],
            type=a['type'],
            start_date=a['start_date'],
            distance=a.get('distance', 0),
            moving_time=a.get('moving_time', 0),
            elapsed_time=a.get('elapsed_time', 0),
            average_speed=a.get('average_speed', 0),
            max_speed=a.get('max_speed', 0),
            total_elevation_gain=a.get('total_elevation_gain', 0),
            elev_high=a.get('elev_high'),
            elev_low=a.get('elev_low'),
            average_heartrate=a.get('average_heartrate'),
            max_heartrate=a.get('max_heartrate'),
            location_city=a.get('location_city'),
            location_state=a.get('location_state'),
            location_country=a.get('location_country'),
            achievement_count=a.get('achievement_count', 0),
            kudos_count=a.get('kudos_count', 0),
            comment_count=a.get('comment_count', 0),
            pr_count=a.get('pr_count', 0),
        )
        for a in activities
    ]

    Activity.objects.bulk_create(
        objs,
        update_conflicts=True,
        unique_fields=['activity_id'],
        update_fields=[
            'name', 'type', 'start_date', 'distance', 'moving_time',
            'elapsed_time', 'average_speed', 'max_speed', 'total_elevation_gain',
            'elev_high', 'elev_low', 'average_heartrate', 'max_heartrate',
            'location_city', 'location_state', 'location_country',
            'achievement_count', 'kudos_count', 'comment_count', 'pr_count',
        ],
    )

    return activities


def get_user_settings(athlete_id: str) -> dict:
    settings, _ = UserSettings.objects.get_or_create(athlete_id=athlete_id)
    return {
        'darkMode': settings.dark_mode,
        'defaultSport': settings.default_sport,
        'defaultFormat': settings.default_format,
        'defaultDate': settings.default_date,
    }


def save_user_settings(athlete_id: str, dark_mode: bool, default_sport: str, default_format: str, default_date: str) -> None:
    UserSettings.objects.update_or_create(
        athlete_id=athlete_id,
        defaults={
            'dark_mode': dark_mode,
            'default_sport': default_sport,
            'default_format': default_format,
            'default_date': default_date,
        }
    )


def update_activity(athlete_id: str, entry_id: str, name: str, description: str) -> None:
    access_token = get_access_token(athlete_id)

    response = requests.put(
        f"https://www.strava.com/api/v3/activities/{entry_id}",
        headers={'Authorization': f'Bearer {access_token}'},
        params={'name': name, 'description': description},
    )
    response.raise_for_status()

    Activity.objects.filter(athlete_id=athlete_id, activity_id=entry_id).update(
        name=name,
        description=description,
    )


def fetch_activity_stream(athlete_id: str, entry_id: str) -> dict:
    access_token = get_access_token(athlete_id)
    response = requests.get(
        f"https://www.strava.com/api/v3/activities/{entry_id}/streams",
        headers={'Authorization': f'Bearer {access_token}'},
        params={'keys': 'latlng', 'key_by_type': 'true'},
    )
    response.raise_for_status()
    return response.json()


def fetch_entry_kudos(athlete_id: str, entry_id: str) -> dict:
    access_token = get_access_token(athlete_id)

    kudos_response = requests.get(
        f"https://www.strava.com/api/v3/activities/{entry_id}/kudos",
        headers={'Authorization': f'Bearer {access_token}'},
    )
    kudos_response.raise_for_status()
    kudos = kudos_response.json()

    comments_response = requests.get(
        f"https://www.strava.com/api/v3/activities/{entry_id}/comments",
        headers={'Authorization': f'Bearer {access_token}'},
    )
    comments_response.raise_for_status()
    comments = comments_response.json()

    Activity.objects.filter(athlete_id=athlete_id, activity_id=entry_id).update(
        kudos_count=len(kudos),
        comment_count=len(comments),
    )

    return {'kudos': kudos, 'comments': comments}


def fetch_individual_entry(athlete_id: str, entry_id: str) -> dict:
    access_token = get_access_token(athlete_id)
    response = requests.get(
        f"https://www.strava.com/api/v3/activities/{entry_id}",
        headers={'Authorization': f'Bearer {access_token}'},
        params={'include_all_efforts': 'true'},
    )
    response.raise_for_status()
    data = response.json()

    Activity.objects.filter(athlete_id=athlete_id, activity_id=entry_id).update(
        individual_activity_cached=True,
        description=data.get('description', ''),
        device_name=data.get('device_name', ''),
        gear_name=(data.get('gear') or {}).get('name', ''),
        map_polyline=(data.get('map') or {}).get('polyline', ''),
        primary_photo_url=((data.get('photos') or {}).get('primary') or {}).get('urls', {}).get('600', ''),
        best_efforts=data.get('best_efforts', []),
        laps=data.get('laps', []),
        segment_efforts=data.get('segment_efforts', []),
    )

    return data


def fetch_monthly_stats(athlete_id: str, activity_type: str = 'Run') -> dict:
    rows = (
        Activity.objects
        .filter(athlete_id=athlete_id, type=activity_type)
        .annotate(month=TruncMonth('start_date'))
        .values('month')
        .annotate(count=Count('id'), distance=Sum('distance'))
        .order_by('-month')
    )
    return {
        row['month'].strftime('%Y-%m'): {
            'count': row['count'],
            'distance': row['distance'],
        }
        for row in rows
    }


def fetch_logged_in_user(athlete_id: str) -> dict:
    access_token = get_access_token(athlete_id)
    response = requests.get(
        STRAVA_ATHLETE_URL,
        headers={'Authorization': f'Bearer {access_token}'},
        params={'scope': 'profile:read_all'},
    )
    response.raise_for_status()
    return response.json()



@transaction.atomic
def destroy_user(athlete_id):
    Activity.objects.filter(athlete_id=athlete_id).delete()
    StravaToken.objects.filter(athlete_id=athlete_id).delete()
    UserSettings.objects.filter(athlete_id=athlete_id).delete()


def fetch_general_individual_entry(athlete_id, activity_id):
    activity = Activity.objects.get(athlete_id=athlete_id, activity_id=activity_id)
    return {
        'id': activity.activity_id,
        'name': activity.name,
        'type': activity.type,
        'start_date': activity.start_date,
        'distance': activity.distance,
        'moving_time': activity.moving_time,
        'elapsed_time': activity.elapsed_time,
        'average_speed': activity.average_speed,
        'max_speed': activity.max_speed,
        'total_elevation_gain': activity.total_elevation_gain,
        'elev_high': activity.elev_high,
        'elev_low': activity.elev_low,
        'average_heartrate': activity.average_heartrate,
        'max_heartrate': activity.max_heartrate,
        'achievement_count': activity.achievement_count,
        'kudos_count': activity.kudos_count,
        'comment_count': activity.comment_count,
        'pr_count': activity.pr_count,
        'calories': 0,
        'start_date_local': activity.start_date,
        'description': activity.description,
        'best_efforts': activity.best_efforts,
        'segment_efforts': activity.segment_efforts,
        'laps': activity.laps,
        'device_name': activity.device_name,
        'gear': {'name': activity.gear_name},
        'map': {'polyline': activity.map_polyline},
        'photos': {
            'count': 1 if activity.primary_photo_url else 0,
            'primary': {'urls': {'600': activity.primary_photo_url}},
        },
    }
