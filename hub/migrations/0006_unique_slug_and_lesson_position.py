"""T05 (3 de 3): slug único y una lección por posición en cada ruta."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('hub', '0005_learning_path_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='learningpath',
            name='slug',
            field=models.SlugField(max_length=200, unique=True),
        ),
        migrations.AddConstraint(
            model_name='lesson',
            constraint=models.UniqueConstraint(
                fields=('path', 'position'), name='unique_lesson_position'
            ),
        ),
    ]
