from django import forms

from .models import Car, MaintenanceRecord


class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ["year", "make", "model", "nickname"]


class MaintenanceRecordForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRecord
        fields = ["description", "mileage", "performed_on"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "performed_on": forms.DateInput(attrs={"type": "date"}),
        }
