from django.contrib import admin

from .models import PageVisit


@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display = ('path', 'visited_at', 'device_type', 'country', 'user')
    list_filter = ('device_type', 'location_resolved', 'visited_at')
    search_fields = ('path', 'ip_address', 'country', 'city')
    date_hierarchy = 'visited_at'
    ordering = ('-visited_at',)
    readonly_fields = [f.name for f in PageVisit._meta.fields]

    def has_add_permission(self, request):
        # These are only ever created by the tracking middleware.
        return False
