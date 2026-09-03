from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count
from django.urls import reverse
from django.views.generic import TemplateView

from blog.models import BlogComment, BlogPost
from home.models import ViewingSchedule, ContactMessage
from properties.models import Property, PropertyStatus
from . import reports
from .geolocation import resolve_pending_locations
from .models import PageVisit
from subscriptions import revenue_reports


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Both dashboard pages are explicitly superuser-only, independent of
    whatever gates the rest of the AdminBase.html back-office (which mixes
    staff, verified owners, etc. depending on the page)."""

    def test_func(self):
        return self.request.user.is_superuser


class VerifiedOwnerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Leads is an owner-facing page - gate it to verified property owners
    (same bar as DashboardAccessMiddleware uses for /dashboard/ itself),
    plus superusers for oversight."""

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        profile = getattr(user, 'profile', None)
        return bool(profile and profile.role == 'owner' and profile.is_verified_owner)


class BaseAnalyticsView(SuperuserRequiredMixin, TemplateView):
    template_name = None
    path_prefix = None  # None = whole site; '/blog/' = blog-only
    exact_path = None   # e.g. '/' for homepage-only - see reports.get_visit_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        range_key = self.request.GET.get('range', reports.DEFAULT_RANGE)
        valid_keys = {k for k, _ in reports.RANGE_CHOICES}
        if range_key not in valid_keys:
            range_key = reports.DEFAULT_RANGE
        start, end, group_by = reports.get_range_bounds(range_key)

        qs = reports.get_visit_queryset(start, end, path_prefix=self.path_prefix, exact_path=self.exact_path)

        # Best-effort location enrichment - see analytics/geolocation.py.
        # Bounded and safe to call every page load.
        resolve_pending_locations()

        labels, values = reports.build_series(qs, 'visited_at', start, end, group_by)
        new_users_labels, new_users_values = reports.get_new_users_series(start, end, group_by)

        context.update({
            'range_choices': reports.RANGE_CHOICES,
            'selected_range': range_key,
            'stats': reports.get_summary_stats(qs),
            'chart_labels': labels,
            'chart_views': values,
            'chart_new_users_labels': new_users_labels,
            'chart_new_users': new_users_values,
            'top_paths': reports.get_top_paths(qs),
            'device_breakdown': reports.get_device_breakdown(qs),
            'location_breakdown': reports.get_location_breakdown(qs),
            'combo_series_label': 'New Users',
            '_qs': qs,  # exposed for subclasses building extra breakdowns (e.g. SiteVisitsView) - not for direct template use
        })
        return context


class TrafficDashboardView(BaseAnalyticsView):
    template_name = 'analytics/traffic.html'
    path_prefix = None


class SiteVisitsView(BaseAnalyticsView):
    """Homepage-only visits - 'how often are people visiting my site' in
    the most literal sense: front-door traffic, separate from the
    whole-site Traffic view (which includes every page) and from Blog
    Analytics."""
    template_name = 'analytics/site_visits.html'
    exact_path = '/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['day_of_week_breakdown'] = reports.get_day_of_week_breakdown(context['_qs'])
        return context


class BlogAnalyticsView(BaseAnalyticsView):
    template_name = 'analytics/blog_analytics.html'
    path_prefix = '/blog/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        range_key = context['selected_range']
        start, end, group_by = reports.get_range_bounds(range_key)

        # Per-post view counts within the selected range, ranked - "which
        # blog was viewed the most" needs a real per-post breakdown, not
        # just the site-wide top-paths list (which would also mix in
        # /blog/ itself and /blog/subscribe/).
        posts = list(BlogPost.objects.filter(is_published=True))
        url_to_post = {p.get_absolute_url(): p for p in posts}
        qs = reports.get_visit_queryset(start, end, path_prefix='/blog/')
        counts = dict(
            qs.filter(path__in=url_to_post.keys())
            .values('path')
            .annotate(count=Count('id'))
            .values_list('path', 'count')
        )
        top_posts = sorted(
            (
                {'post': url_to_post[path], 'views': counts.get(path, 0)}
                for path in url_to_post
            ),
            key=lambda row: -row['views'],
        )[:10]

        # Comments-per-day is the blog page's equivalent of "users who
        # joined" on the main Traffic page - a real, blog-specific
        # engagement signal for the line+bar combo chart.
        comment_labels, comment_values = reports.build_series(
            BlogComment.objects.all(), 'created_at', start, end, group_by
        )

        context.update({
            'top_posts': top_posts,
            'top_posts_chart_data': [
                {'title': (row['post'].display_title or row['post'].title)[:30], 'views': row['views']}
                for row in top_posts
            ],
            'chart_new_users_labels': comment_labels,
            'chart_new_users': comment_values,
            'combo_series_label': 'New Comments',
        })
        return context


