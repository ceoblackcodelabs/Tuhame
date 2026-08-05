from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from django_ckeditor_5.fields import CKEditor5Field


CATEGORY_CHOICES = [
    ('market-insights', 'Market Insights'),
    ('renting-tips', 'Renting Tips'),
    ('landlord-guides', 'Landlord Guides'),
    ('moving-guides', 'Moving Guides'),
    ('neighborhood-guides', 'Neighborhood Guides'),
    ('company-news', '2Hame News'),
]


class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='blog_posts',
    )

    cover_image = models.ImageField(upload_to='blog/covers/', blank=True, null=True)
    excerpt = models.CharField(
        max_length=300, blank=True,
        help_text="Short teaser shown on the blog list and used as a fallback meta description."
    )
    content = CKEditor5Field('Content', config_name='blog')

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='market-insights')
    tags = models.CharField(
        max_length=255, blank=True,
        help_text="Comma-separated, e.g. 'Nairobi, first apartment, moving tips'."
    )

    # SEO
    seo_title = models.CharField(
        max_length=70, blank=True,
        help_text="Overrides the page <title>. Falls back to the post title if left blank."
    )
    seo_description = models.CharField(
        max_length=160, blank=True,
        help_text="Meta description. Falls back to the excerpt if left blank."
    )
    seo_keywords = models.CharField(max_length=255, blank=True)

    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)
    views_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['-published_at']),
            models.Index(fields=['is_published']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:blog_detail', kwargs={'slug': self.slug})

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    @property
    def reading_time_minutes(self):
        """Rough estimate — ~200 words/minute, stripped of HTML tags."""
        import re
        text = re.sub('<[^<]+?>', ' ', self.content or '')
        word_count = len(text.split())
        return max(1, round(word_count / 200))

    @property
    def meta_description(self):
        return self.seo_description or self.excerpt

    @property
    def display_title(self):
        return self.seo_title or self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:200]
            slug = base_slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug
        if self.cover_image:
            from Tuhame.image_utils import optimize_image_field
            optimize_image_field(self.cover_image, max_dimension=1600)
        super().save(*args, **kwargs)


class NewsletterSubscriber(models.Model):
    """Backs the blog's newsletter signup form (templates/blog/blog_list.html)."""
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-subscribed_at']

    def __str__(self):
        return self.email


class BlogComment(models.Model):
    """A comment on a BlogPost. Requires a logged-in user (ties to the
    site's existing accounts rather than accepting anonymous name/email
    input, which cuts down on spam)."""
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blog_comments')
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(
        default=True,
        help_text='Uncheck to hide this comment from the public post page without deleting it.',
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author} on {self.post}: {self.content[:40]}'


class BlogLike(models.Model):
    """One like per (post, user) pair."""
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blog_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')

    def __str__(self):
        return f'{self.user} likes {self.post}'
