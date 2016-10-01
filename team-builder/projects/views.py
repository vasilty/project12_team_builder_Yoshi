import json

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse_lazy
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template.loader import render_to_string
from django.views import generic


from braces.views import LoginRequiredMixin
from pusher import Pusher

from . import forms
from . import models
from . import utils


def set_from_list(values_list):
    """Returns a set of lower cased values from a list."""
    return set(map(lambda v: v.lower(), values_list))


def context_from_values_list(initial_list, additional_value):
    """From a list of values makes a set of unique case-insensitive values.
    Returns the set with an additional value inserted at index 0."""
    # Lowercase values and get a set of unique values.
    values = set_from_list(initial_list)
    # Sort values alphabetically.
    values = sorted(values)
    values.insert(0, additional_value)
    return values


class IndexView(generic.ListView):
    """Index view."""
    template_name = 'projects/index.html'
    context_object_name = 'projects'
    model = models.Project
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data()

        queryset = self.model.objects.filter(active=True)
        # Get project needs
        term = self.request.GET.get('q')
        if term:
            queryset = queryset.filter(
                Q(name__icontains=term) |
                Q(description__icontains=term)
            )
        positions = models.Position.objects.filter(
            project__in=queryset
        ).values_list('role__name', flat=True)
        context['needs'] = context_from_values_list(
            initial_list=positions,
            additional_value='all needs'
        )

        # Get position to filter by
        if not self.request.GET.get('position'):
            context['filtered_position'] = "all needs"
        else:
            context['filtered_position'] = self.request.GET.get('position')

        # Get search term to filter by
        if not self.request.GET.get('q'):
            context['search_term'] = ''
        else:
            context['search_term'] = self.request.GET.get('q')
        return context

    def get_queryset(self):
        queryset = self.model.objects.filter(active=True).prefetch_related(
            'positions',
            'positions__role'
        )

        term = self.request.GET.get('q')
        if term:
            queryset = queryset.filter(
                Q(name__icontains=term) |
                Q(description__icontains=term)
            )

        if self.request.GET.get('position'):
            position = self.request.GET.get('position')
            queryset = queryset.filter(
                positions__role__name__iexact=position
            ).distinct()
        return queryset


