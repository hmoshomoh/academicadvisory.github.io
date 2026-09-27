from django import forms

from .models import Complaint, ComplaintCategory, ComplaintStatus


class ComplaintForm(forms.ModelForm):
    """Submission form. The `submit_anonymously` toggle decides whether any
    identity is stored at all — see `Complaint`'s anonymity note."""

    submit_anonymously = forms.BooleanField(
        required=False,
        label="Submit this anonymously",
        help_text=(
            "Your name is not stored with the complaint at all. Keep the tracking "
            "reference you get on the next screen — it is the only way to follow up."
        ),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Complaint
        fields = ["category", "subject", "body", "attachment"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "attachment": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
        labels = {"body": "What happened?", "attachment": "Attachment (optional)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ComplaintCategory.objects.all()
        self.fields["category"].empty_label = "Choose a category"


class TrackingForm(forms.Form):
    reference = forms.CharField(
        max_length=32,
        label="Tracking reference",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "ACS-XXXXXXXXXX"}
        ),
    )


class RecategoriseForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=ComplaintCategory.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    note = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Note (optional)",
    )


class ResolveForm(forms.Form):
    note = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        label="Resolution note",
    )


class EscalateForm(forms.Form):
    note = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        label="Why is this being escalated?",
    )


class ReviewForm(forms.Form):
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        label="Note (optional)",
    )


ADMIN_STATUS_FILTERS = [("", "All statuses")] + list(ComplaintStatus.choices)
