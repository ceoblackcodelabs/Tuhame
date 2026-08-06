from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count
from django.views.generic import TemplateView

from blog.models import BlogComment, BlogPost
from . import reports
from .geolocation import resolve_pending_locations
from .models import PageVisit


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Both dashboard pages are explicitly superuser-only, independent of
    whatever gates the rest of the AdminBase.html back-office (which mixes
    staff, verified owners, etc. depending on the page)."""

    def test_func(self):
        return self.request.user.is_superuser


class BaseAnalyticsView(SuperuserRequiredMixin, TemplateView):
    template_name = None
    path_prefix = None  # None = whole site; '/blog/' = blog-only

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        range_key = self.request.GET.get('range', reports.DEFAULT_RANGE)
        valid_keys = {k for k, _ in reports.RANGE_CHOICES}
        if range_key not in valid_keys:
            range_key = reports.DEFAULT_RANGE
        start, end, group_by = reports.get_range_bounds(range_key)

        qs = reports.get_visit_queryset(start, end, path_prefix=self.path_prefix)

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
        })
        return context


class TrafficDashboardView(BaseAnalyticsView):
    template_name = 'analytics/traffic.html'
    path_prefix = None


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
