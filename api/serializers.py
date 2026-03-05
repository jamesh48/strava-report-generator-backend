from rest_framework import serializers
from .models import Activity


class ActivitySerializer(serializers.ModelSerializer):
    activityId = serializers.IntegerField(source='activity_id')
    athleteId = serializers.CharField(source='athlete_id')
    startDate = serializers.DateTimeField(source='start_date')
    movingTime = serializers.IntegerField(source='moving_time')
    elapsedTime = serializers.IntegerField(source='elapsed_time')
    averageSpeed = serializers.FloatField(source='average_speed')
    maxSpeed = serializers.FloatField(source='max_speed')
    totalElevationGain = serializers.FloatField(source='total_elevation_gain')
    elevHigh = serializers.FloatField(source='elev_high')
    elevLow = serializers.FloatField(source='elev_low')
    averageHeartrate = serializers.FloatField(source='average_heartrate')
    maxHeartrate = serializers.FloatField(source='max_heartrate')
    locationCity = serializers.CharField(source='location_city')
    locationState = serializers.CharField(source='location_state')
    locationCountry = serializers.CharField(source='location_country')
    achievementCount = serializers.IntegerField(source='achievement_count')
    kudosCount = serializers.IntegerField(source='kudos_count')
    commentCount = serializers.IntegerField(source='comment_count')
    prCount = serializers.IntegerField(source='pr_count')

    class Meta:
        model = Activity
        fields = [
            'id', 'activityId', 'athleteId', 'name', 'type', 'startDate',
            'distance', 'movingTime', 'elapsedTime', 'averageSpeed', 'maxSpeed',
            'totalElevationGain', 'elevHigh', 'elevLow', 'averageHeartrate',
            'maxHeartrate', 'locationCity', 'locationState', 'locationCountry',
            'achievementCount', 'kudosCount', 'commentCount', 'prCount',
        ]