class ProfileAnalyticsView(TemplateView):
    """
    Section 13 of the public-profile redesign spec: a separate analytics
    page (own base layout, not the dashboard theme) showing traffic to an
    owner's own public profile page specifically - not their properties,
    not the whole site. Gated to the profile owner themselves, or a
    superuser.
    """
    template_name = 'public_profile/profile_analytics.html'

    def dispatch(self, request, *args, **kwargs):
        from django.shortcuts import get_object_or_404
        from users.models import Profile

        self.owner_profile = get_object_or_404(
            Profile.objects.select_related('user'),
            user__username=kwargs['username'], role='owner',
        )
        if not (request.user.is_superuser or request.user == self.owner_profile.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.urls import reverse
        from django.utils import timezone
        from datetime import timedelta

        profile_path = reverse('home:owner_portfolio', kwargs={'username': self.owner_profile.user.username})
        now = timezone.now()

        resolve_pending_locations()

        # ── Fixed reference-point cards - always all shown, independent of
        #    the chart's range filter below. ──
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        year_start = now - timedelta(days=365)

        def visitor_count(since):
            return reports.get_visit_queryset(since, now, exact_path=profile_path).exclude(session_key='').values('session_key').distinct().count()

        all_time_qs = reports.get_visit_queryset(
            self.owner_profile.user.date_joined, now, exact_path=profile_path
        )
        returning_stats = reports.get_returning_visitor_stats(all_time_qs)

        # ── Chart range filter ──
        range_key = self.request.GET.get('range', 'week')
        range_map = {
            'today': (today_start, now, 'hour'),
            'week': (week_start, now, 'day'),
            'month': (month_start, now, 'day'),
            'year': (year_start, now, 'day'),
        }
        if range_key == 'custom':
            start = self.request.GET.get('start')
            end = self.request.GET.get('end')
            try:
                from datetime import datetime
                chart_start = timezone.make_aware(datetime.strptime(start, '%Y-%m-%d'))
                chart_end = timezone.make_aware(datetime.strptime(end, '%Y-%m-%d')) + timedelta(days=1)
            except (TypeError, ValueError):
                chart_start, chart_end, group_by = week_start, now, 'day'
            else:
                group_by = 'day'
        else:
            chart_start, chart_end, group_by = range_map.get(range_key, range_map['week'])

        chart_qs = reports.get_visit_queryset(chart_start, chart_end, exact_path=profile_path)
        labels, values = reports.build_series(chart_qs, 'visited_at', chart_start, chart_end, group_by)

        context.update({
            'owner_profile': self.owner_profile,
            'brand_name': self.owner_profile.owner_brand_name or self.owner_profile.get_full_name() or self.owner_profile.user.username,
            'profile_picture_url': self.owner_profile.profile_picture.url if self.owner_profile.profile_picture else None,
            'is_own_profile': self.request.user.is_authenticated and self.request.user.id == self.owner_profile.user.id,

            'total_visitors': returning_stats['total_visitors'],
            'today_visitors': visitor_count(today_start),
            'week_visitors': visitor_count(week_start),
            'month_visitors': visitor_count(month_start),
            'year_visitors': visitor_count(year_start),
            'returning_visitors': returning_stats['returning_visitors'],
            'returning_pct': returning_stats['returning_pct'],

            'range_choices': [
                ('today', 'Today'), ('week', 'Week'), ('month', 'Month'), ('year', 'Year'), ('custom', 'Custom'),
            ],
            'selected_range': range_key,
            'chart_labels': labels,
            'chart_values': values,

            'device_breakdown': reports.get_device_breakdown(chart_qs),
            'browser_breakdown': reports.get_browser_breakdown(chart_qs),
            'country_breakdown': reports.get_location_breakdown(chart_qs),
            'region_breakdown': reports.get_region_breakdown(chart_qs),
            'referrer_breakdown': reports.get_referrer_breakdown(chart_qs),
        })
        return context


class LeadsView(VerifiedOwnerRequiredMixin, TemplateView):
    """
    Owner-facing analytics: how their own listings are performing (views +
    real viewing-request leads), plus a platform-wide "trending" section so
    an owner can see what kind of property is getting attention right now
    and adjust what they list/how they price it. The trending section is
    aggregate view counts on public listings - not private data about any
    other specific owner.
    """
    template_name = 'analytics/leads.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        range_key = self.request.GET.get('range', reports.DEFAULT_RANGE)
        valid_keys = {k for k, _ in reports.RANGE_CHOICES}
        if range_key not in valid_keys:
            range_key = reports.DEFAULT_RANGE
        start, end, group_by = reports.get_range_bounds(range_key)

        resolve_pending_locations()

        my_properties = list(Property.objects.filter(owner=self.request.user))
        url_to_property = {
            reverse('home:about_property', kwargs={'slug': p.slug}): p for p in my_properties
        }

        qs = reports.get_visit_queryset_for_paths(start, end, url_to_property.keys())
        my_leads = ViewingSchedule.objects.filter(
            property__owner=self.request.user, created_at__gte=start, created_at__lte=end,
        )

        total_views = qs.count()
        total_leads = my_leads.count()

        labels, values = reports.build_series(qs, 'visited_at', start, end, group_by)
        lead_labels, lead_values = reports.build_series(my_leads, 'created_at', start, end, group_by)

        view_counts = dict(
            qs.values('path').annotate(count=Count('id')).values_list('path', 'count')
        )
        lead_counts_by_property = dict(
            my_leads.values('property_id').annotate(count=Count('id')).values_list('property_id', 'count')
        )
        my_properties_ranked = sorted(
            (
                {
                    'property': prop,
                    'views': view_counts.get(url, 0),
                    'leads': lead_counts_by_property.get(prop.id, 0),
                }
                for url, prop in url_to_property.items()
            ),
            key=lambda row: -row['views'],
        )

        # Platform-wide trending properties (active listings only) - real
        # public view counts, no owner-identifying detail beyond what's
        # already visible on the public listing itself.
        trending_qs = reports.get_visit_queryset(start, end, path_prefix='/property/listing/')
        trending_counts = dict(
            trending_qs.values('path').annotate(count=Count('id')).values_list('path', 'count')
        )
        all_active_properties = Property.objects.filter(
            is_active=True, status=PropertyStatus.AVAILABLE
        ).exclude(owner=self.request.user)
        trending = sorted(
            (
                {
                    'property': p,
                    'views': trending_counts.get(
                        reverse('home:about_property', kwargs={'slug': p.slug}), 0
                    ),
                }
                for p in all_active_properties
            ),
            key=lambda row: -row['views'],
        )
        trending = [row for row in trending if row['views'] > 0][:10]

        context.update({
            'range_choices': reports.RANGE_CHOICES,
            'selected_range': range_key,
            'total_views': total_views,
            'total_leads': total_leads,
            'conversion_rate': round(total_leads / total_views * 100, 1) if total_views else 0,
            'chart_labels': labels,
            'chart_views': values,
            'chart_leads': lead_values,
            'device_breakdown': reports.get_device_breakdown(qs),
            'location_breakdown': reports.get_location_breakdown(qs),
            'my_properties_ranked': my_properties_ranked,
            'trending_properties': trending,
            'has_properties': bool(my_properties),
        })
        return context


class SubscriptionRevenueView(SuperuserRequiredMixin, TemplateView):
    """Admin-only: money coming in through subscription payments. Same
    range-picker + card/chart/table layout as TrafficDashboardView, but
    reading from SubscriptionPayment instead of PageVisit."""
    template_name = 'analytics/revenue.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        range_key = self.request.GET.get('range', reports.DEFAULT_RANGE)
        valid_keys = {k for k, _ in reports.RANGE_CHOICES}
        if range_key not in valid_keys:
            range_key = reports.DEFAULT_RANGE
        start, end, group_by = reports.get_range_bounds(range_key)

        from subscriptions.models import SubscriptionPayment
        all_attempts = SubscriptionPayment.objects.all()
        completed = all_attempts.filter(status=SubscriptionPayment.STATUS_COMPLETED)

        revenue_labels, revenue_values = revenue_reports.build_sum_series(
            completed, 'completed_at', 'amount', start, end, group_by,
        )
        volume_labels, volume_values = revenue_reports.build_count_series(
            all_attempts, 'created_at', start, end, group_by,
        )

        context.update({
            'range_choices': reports.RANGE_CHOICES,
            'selected_range': range_key,
            'stats': revenue_reports.get_summary_stats(start, end),
            'status_breakdown': revenue_reports.get_status_breakdown(start, end),
            'revenue_labels': revenue_labels,
            'revenue_values': revenue_values,
            'volume_labels': volume_labels,
            'volume_values': volume_values,
            'transactions': revenue_reports.get_recent_transactions(start, end),
        })
        return context


class DirectContactView(SuperuserRequiredMixin, TemplateView):
    """"Direct Contact" - messages a visitor sent through this admin's own
    public TuHame portfolio page (see OwnerContactSubmitView and the
    #connect form in owner_portfolio.html). Scoped to owner=request.user,
    not every ContactMessage in the system - this is "who contacted me",
    not a platform-wide inbox (the platform's own general Contact Us
    submissions, where owner is null, are handled separately via Django
    admin - home.admin.ContactMessageAdmin)."""
    template_name = 'analytics/direct_contact.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        messages_qs = ContactMessage.objects.filter(owner=self.request.user).order_by('-created_at')

        # Mark as read once viewed here, so the sidebar (if a badge count
        # is ever added later) and this list agree on what's new.
        unread_ids = list(messages_qs.filter(is_read=False).values_list('id', flat=True))
        if unread_ids:
            ContactMessage.objects.filter(id__in=unread_ids).update(is_read=True)

        context['contact_messages'] = messages_qs
        context['new_count'] = len(unread_ids)
        return context
