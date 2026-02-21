from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from decks.models import Card, Deck


class Trail(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trails')
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icon        = models.CharField(max_length=10, default='📚')
    deck        = models.ForeignKey(
        Deck, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='trails'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.name

    @property
    def total_lessons(self):
        return self.lessons.count()

    def completed_count(self, user):
        return LessonProgress.objects.filter(
            user=user, lesson__trail=self, completed=True
        ).count()


class Lesson(models.Model):
    trail      = models.ForeignKey(Trail, on_delete=models.CASCADE, related_name='lessons')
    order      = models.PositiveIntegerField()
    title      = models.CharField(max_length=200)
    cards      = models.ManyToManyField(Card, blank=True, related_name='lessons')
    xp_reward  = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.trail.name} — Lição {self.order}: {self.title}'

    def is_unlocked(self, user):
        if self.order == 1:
            return True
        prev = Lesson.objects.filter(trail=self.trail, order=self.order - 1).first()
        if not prev:
            return True
        return LessonProgress.objects.filter(
            user=user, lesson=prev, completed=True
        ).exists()

    def is_completed(self, user):
        return LessonProgress.objects.filter(
            user=user, lesson=self, completed=True
        ).exists()


class LessonProgress(models.Model):
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson       = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    completed    = models.BooleanField(default=False)
    xp_earned    = models.PositiveIntegerField(default=0)
    score        = models.PositiveIntegerField(default=0)   # accuracy %
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'lesson']

    def __str__(self):
        status = 'completa' if self.completed else 'em progresso'
        return f'{self.user.username} – {self.lesson} ({status})'
