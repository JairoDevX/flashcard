from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trails', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trail',
            name='streak',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='trail',
            name='last_lesson_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='lesson',
            name='phase',
            field=models.CharField(
                max_length=10,
                choices=[
                    ('passive', 'Passiva – reconhecimento'),
                    ('active',  'Ativa – produção'),
                ],
                default='passive',
            ),
        ),
        migrations.AddField(
            model_name='lesson',
            name='grammar_notes',
            field=models.TextField(
                blank=True,
                help_text='Notas de gramática exibidas ao fim da lição.',
            ),
        ),
    ]
