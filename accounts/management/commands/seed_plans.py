"""
Management command to create the default subscription plans.
Usage: python manage.py seed_plans
"""
from django.core.management.base import BaseCommand
from accounts.models import Plan


PLANS = [
    {
        "name": "Grátis",
        "slug": "free",
        "description": "Perfeito para começar a aprender com flashcards.",
        "price_monthly": 0,
        "price_yearly": 0,
        "max_decks": 3,
        "max_cards": 100,
        "max_cards_per_day": 20,
        "ai_generation": False,
        "priority_support": False,
        "is_active": True,
        "is_default": True,
        "sort_order": 0,
    },
    {
        "name": "Pro",
        "slug": "pro",
        "description": "Para estudantes sérios que querem ir além.",
        "price_monthly": "19.90",
        "price_yearly": "179.90",
        "max_decks": None,
        "max_cards": None,
        "max_cards_per_day": 200,
        "ai_generation": True,
        "priority_support": False,
        "is_active": True,
        "is_default": False,
        "sort_order": 1,
    },
    {
        "name": "Premium",
        "slug": "premium",
        "description": "Tudo do Pro + suporte prioritário e recursos exclusivos.",
        "price_monthly": "39.90",
        "price_yearly": "359.90",
        "max_decks": None,
        "max_cards": None,
        "max_cards_per_day": 500,
        "ai_generation": True,
        "priority_support": True,
        "is_active": True,
        "is_default": False,
        "sort_order": 2,
    },
]


class Command(BaseCommand):
    help = "Cria os planos de assinatura padrão"

    def handle(self, *args, **options):
        for data in PLANS:
            plan, created = Plan.objects.update_or_create(
                slug=data["slug"],
                defaults=data,
            )
            status = "criado" if created else "atualizado"
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ Plano '{plan.name}' {status}")
            )
        self.stdout.write(self.style.SUCCESS("\nPlanos configurados com sucesso!"))