class ForMeView(LoginRequiredMixin, generic.ListView):
    """View to list projects that have positions fitting a user."""
    template_name = 'projects/index.html'
    context_object_name = 'projects'
    model = models.Project
    login_url = reverse_lazy('accounts:sign-in')
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        self.for_me_projects = self.get_for_me(
            request,
            self.model.objects.filter(active=True)
        )
        return super(ForMeView, self).get(request, *args, **kwargs)

    def get_for_me(self, request, queryset):
        """Get projects that have positions fitting a User."""
        user = request.user
        user_skills = user.userprofile.skills.all().values_list('name',
                                                                flat=True)
        user_skills = set_from_list(user_skills)
        positions = models.Position.objects.all().prefetch_related(
            'related_skills')
        positions_need_me = []
        for position in positions:
            position_skills = [skill.name for skill in
                               position.related_skills.all()]
            position_skills = set_from_list(position_skills)
            missing_skills = [skill for skill in position_skills if skill not
                              in user_skills]
            if not missing_skills:
                positions_need_me.append(position)

        return queryset.filter(
            positions__in=positions_need_me
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super(ForMeView, self).get_context_data()

        # Get project needs
        queryset = self.for_me_projects
        positions = models.Position.objects.filter(
            project__in=queryset
        ).values_list('role__name', flat=True)
        context['needs'] = context_from_values_list(
            initial_list=positions,
            additional_value='all needs'
        )

        # Get position to filter by
        if not self.request.GET.get('position'):
            context['filtered_position'] = "all needs"
        else:
            context['filtered_position'] = self.request.GET.get('position')

        context['forme'] = True
        return context

    def get_queryset(self):
        queryset = self.for_me_projects.prefetch_related(
            'positions',
            'positions__role'
        )

        if self.request.GET.get('position'):
            position = self.request.GET.get('position')
            queryset = queryset.filter(
                positions__role__name__icontains=position
            ).distinct()
        return queryset


class ProjectDetailView(LoginRequiredMixin, generic.DetailView):
    """Project detail view."""
    model = models.Project
    template_name = 'projects/project.html'
    login_url = reverse_lazy('accounts:sign-in')

    def get_queryset(self):
        return self.model.objects.all().select_related(
            'owner',
            'owner__userprofile',
        ).prefetch_related(
            'positions',
            'positions__related_skills',
            'positions__role',
            'positions__user',
            'positions__applications',
            'positions__applications__applicant'
        )


class ProjectUpdateView(LoginRequiredMixin, generic.UpdateView):
    """View to update a project."""
    model = models.Project
    template_name = 'projects/project_edit.html'
    form_class = forms.ProjectForm
    login_url = reverse_lazy('accounts:sign-in')

    def get_success_url(self):
        return reverse_lazy('projects:project-detail',
                            kwargs={'pk': self.object.id})

    def get_queryset(self):
        queryset = super(ProjectUpdateView, self).get_queryset()
        queryset = queryset.filter(owner=self.request.user)
        return queryset

    def get_object(self, queryset=None):
        if self.kwargs.get('pk'):
            return super(ProjectUpdateView, self).get_object(queryset)
        else:
            return None

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates prefilled versions of the form
        and its inline formset.
        """
        self.object = self.get_object()
        form = self.get_form()
        position_formset = forms.ProjectFormSet(
            instance=self.object,
        )

        return self.render_to_response(
            self.get_context_data(form=form,
                                  position_formset=position_formset))

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance and its inline
        formset with the passed POST variables and then checking them for
        validity.
        """
        self.object = self.get_object()
        form = self.get_form()
        position_formset = forms.ProjectFormSet(
            self.request.POST,
            instance=self.object,
        )

        if form.is_valid() and position_formset.is_valid():
            return self.form_valid(form, position_formset)
        else:
            return self.form_invalid(form, position_formset)

    def form_valid(self, form, position_formset):
        """
        Called if all forms are valid. Updates or creates a Project instance
        along with associated Positions and then redirects to a success page.
        """

        self.object = self.get_object()

        if self.object is not None:
            form.save()
        else:
            self.object = form.save(commit=False)
            self.object.owner = self.request.user
            self.object.save()

        positions = position_formset.save(commit=False)

        for position in positions:
            position.project = self.object
            position.save()

        for position in position_formset.deleted_objects:
            position.delete()

        position_formset.save_m2m()

        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, position_formset):
        """
        Called if a form is invalid. Re-renders the context data with the
        data-filled forms and errors.
        """

        return self.render_to_response(
            self.get_context_data(
                form=form,
                position_formset=position_formset,
            )
        )


class ProjectDeleteView(LoginRequiredMixin, generic.DeleteView):
    """"View to delete a project."""
    model = models.Project
    login_url = reverse_lazy('accounts:sign-in')

    def get_queryset(self):
        queryset = super(ProjectDeleteView, self).get_queryset()
        return queryset.filter(owner=self.request.user)

    def get_success_url(self):
        success_url = reverse_lazy('projects:user-profile-detail',
                                   kwargs={'pk': self.request.user.id})
        return success_url

    def delete(self, request, *args, **kwargs):
        """
        Calls the delete() method on the fetched object and then
        redirects to the success URL.
        """
        self.object = self.get_object()
        success_url = self.get_success_url()
        response = {'url': str(success_url)}
        self.object.delete()
        return HttpResponse(json.dumps(response),
                            content_type='application/json')


