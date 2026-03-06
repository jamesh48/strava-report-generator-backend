import os
from django.shortcuts import redirect as django_redirect
from rest_framework.decorators import api_view
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework import status

from .models import Activity, StravaToken
from .serializers import ActivitySerializer
from .services import add_all_activities, exchange_token, fetch_activity_stream, fetch_athlete_stats, fetch_entry_kudos, fetch_individual_entry, fetch_logged_in_user, fetch_monthly_stats, get_user_settings, save_user_settings, update_activity


@api_view(['GET'])
def healthcheck(request):
    return Response({'status': 'ok'})


@api_view(['GET'])
def auth(request):
    client_id = os.environ.get('STRAVA_CLIENT_ID')
    redirect_uri = os.environ.get('STRAVA_REDIRECT_URI')
    url = (
        f"http://www.strava.com/oauth/authorize?client_id={client_id}"
        f"&response_type=code&redirect_uri={redirect_uri}"
        f"&approval_prompt=force&scope=profile:read_all,activity:read_all"
    )
    return django_redirect(url)

@api_view(['GET'])
def exchange_token_view(request):
    code = request.query_params.get('code')

    if not code:
        return Response({'error': 'code is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        athlete_id = exchange_token(code)
        return Response(athlete_id)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_athlete_stats(request, athlete_id):
    try:
        data = fetch_athlete_stats(athlete_id)
        return Response(data)
    except StravaToken.DoesNotExist:
        return Response({'error': 'Athlete not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_user_settings_view(request):
    athlete_id = request.query_params.get('srg_athlete_id')

    if not athlete_id:
        return Response({'error': 'srg_athlete_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        return Response(get_user_settings(athlete_id))
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def save_user_settings_view(request):
    athlete_id = request.query_params.get('srg_athlete_id')

    if not athlete_id:
        return Response({'error': 'srg_athlete_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        save_user_settings(
            athlete_id=athlete_id,
            dark_mode=request.data.get('darkMode', False),
            default_sport=request.data.get('defaultSport', 'Run'),
            default_format=request.data.get('defaultFormat', 'speedDesc'),
            default_date=request.data.get('defaultDate', 'allTime'),
        )
        return Response({'message': 'success'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
def put_activity_update(request):
    athlete_id = request.query_params.get('srg_athlete_id')
    entry_id = request.query_params.get('entry_id')
    name = request.query_params.get('name')
    description = request.query_params.get('description')

    if not all([athlete_id, entry_id, name, description]):
        return Response({'error': 'srg_athlete_id, entry_id, name, and description are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        update_activity(athlete_id, entry_id, name, description)
        return Response({'message': 'updated activity!'})
    except StravaToken.DoesNotExist:
        return Response({'error': 'Athlete not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_activity_stream(request, entry_id):
    athlete_id = request.query_params.get('srg_athlete_id')

    if not athlete_id:
        return Response({'error': 'srg_athlete_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        data = fetch_activity_stream(athlete_id, entry_id)
        return Response(data)
    except StravaToken.DoesNotExist:
        return Response({'error': 'Athlete not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_entry_kudos(request, entry_id):
    athlete_id = request.query_params.get('srg_athlete_id')

    if not athlete_id:
        return Response({'error': 'srg_athlete_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        data = fetch_entry_kudos(athlete_id, entry_id)
        return Response(data)
    except StravaToken.DoesNotExist:
        return Response({'error': 'Athlete not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_individual_entry(request, entry_id):
    athlete_id = request.query_params.get('srg_athlete_id')

    if not athlete_id:
        return Response({'error': 'srg_athlete_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        data = fetch_individual_entry(athlete_id, entry_id)
        return Response(data)
    except StravaToken.DoesNotExist:
        return Response({'error': 'Athlete not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_all_entries(request):
    athlete_id = request.query_params.get('srg_athlete_id')
    activity_type = request.query_params.get('activity_type')
    min_distance = request.query_params.get('min_distance', 0)
    after_date = request.query_params.get('after_date')
    before_date = request.query_params.get('before_date')

    qs = Activity.objects.filter(athlete_id=athlete_id, type=activity_type, distance__gte=min_distance)

    if after_date:
        qs = qs.filter(start_date__date__gte=after_date)
    if before_date:
        qs = qs.filter(start_date__date__lte=before_date)

    search = request.query_params.get('search')
    if search:
        qs = qs.filter(name__icontains=search)

    has_achievements = request.query_params.get('has_achievements', 'false')
    if has_achievements == 'true':
        qs = qs.filter(achievement_count__gt=0)
    else:
        qs = qs.filter(achievement_count=0)

    sort_map = {
        'speedDesc':        '-average_speed',
        'dateDesc':         '-start_date',
        'dateAsc':          'start_date',
        'movingTimeDesc':   '-moving_time',
        'movingTimeAsc':    'moving_time',
        'timeElapsedDesc':  '-elapsed_time',
        'timeElapsedAsc':   'elapsed_time',
        'distanceDesc':     '-distance',
    }
    sort_condition = request.query_params.get('sort_condition', 'speedDesc')
    qs = qs.order_by(sort_map.get(sort_condition, '-average_speed'))

    paginator = LimitOffsetPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(ActivitySerializer(page, many=True).data)

@api_view(['GET'])
def get_monthly_stats(request):
    athlete_id = request.query_params.get('srg_athlete_id')
    activity_type = request.query_params.get('activity_type', 'Run')

    if not athlete_id:
        return Response({'error': 'srg_athlete_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        data = fetch_monthly_stats(athlete_id, activity_type)
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def add_all_activities_view(request):
    athlete_id = request.query_params.get('srg_athlete_id')

    if not athlete_id:
        return Response({'error': 'srg_athlete_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        activities = add_all_activities(athlete_id)
        return Response(activities)
    except StravaToken.DoesNotExist:
        return Response({'error': 'Athlete not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_logged_in_user(request):
    athlete_id = request.query_params.get('srg_athlete_id')
    print('ok')
    if not athlete_id:
        return Response({'error': 'srg_athlete_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        data = fetch_logged_in_user(athlete_id)
        return Response(data)
    except StravaToken.DoesNotExist:
        return Response({'error': 'Athlete not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
