from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserStudySettings


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class StudySettingsForm(forms.ModelForm):
    class Meta:
        model = UserStudySettings
        fields = ("new_cards_per_day", "max_reviews_per_day", "timezone", "session_order")
        widgets = {
            "new_cards_per_day": forms.NumberInput(attrs={"min": 1, "max": 200}),
            "max_reviews_per_day": forms.NumberInput(attrs={"min": 1, "max": 9999}),
        }
