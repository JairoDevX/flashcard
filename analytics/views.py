from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from study.models import ReviewLog, CardSchedule
from decks.models import Card


@login_required
def analytics_dashboard(request):
    today = date.today()
    user = request.user

    # ── Totals ──────────────────────────────────────────────────────────────
    total_reviews = ReviewLog.objects.filter(user=user).count()
    today_reviews = ReviewLog.objects.filter(user=user, reviewed_at__date=today).count()
    correct_total = ReviewLog.objects.filter(user=user, was_correct=True).count()
    accuracy = int(correct_total / total_reviews * 100) if total_reviews else 0

    total_cards = Card.objects.filter(deck__user=user).count()
    learned_cards = CardSchedule.objects.filter(
        card__deck__user=user,
        state=CardSchedule.STATE_REVIEW,
    ).count()

    # ── Streak ───────────────────────────────────────────────────────────────
    streak = 0
    d = today
    while True:
        if ReviewLog.objects.filter(user=user, reviewed_at__date=d).exists():
            streak += 1
            d -= timedelta(days=1)
        else:
            break

    # ── 7-day daily chart ────────────────────────────────────────────────────
    daily_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = ReviewLog.objects.filter(user=user, reviewed_at__date=day).count()
        correct = ReviewLog.objects.filter(user=user, reviewed_at__date=day, was_correct=True).count()
        daily_data.append({
            'label': day.strftime('%a'),
            'date': day.strftime('%d/%m'),
            'count': count,
            'correct': correct,
        })

    max_count = max((d['count'] for d in daily_data), default=1) or 1

    # ── Due tomorrow ─────────────────────────────────────────────────────────
    tomorrow = today + timedelta(days=1)
    due_tomorrow = CardSchedule.objects.filter(
        card__deck__user=user,
        due_at=tomorrow,
    ).count()

    return render(request, 'analytics/dashboard.html', {
        'total_reviews': total_reviews,
        'today_reviews': today_reviews,
        'accuracy': accuracy,
        'total_cards': total_cards,
        'learned_cards': learned_cards,
        'streak': streak,
        'daily_data': daily_data,
        'max_count': max_count,
        'due_tomorrow': due_tomorrow,
    })


@login_required
def leaderboard(request):
    from django.contrib.auth.models import User
    from django.db.models import Sum
    from trails.models import LessonProgress

    users = list(User.objects.filter(is_active=True))
    users_xp = []
    for u in users:
        trail_xp = LessonProgress.objects.filter(
            user=u, completed=True
        ).aggregate(t=Sum('xp_earned'))['t'] or 0
        review_xp = ReviewLog.objects.filter(user=u, was_correct=True).count() * 5
        users_xp.append({
            'user': u,
            'xp': trail_xp + review_xp,
            'initials': (u.first_name[:1] + u.last_name[:1]).upper() or u.username[:2].upper(),
        })

    users_xp.sort(key=lambda x: x['xp'], reverse=True)

    current_rank = next(
        (i + 1 for i, u in enumerate(users_xp) if u['user'] == request.user), None
    )
    current_data = next((u for u in users_xp if u['user'] == request.user), None)

    return render(request, 'analytics/leaderboard.html', {
        'podium':       users_xp[:3],
        'listing':      users_xp[3:20],
        'current_rank': current_rank,
        'current_data': current_data,
        'total_users':  len(users_xp),
    })
