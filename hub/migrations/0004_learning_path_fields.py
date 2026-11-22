"""T05 (1 de 3): campos nuevos de rutas y lecciones; el slug aún sin restricción única."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('hub', '0003_alter_resource_area'),
    ]

    operations = [
        migrations.AddField(
            model_name='learningpath',
            name='slug',
            field=models.SlugField(default='', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='learningpath',
            name='intro_html',
            field=models.TextField(
                blank=True,
                help_text='Introducción en HTML. Se limita a las etiquetas permitidas al guardar.',
            ),
        ),
        migrations.AddField(
            model_name='learningpath',
            name='position',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name='learningpath',
            options={'ordering': ['position', 'id']},
        ),
        migrations.AddField(
            model_name='lesson',
            name='body_html',
            field=models.TextField(
                blank=True,
                help_text='Contenido en HTML. Se limita a las etiquetas permitidas al guardar.',
            ),
        ),
        migrations.AlterField(
            model_name='lesson',
            name='body',
            field=models.TextField(
                blank=True,
                help_text='Texto plano. Si hay contenido HTML, se calcula a partir de él.',
            ),
        ),
    ]
