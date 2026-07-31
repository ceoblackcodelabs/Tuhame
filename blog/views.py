from django.db.models import F
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView

from .models import BlogPost, CATEGORY_CHOICES


class BlogListView(ListView):
    model = BlogPost
    template_name = 'blog/blog_list.html'
    context_object_name = 'posts'
    paginate_by = 9

    def get_queryset(self):
        qs = BlogPost.objects.filter(is_published=True).select_related('author')
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category=category)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(title__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = CATEGORY_CHOICES
        context['active_category'] = self.request.GET.get('category', '')
        context['query'] = self.request.GET.get('q', '')
        context['featured_post'] = BlogPost.objects.filter(is_published=True).first()
        return context


class BlogDetailView(DetailView):
    model = BlogPost
    template_name = 'blog/blog_detail.html'
    context_object_name = 'post'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return BlogPost.objects.filter(is_published=True).select_related('author')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Simple view counter — one increment per request is good enough
        # here; no need for session/IP dedup on a small blog.
        BlogPost.objects.filter(pk=obj.pk).update(views_count=F('views_count') + 1)
        obj.refresh_from_db(fields=['views_count'])
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object
        context['related_posts'] = BlogPost.objects.filter(
            is_published=True, category=post.category
        ).exclude(pk=post.pk)[:3]
        return context
