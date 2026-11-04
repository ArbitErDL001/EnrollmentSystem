from django import forms

from .models import Payment


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ('amount', 'note')
        widgets = {'amount': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'})}

    def __init__(self, *args, assessment, recorded_by, **kwargs):
        self.assessment = assessment
        self.recorded_by = recorded_by
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount > self.assessment.balance:
            raise forms.ValidationError('Payment cannot exceed the outstanding balance.')
        return amount

    def save(self, commit=True):
        payment = super().save(commit=False)
        payment.assessment = self.assessment
        payment.recorded_by = self.recorded_by
        if commit:
            payment.save()
        return payment
