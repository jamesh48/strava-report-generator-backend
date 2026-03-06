from django.urls import path
from .views import add_all_activities_view, auth, exchange_token_view, get_activity_stream, get_all_entries, get_athlete_stats, get_entry_kudos, get_individual_entry, get_logged_in_user, get_user_settings_view, put_activity_update, save_user_settings_view

urlpatterns = [
    path('auth', auth),
    path('exchange_token', exchange_token_view),
    path('getLoggedInUser', get_logged_in_user),
    path('getAthleteStats/<str:athlete_id>', get_athlete_stats),
    path('addAllActivities', add_all_activities_view),
    path('allActivities', get_all_entries),
    path('individualEntry/<str:entry_id>', get_individual_entry),
    path('entryKudos/<str:entry_id>', get_entry_kudos),
    path('activityStream/<str:entry_id>', get_activity_stream),
    path('activityUpdate', put_activity_update),
    path('getUserSettings', get_user_settings_view),
    path('saveUserSettings', save_user_settings_view),
]
