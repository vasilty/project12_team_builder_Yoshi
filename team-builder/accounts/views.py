from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView
from django.views.generic.edit import FormView

from braces.views import LoginRequiredMixin
from registration.backends.hmac.views import RegistrationView, ActivationView
from registration.signals import user_activated

from . import forms


class SignInView(FormView):
    """Sign in view."""
    template_name = 'accounts/signin.html'
    form_class = forms.CustomAuthenticationForm
    success_url = reverse_lazy('projects:home')

    def form_valid(self, form):
        messages.success(self.request, "You've been successfully logged in!")
        login(self.request, form.user_cache)
        return super(SignInView, self).form_valid(form)


class SignOutView(LoginRequiredMixin, RedirectView):
    """Sign out view."""
    url = reverse_lazy('projects:home')
    login_url = reverse_lazy('accounts:sign-in')

    def get(self, request):
        logout(request)
        messages.success(self.request, "You've been successfully logged out!")
        return super(SignOutView, self).get(request)


class SignUpView(RegistrationView):
    """Sign up view."""
    form_class = forms.CustomRegistrationForm
    template_name = 'accounts/signup.html'

    def get_form_class(self):
        return forms.CustomRegistrationForm

    def create_inactive_user(self, form):
        """
        Create the inactive user account and send an email containing
        activation instructions.
        Save user's full name to UserProfile.
        """
        new_user = form.save(commit=False)
        new_user.is_active = False
        new_user.save()

        new_user.userprofile.full_name = form.cleaned_data['full_name']
        new_user.userprofile.save()

        self.send_activation_email(new_user)

        return new_user


class AccountActivateView(ActivationView):
    """Account activation view."""
    def get_success_url(self, user):
        return reverse_lazy('projects:user-profile-update')


def login_and_flash_messages(**kwargs):
    """Login user and send success flash messages."""
    request = kwargs.get('request')
    user = kwargs.get('user')
    login(request, user)
    messages.success(request,
                     'You have successfully registered and logged in.')
    messages.success(request, 'Tell us a little bit about yourself.')

user_activated.connect(login_and_flash_messages)
