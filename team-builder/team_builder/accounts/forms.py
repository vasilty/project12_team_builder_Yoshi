from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import ugettext_lazy as _

from registration.forms import RegistrationFormUniqueEmail


class CustomAuthenticationForm(forms.ModelForm):
    """Form for authenticating users."""
    class Meta:
        model = get_user_model()
        fields = ('email', 'password',)
        widgets = {
            'email': forms.EmailInput(
                attrs={'placeholder': 'Email Address'},
            ),
            'password': forms.PasswordInput(
                attrs={'placeholder': 'Password'}
            ),
        }

    error_messages = {
        'invalid_login': _(
            "Please enter a correct email and password. Note that both "
            "fields may be case-sensitive."
        ),
        'inactive': _("This account is inactive."),
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super(CustomAuthenticationForm, self).__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email is not None and password:
            self.user_cache = authenticate(email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

    def confirm_login_allowed(self, user):
        """
        Controls whether the given User may log in. This is a policy setting,
        independent of end-user authentication. This default behavior is to
        allow login by active users, and reject login by inactive users.
        If the given user cannot log in, this method should raise a
        ``forms.ValidationError``.
        If the given user may log in, this method should return None.
        """
        if not user.is_active:
            raise forms.ValidationError(
                self.error_messages['inactive'],
                code='inactive',
            )


class CustomRegistrationForm(RegistrationFormUniqueEmail):
    """Form for user registration."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Email Address'})

    )
    password1 = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})

    )
    password2 = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'})

    )
    full_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Full Name'})
    )

    class Meta:
        model = get_user_model()
        fields = ('email',)
