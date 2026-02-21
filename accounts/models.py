from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserStudySettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="study_settings")
    new_cards_per_day = models.PositiveIntegerField(default=20)
    max_reviews_per_day = models.PositiveIntegerField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="America/Sao_Paulo")
    session_order = models.CharField(
        max_length=32,
        choices=[("reviews_first", "Revisões primeiro"), ("new_first", "Novas primeiro")],
        default="reviews_first",
    )

    def __str__(self):
        return f"Settings de {self.user.username}"


# ─── Subscription Plans ───────────────────────────────────────────────────────

class Plan(models.Model):
    SLUG_FREE    = "free"
    SLUG_PRO     = "pro"
    SLUG_PREMIUM = "premium"

    name              = models.CharField(max_length=80)
    slug              = models.SlugField(unique=True)
    description       = models.TextField(blank=True)
    price_monthly     = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    price_yearly      = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Limits (null = unlimited)
    max_decks         = models.PositiveIntegerField(null=True, blank=True, help_text="null = ilimitado")
    max_cards         = models.PositiveIntegerField(null=True, blank=True, help_text="null = ilimitado")
    max_cards_per_day = models.PositiveIntegerField(default=20)
    ai_generation     = models.BooleanField(default=False, help_text="Acesso à geração de cards por IA")
    priority_support  = models.BooleanField(default=False)

    is_active         = models.BooleanField(default=True)
    is_default        = models.BooleanField(default=False, help_text="Plano atribuído automaticamente a novos usuários")
    sort_order        = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} (R$ {self.price_monthly}/mês)"

    def get_max_decks_display(self):
        return "Ilimitado" if self.max_decks is None else str(self.max_decks)

    def get_max_cards_display(self):
        return "Ilimitado" if self.max_cards is None else str(self.max_cards)


class UserSubscription(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    plan       = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscribers")
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="null = nunca expira")
    is_active  = models.BooleanField(default=True)
    notes      = models.TextField(blank=True)

    class Meta:
        verbose_name = "Assinatura"
        verbose_name_plural = "Assinaturas"

    def __str__(self):
        return f"{self.user.username} → {self.plan.name}"

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True
