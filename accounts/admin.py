from django.contrib import admin
from django.utils.html import format_html
from .models import UserStudySettings, Plan, UserSubscription


@admin.register(UserStudySettings)
class UserStudySettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'new_cards_per_day', 'max_reviews_per_day', 'session_order')
    search_fields = ('user__username', 'user__email')


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display  = ('name', 'slug', 'price_badge', 'max_decks_display', 'max_cards_display',
                     'max_cards_per_day', 'ai_generation', 'is_active', 'is_default', 'sort_order')
    list_editable = ('is_active', 'is_default', 'sort_order')
    list_filter   = ('is_active', 'ai_generation')
    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        ('Informações', {
            'fields': ('name', 'slug', 'description', 'sort_order', 'is_active', 'is_default')
        }),
        ('Preços', {
            'fields': ('price_monthly', 'price_yearly'),
        }),
        ('Limites', {
            'fields': ('max_decks', 'max_cards', 'max_cards_per_day'),
            'description': 'Deixe em branco para ilimitado.',
        }),
        ('Recursos', {
            'fields': ('ai_generation', 'priority_support'),
        }),
    )

    def price_badge(self, obj):
        if obj.price_monthly == 0:
            return format_html('<span style="color:green;font-weight:bold">Grátis</span>')
        return format_html('R$ {}/mês', obj.price_monthly)
    price_badge.short_description = 'Preço'

    def max_decks_display(self, obj):
        return obj.get_max_decks_display()
    max_decks_display.short_description = 'Max. Decks'

    def max_cards_display(self, obj):
        return obj.get_max_cards_display()
    max_cards_display.short_description = 'Max. Cards'


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display  = ('user', 'plan', 'started_at', 'expires_at', 'is_active', 'status_badge')
    list_filter   = ('is_active', 'plan')
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',)
    autocomplete_fields = []

    def status_badge(self, obj):
        if obj.is_valid:
            return format_html('<span style="color:green">✓ Ativa</span>')
        return format_html('<span style="color:red">✗ Expirada</span>')
    status_badge.short_description = 'Status'
