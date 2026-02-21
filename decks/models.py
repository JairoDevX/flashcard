from django.db import models
from django.contrib.auth.models import User


LANGUAGE_CHOICES = [
    ('pt-BR', '🇧🇷 Português (Brasil)'),
    ('en-US', '🇺🇸 English (US)'),
    ('en-GB', '🇬🇧 English (UK)'),
    ('es-ES', '🇪🇸 Español'),
    ('fr-FR', '🇫🇷 Français'),
    ('de-DE', '🇩🇪 Deutsch'),
    ('it-IT', '🇮🇹 Italiano'),
    ('ja-JP', '🇯🇵 日本語'),
    ('zh-CN', '🇨🇳 中文'),
    ('ko-KR', '🇰🇷 한국어'),
]


class Deck(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="decks")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    front_language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='en-US',
        verbose_name='Idioma da frente (pronúncia)',
    )
    back_language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='pt-BR',
        verbose_name='Idioma do verso (pronúncia)',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def card_count(self):
        return self.cards.count()

    def due_count(self):
        from datetime import date
        from study.models import CardSchedule
        return CardSchedule.objects.filter(
            card__deck=self,
            due_at__lte=date.today(),
        ).count()

    def new_count(self):
        from study.models import CardSchedule
        scheduled_ids = CardSchedule.objects.filter(card__deck=self).values_list("card_id", flat=True)
        return self.cards.exclude(id__in=scheduled_ids).count()


class Card(models.Model):
    CARD_TYPE_NORMAL = 'normal'
    CARD_TYPE_CLOZE = 'cloze'
    CARD_TYPE_TRANSLATION = 'translation'
    CARD_TYPE_CHOICES = [
        ('normal', 'Normal'),
        ('cloze', 'Cloze (lacuna)'),
        ('translation', 'Tradução'),
    ]

    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="cards")
    card_type = models.CharField(
        max_length=15,
        choices=CARD_TYPE_CHOICES,
        default='normal',
        verbose_name='Tipo do card',
    )
    front = models.TextField()
    back = models.TextField()
    context_sentence = models.TextField(
        blank=True,
        verbose_name='Frase de contexto',
        help_text='Frase completa onde a palavra/expressão aparece. Ex: "I go to the store every day."',
    )
    tags = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.front[:50]}…"

    def get_tags_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]
