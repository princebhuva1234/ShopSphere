from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):

    class Meta:
        model = Review

        fields = [
            'rating',
            'title',
            'comment',
        ]

        widgets = {
            'rating': forms.Select(
                attrs={
                    'class': 'form-control',
                }
            ),

            'title': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter your review title',
                    'maxlength': 150,
                }
            ),

            'comment': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Share your experience with this product',
                    'rows': 5,
                }
            ),
        }

        labels = {
            'rating': 'Your Rating',
            'title': 'Review Title',
            'comment': 'Your Review',
        }

    def clean_title(self):
        title = self.cleaned_data['title'].strip()

        if not title:
            raise forms.ValidationError(
                'Please enter a review title.'
            )

        return title

    def clean_comment(self):
        comment = self.cleaned_data['comment'].strip()

        if not comment:
            raise forms.ValidationError(
                'Please write your review.'
            )

        return comment