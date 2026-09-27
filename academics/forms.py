from django import forms

from .models import AdvisoryRequest


class AdvisoryRequestForm(forms.ModelForm):
    class Meta:
        model = AdvisoryRequest
        fields = ["subject", "body"]
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }
        labels = {"body": "What do you need help with?"}


class AdvisoryResponseForm(forms.ModelForm):
    class Meta:
        model = AdvisoryRequest
        fields = ["response"]
        widgets = {
            "response": forms.Textarea(attrs={"class": "form-control", "rows": 5})
        }
        labels = {"response": "Your response"}

    def clean_response(self):
        value = (self.cleaned_data.get("response") or "").strip()
        if not value:
            raise forms.ValidationError("Write a response before sending it.")
        return value
