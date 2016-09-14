import json

from django.contrib import messages
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse_lazy
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.views import generic

from braces.views import LoginRequiredMixin


from . import forms
from . import models


def set_from_list_of_values(values_list):
    """Returns a set of lower cased values from a list."""
    return set(map(lambda v: v.lower(), values_list))


class IndexListView(generic.ListView):
    def get_project_needs(self, queryset):
        """Returns a list of unique project needs for a provided queryset."""
        positions = models.Position.objects.filter(
            project__in=queryset
        ).values_list('role__name', flat=True)
        # Lower position names and get a set of unique names.
        positions = set_from_list_of_values(positions)
        # Sort positions alphabetically.
        positions = sorted(positions)
        positions.insert(0, 'all needs')
        return positions


class IndexView(IndexListView):
    """Index view."""
    template_name = 'projects/index.html'
    context_object_name = 'projects'
    model = models.Project
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data()

        term = self.request.GET.get('q')
        if term:
            queryset = self.model.objects.filter(
                Q(name__icontains=term) |
                Q(description__icontains=term)
            )
        else:
            queryset = self.model.objects.all()
        context['needs'] = self.get_project_needs(queryset=queryset)
        if not self.request.GET.get('position'):
            context['filtered_position'] = "All Needs"
        else:
            context['filtered_position'] = self.request.GET.get('position')
        if not self.request.GET.get('q'):
            context['search_term'] = ''
        else:
            context['search_term'] = self.request.GET.get('q')
        return context

    def get_queryset(self):
        queryset = self.model.objects.all().prefetch_related(
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
                positions__role__name__icontains=position
            ).distinct()
        return queryset


