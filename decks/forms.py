from django import forms
from .models import Deck, Card


class DeckForm(forms.ModelForm):
    class Meta:
        model = Deck
        fields = ('name', 'description', 'front_language', 'back_language')
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ex: Vocabulário Inglês'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descrição opcional...'}),
        }
        labels = {
            'front_language': 'Idioma da Frente 🔊',
            'back_language': 'Idioma do Verso 🔊',
        }


class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = ('card_type', 'front', 'back', 'tags')
        widgets = {
            'card_type': forms.Select(attrs={'id': 'id_card_type'}),
            'front': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Frente do card (pergunta)', 'id': 'id_front'}),
            'back': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Verso do card (resposta)'}),
            'tags': forms.TextInput(attrs={'placeholder': 'Ex: verbo, gramática, básico'}),
        }
        labels = {
            'card_type': 'Tipo do Card',
            'front': 'Frente',
            'back': 'Verso',
            'tags': 'Tags (separadas por vírgula)',
        }
