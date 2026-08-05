# core/management/commands/aggregate_analytics.py
"""
Nightly analytics aggregation + retention.

1. Fills DailyAnalytics / HourlyAnalytics from the raw tables for every
   complete day (strictly before today) that has raw data and no aggregate yet.
2. Prunes raw analytics rows older than the retention window (default 90 days):
   PageView, UserActivity, SearchLog, PostcardInteraction, RealTimeVisitor.
   IPLocation (the geolocation cache) is always kept.

Usage:
    manage.py aggregate_analytics
    manage.py aggregate_analytics --retention-days 120
    manage.py aggregate_analytics --no-prune
    manage.py aggregate_analytics --rebuild   # recompute existing aggregates too
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Min
from django.utils import timezone

from core.models import (
    ContactMessage, CustomUser, DailyAnalytics, HourlyAnalytics, PageView,
    PostcardInteraction, PostcardLike, RealTimeVisitor, SearchLog,
    AnimationSuggestion, UserActivity, VisitorSession,
)

PRUNE_SPECS = [
    (PageView, 'timestamp'),
    (UserActivity, 'timestamp'),
    (SearchLog, 'created_at'),
    (PostcardInteraction, 'timestamp'),
    (RealTimeVisitor, 'last_activity'),
]


def _top_counts(queryset, field, limit=10):
    """{value: count} dict of the top values of `field` in queryset."""
    rows = (
        queryset.exclude(**{field: ''})
        .values(field)
        .annotate(n=Count('id'))
        .order_by('-n')[:limit]
    )
    return {row[field]: row['n'] for row in rows}


class Command(BaseCommand):
    help = ('Aggregate raw analytics into DailyAnalytics/HourlyAnalytics and '
            'prune raw rows older than the retention window (IPLocation kept)')

    def add_arguments(self, parser):
        parser.add_argument(
            '--retention-days', type=int, default=90,
            help='Days of raw analytics data to keep (default: 90)',
        )
        parser.add_argument(
            '--no-prune', action='store_true',
            help='Aggregate only, do not delete old raw rows',
        )
        parser.add_argument(
            '--rebuild', action='store_true',
            help='Recompute days that already have a DailyAnalytics row',
        )

    def handle(self, *args, **options):
        retention_days = options['retention_days']
        prune = not options['no_prune']
        rebuild = options['rebuild']

        today = timezone.localdate()

        # ---- find the day range with raw data ----
        first_dates = [
            d for d in (
                PageView.objects.aggregate(d=Min('timestamp'))['d'],
                VisitorSession.objects.aggregate(d=Min('first_visit'))['d'],
                SearchLog.objects.aggregate(d=Min('created_at'))['d'],
                PostcardLike.objects.aggregate(d=Min('created_at'))['d'],
            ) if d is not None
        ]

        if not first_dates:
            self.stdout.write('No raw analytics data found — nothing to aggregate.')
        else:
            start_date = min(
                (timezone.localtime(d) if timezone.is_aware(d) else d).date()
                for d in first_dates
            )
            existing = set(
                DailyAnalytics.objects.values_list('date', flat=True)
            )

            aggregated = 0
            day = start_date
            while day < today:  # complete days only
                if rebuild or day not in existing:
                    self.aggregate_day(day)
                    aggregated += 1
                day += timedelta(days=1)

            self.stdout.write(self.style.SUCCESS(
                f'Aggregated {aggregated} day(s) '
                f'({start_date} → {today - timedelta(days=1)}).'
            ))

        # ---- retention ----
        if prune:
            cutoff = timezone.now() - timedelta(days=retention_days)
            self.stdout.write('')
            self.stdout.write(f'Pruning raw analytics rows older than {retention_days} days:')
            for model, field in PRUNE_SPECS:
                deleted, _ = model.objects.filter(**{f'{field}__lt': cutoff}).delete()
                self.stdout.write(f'  {model.__name__}: {deleted} row(s) deleted')
            self.stdout.write('  IPLocation: kept (geolocation cache)')
        else:
            self.stdout.write('Prune skipped (--no-prune).')

    # ------------------------------------------------------------------

    def aggregate_day(self, day):
        """Compute and upsert DailyAnalytics + 24 HourlyAnalytics rows for one day."""
        page_views_qs = PageView.objects.filter(timestamp__date=day)
        sessions_qs = VisitorSession.objects.filter(first_visit__date=day)
        searches_qs = SearchLog.objects.filter(created_at__date=day)
        likes_qs = PostcardLike.objects.filter(created_at__date=day)
        activities_qs = UserActivity.objects.filter(timestamp__date=day)
        interactions_qs = PostcardInteraction.objects.filter(timestamp__date=day)

        total_visits = sessions_qs.count()
        page_views = page_views_qs.count()
        unique_visitors = page_views_qs.values('ip_address').distinct().count()
        new_users = CustomUser.objects.filter(date_joined__date=day).count()
        total_searches = searches_qs.count()
        total_likes = likes_qs.count()

        total_postcards_viewed = activities_qs.filter(action='postcard_view').count()
        if total_postcards_viewed == 0:
            total_postcards_viewed = interactions_qs.filter(interaction_type='view').count()

        total_animations_viewed = interactions_qs.filter(
            interaction_type='animation_view'
        ).count()

        total_zooms = interactions_qs.filter(interaction_type='zoom').count()
        if total_zooms == 0:
            total_zooms = activities_qs.filter(action='postcard_zoom').count()

        total_messages = ContactMessage.objects.filter(created_at__date=day).count()
        total_suggestions = AnimationSuggestion.objects.filter(created_at__date=day).count()

        single_page = sessions_qs.filter(page_views__lte=1).count()
        bounce_rate = round(single_page / total_visits * 100, 1) if total_visits else 0.0

        avg_duration = sessions_qs.filter(total_time_spent__gt=0).aggregate(
            avg=Avg('total_time_spent')
        )['avg'] or 0

        device_counts = {'mobile': 0, 'tablet': 0, 'desktop': 0}
        for row in sessions_qs.exclude(device_type='').values('device_type').annotate(n=Count('id')):
            dtype = row['device_type'].lower()
            if 'mobile' in dtype:
                device_counts['mobile'] += row['n']
            elif 'tablet' in dtype:
                device_counts['tablet'] += row['n']
            elif 'desktop' in dtype:
                device_counts['desktop'] += row['n']

        DailyAnalytics.objects.update_or_create(
            date=day,
            defaults={
                'total_visits': total_visits,
                'unique_visitors': unique_visitors,
                'page_views': page_views,
                'new_users': new_users,
                'total_searches': total_searches,
                'total_likes': total_likes,
                'total_postcards_viewed': total_postcards_viewed,
                'total_animations_viewed': total_animations_viewed,
                'total_zooms': total_zooms,
                'total_messages': total_messages,
                'total_suggestions': total_suggestions,
                'bounce_rate': bounce_rate,
                'avg_session_duration': int(avg_duration),
                'mobile_visits': device_counts['mobile'],
                'tablet_visits': device_counts['tablet'],
                'desktop_visits': device_counts['desktop'],
                'top_countries': _top_counts(page_views_qs, 'country'),
                'top_referrers': _top_counts(sessions_qs, 'referrer_domain'),
                'top_pages': _top_counts(page_views_qs, 'page_name'),
                'top_searches': _top_counts(searches_qs, 'keyword'),
            },
        )

        for hour in range(24):
            hour_page_views = page_views_qs.filter(timestamp__hour=hour)
            HourlyAnalytics.objects.update_or_create(
                date=day,
                hour=hour,
                defaults={
                    'page_views': hour_page_views.count(),
                    'unique_visitors': hour_page_views.values('ip_address').distinct().count(),
                    'searches': searches_qs.filter(created_at__hour=hour).count(),
                    'likes': likes_qs.filter(created_at__hour=hour).count(),
                },
            )

        self.stdout.write(f'  {day}: {page_views} vues, {total_visits} sessions, '
                          f'{total_searches} recherches, {total_likes} likes')
