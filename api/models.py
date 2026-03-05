from django.db import models


class StravaToken(models.Model):
    athlete_id = models.CharField(max_length=50, unique=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.BigIntegerField()

    class Meta:
        db_table = 'strava_tokens'


class UserSettings(models.Model):
    athlete_id = models.CharField(max_length=50, unique=True)
    dark_mode = models.BooleanField(default=False)
    default_sport = models.CharField(max_length=50, default='Run')
    default_format = models.CharField(max_length=50, default='speedDesc')
    default_date = models.CharField(max_length=50, default='allTime')

    class Meta:
        db_table = 'user_settings'


class Activity(models.Model):
    athlete_id = models.CharField(max_length=50, db_index=True)
    activity_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, db_index=True)
    start_date = models.DateTimeField()
    distance = models.FloatField(default=0)
    moving_time = models.IntegerField(default=0)
    elapsed_time = models.IntegerField(default=0)
    average_speed = models.FloatField(default=0)
    max_speed = models.FloatField(default=0)
    total_elevation_gain = models.FloatField(default=0)
    elev_high = models.FloatField(null=True, blank=True)
    elev_low = models.FloatField(null=True, blank=True)
    average_heartrate = models.FloatField(null=True, blank=True)
    max_heartrate = models.FloatField(null=True, blank=True)
    location_city = models.CharField(max_length=100, null=True, blank=True)
    location_state = models.CharField(max_length=100, null=True, blank=True)
    location_country = models.CharField(max_length=100, null=True, blank=True)
    achievement_count = models.IntegerField(default=0)
    kudos_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    pr_count = models.IntegerField(default=0)
    # Cached from individualEntry fetch
    individual_activity_cached = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    device_name = models.CharField(max_length=100, null=True, blank=True)
    gear_name = models.CharField(max_length=100, null=True, blank=True)
    map_polyline = models.TextField(null=True, blank=True)
    primary_photo_url = models.TextField(null=True, blank=True)
    best_efforts = models.JSONField(null=True, blank=True)
    laps = models.JSONField(null=True, blank=True)
    segment_efforts = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'activities'