class UserProfileDetailView(LoginRequiredMixin, generic.DetailView):
    model = models.UserProfile
    template_name = 'projects/profile.html'
    login_url = reverse_lazy('accounts:sign-in')

    def get_queryset(self):
        queryset = models.UserProfile.objects.all().select_related(
            'user',
        ).prefetch_related(
            'skills'
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['past_projects'] = models.Project.objects.filter(
            positions__user=context['userprofile'].user
        ).prefetch_related(
            'positions__user',
            'positions__role',
        ).distinct()
        return context


class UserProfileUpdateView(LoginRequiredMixin, generic.UpdateView):
    """View to update user profile."""
    model = models.UserProfile
    template_name = 'projects/profile_edit.html'
    form_class = forms.UserProfileForm
    login_url = reverse_lazy('accounts:sign-in')

    def get_success_url(self):
        return reverse_lazy('projects:user-profile-detail',
                            kwargs={'pk': self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = context['userprofile'].user.projects.all()
        context['past_projects'] = models.Project.objects.filter(
            positions__user=context['userprofile'].user
        ).prefetch_related(
            'positions__user',
            'positions__role',
        ).distinct()
        return context

    def get_object(self, queryset=None):
        """
        Returns the object the view is displaying.
        Returns a current user UserProfile.
        As a result users can edit only their UserProfiles.
        """
        if queryset is None:
            queryset = self.get_queryset().select_related(
                'user'
            )
        user = self.request.user
        obj = queryset.get(user=user)
        return obj

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates prefilled versions of the form
        and its inline formset.
        """
        self.object = self.get_object()
        form = self.get_form()
        skill_formset = forms.UserProfileSkillFormSet(instance=self.object)
        return self.render_to_response(
            self.get_context_data(form=form,
                                  skill_formset=skill_formset))

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance and its inline
        formset with the passed POST variables and then checking them for
        validity.
        """
        self.object = self.get_object()
        form = self.get_form()
        skill_formset = forms.UserProfileSkillFormSet(
            self.request.POST,
            instance=self.object,
        )

        if form.is_valid() and skill_formset.is_valid():
            return self.form_valid(request, form, skill_formset)
        else:
            return self.form_invalid(form, skill_formset)

    def form_valid(self, request, form, skill_formset):
        """
        Called if all forms are valid. Updates a UserProfile instance
        with the associated Skills and then redirects to a success page.
        """
        # Save UserProfileForm
        form.save()

        # For each skill form in the formset
        for skill_form in skill_formset:
            # If skill form is not in the deleted forms
            if skill_form not in skill_formset.deleted_forms:
                # If there are data in the form
                if skill_form.cleaned_data:
                    # If the form instance has a pk but no skill name data,
                    # delete form instance
                    if skill_form.instance.pk and (
                            not skill_form.cleaned_data['skill_name']):
                        skill_form.instance.delete()
                    # Otherwise save the form
                    else:
                        skill_form.save()
            # If skill form is in the deleted forms
            else:
                # If there is an instance associated with the form, delete
                # form instance
                if skill_form.instance.pk:
                    skill_form.instance.delete()
        messages.success(request, 'User Profile successfully saved.')
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, skill_formset):
        """
        Called if a form is invalid. Re-renders the context data with the
        data-filled forms and errors.
        """
        return self.render_to_response(
            self.get_context_data(
                form=form,
                skill_formset=skill_formset,
            )
        )


class CreateApplicationView(LoginRequiredMixin, generic.View):
    """View to create Application."""
    model = models.Application
    login_url = reverse_lazy('accounts:sign-in')
    form_class = forms.ApplicationForm
    email_subject_template = 'projects/new_application_email_subject.txt'
    email_body_template = 'projects/new_application_email.txt'

    def get_success_url(self):
        success_url = reverse_lazy('projects:project-detail',
                                   kwargs={'pk': self.kwargs.get('pk')})
        return success_url

    def get_email_context(self, application):
        """Build the template context used for the email."""
        return {'application': application}

    def send_email(self, application):
        """Send email."""
        context = self.get_email_context(application)
        subject = render_to_string(self.email_subject_template, context)
        # Force subject to a single line to avoid header-injection issues.
        subject = ''.join(subject.splitlines())
        message = render_to_string(self.email_body_template, context)

        email = EmailMessage(
            subject=subject,
            body=message,
            to=(application.position.project.owner.email,)
        )
        email.send()

    def post(self, request, *args, **kwargs):
        form = self.form_class(data=request.POST, request=request)
        if form.is_valid():

            application = form.save(commit=False)
            application.applicant = request.user
            application.save()

            messages.success(
                request,
                ('You have successfully applied for ' +
                 application.position.role.name + ' position.')
            )

            self.send_email(application)
        else:
            messages.error(
                request,
                'An error occurred while sending your application.'
            )
        return HttpResponseRedirect(self.get_success_url())


class ApplicationsListView(LoginRequiredMixin, generic.ListView):
    """View that lists all applications."""
    template_name = 'projects/applications.html'
    model = models.Application
    context_object_name = 'applications'
    paginate_by = 20
    login_url = reverse_lazy('accounts:sign-in')

    def get_context_data(self, **kwargs):
        context = super(ApplicationsListView, self).get_context_data()

        # Get projects
        projects = models.Project.objects.filter(
            owner=self.request.user
        ).values_list('name', flat=True)
        context['projects'] = context_from_values_list(
            initial_list=projects,
            additional_value='all projects'
        )

        # Get project needs
        project = self.request.GET.get('project')
        if project:
            queryset = models.Project.objects.filter(
                owner=self.request.user,
                name__iexact=project,
            )
        else:
            queryset = models.Project.objects.filter(owner=self.request.user)

        positions = models.Position.objects.filter(
            project__in=queryset
        ).values_list('role__name', flat=True)
        context['needs'] = context_from_values_list(
            initial_list=positions,
            additional_value='all needs'
        )

        # Get statuses
        context['statuses'] = [
            'all applications',
            'new applications',
            'accepted',
            'rejected',
        ]

        # Get position to filter by
        if not self.request.GET.get('position'):
            context['filtered_position'] = "all needs"
        else:
            context['filtered_position'] = self.request.GET.get('position')

        # Get project to filter by
        if not self.request.GET.get('project'):
            context['filtered_project'] = 'all projects'
        else:
            context['filtered_project'] = self.request.GET.get('project')

        # Get status to filter by
        if not self.request.GET.get('status'):
            context['filtered_status'] = 'all applications'
        else:
            context['filtered_status'] = self.request.GET.get('status')

        return context

    def get_queryset(self):
        queryset = self.model.objects.filter(
            position__project__owner=self.request.user
        ).select_related(
            'applicant',
            'applicant__userprofile'
        ).prefetch_related(
            'position',
            'position__role',
            'position__project'
        )

        if self.request.GET.get('position'):
            position = self.request.GET.get('position')
            queryset = queryset.filter(
                position__role__name__iexact=position
            ).distinct()

        if self.request.GET.get('project'):
            project = self.request.GET.get('project')
            queryset = queryset.filter(
                position__project__name__iexact=project
            ).distinct()

        if self.request.GET.get('status'):
            status = self.request.GET.get('status')
            if status:
                term = ''
                if status == 'new applications':
                    term = 'n'
                elif status == 'accepted':
                    term = 'a'
                elif status == 'rejected':
                    term = 'r'
                queryset = queryset.filter(
                    status=term
                ).distinct()

        return queryset


class ApplicationsUpdateView(LoginRequiredMixin, generic.View):
    """View to update Application."""
    model = models.Application
    login_url = reverse_lazy('accounts:sign-in')
    email_subject_template = (
        'projects/application_status_change_email_subject.txt')
    email_body_template = 'projects/application_status_change_email.txt'
    notification_subject_template = (
        'projects/application_status_change_notification_subject.txt')
    notification_body_template = (
        'projects/application_status_change_notification.txt')

    def get_success_url(self):
        success_url = reverse_lazy('projects:applications')
        url_kwargs = {}
        if self.request.GET.get('status'):
            url_kwargs['status'] = self.request.GET.get('status')
        if self.request.GET.get('project'):
            url_kwargs['project'] = self.request.GET.get('project')
        if self.request.GET.get('position'):
            url_kwargs['position'] = self.request.GET.get('position')
        return success_url + utils.make_url(**url_kwargs)

    def get_email_context(self, application, status):
        """Build the template context used for the email."""
        return {'application': application, 'status': status}

    def send_email(self, application, status):
        """Send email."""
        context = self.get_email_context(application, status)
        subject = render_to_string(self.email_subject_template, context)
        # Force subject to a single line to avoid header-injection issues.
        subject = ''.join(subject.splitlines())
        message = render_to_string(self.email_body_template, context)

        email = EmailMessage(
            subject=subject,
            body=message,
            to=(application.applicant.email,)
        )
        email.send()

    def get_object(self, pk):
        try:
            obj = self.model.objects.get(
                id=pk,
                position__project__owner=self.request.user
            )
        except self.model.DoesNotExist():
            raise Http404
        else:
            return obj

    def send_push_notification(self, application, status):
        """Send push notification regarding the application status update."""
        context = self.get_email_context(application, status)
        subject = render_to_string(self.notification_subject_template, context)
        # Force subject to a single line to avoid header-injection issues.
        subject = ''.join(subject.splitlines())
        message = render_to_string(self.notification_body_template, context)

        push = Pusher(
            app_id=settings.PUSHER_APP_ID,
            key=settings.PUSHER_KEY,
            secret=settings.PUSHER_SECRET,
            host=settings.PUSHER_HOST,
        )

        push.trigger(
            'team-builder-'+str(application.applicant.id),
            'new_notification',
            {'title': subject, 'message': message}
        )

    def post(self, request, *args, **kwargs):
        status = self.kwargs.get('status')
        pk = self.request.POST.get('id')
        application = self.get_object(pk=pk)

        if status == 'accept':
            # Update status of the application
            application.status = 'a'
            application.save()

            # Update position (add a user to the position)
            position = application.position
            position.user = application.applicant
            position.save()

            # Set status rejected for the rest of not yet rejected applications
            # for the same position.
            applications = models.Application.objects.filter(
                ~Q(id=pk),
                ~Q(status='r'),
                position=position,
            )

            for app in applications:
                app.status = 'r'
                app.save()

                # Send email to all rejected applicants
                self.send_email(application=app, status='reject')

                # Send push notification to the applicant
                if settings.USE_PUSHER:
                    self.send_push_notification(
                        application=app,
                        status='reject'
                    )

        elif status == 'reject':
            # Update status of the application
            application.status = 'r'
            application.save()

            # If this application was before accepted, i.e. if the applicant
            # was set as a position user, set position user to NULL
            position = application.position
            if position.user and position.user == application.applicant:
                position.user = None
                position.save()

        # Check whether the project is still active (has unfilled positions)
        # and mark appropriately.
        project = application.position.project
        unfilled_positions = 0
        for pos in project.positions.all():
            if not pos.user:
                unfilled_positions += 1

        if unfilled_positions and not project.active:
            project.active = True
            project.save()
        elif not unfilled_positions and project.active:
            project.active = False
            project.save()

        # Send email to the applicant
        self.send_email(application=application, status=status)

        # Send push notification to the applicant
        if settings.USE_PUSHER:
            self.send_push_notification(application=application, status=status)

        # Flash message
        flash_message = (application.applicant.userprofile.full_name +
                         ' has been ' + status + 'ed for a ' +
                         application.position.role.name +
                         ' position in the "' +
                         application.position.project.name + '" project.')

        messages.success(request, flash_message)

        return HttpResponseRedirect(self.get_success_url())
