from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .forms import RegisterForm, StudySettingsForm
from .models import UserStudySettings, Plan, UserSubscription


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _set_jwt_cookies(response, user):
    """Issue JWT tokens and store them in httpOnly cookies."""
    refresh = RefreshToken.for_user(user)
    access  = refresh.access_token

    from django.conf import settings as django_settings
    jwt_cfg = django_settings.SIMPLE_JWT

    response.set_cookie(
        jwt_cfg["AUTH_COOKIE"],
        str(access),
        max_age=int(jwt_cfg["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        httponly=jwt_cfg["AUTH_COOKIE_HTTP_ONLY"],
        samesite=jwt_cfg["AUTH_COOKIE_SAMESITE"],
        secure=jwt_cfg["AUTH_COOKIE_SECURE"],
        path=jwt_cfg["AUTH_COOKIE_PATH"],
    )
    response.set_cookie(
        jwt_cfg["AUTH_COOKIE_REFRESH"],
        str(refresh),
        max_age=int(jwt_cfg["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=jwt_cfg["AUTH_COOKIE_HTTP_ONLY"],
        samesite=jwt_cfg["AUTH_COOKIE_SAMESITE"],
        secure=jwt_cfg["AUTH_COOKIE_SECURE"],
        path=jwt_cfg["AUTH_COOKIE_PATH"],
    )
    return str(access), str(refresh)


def _clear_jwt_cookies(response):
    from django.conf import settings as django_settings
    jwt_cfg = django_settings.SIMPLE_JWT
    response.delete_cookie(jwt_cfg["AUTH_COOKIE"])
    response.delete_cookie(jwt_cfg["AUTH_COOKIE_REFRESH"])


def _assign_default_plan(user):
    """Assign the default plan to a new user if one exists."""
    try:
        default_plan = Plan.objects.get(is_default=True, is_active=True)
        UserSubscription.objects.get_or_create(user=user, defaults={"plan": default_plan})
    except Plan.DoesNotExist:
        pass


# ─── Web Views ────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)                    # Session auth (for HTMX / web)
            response = redirect(request.POST.get("next") or "/")
            _set_jwt_cookies(response, user)        # JWT cookies (for API / mobile)
            messages.success(request, f"Bem-vindo, {user.username}! 🎉")
            return response
        else:
            messages.error(request, "Usuário ou senha incorretos.")

    return render(request, "accounts/login.html", {
        "next": request.GET.get("next", ""),
    })


def logout_view(request):
    if request.method == "POST":
        # Try to blacklist the refresh token
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        logout(request)
        response = redirect("login")
        _clear_jwt_cookies(response)
        messages.info(request, "Você saiu da conta.")
        return response
    return redirect("/")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserStudySettings.objects.create(user=user)
            _assign_default_plan(user)
            login(request, user)
            response = redirect("/")
            _set_jwt_cookies(response, user)
            messages.success(request, "Conta criada com sucesso! 🚀")
            return response
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile_view(request):
    study_settings, _ = UserStudySettings.objects.get_or_create(user=request.user)
    subscription = getattr(request.user, "subscription", None)

    if request.method == "POST":
        form = StudySettingsForm(request.POST, instance=study_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Preferências salvas!")
            return redirect("profile")
    else:
        form = StudySettingsForm(instance=study_settings)

    return render(request, "accounts/profile.html", {
        "form": form,
        "subscription": subscription,
    })


# ─── JWT API Endpoints ────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def api_token_obtain(request):
    """
    POST /api/auth/token/
    Body: {"username": "...", "password": "..."}
    Returns: {"access": "...", "refresh": "..."}
    """
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(username=username, password=password)

    if user is None:
        return Response(
            {"detail": "Credenciais inválidas."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    refresh = RefreshToken.for_user(user)
    return Response({
        "access":  str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id":       user.id,
            "username": user.username,
            "email":    user.email,
        },
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def api_token_refresh(request):
    """
    POST /api/auth/token/refresh/
    Body: {"refresh": "..."}
    Returns: {"access": "..."}
    """
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return Response({"detail": "Token de refresh necessário."}, status=400)

    try:
        refresh = RefreshToken(refresh_token)
        return Response({"access": str(refresh.access_token)})
    except TokenError as e:
        return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_me(request):
    """GET /api/auth/me/ — current user info"""
    user = request.user
    subscription = getattr(user, "subscription", None)
    return Response({
        "id":       user.id,
        "username": user.username,
        "email":    user.email,
        "plan":     subscription.plan.slug if subscription else "free",
    })
