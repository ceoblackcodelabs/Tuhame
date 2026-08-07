"""
Shared aggregation logic for the Traffic and Blog Analytics dashboards.
Uses Django's TruncDate/TruncHour (not raw SQL date functions) so this
works the same on SQLite in dev and MySQL in production - see
Tuhame/settings.py's DB_ENGINE switch.
"""
from datetime import timedelta, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone

from .models import PageVisit

RANGE_CHOICES = [
    ('24h', 'Last 24 hours'),
    ('7d', 'Last 7 days'),
    ('30d', 'Last 30 days'),
    ('90d', 'Last 90 days'),
]
DEFAULT_RANGE = '7d'


def get_range_bounds(range_key):
    """Returns (start, end, group_by) where group_by is 'hour' or 'day'."""
    end = timezone.now()
    if range_key == '24h':
        return end - timedelta(hours=24), end, 'hour'
    if range_key == '30d':
        return end - timedelta(days=30), end, 'day'
    if range_key == '90d':
        return end - timedelta(days=90), end, 'day'
    # default / '7d'
    return end - timedelta(days=7), end, 'day'


def _label_for(dt, group_by):
    return dt.strftime('%H:00' if group_by == 'hour' else '%b %d')


def build_series(queryset, date_field, start, end, group_by, count_field=None):
    """
    Buckets `queryset` by hour/day between start and end, filling in zero
    for buckets with no rows (otherwise a quiet day would just be missing
    from the chart instead of showing as zero, which reads as a data gap
    rather than "nothing happened").

    Explicitly truncates in UTC (tzinfo=dt_timezone.utc) rather than
    letting Django convert to settings.TIME_ZONE (Africa/Nairobi) first.
    On MySQL, that conversion goes through CONVERT_TZ(), which silently
    returns NULL if the server's timezone tables haven't been loaded
    (mysql_tzinfo_to_sql) - extremely common on shared hosting, where you
    don't have the access to run that yourself. When every row's Trunc
    result is NULL, every row collapses into one bucket=None group and
    this crashed instead of charting anything. Bucketing in UTC sidesteps
    that conversion entirely - the only cost is that day boundaries are
    UTC midnight rather than Nairobi midnight (a 3-hour offset), which
    doesn't affect a rough daily/hourly traffic chart in any way that
    matters here.
    """
    trunc = TruncHour if group_by == 'hour' else TruncDate
    rows = (
        queryset.filter(**{f'{date_field}__gte': start, f'{date_field}__lte': end})
        .exclude(**{f'{date_field}__isnull': True})
        .annotate(bucket=trunc(date_field, tzinfo=dt_timezone.utc))
        .values('bucket')
        .annotate(count=Count(count_field or 'id'))
        .order_by('bucket')
    )
    counts_by_bucket = {}
    for row in rows:
        bucket = row['bucket']
        if bucket is None:
            # Belt-and-suspenders: the exclude() above should already
            # prevent this, but a NULL date_field wrecking the whole
            # dashboard with a 500 is worse than silently dropping one
            # ungrouped row, so guard here too.
            continue
        key = bucket.strftime('%Y-%m-%d %H') if group_by == 'hour' else bucket.strftime('%Y-%m-%d')
        counts_by_bucket[key] = row['count']

    labels, values = [], []
    step = timedelta(hours=1) if group_by == 'hour' else timedelta(days=1)
    cursor = start.replace(minute=0, second=0, microsecond=0) if group_by == 'hour' else start.replace(hour=0, minute=0, second=0, microsecond=0)
    # Walk forward one bucket at a time so gaps show as real zeros.
    while cursor <= end:
        key = cursor.strftime('%Y-%m-%d %H') if group_by == 'hour' else cursor.strftime('%Y-%m-%d')
        labels.append(_label_for(cursor, group_by))
        values.append(counts_by_bucket.get(key, 0))
        cursor += step

    return labels, values


