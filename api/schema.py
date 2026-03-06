import graphene
from graphene_django import DjangoObjectType
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from .models import Activity, UserSettings


class ActivityType(DjangoObjectType):
    class Meta:
        model = Activity
        fields = [
            'id', 'activity_id', 'athlete_id', 'name', 'type', 'start_date',
            'distance', 'moving_time', 'elapsed_time', 'average_speed', 'max_speed',
            'total_elevation_gain', 'elev_high', 'elev_low', 'average_heartrate',
            'max_heartrate', 'location_city', 'location_state', 'location_country',
            'achievement_count', 'kudos_count', 'comment_count', 'pr_count',
            'individual_activity_cached', 'description', 'device_name', 'gear_name',
            'map_polyline', 'primary_photo_url', 'best_efforts', 'laps', 'segment_efforts',
        ]


class UserSettingsType(DjangoObjectType):
    class Meta:
        model = UserSettings
        fields = ['athlete_id', 'dark_mode', 'default_sport', 'default_format', 'default_date']


class MonthlyStatType(graphene.ObjectType):
    month = graphene.String()
    count = graphene.Int()
    distance = graphene.Float()


class PaginatedActivities(graphene.ObjectType):
    items = graphene.List(ActivityType)
    total = graphene.Int()
    next_offset = graphene.Int()


class Query(graphene.ObjectType):
    activities = graphene.Field(
        PaginatedActivities,
        athlete_id=graphene.String(required=True),
        activity_type=graphene.String(),
        min_distance=graphene.Float(),
        has_achievements=graphene.Boolean(),
        search=graphene.String(),
        after_date=graphene.Date(),
        before_date=graphene.Date(),
        sort_condition=graphene.String(),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    activity = graphene.Field(ActivityType, activity_id=graphene.String(required=True))

    user_settings = graphene.Field(UserSettingsType, athlete_id=graphene.String(required=True))

    monthly_stats = graphene.List(
        MonthlyStatType,
        athlete_id=graphene.String(required=True),
        activity_type=graphene.String(),
    )

    def resolve_activities(root, info, athlete_id, activity_type=None, min_distance=None,
                           has_achievements=False, search=None, after_date=None,
                           before_date=None, sort_condition=None,
                           limit=None, offset=None):
        limit = limit or 50
        offset = offset or 0
        min_distance = min_distance or 0
        sort_condition = sort_condition or 'speedDesc'
        sort_map = {
            'speedDesc':       '-average_speed',
            'dateDesc':        '-start_date',
            'dateAsc':         'start_date',
            'movingTimeDesc':  '-moving_time',
            'movingTimeAsc':   'moving_time',
            'timeElapsedDesc': '-elapsed_time',
            'timeElapsedAsc':  'elapsed_time',
            'distanceDesc':    '-distance',
        }

        qs = Activity.objects.filter(athlete_id=athlete_id, distance__gte=min_distance)

        if activity_type:
            qs = qs.filter(type=activity_type)
        if has_achievements:
            qs = qs.filter(achievement_count__gt=0)
        else:
            qs = qs.filter(achievement_count=0)
        if search:
            qs = qs.filter(name__icontains=search)
        if after_date:
            qs = qs.filter(start_date__date__gte=after_date)
        if before_date:
            qs = qs.filter(start_date__date__lte=before_date)

        qs = qs.order_by(sort_map.get(sort_condition, '-average_speed'))
        total = qs.count()
        page = qs[offset:offset + limit]
        next_offset = offset + limit if offset + limit < total else None

        return PaginatedActivities(items=page, total=total, next_offset=next_offset)

    def resolve_monthly_stats(root, info, athlete_id, activity_type=None):
        activity_type = activity_type or 'Run'
        rows = (
            Activity.objects
            .filter(athlete_id=athlete_id, type=activity_type)
            .annotate(month=TruncMonth('start_date'))
            .values('month')
            .annotate(count=Count('id'), distance=Sum('distance'))
            .order_by('-month')
        )
        return [
            MonthlyStatType(
                month=row['month'].strftime('%Y-%m'),
                count=row['count'],
                distance=row['distance'],
            )
            for row in rows
        ]

    def resolve_activity(root, info, activity_id):
        return Activity.objects.get(activity_id=activity_id)

    def resolve_user_settings(root, info, athlete_id):
        settings, _ = UserSettings.objects.get_or_create(athlete_id=athlete_id)
        return settings


schema = graphene.Schema(query=Query)
