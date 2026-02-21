from django.contrib import admin
from .models import Deck, Card


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'card_count', 'created_at')
    list_filter = ('user',)
    search_fields = ('name', 'description')
    ordering = ('-created_at',)


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('front', 'deck', 'tags', 'created_at')
    list_filter = ('deck',)
    search_fields = ('front', 'back', 'tags')
    ordering = ('deck', 'created_at')