def get_visit_queryset(start, end, path_prefix=None, exact_path=None, exclude_bots=True):
    qs = PageVisit.objects.filter(visited_at__gte=start, visited_at__lte=end)
    if exact_path is not None:
        # '/' as a *prefix* would match every path on the site, since
        # every path starts with '/' - homepage-only tracking needs an
        # exact match instead.
        qs = qs.filter(path=exact_path)
    elif path_prefix:
        qs = qs.filter(path__startswith=path_prefix)
    if exclude_bots:
        qs = qs.exclude(device_type=PageVisit.DEVICE_BOT)
    return qs


def get_visit_queryset_for_paths(start, end, paths, exclude_bots=True):
    """Same as get_visit_queryset, but scoped to an explicit list of paths
    rather than a prefix - for "just this owner's properties", which don't
    share any prefix narrower than /property/listing/ (every property
    lives there, not just this owner's)."""
    qs = PageVisit.objects.filter(visited_at__gte=start, visited_at__lte=end, path__in=list(paths))
    if exclude_bots:
        qs = qs.exclude(device_type=PageVisit.DEVICE_BOT)
    return qs


def get_summary_stats(qs):
    total_views = qs.count()
    unique_visitors = qs.exclude(session_key='').values('session_key').distinct().count()
    return {
        'total_views': total_views,
        'unique_visitors': unique_visitors,
        'avg_views_per_visitor': round(total_views / unique_visitors, 1) if unique_visitors else 0,
    }


def get_device_breakdown(qs):
    total = qs.count()
    rows = qs.values('device_type').annotate(count=Count('id')).order_by('-count')
    device_labels = dict(PageVisit.DEVICE_CHOICES)
    result = []
    for row in rows:
        count = row['count']
        result.append({
            'device': device_labels.get(row['device_type'], row['device_type'].title()),
            'count': count,
            'pct': round(count / total * 100, 1) if total else 0,
        })
    return result


def get_location_breakdown(qs, limit=10):
    total = qs.count()
    rows = (
        qs.filter(location_resolved=True)
        .exclude(country='')
        .values('country')
        .annotate(count=Count('id'))
        .order_by('-count')[:limit]
    )
    result = [
        {'location': row['country'], 'count': row['count'], 'pct': round(row['count'] / total * 100, 1) if total else 0}
        for row in rows
    ]
    unresolved = qs.filter(location_resolved=False).count() + qs.filter(location_resolved=True, country='').count()
    if unresolved:
        result.append({
            'location': 'Unknown',
            'count': unresolved,
            'pct': round(unresolved / total * 100, 1) if total else 0,
        })
    return result


def get_top_paths(qs, limit=8):
    rows = qs.values('path').annotate(count=Count('id')).order_by('-count')[:limit]
    return [{'path': row['path'], 'count': row['count']} for row in rows]


def get_new_users_series(start, end, group_by):
    User = get_user_model()
    return build_series(User.objects.all(), 'date_joined', start, end, group_by)


def get_day_of_week_breakdown(qs):
    """How visit volume breaks down across Mon-Sun - useful for a
    single-page view (like the homepage) where a 'top pages' chart
    wouldn't mean anything, since there's only one page."""
    from django.db.models.functions import ExtractWeekDay
    # Django's ExtractWeekDay is 1=Sunday..7=Saturday regardless of DB backend.
    # Same tzinfo=UTC reasoning as build_series() above - avoids MySQL's
    # CONVERT_TZ() requiring timezone tables that may not be loaded.
    day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    rows = dict(
        qs.exclude(visited_at__isnull=True)
        .annotate(weekday=ExtractWeekDay('visited_at', tzinfo=dt_timezone.utc))
        .values('weekday')
        .annotate(count=Count('id'))
        .values_list('weekday', 'count')
    )
    return [{'day': day_names[i - 1], 'count': rows.get(i, 0)} for i in range(1, 8)]
