# dashboard/forms.py
from django import forms
from django.forms import modelformset_factory
from hiva.models import HQIPAssessment, Score, Facility, Assessor, Implementor, Assessmenttype

class AssessmentHeaderForm(forms.Form):
    facilityfk = forms.ModelChoiceField(queryset=Facility.objects.none(), label="Facility")
    assesorfk = forms.ModelChoiceField(queryset=Assessor.objects.all(), label="Assessor")
    implementorfk = forms.ModelChoiceField(queryset=Implementor.objects.all(), label="Implementor")
    assessmenttype = forms.ModelChoiceField(queryset=Assessmenttype.objects.all(), label="Assessment type")
    assessmentdate = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, facility_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if facility_qs is not None:
            self.fields["facilityfk"].queryset = facility_qs


class AssessmentRowForm(forms.ModelForm):
    scorefk = forms.ModelChoiceField(
        queryset=Score.objects.all().order_by("id"),
        required=False,
        label="Score"
    )

    class Meta:
        model = HQIPAssessment
        fields = ["scorefk", "remarks"]
        widgets = {
            "remarks": forms.Textarea(attrs={"rows": 1}),
        }


AssessmentFormSet = modelformset_factory(
    HQIPAssessment,
    form=AssessmentRowForm,
    extra=0,
    can_delete=False
)
