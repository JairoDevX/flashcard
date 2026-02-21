from datetime import date, timedelta
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from study.models import ReviewLog, CardSchedule
from decks.models import Card, Deck, LANGUAGE_CHOICES


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

    # Cards consolidados: state=REVIEW com ease_factor >= 2.0
    consolidated = CardSchedule.objects.filter(
        card__deck__user=user,
        state=CardSchedule.STATE_REVIEW,
        ease_factor__gte=2.0,
    ).count()

    # ── Retenção últimos 30 dias ─────────────────────────────────────────────
    thirty_ago = today - timedelta(days=30)
    reviews_30 = ReviewLog.objects.filter(user=user, reviewed_at__date__gte=thirty_ago)
    reviews_30_count = reviews_30.count()
    correct_30 = reviews_30.filter(was_correct=True).count()
    retention_30 = int(correct_30 / reviews_30_count * 100) if reviews_30_count else 0

    # ── Streak de revisões (dias consecutivos) ───────────────────────────────
    streak = 0
    d = today
    while True:
        if ReviewLog.objects.filter(user=user, reviewed_at__date=d).exists():
            streak += 1
            d -= timedelta(days=1)
        else:
            break

    # ── Breakdown por idioma ─────────────────────────────────────────────────
    lang_map = dict(LANGUAGE_CHOICES)
    decks = Deck.objects.filter(user=user)
    lang_stats = defaultdict(lambda: {'cards': 0, 'learned': 0})
    for deck in decks:
        lang = deck.front_language
        lang_stats[lang]['cards'] += deck.cards.count()
        lang_stats[lang]['learned'] += CardSchedule.objects.filter(
            card__deck=deck, state=CardSchedule.STATE_REVIEW
        ).count()
    language_data = [
        {
            'code':    lang,
            'name':    lang_map.get(lang, lang),
            'cards':   stats['cards'],
            'learned': stats['learned'],
            'pct':     int(stats['learned'] / stats['cards'] * 100) if stats['cards'] else 0,
        }
        for lang, stats in lang_stats.items()
        if stats['cards'] > 0
    ]
    language_data.sort(key=lambda x: x['learned'], reverse=True)

    # ── Streak por trilha ────────────────────────────────────────────────────
    from trails.models import Trail
    trail_streaks = list(
        Trail.objects.filter(user=user, streak__gt=0)
        .order_by('-streak')
        .values('name', 'streak', 'icon')[:5]
    )

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
        'total_reviews':  total_reviews,
        'today_reviews':  today_reviews,
        'accuracy':       accuracy,
        'total_cards':    total_cards,
        'learned_cards':  learned_cards,
        'consolidated':   consolidated,
        'retention_30':   retention_30,
        'streak':         streak,
        'daily_data':     daily_data,
        'max_count':      max_count,
        'due_tomorrow':   due_tomorrow,
        'language_data':  language_data,
        'trail_streaks':  trail_streaks,
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
