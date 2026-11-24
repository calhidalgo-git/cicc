from django.contrib import admin
from django.db.models import Count, Max

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
    SectionBlock,
    SectionPage,
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

    def save_formset(self, request, form, formset, change):
        """Reordenar las lecciones en un solo guardado (quinta revisión de Codex, 24-11-2026).

        La posición es única en cada ruta y la base la comprueba fila a fila. Si dos lecciones
        intercambian posiciones, la primera chocaría con la segunda todavía en su sitio. Antes de
        guardar, las lecciones que cambian de posición pasan a posiciones libres por encima de
        todas las demás; después cada una recibe la suya.
        """
        if formset.model is Lesson:
            moving = [
                f.instance.pk
                for f in formset.forms
                if f.instance.pk
                and 'position' in f.changed_data
                and not formset._should_delete_form(f)
            ]
            if moving:
                finals = [f.cleaned_data.get('position') or 0 for f in formset.forms]
                stored = Lesson.objects.filter(path=form.instance).aggregate(top=Max('position'))
                base = max([stored['top'] or 0, *finals])
                for offset, pk in enumerate(moving, 1):
                    Lesson.objects.filter(pk=pk).update(position=base + offset)
        super().save_formset(request, form, formset, change)


EDIT_PERMISSION = 'hub.change_sectionpage'


class SectionBlockInline(admin.StackedInline):
    """Bloques de teoría. Se ordenan por el número de posición."""

    model = SectionBlock
    extra = 0
    fields = ('position', 'title', 'body_html')
    ordering = ('position', 'id')

    # Página y bloques se editan con un único permiso: hub.change_sectionpage.
    def has_view_permission(self, request, obj=None):
        return request.user.has_perm(EDIT_PERMISSION) or request.user.has_perm(
            'hub.view_sectionpage'
        )

    def has_add_permission(self, request, obj=None):
        return request.user.has_perm(EDIT_PERMISSION)

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm(EDIT_PERMISSION)

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm(EDIT_PERMISSION)


@admin.register(SectionPage)
class SectionPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'block_count', 'origin', 'updated', 'updated_by')
    list_filter = ('origin',)
    search_fields = ('title', 'slug', 'intro', 'blocks__title', 'blocks__body')
    fields = ('slug', 'title', 'intro_html', 'origin', 'updated', 'updated_by')
    readonly_fields = ('slug', 'origin', 'updated', 'updated_by')
    inlines = [SectionBlockInline]

    @admin.display(description='bloques')
    def block_count(self, obj):
        return obj.block_count

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('updated_by')
        return queryset.annotate(block_count=Count('blocks'))

    # Hay una página por opción del menú: no se crean ni se borran desde aquí.
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # Django llama a save_model aunque solo cambien los bloques: cuenta como edición manual.
        obj.origin = 'admin'
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


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
