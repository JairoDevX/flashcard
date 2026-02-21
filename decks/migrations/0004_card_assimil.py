from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('decks', '0003_card_card_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='context_sentence',
            field=models.TextField(
                blank=True,
                verbose_name='Frase de contexto',
                help_text='Frase completa onde a palavra/expressão aparece.',
            ),
        ),
        migrations.AlterField(
            model_name='card',
            name='card_type',
            field=models.CharField(
                max_length=15,
                choices=[
                    ('normal', 'Normal'),
                    ('cloze', 'Cloze (lacuna)'),
                    ('translation', 'Tradução'),
                ],
                default='normal',
                verbose_name='Tipo do card',
            ),
        ),
    ]
