from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import connection, models, transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver
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


def unique_slug(model, title, exclude_pk=None, reserved=()):
    """``slugify(title)`` con un sufijo -2, -3… si ya existe o está reservado."""
    base = slugify(title)[:190] or 'ruta'
    candidate, number = base, 2
    others = model.objects.exclude(pk=exclude_pk) if exclude_pk else model.objects.all()
    while candidate in reserved or others.filter(slug=candidate).exists():
        candidate = f'{base}-{number}'
        number += 1
    return candidate


def official_course_slugs():
    """Slugs reservados para los cursos oficiales de hub/content/courses/."""
    from .services.courses import official_slugs

    return official_slugs()


class LearningPathQuerySet(models.QuerySet):
    """Las operaciones en lote tampoco cambian ni toman el slug de un curso oficial.

    ``save()`` y ``clean()`` ya lo impiden en cada ruta; ``update()`` y ``bulk_update()`` no
    pasan por ellos (tercera revisión de Codex, 23-11-2026).
    """

    def update(self, **kwargs):
        """Comprueba el slug que queda guardado, no el valor recibido: con una expresión de
        Django (``Concat``, ``Value``, ``F``…) el valor solo se conoce después de aplicarla
        (cuarta revisión de Codex, 24-11-2026). Si una ruta cambia de slug o toma uno oficial,
        se deshace todo el cambio.
        """
        if 'slug' not in kwargs:
            return super().update(**kwargs)
        official = official_course_slugs()
        new = kwargs['slug']
        if isinstance(new, str):
            # Un valor literal se comprueba antes: la base rechazaría el slug repetido sin decir
            # que es oficial.
            others = self.exclude(slug=new)
            if others.filter(slug__in=official).exists():
                raise ValidationError('La dirección de un curso oficial no se puede cambiar.')
            if new in official and others.exists():
                raise ValidationError(
                    f'El slug {new!r} está reservado para un curso oficial; '
                    'solo load_courses puede usarlo.'
                )
        with transaction.atomic(using=self.db):
            before = dict(self.values_list('pk', 'slug'))
            rows = super().update(**kwargs)
            after = self.model._base_manager.using(self.db).filter(pk__in=list(before))
            for pk, slug in after.values_list('pk', 'slug'):
                if slug == before[pk]:
                    continue
                if before[pk] in official:
                    raise ValidationError('La dirección de un curso oficial no se puede cambiar.')
                if slug in official:
                    raise ValidationError(
                        f'El slug {slug!r} está reservado para un curso oficial; '
                        'solo load_courses puede usarlo.'
                    )
        return rows

    def bulk_update(self, objs, fields, *args, **kwargs):
        # Una lista: un iterador se consumiría al comprobarlo y no se guardaría nada.
        objs = list(objs)
        if 'slug' in fields:
            for obj in objs:
                if obj.leaves_official_slug() or obj.takes_official_slug():
                    raise ValidationError(
                        f'La ruta {obj.pk}: la dirección de un curso oficial no se puede cambiar '
                        'ni usar en otra ruta.'
                    )
        return super().bulk_update(objs, fields, *args, **kwargs)


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

    objects = LearningPathQuerySet.as_manager()

    class Meta:
        ordering = ['position', 'id']

    def stored_slug(self):
        if self.pk is None:
            return None
        return LearningPath.objects.filter(pk=self.pk).values_list('slug', flat=True).first()

    def takes_official_slug(self):
        """True si esta ruta tomaría el slug de un curso oficial que no era suyo.

        Solo load_courses crea los cursos oficiales (marca ``_official_course``). Una ruta local
        con el mismo nombre recibe otro slug y queda separada, con su contenido y su avance.
        """
        if getattr(self, '_official_course', False):
            return False
        return self.slug in official_course_slugs() and self.stored_slug() != self.slug

    def leaves_official_slug(self):
        """True si un curso oficial guardado cambiaría de slug (revisión de Codex, 22-11-2026).

        La dirección oficial dejaría de responder y load_courses crearía un segundo curso.
        """
        stored = self.stored_slug()
        return stored in official_course_slugs() and self.slug != stored

    def clean(self):
        super().clean()
        if self.leaves_official_slug():
            raise ValidationError({'slug': 'La dirección de un curso oficial no se puede cambiar.'})
        if self.slug and self.takes_official_slug():
            raise ValidationError(
                {
                    'slug': 'Esta dirección está reservada para un curso oficial. '
                    'Elige otra para esta ruta.'
                }
            )

    def save(self, *args, **kwargs):
        if self.leaves_official_slug():
            raise ValidationError(
                f'La ruta {self.pk} es un curso oficial: su slug no se puede cambiar.'
            )
        if not self.slug:
            self.slug = unique_slug(
                LearningPath, self.title, exclude_pk=self.pk, reserved=official_course_slugs()
            )
        elif self.takes_official_slug():
            raise ValidationError(
                f'El slug {self.slug!r} está reservado para un curso oficial; '
                'solo load_courses puede usarlo.'
            )
        clean_learning_path(self)
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
    # Marca de lección oficial: «<slug del curso>:<posición oficial>». Solo la escribe
    # load_courses al crear la lección, y load_courses --force solo reescribe lecciones con marca.
    # Una lección propia nunca la tiene, esté en la posición que esté (decisión de Carlos,
    # 24-11-2026, tras la sexta revisión de Codex). No se edita en los formularios.
    official_key = models.CharField(max_length=220, blank=True, default='', editable=False)

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(fields=['path', 'position'], name='unique_lesson_position'),
            models.UniqueConstraint(
                fields=['path', 'official_key'],
                condition=~models.Q(official_key=''),
                name='unique_lesson_official_key',
            ),
        ]

    def save(self, *args, **kwargs):
        clean_lesson(self)
        self.drop_official_key_when_moved()

        super().save(*args, **kwargs)

    def drop_official_key_when_moved(self):
        """Una lección que pasa a otra ruta deja de ser la lección oficial de su curso.

        Así load_courses puede reponer la oficial en el curso y la lección se puede devolver
        después sin chocar con la marca de la repuesta (séptima revisión de Codex, 24-11-2026).
        """
        if not self.official_key or self.pk is None:
            return
        stored = Lesson.objects.filter(pk=self.pk).values_list('path_id', flat=True).first()
        if stored is not None and stored != self.path_id:
            self.official_key = ''

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


class SectionPageManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class SectionPage(models.Model):
    """Teoría de una opción del menú (una fila por slug de NAV). Se muestra arriba de la sección.

    Su clave estable es ``slug``: los respaldos la usan en lugar del número interno.
    """

    ORIGIN_CHOICES = [
        ('', 'Sin contenido'),
        ('file', 'Cargado desde archivo'),
        ('admin', 'Editado en el administrador'),
    ]

    slug = models.SlugField(max_length=50, unique=True, verbose_name='sección')
    title = models.CharField(max_length=200, verbose_name='título')
    intro_html = models.TextField(
        blank=True,
        verbose_name='introducción',
        help_text='Introducción en HTML. Se limita a las etiquetas permitidas al guardar.',
    )
    intro = models.TextField(
        blank=True, editable=False, help_text='Texto plano de la introducción, para la búsqueda.'
    )
    origin = models.CharField(
        max_length=10, blank=True, choices=ORIGIN_CHOICES, editable=False, verbose_name='origen'
    )
    source_hash = models.CharField(max_length=64, blank=True, editable=False)
    updated = models.DateTimeField(auto_now=True, verbose_name='actualizada')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        editable=False,
        related_name='+',
        verbose_name='actualizada por',
    )

    class Meta:
        ordering = ['id']
        verbose_name = 'página de sección'
        verbose_name_plural = 'páginas de sección'

    objects = SectionPageManager()

    def natural_key(self):
        return (self.slug,)

    def save(self, *args, **kwargs):
        clean_section_page(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class SectionBlock(models.Model):
    """Bloque de teoría de una página de sección, en el orden de ``position``."""

    page = models.ForeignKey(SectionPage, on_delete=models.CASCADE, related_name='blocks')
    title = models.CharField(max_length=200, verbose_name='título')
    body_html = models.TextField(
        blank=True,
        verbose_name='contenido',
        help_text='Contenido en HTML. Se limita a las etiquetas permitidas al guardar.',
    )
    body = models.TextField(
        blank=True, editable=False, help_text='Texto plano del contenido, para la búsqueda.'
    )
    position = models.PositiveIntegerField(default=1, verbose_name='posición')

    class Meta:
        ordering = ['position', 'id']
        verbose_name = 'bloque de teoría'
        verbose_name_plural = 'bloques de teoría'

    def save(self, *args, **kwargs):
        clean_section_block(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


def clean_section_page(page):
    from .services.courses import html_to_text, sanitize_html

    page.intro_html = sanitize_html(page.intro_html)
    page.intro = html_to_text(page.intro_html)


def clean_section_block(block):
    from .services.courses import html_to_text, sanitize_html

    block.body_html = sanitize_html(block.body_html)
    block.body = html_to_text(block.body_html)


def clean_learning_path(path):
    from .services.courses import sanitize_html

    path.intro_html = sanitize_html(path.intro_html)


def clean_lesson(lesson):
    from .services.courses import html_to_text, sanitize_html

    lesson.body_html = sanitize_html(lesson.body_html)
    if lesson.body_html:
        lesson.body = html_to_text(lesson.body_html)


RAW_CLEANERS = {
    SectionPage: clean_section_page,
    SectionBlock: clean_section_block,
    LearningPath: clean_learning_path,
    Lesson: clean_lesson,
}


@receiver(pre_save)
def sanitize_restored_html(sender, instance, raw=False, **kwargs):
    """Al restaurar un respaldo con loaddata, save() no se llama: el HTML se sanea aquí."""
    cleaner = RAW_CLEANERS.get(sender)
    if raw and cleaner:
        cleaner(instance)


@receiver(pre_save, sender=LearningPath)
def restore_learning_path(sender, instance, raw=False, **kwargs):
    """Restauración con loaddata (save() no se llama): admite respaldos JSON anteriores a T05.

    Un respaldo de T04 no trae slug. La ruta recibe uno propio, nunca el de un curso oficial,
    porque antes de T05 los cursos no estaban en la base. Si la fila del respaldo ocuparía un
    curso oficial que ya existe en la base, la restauración se detiene sin aplicar nada.
    """
    if not raw:
        return
    stored = instance.stored_slug()
    if stored and stored in official_course_slugs() and instance.slug != stored:
        raise ValueError(
            f'La ruta {instance.pk} del respaldo ocuparía el curso oficial {stored!r}. '
            'Restaura el respaldo en una base vacía (solo migrate) y ejecuta después '
            'load_courses.'
        )
    if not instance.slug:
        instance.slug = unique_slug(
            LearningPath, instance.title, exclude_pk=instance.pk, reserved=official_course_slugs()
        )


@receiver(pre_save, sender=Lesson)
def restore_lesson(sender, instance, raw=False, **kwargs):
    """Restauración con loaddata: una lección con la posición repetida pasa al final de su ruta.

    Antes de T05 la posición podía repetirse; ahora es única en cada ruta.
    """
    if not raw:
        return
    others = Lesson.objects.filter(path_id=instance.path_id).exclude(pk=instance.pk)
    if others.filter(position=instance.position).exists():
        last = others.aggregate(models.Max('position'))['position__max'] or 0
        top = connection.ops.integer_field_range('PositiveIntegerField')[1]
        if last < top:
            instance.position = last + 1
            return
        # El final está en el máximo del campo: se usa el primer número libre (séptima
        # revisión de Codex, 24-11-2026).
        taken = set(others.values_list('position', flat=True))
        instance.position = next(
            number for number in range(1, len(taken) + 2) if number not in taken
        )
