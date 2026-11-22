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

for model in [
    Resource,
    ResourceVersion,
    LearningPath,
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
