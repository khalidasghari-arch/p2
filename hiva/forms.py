from django import forms
from .models import aimpee

AFGHAN_MONTH_CHOICES = [
    ("01", "Hamal"),
    ("02", "Saur"),
    ("03", "Jauza"),
    ("04", "Saratan"),
    ("05", "Asad"),
    ("06", "Sonbola"),
    ("07", "Mizan"),
    ("08", "Aqrab"),
    ("09", "Qaws"),
    ("10", "Jadi"),
    ("11", "Dalw"),
    ("12", "Hoot"),
]

AFGHAN_YEAR_CHOICES = [
    ("1404", "1404"),
    ("1405", "1405"),
    ("1406", "1406"),
]

AFGHAN_PY_CHOICES = [
    ("PY1-Q1", "PY1-Q1"),
    ("PY1-Q2", "PY1-Q2"),
    ("PY1-Q3", "PY1-Q3"),
    ("PY1-Q4", "PY1-Q4"),
]

AFGHAN_BL_CHOICES = [
    ("PRE_I", "PRE_Intervention"),
    ("PRE_P", "POST_Intervention"),
]

# English (Gregorian) months
ENGLISH_MONTH_CHOICES = [
    ("01", "January"),
    ("02", "February"),
    ("03", "March"),
    ("04", "April"),
    ("05", "May"),
    ("06", "June"),
    ("07", "July"),
    ("08", "August"),
    ("09", "September"),
    ("10", "October"),
    ("11", "November"),
    ("12", "December"),
]

# English Years (define the range you want)
YEAR_CHOICES = [(str(y), str(y)) for y in range(2025, 2026)]

class AimpeeAdminForm(forms.ModelForm):
    shamsiyear = forms.ChoiceField(label="Shamsi Year", choices=AFGHAN_YEAR_CHOICES)
    shamsimonth = forms.ChoiceField(label="Shamsi Month", choices=AFGHAN_MONTH_CHOICES)
    period = forms.ChoiceField(label="Period", choices=AFGHAN_PY_CHOICES)
    bl_progress = forms.ChoiceField(label="BL_and_Progress", choices=AFGHAN_BL_CHOICES)
    gre_month = forms.ChoiceField(label="", choices=ENGLISH_MONTH_CHOICES)
    gre_year = forms.ChoiceField(label="sd", choices=YEAR_CHOICES, 
    )                                  
    
    class Meta:
        model = aimpee
        fields = "__all__"
