from django.contrib import admin
from django.db.models import Count

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


class ResourceVersionInline(admin.TabularInline):
    model = ResourceVersion
    extra = 0
    fields = ('number', 'file', 'notes', 'created')
    readonly_fields = ('created',)


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'area', 'kind', 'published')
    list_filter = ('area', 'kind', 'published')
    search_fields = ('title', 'description')
    inlines = [ResourceVersionInline]


class QuestionInline(admin.StackedInline):
    """El formulario de cada pregunta ejecuta Question.clean() antes de guardar."""

    model = Question
    extra = 0
    fields = ('text', 'options', 'correct', 'explanation')


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'area', 'minutes', 'pass_score')
    list_filter = ('area',)
    search_fields = ('title',)
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """El formulario del administrador ejecuta Question.clean() antes de guardar."""

    list_display = ('text', 'assessment', 'correct')
    list_filter = ('assessment',)
    search_fields = ('text',)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Registros que la aplicación escribe sola: se consultan, no se crean ni se cambian.

    Solo un superusuario puede borrarlos.
    """

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Attempt)
class AttemptAdmin(ReadOnlyAdmin):
    list_display = ('user', 'assessment', 'started', 'finished', 'score')
    list_filter = (('started', admin.DateFieldListFilter), 'finished')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    list_select_related = ('user', 'assessment')
    date_hierarchy = 'started'


@admin.register(Audit)
class AuditAdmin(ReadOnlyAdmin):
    list_display = ('created', 'user', 'action')
    list_filter = (('created', admin.DateFieldListFilter),)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'action')
    list_select_related = ('user',)
    date_hierarchy = 'created'


@admin.register(Progress)
class ProgressAdmin(ReadOnlyAdmin):
    list_display = ('user', 'lesson')
    search_fields = ('user__username', 'lesson__title')
    list_select_related = ('user', 'lesson', 'lesson__path')


for model in [ResourceVersion, Lesson]:
    admin.site.register(model)

admin.site.site_header = 'CICC — Centro Integral de Control de Calidad'
admin.site.site_title = 'CICC'
admin.site.index_title = 'Sección de Control de Calidad'
