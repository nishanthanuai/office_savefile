from django import forms
from django.core.exceptions import ValidationError
from .models import GPXFile

def validate_gpx_file(value):
    if not value.name.endswith('.gpx'):
        raise ValidationError("Only .gpx files are allowed.")

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class GpxUploadForm(forms.Form):
    gpx_file = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True, 'accept': '.gpx'}),
        required=True,
        validators=[validate_gpx_file]
    )

class GPXUploadFormEdit(forms.ModelForm):
    class Meta:
        model = GPXFile
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'accept': '.gpx'}),
        }

        
from .models import CustomUser

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'role']


from django import forms
from .models import CustomUser

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': "Set User's password"})
    )

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'role']
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': "Enter User's email"}),
            'role': forms.Select(attrs={'placeholder': "Select User's role"}),
        }
