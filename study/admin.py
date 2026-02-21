from django.contrib import admin
from .models import CardSchedule, ReviewLog


@admin.register(CardSchedule)
class CardScheduleAdmin(admin.ModelAdmin):
    list_display = ('card', 'state', 'due_at', 'interval_days', 'ease_factor', 'repetitions', 'lapses')
    list_filter = ('state',)
    search_fields = ('card__front',)
    ordering = ('due_at',)


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'card', 'rating', 'was_correct', 'time_spent_ms', 'reviewed_at')
    list_filter = ('was_correct', 'rating', 'user')
    search_fields = ('user__username', 'card__front')
    ordering = ('-reviewed_at',)
