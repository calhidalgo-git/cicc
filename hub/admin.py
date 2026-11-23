from django.contrib import admin

from .models import (
    Assessment,
    Attempt,
    Audit,
    LearningPath,
    Lesson,
    Progress,
    Question,
    Resource,
    ResourceVersion,
)
from .services.courses import official_slugs


class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 0
    fields = ('position', 'title', 'body_html', 'body')
    ordering = ('position',)


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'area', 'position')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [LessonInline]

    @staticmethod
    def is_official(obj):
        return obj is not None and obj.stored_slug() in official_slugs()

    def get_readonly_fields(self, request, obj=None):
        """La dirección de un curso oficial no se edita (revisión de Codex, 22-11-2026)."""
        fields = super().get_readonly_fields(request, obj)
        if self.is_official(obj):
            return (*fields, 'slug')
        return fields

    def get_prepopulated_fields(self, request, obj=None):
        if self.is_official(obj):
            return {}
        return super().get_prepopulated_fields(request, obj)


for model in [
    Resource,
    ResourceVersion,
    Lesson,
    Assessment,
    Question,
    Audit,
    Progress,
    Attempt,
]:
    admin.site.register(model)

admin.site.site_header = 'CICC — Centro Integral de Control de Calidad'
admin.site.site_title = 'CICC'
admin.site.index_title = 'Sección de Control de Calidad'
