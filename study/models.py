from django.db import models
from django.contrib.auth.models import User
from datetime import date


class CardSchedule(models.Model):
    STATE_NEW = 'NEW'
    STATE_LEARNING = 'LEARNING'
    STATE_REVIEW = 'REVIEW'
    STATE_CHOICES = [
        (STATE_NEW, 'Nova'),
        (STATE_LEARNING, 'Aprendendo'),
        (STATE_REVIEW, 'Revisão'),
    ]

    card = models.OneToOneField(
        'decks.Card', on_delete=models.CASCADE, related_name='schedule'
    )
    ease_factor = models.FloatField(default=2.5)
    interval_days = models.PositiveIntegerField(default=0)
    repetitions = models.PositiveIntegerField(default=0)
    due_at = models.DateField(default=date.today)
    lapses = models.PositiveIntegerField(default=0)
    state = models.CharField(max_length=10, choices=STATE_CHOICES, default=STATE_NEW)

    class Meta:
        ordering = ['due_at']

    def __str__(self):
        return f"Schedule: {self.card} | state={self.state} | due={self.due_at}"


class ReviewLog(models.Model):
    RATING_WRONG = 0
    RATING_HARD = 1
    RATING_GOOD = 2
    RATING_EASY = 3

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_logs')
    card = models.ForeignKey(
        'decks.Card', on_delete=models.CASCADE, related_name='review_logs'
    )
    reviewed_at = models.DateTimeField(auto_now_add=True)
    rating = models.PositiveSmallIntegerField()
    time_spent_ms = models.PositiveIntegerField(null=True, blank=True)
    was_correct = models.BooleanField()

    class Meta:
        ordering = ['-reviewed_at']

    def __str__(self):
        return f"{self.user} | card={self.card_id} | rating={self.rating}"
