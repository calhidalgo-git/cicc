from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class Resource(models.Model):
    title = models.CharField(max_length=200)
    area = models.CharField(
        max_length=20,
        choices=[
            ('Mainframe', 'Mainframe'),
            ('Distribuido', 'Distribuido'),
            ('Transversal', 'Transversal'),
        ],
    )
    kind = models.CharField(max_length=20, default='Documento')
    description = models.TextField()
    url = models.URLField(blank=True)
    published = models.BooleanField(default=True)
    # Si se indica, el recurso abre esa ruta de aprendizaje con su nombre (decisión de Carlos,
    # 21-11-2026): así se veían los tres cursos desde la biblioteca antes de T05.
    learning_path = models.ForeignKey(
        'LearningPath',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='resources',
        verbose_name='abre la ruta de aprendizaje',
        help_text='Si se elige, el recurso muestra el nombre de la ruta y abre su teoría.',
    )

    @property
    def display_title(self):
        return self.learning_path.title if self.learning_path_id else self.title

    @property
    def display_kind(self):
        from .catalog import MODULES

        return MODULES.get(self.kind, self.kind)

    def __str__(self):
        return self.title


class ResourceVersion(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='versions')
    number = models.PositiveIntegerField()
    notes = models.TextField()
    file = models.FileField(upload_to='resources/%Y/%m', blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['resource', 'number'], name='unique_version')
        ]


def unique_slug(model, title, exclude_pk=None):
    """``slugify(title)`` con un sufijo -2, -3… si ya existe."""
    base = slugify(title)[:190] or 'ruta'
    candidate, number = base, 2
    others = model.objects.exclude(pk=exclude_pk) if exclude_pk else model.objects.all()
    while others.filter(slug=candidate).exists():
        candidate = f'{base}-{number}'
        number += 1
    return candidate


class LearningPath(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    area = models.CharField(max_length=20)
    description = models.TextField()
    intro_html = models.TextField(
        blank=True,
        help_text='Introducción en HTML. Se limita a las etiquetas permitidas al guardar.',
    )
    position = models.IntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def save(self, *args, **kwargs):
        from .services.courses import sanitize_html

        if not self.slug:
            self.slug = unique_slug(LearningPath, self.title, exclude_pk=self.pk)
        self.intro_html = sanitize_html(self.intro_html)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Lesson(models.Model):
    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    body = models.TextField(
        blank=True, help_text='Texto plano. Si hay contenido HTML, se calcula a partir de él.'
    )
    body_html = models.TextField(
        blank=True, help_text='Contenido en HTML. Se limita a las etiquetas permitidas al guardar.'
    )
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(fields=['path', 'position'], name='unique_lesson_position')
        ]

    def save(self, *args, **kwargs):
        from .services.courses import html_to_text, sanitize_html

        self.body_html = sanitize_html(self.body_html)
        if self.body_html:
            self.body = html_to_text(self.body_html)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Progress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'lesson'], name='unique_progress')]


class Assessment(models.Model):
    title = models.CharField(max_length=200)
    area = models.CharField(max_length=20)
    minutes = models.PositiveIntegerField(
        default=20, validators=[MinValueValidator(1), MaxValueValidator(240)]
    )
    pass_score = models.PositiveIntegerField(default=70, validators=[MaxValueValidator(100)])


class Question(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    options = models.JSONField(default=list)
    correct = models.PositiveSmallIntegerField()
    explanation = models.TextField()

    def clean(self):
        if (
            not isinstance(self.options, list)
            or len(self.options) < 2
            or any(not isinstance(o, str) or not o.strip() for o in self.options)
        ):
            raise ValidationError(
                {'options': 'Ingresa una lista JSON de al menos dos opciones de texto.'}
            )
        if self.correct is None or not 0 <= self.correct < len(self.options):
            raise ValidationError(
                {'correct': 'El índice debe corresponder a una opción, comenzando en cero.'}
            )


class Attempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assessment = models.ForeignKey(Assessment, on_delete=models.PROTECT)
    started = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField()
    answers = models.JSONField(default=dict)
    finished = models.BooleanField(default=False)
    score = models.FloatField(default=0)
    updated = models.DateTimeField(auto_now=True)


class Audit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=200)
    created = models.DateTimeField(auto_now_add=True)