class FitMeView(LoginRequiredMixin, IndexListView):
    """View to list projects that have positions fitting a user."""
    template_name = 'projects/index.html'
    context_object_name = 'projects'
    model = models.Project
    login_url = reverse_lazy('accounts:sign-in')
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self.fit_me_projects = self.get_fit_me(request,
                                               self.model.objects.all())
        return super(FitMeView, self).dispatch(request, *args, **kwargs)

    def get_fit_me(self, request, queryset):
        """Get projects that have positions fitting a User."""
        user = request.user
        user_skills = user.userprofile.skills.all().values_list('name',
                                                                flat=True)
        user_skills = set_from_list_of_values(user_skills)
        positions = models.Position.objects.all().prefetch_related(
            'related_skills')
        positions_need_me = []
        for position in positions:
            position_skills = [skill.name for skill in
                               position.related_skills.all()]
            position_skills = set_from_list_of_values(position_skills)
            missing_skills = [skill for skill in position_skills if skill not
                              in user_skills]
            if not missing_skills:
                positions_need_me.append(position)

        return queryset.filter(
            positions__in=positions_need_me
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super(FitMeView, self).get_context_data()
        # queryset = self.get_fit_me(queryset=self.model.objects.all())
        queryset = self.fit_me_projects
        context['needs'] = self.get_project_needs(queryset=queryset)
        if not self.request.GET.get('position'):
            context['filtered_position'] = "All Needs"
        else:
            context['filtered_position'] = self.request.GET.get('position')
        context['fitme'] = True
        return context

    def get_queryset(self):
        # queryset = self.model.objects.all().prefetch_related(
        #     'positions',
        #     'positions__role'
        # )

        # queryset = self.get_fit_me(queryset)
        queryset = self.fit_me_projects.prefetch_related(
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
    model = models.Project
    template_name = 'projects/project_edit.html'
    form_class = forms.ProjectForm
    login_url = reverse_lazy('accounts:sign-in')

    def get_success_url(self):
        return reverse_lazy('projects:project-detail',
                            kwargs={'pk': self.object.id})

    # def get_queryset(self):
    #     queryset = super(ProjectUpdateView, self).get_queryset()
    #     queryset = queryset.prefetch_related(
    #         'positions__related_skills'
    #     )
    #     return queryset
    
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

        # if form.is_valid() and position_formset.is_valid():
        if form.is_valid():
            print('Form is valid!')
            if position_formset.is_valid():
                print('Formset is valid!')
                return self.form_valid(form, position_formset)
            else:
                print(position_formset.errors)
                return self.form_invalid(form, position_formset)
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
    model = models.Project
    login_url = reverse_lazy('accounts:sign-in')

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
        context['past_positions'] = context['userprofile'].user.positions.all(
        ).select_related(
            'role',
            'project'
        )
        return context


class UserProfileUpdateView(LoginRequiredMixin, generic.UpdateView):
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
        context['past_positions'] = context['userprofile'].user.positions.all(
        ).select_related(
            'role',
            'project'
        )
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
            return self.form_valid(form, skill_formset)
        else:
            return self.form_invalid(form, skill_formset)

    def form_valid(self, form, skill_formset):
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

    def get_success_url(self):
        success_url = reverse_lazy('projects:project-detail',
                                   kwargs={'pk': self.kwargs.get('pk')})
        return success_url

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            application = form.save(commit=False)

            # If an application for this position from this user already exists
            if models.Application.objects.filter(
                applicant=request.user,
                position=application.position
            ).exists():
                # Warn the user
                messages.warning(request,
                                 'You have already applied for this position.')
            else:
                # If this is a new application, save it to the database.
                application.applicant = request.user
                application.save()
                messages.success(request,
                                 ('You have successfully applied for ' +
                                  application.position.role.name + ' position.')
                                 )
                title = ('Application for ' + application.position.role.name +
                         ' position in project ' +
                         application.position.project.name)
                message = (application.applicant.userprofile.full_name +
                           ' has applied for the ' +
                           application.position.role.name +
                           ' position in project ' +
                           application.position.project.name)
                email = EmailMessage(
                    title,
                    message,
                    to=(application.position.project.owner.email,)
                )
                # email.send()
        else:
            messages.error(request,
                           'An error occurred, while sending your application.')
        return HttpResponseRedirect(self.get_success_url())


class ApplicationsListView(LoginRequiredMixin, IndexListView):
    """Applications view."""
    template_name = 'projects/applications.html'
    model = models.Application
    context_object_name = 'applications'

    def get_context_data(self, **kwargs):
        context = super(ApplicationsListView, self).get_context_data()

        projects = models.Project.objects.filter(
            owner=self.request.user
        ).values_list('name', flat=True)
        # Lower position names and get a set of unique names.
        projects = set_from_list_of_values(projects)
        # Sort positions alphabetically.
        projects = sorted(projects)
        projects.insert(0, 'all projects')
        context['projects'] = projects

        project = self.request.GET.get('project')
        if project:
            queryset = models.Project.objects.filter(
                owner=self.request.user,
                name__iexact=project,
            )
        else:
            queryset = models.Project.objects.filter(owner=self.request.user)
        context['needs'] = self.get_project_needs(queryset=queryset)

        context['statuses'] = [
            'all applications',
            'new applications',
            'accepted',
            'rejected',
        ]

        if not self.request.GET.get('position'):
            context['filtered_position'] = "all needs"
        else:
            context['filtered_position'] = self.request.GET.get('position')
        if not self.request.GET.get('project'):
            context['filtered_project'] = 'all projects'
        else:
            context['filtered_project'] = self.request.GET.get('project')
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
    success_url = reverse_lazy('projects:applications')

    def post(self, request, *args, **kwargs):
        status = self.kwargs.get('status')
        pk = self.request.POST.get('id')
        application = models.Application.objects.get(id=pk)
        if status == 'accept':
            # Update status of the application
            application.status = 'a'
            application.save()

            # Update position (add a user to the position)
            position = application.position
            position.user = application.applicant
            position.save()

            # Set status rejected for the rest of applications for the same
            # position.
            applications = models.Application.objects.filter(
                ~Q(id=pk),
                position=position,
            )
            for app in applications:
                app.status = 'r'
                app.save()

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

        # email = EmailMessage(
        #     title,
        #     message,
        #     to=(application.position.project.owner.email,)
        # )
        # email.send()

        return HttpResponseRedirect(self.success_url)
