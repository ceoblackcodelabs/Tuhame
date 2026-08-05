from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from .forms import BlogCommentForm
from .models import BlogComment, BlogLike, BlogPost, CATEGORY_CHOICES, NewsletterSubscriber


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

        # Sidebar: recent posts sitewide (not just same category) and the
        # category list, so a reader can keep browsing without scrolling
        # all the way down to the related-posts row.
        context['sidebar_recent_posts'] = BlogPost.objects.filter(
            is_published=True
        ).exclude(pk=post.pk).select_related('author')[:5]
        context['sidebar_categories'] = CATEGORY_CHOICES

        context['comments'] = post.comments.filter(is_approved=True).select_related('author', 'author__profile')
        context['comment_count'] = context['comments'].count()
        context['comment_form'] = BlogCommentForm()

        context['like_count'] = post.likes.count()
        if self.request.user.is_authenticated:
            context['user_has_liked'] = post.likes.filter(user=self.request.user).exists()
        else:
            context['user_has_liked'] = False

        return context


@login_required
@require_POST
def add_comment(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    form = BlogCommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        messages.success(request, 'Your comment was posted.')
    else:
        for error in form.errors.get('content', []):
            messages.error(request, error)

    return redirect(post.get_absolute_url() + '#comments')


@login_required
@require_POST
def toggle_like(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    like, created = BlogLike.objects.get_or_create(post=post, user=request.user)

    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    like_count = post.likes.count()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'liked': liked, 'like_count': like_count})

    return redirect(post.get_absolute_url())


@require_POST
def newsletter_subscribe(request):
    email = (request.POST.get('email') or '').strip()

    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        redirect_target = next_url
    else:
        redirect_target = reverse('blog:blog_list')

    if not email:
        messages.error(request, "Please enter an email address to subscribe.")
        return redirect(redirect_target)

    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "That doesn't look like a valid email address.")
        return redirect(redirect_target)

    try:
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email__iexact=email, defaults={'email': email}
        )
    except IntegrityError:
        created = False

    if created:
        messages.success(request, "You're subscribed! Watch your inbox for real estate tips.")
    else:
        messages.info(request, "That email is already subscribed.")

    return redirect(redirect_target)
