from datetime import date, timedelta
from .models import CardSchedule, ReviewLog


def get_daily_queue(user):
    """
    Returns a list of Card objects for today's study session.
    Order: learning (reinforcement) → due reviews → new cards.
    """
    from decks.models import Card
    from accounts.models import UserStudySettings

    settings, _ = UserStudySettings.objects.get_or_create(user=user)
    today = date.today()

    # 1. Learning cards – wrong recently, need reinforcement today
    learning_ids = CardSchedule.objects.filter(
        card__deck__user=user,
        state=CardSchedule.STATE_LEARNING,
        due_at__lte=today,
    ).values_list('card_id', flat=True)
    learning_cards = list(Card.objects.filter(id__in=learning_ids))

    # 2. Due cards – reviews whose date has arrived
    due_ids = CardSchedule.objects.filter(
        card__deck__user=user,
        state=CardSchedule.STATE_REVIEW,
        due_at__lte=today,
    ).values_list('card_id', flat=True)
    due_qs = Card.objects.filter(id__in=due_ids)
    if settings.max_reviews_per_day:
        due_qs = due_qs[: settings.max_reviews_per_day]
    due_cards = list(due_qs)

    # 3. New cards – not yet scheduled
    scheduled_ids = CardSchedule.objects.filter(
        card__deck__user=user
    ).values_list('card_id', flat=True)
    new_cards = list(
        Card.objects.filter(deck__user=user)
        .exclude(id__in=scheduled_ids)[: settings.new_cards_per_day]
    )

    if settings.session_order == 'new_first':
        return new_cards + due_cards + learning_cards
    return learning_cards + due_cards + new_cards


def process_review(card, rating, user, time_spent_ms=None):
    """
    Apply SM-2 simplified algorithm to the card schedule.

    rating:
        0 = Errei
        1 = Difícil
        2 = Bom
        3 = Fácil
    """
    today = date.today()

    schedule, _ = CardSchedule.objects.get_or_create(
        card=card,
        defaults={
            'ease_factor': 2.5,
            'interval_days': 0,
            'repetitions': 0,
            'due_at': today,
            'state': CardSchedule.STATE_NEW,
        },
    )

    ef = schedule.ease_factor
    reps = schedule.repetitions
    interval = max(schedule.interval_days, 1)

    if rating == 0:  # Errei
        schedule.repetitions = 0
        schedule.interval_days = 1
        schedule.ease_factor = max(1.3, ef - 0.2)
        schedule.lapses += 1
        schedule.state = CardSchedule.STATE_LEARNING

    elif rating == 1:  # Difícil
        schedule.ease_factor = max(1.3, ef - 0.15)
        schedule.interval_days = max(1, round(interval * 1.2))
        schedule.state = CardSchedule.STATE_REVIEW

    elif rating == 2:  # Bom
        schedule.ease_factor = max(1.3, ef - 0.05)
        if reps == 0:
            schedule.interval_days = 1
        elif reps == 1:
            schedule.interval_days = 6
        else:
            schedule.interval_days = round(interval * ef)
        schedule.repetitions = reps + 1
        schedule.state = CardSchedule.STATE_REVIEW

    elif rating == 3:  # Fácil
        schedule.ease_factor = ef + 0.1
        if reps == 0:
            schedule.interval_days = 2
        elif reps == 1:
            schedule.interval_days = 7
        else:
            schedule.interval_days = round(interval * (ef + 0.15))
        schedule.repetitions = reps + 1
        schedule.state = CardSchedule.STATE_REVIEW

    schedule.due_at = today + timedelta(days=schedule.interval_days)
    schedule.save()

    ReviewLog.objects.create(
        user=user,
        card=card,
        rating=rating,
        time_spent_ms=time_spent_ms,
        was_correct=(rating >= 2),
    )

    return schedule
