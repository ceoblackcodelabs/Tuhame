"""
Aggregation helpers for the admin Subscription Revenue dashboard
(analytics.views.SubscriptionRevenueView). Kept in the subscriptions app
since it's SubscriptionPayment-specific, but follows the exact same
bucketing approach as analytics/reports.py (UTC TruncDate, zero-filled
buckets) so both dashboards behave identically.
"""
from datetime import timedelta, timezone as dt_timezone

from django.db.models import Sum, Count
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone

from .models import SubscriptionPayment


def build_sum_series(queryset, date_field, value_field, start, end, group_by):
    """Same bucketing contract as analytics.reports.build_series, but sums
    `value_field` per bucket instead of counting rows - needed for revenue
    (KES per day), where a day with fewer transactions can still be worth
    more than a day with many."""
    trunc = TruncHour if group_by == 'hour' else TruncDate
    rows = (
        queryset.filter(**{f'{date_field}__gte': start, f'{date_field}__lte': end})
        .annotate(bucket=trunc(date_field, tzinfo=dt_timezone.utc))
        .values('bucket')
        .annotate(total=Sum(value_field))
        .order_by('bucket')
    )
    totals_by_bucket = {}
    for row in rows:
        bucket = row['bucket']
        if bucket is None:
            continue
        key = bucket.strftime('%Y-%m-%d %H') if group_by == 'hour' else bucket.strftime('%Y-%m-%d')
        totals_by_bucket[key] = float(row['total'] or 0)

    labels, values = [], []
    step = timedelta(hours=1) if group_by == 'hour' else timedelta(days=1)
    cursor = start.replace(minute=0, second=0, microsecond=0) if group_by == 'hour' else start.replace(hour=0, minute=0, second=0, microsecond=0)
    label_fmt = '%H:00' if group_by == 'hour' else '%b %d'
    while cursor <= end:
        key = cursor.strftime('%Y-%m-%d %H') if group_by == 'hour' else cursor.strftime('%Y-%m-%d')
        labels.append(cursor.strftime(label_fmt))
        values.append(totals_by_bucket.get(key, 0))
        cursor += step

    return labels, values


def build_count_series(queryset, date_field, start, end, group_by):
    """Transaction *volume* per bucket (all attempts, any status) -
    deliberately separate from revenue so a spike in failed/cancelled
    attempts is visible even on a day revenue didn't move."""
    trunc = TruncHour if group_by == 'hour' else TruncDate
    rows = (
        queryset.filter(**{f'{date_field}__gte': start, f'{date_field}__lte': end})
        .annotate(bucket=trunc(date_field, tzinfo=dt_timezone.utc))
        .values('bucket')
        .annotate(count=Count('id'))
        .order_by('bucket')
    )
    counts_by_bucket = {}
    for row in rows:
        bucket = row['bucket']
        if bucket is None:
            continue
        key = bucket.strftime('%Y-%m-%d %H') if group_by == 'hour' else bucket.strftime('%Y-%m-%d')
        counts_by_bucket[key] = row['count']

    labels, values = [], []
    step = timedelta(hours=1) if group_by == 'hour' else timedelta(days=1)
    cursor = start.replace(minute=0, second=0, microsecond=0) if group_by == 'hour' else start.replace(hour=0, minute=0, second=0, microsecond=0)
    label_fmt = '%H:00' if group_by == 'hour' else '%b %d'
    while cursor <= end:
        key = cursor.strftime('%Y-%m-%d %H') if group_by == 'hour' else cursor.strftime('%Y-%m-%d')
        labels.append(cursor.strftime(label_fmt))
        values.append(counts_by_bucket.get(key, 0))
        cursor += step

    return labels, values


def get_summary_stats(start, end):
    """The 4 top-of-page stat cards."""
    completed = SubscriptionPayment.objects.filter(
        status=SubscriptionPayment.STATUS_COMPLETED, completed_at__gte=start, completed_at__lte=end,
    )
    all_attempts = SubscriptionPayment.objects.filter(created_at__gte=start, created_at__lte=end)

    total_revenue = completed.aggregate(total=Sum('amount'))['total'] or 0
    total_attempts = all_attempts.count()
    completed_count = completed.count()
    success_rate = round(completed_count / total_attempts * 100, 1) if total_attempts else 0

    return {
        'total_revenue': total_revenue,
        'total_attempts': total_attempts,
        'completed_count': completed_count,
        'success_rate': success_rate,
    }


def get_status_breakdown(start, end):
    """The 3 stats below the transactions table - where the money that
    DIDN'T come in went, so nothing needs to be guessed at."""
    qs = SubscriptionPayment.objects.filter(created_at__gte=start, created_at__lte=end)
    counts = {row['status']: row['count'] for row in qs.values('status').annotate(count=Count('id'))}
    return {
        'failed_count': counts.get(SubscriptionPayment.STATUS_FAILED, 0),
        'cancelled_count': counts.get(SubscriptionPayment.STATUS_CANCELLED, 0),
        'timeout_count': counts.get(SubscriptionPayment.STATUS_TIMEOUT, 0),
    }


def get_recent_transactions(start, end, limit=50):
    return (
        SubscriptionPayment.objects.filter(created_at__gte=start, created_at__lte=end)
        .select_related('user', 'plan')
        .order_by('-created_at')[:limit]
    )
