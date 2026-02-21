from django.contrib import admin
from .models import Trail, Lesson, LessonProgress


class LessonInline(admin.TabularInline):
    model  = Lesson
    extra  = 0
    fields = ('order', 'title', 'xp_reward')
    ordering = ('order',)


@admin.register(Trail)
class TrailAdmin(admin.ModelAdmin):
    list_display  = ('name', 'user', 'total_lessons', 'created_at')
    list_filter   = ('user',)
    search_fields = ('name',)
    inlines       = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display  = ('trail', 'order', 'title', 'xp_reward')
    list_filter   = ('trail',)
    filter_horizontal = ('cards',)


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'completed', 'score', 'xp_earned', 'completed_at')
    list_filter  = ('completed', 'lesson__trail')
