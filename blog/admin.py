from django.contrib import admin
from django.utils.html import format_html

from .models import BlogComment, BlogLike, BlogPost, NewsletterSubscriber


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    """
    Default admin.site.register(BlogPost) put every field - including the
    CKEditor5 'content' widget - into one wide "aligned" fieldset. Django
    admin's aligned layout floats each field's label/input; a widget as
    tall/wide as CKEditor breaks that float flow, which visually hides
    (or shoves far down/behind) whatever fields and the Save row come
    after it. Splitting the form into explicit fieldsets - with the editor
    isolated in its own, non-"aligned" fieldset - fixes that at the root,
    instead of just patching around it with CSS.
    """

    list_display = ('title', 'category', 'is_published', 'author', 'published_at', 'views_count')
    list_filter = ('is_published', 'category', 'published_at')
    search_fields = ('title', 'excerpt', 'tags', 'seo_title', 'seo_description')
    list_editable = ('is_published',)
    # date_hierarchy = 'published_at'
    ordering = ('-published_at',)
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('views_count', 'created_at', 'updated_at')
    save_on_top = True

    fieldsets = (
        ('Post', {
            'fields': ('title', 'slug', 'author', 'cover_image', 'excerpt', 'seo_description', 'seo_keywords'),
        }),
        # Isolated on its own so the CKEditor widget can't break the
        # aligned-fieldset float layout of the fields around it.
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',),
        }),
        ('Organization', {
            'fields': ('category', 'tags'),
        }),
        ('Publishing', {
            'fields': ('is_published', 'published_at', 'views_count', 'created_at', 'updated_at'),
        }),
        ('SEO', {
            'fields': ('seo_title',),
            'description': 'Leave blank to fall back to the post title / excerpt.',
        }),
    )

    class Media:
        css = {
            'all': ('blog/admin-fix.css',),
        }

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'subscribed_at')
    list_filter = ('is_active',)
    search_fields = ('email',)
    ordering = ('-subscribed_at',)


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'short_content', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at')
    list_editable = ('is_approved',)
    search_fields = ('content', 'author__username', 'post__title')
    autocomplete_fields = ('post',)
    ordering = ('-created_at',)

    def short_content(self, obj):
        return obj.content[:60] + ('…' if len(obj.content) > 60 else '')
    short_content.short_description = 'Comment'


@admin.register(BlogLike)
class BlogLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    search_fields = ('user__username', 'post__title')
    ordering = ('-created_at',)
