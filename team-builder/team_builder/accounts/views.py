from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.views.generic.edit import FormView, View

from braces.views import LoginRequiredMixin

from registration import signals
from registration.backends.hmac.views import (RegistrationView,
                                              ActivationView)

from . import forms


class SignInView(FormView):
    """Sign in view."""
    template_name = 'accounts/signin.html'
    form_class = forms.CustomAuthenticationForm
    success_url = reverse_lazy('projects:home')

    def form_valid(self, form):
        # form.send_email()
        messages.success(self.request, "You've been successfully logged in!")
        login(self.request, form.user_cache)
        return super(SignInView, self).form_valid(form)


class SignOutView(LoginRequiredMixin, View):
    """Sign out view."""
    success_url = reverse_lazy('projects:home')
    login_url = reverse_lazy('accounts:sign-in')

    def get(self, request):
        logout(request)
        messages.success(self.request, "You've been successfully logged out!")
        return HttpResponseRedirect(self.success_url)


class RegistrationCompleteView(TemplateView):
    template_name = 'accounts/registration_complete.html'


class SignUpView(RegistrationView):
    form_class = forms.CustomRegistrationForm
    template_name = 'accounts/signup.html'
    email_body_template = 'accounts/activation_email.txt'
    email_subject_template = 'accounts/activation_email_subject.txt'

    def get_success_url(self, user):
        return reverse_lazy('accounts:registration-complete')

    def get_form_class(self):
        return forms.CustomRegistrationForm

    def create_inactive_user(self, form):
        """
        Create the inactive user account and send an email containing
        activation instructions.
        Save user's email to UserProfile.
        """
        new_user = form.save(commit=False)
        new_user.is_active = False
        new_user.save()

        new_user.userprofile.full_name = form.cleaned_data['full_name']
        new_user.userprofile.save()

        self.send_activation_email(new_user)

        return new_user


class AccountActivateView(ActivationView):
    template_name = 'accounts/registration_activate.html'

    def get_success_url(self, user):
        return reverse_lazy('accounts:sign-in')

    def get(self, *args, **kwargs):
        """
        The base activation logic; subclasses should leave this method
        alone and implement activate(), which is called from this
        method.
        """
        activated_user = self.activate(*args, **kwargs)
        if activated_user:
            signals.user_activated.send(
                sender=self.__class__,
                user=activated_user,
                request=self.request
            )
            success_url = self.get_success_url(activated_user)
            try:
                to, args, kwargs = success_url
                messages.success(self.request,
                                 ('Your account has been successfully'
                                  ' activated.'))
                return redirect(to, *args, **kwargs)
            except ValueError:
                messages.success(self.request,
                                 ('Your account has been successfully'
                                  ' activated.'))
                return redirect(success_url)
        return super(AccountActivateView, self).get(*args, **kwargs)


class AccountActivationCompleteView(TemplateView):
    template_name = 'accounts/registration_activation_complete.html'
