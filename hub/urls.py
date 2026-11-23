"""Rutas de la aplicación CICC. Cada ruta conserva su patrón y su nombre."""

from django.contrib.auth import views as auth
from django.urls import path

from . import views as v

urlpatterns = [
    path('rutas/<slug:slug>/', v.path_detail, name='path_detail'),
    path('rutas/<slug:slug>/<int:position>/', v.lesson_detail, name='lesson_detail'),
    # Cursos anteriores a T05: redirección permanente a su ruta de aprendizaje.
    path('qa/certificacion/', v.certification, name='certification'),
    path('qa/certificacion/tema/<int:topic>/', v.certification_topic, name='certification_topic'),
    path('qa/avanzado/', v.qa_advanced, name='qa_advanced'),
    path('qa/avanzado/semana/<int:week>/', v.qa_advanced_week, name='qa_advanced_week'),
    path('qa/fundamentos/', v.qa_fundamentals, name='qa_fundamentals'),
    path('qa/fundamentos/semana/<int:week>/', v.qa_week, name='qa_week'),
    path('login/', auth.LoginView.as_view(template_name='login.html')),
    path('logout/', auth.LogoutView.as_view()),
    path('', v.page, name='home'),
    path('p/<slug:section>/', v.page, name='page'),
    path('resource/<int:pk>/', v.resource, name='resource'),
    path('download/<int:pk>/', v.download, name='download'),
    path('exam/<int:pk>/start/', v.start, name='start'),
    path('attempt/<int:pk>/', v.exam, name='exam'),
    path('attempt/<int:pk>/save/', v.save, name='save'),
    path('attempt/<int:pk>/finish/', v.finish, name='finish'),
    path('results/<int:pk>/', v.results, name='results'),
    path('import/', v.import_excel, name='import'),
    path('template/', v.excel_template, name='template'),
    path('report.xlsx', v.report, name='report'),
    path('backup/', v.backup, name='backup'),
    path('lesson/<int:pk>/complete/', v.complete, name='complete'),
]
