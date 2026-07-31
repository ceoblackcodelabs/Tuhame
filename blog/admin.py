from django.contrib import admin
from django.utils.html import format_html

from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('cover_preview', 'title', 'category', 'author', 'is_published', 'published_at', 'views_count')
    list_editable = ('is_published',)
    list_filter = ('category', 'is_published', 'published_at')
    search_fields = ('title', 'excerpt', 'tags', 'content')
    prepopulated_fields = {'slug': ('title',)}
    # date_hierarchy = 'published_at'
    readonly_fields = ('views_count', 'created_at', 'updated_at')

    class Media:
        css = {'all': ('blog/admin_ckeditor_fix.css',)}

    fieldsets = (
        (None, {'fields': ('title', 'slug', 'author', 'category', 'tags')}),
        ('Content', {'fields': ('cover_image', 'excerpt', 'content')}),
        ('SEO', {'fields': ('seo_title', 'seo_description', 'seo_keywords'), 'classes': ('collapse',)}),
        ('Publishing', {'fields': ('is_published', 'published_at', 'views_count')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" style="height:36px;width:56px;object-fit:cover;border-radius:4px;" />', obj.cover_image.url)
        return '—'
    cover_preview.short_description = 'Cover'

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)
