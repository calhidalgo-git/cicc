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

    def save_formset(self, request, form, formset, change):
        """Reordenar las lecciones en un solo guardado (quinta revisión de Codex, 24-11-2026).

        La posición es única en cada ruta y la base la comprueba fila a fila. Si dos lecciones
        intercambian posiciones, la primera chocaría con la segunda todavía en su sitio. Antes de
        guardar, las lecciones que cambian de posición, y las que se van a quitar, pasan a
        posiciones libres; después cada una recibe la suya o se borra.

        Sexta revisión de Codex (24-11-2026): las posiciones libres son los números más bajos que
        no usa ninguna lección, ni antes ni después del guardado, así que siempre caben en el rango
        del campo. Quitar una lección y dar su puesto a otra en el mismo guardado también funciona.
        """
        if formset.model is Lesson:
            moving = [
                f.instance.pk
                for f in formset.forms
                if f.instance.pk
                and ('position' in f.changed_data or formset._should_delete_form(f))
            ]
            if moving:
                finals = {f.cleaned_data.get('position') for f in formset.forms}
                stored = set(
                    Lesson.objects.filter(path=form.instance).values_list('position', flat=True)
                )
                busy = finals | stored
                free = (number for number in range(1, len(busy) + len(moving) + 2))
                free = (number for number in free if number not in busy)
                for pk, number in zip(moving, free, strict=False):
                    Lesson.objects.filter(pk=pk).update(position=number)
        super().save_formset(request, form, formset, change)


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
