from binascii import a2b_base64
import os

from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify

from markdownx.widgets import MarkdownxWidget

from . import models


class SkillField(forms.Field):
    """Custom skill field."""

    def prepare_value(self, value):
        """Prepares a field value in a prepopulated form."""
        if not value:
            return None
        elif isinstance(value, str):
            return value
        else:
            return ', '.join([str(v) for v in value])

    def clean(self, value):
        """Splits the input string into a list of skill names using comma as a
        delimiter. A list of unique skill name, consisting of at least one
        non-space character is returned.
        """
        if not value:
            return None
        else:
            value = value.split(',')
            value = list(self._remove_duplicates(value))
            data = []
            for val in value:
                val = val.strip()
                if val:
                    data.append(val)
            return data

    @classmethod
    def _remove_duplicates(cls, seq):
        """Remove duplicates in a case insensitive, but case preserving
        manner."""
        duplicates = {}
        for item in seq:
            if item.lower() not in duplicates:
                duplicates[item.lower()] = True
                yield item


class ProjectForm(forms.ModelForm):
    """Project form."""
    class Meta:
        model = models.Project
        fields = ('name', 'description', 'timeline', 'requirements')
        widgets = {
            'name': forms.TextInput(
                attrs={'placeholder': 'Project Title',
                       'class': 'circle--input--h1'}),
            'description': MarkdownxWidget(
                attrs={'placeholder': 'Project description...'}),
            'timeline': forms.Textarea(
                attrs={'placeholder': 'Time estimate',
                       'class': 'circle--textarea--input'}),
        }


class PositionForm(forms.ModelForm):
    """Position form."""
    related_skills = SkillField(widget=forms.TextInput(
        attrs={'data-multiple': '',
               'data-list': "#skilllist",
               'placeholder': 'Related Skills (comma separated)'}))

    role_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={'placeholder': 'Position Title',
                   'data-list': "#rolelist",
                   'class': 'circle--input--h3 awesomplete'}),
    )

    def __init__(self, *args, **kwargs):
        super(PositionForm, self).__init__(*args, **kwargs)
        if self.initial:
            self.fields['role_name'].initial = self.instance.role.name

    class Meta:
        model = models.Position
        fields = ('description', 'related_skills', 'involvement',)
        widgets = {
            'description': MarkdownxWidget(
                attrs={'placeholder': 'Position description...'}),
            'involvement': forms.TextInput(
                attrs={'placeholder': 'Length of Involvement'}),
        }

    def save(self, commit=True):
        if 'related_skills' in self.cleaned_data:
            value = self.cleaned_data['related_skills']
            data = []
            if value:
                for val in value:
                    skill, created = models.Skill.objects.get_or_create(
                        name__iexact=val,
                        defaults={'name': val}
                    )
                    data.append(skill.id)
            self.cleaned_data['related_skills'] = data

        if 'role_name' in self.cleaned_data and (
                'role_name' in self.changed_data):
            value = self.cleaned_data['role_name']
            role, created = models.Role.objects.get_or_create(
                name__iexact=value,
                defaults={'name': value}
            )
            if self.instance.role:
                if self.instance.role.positions.count() == 1:
                    self.instance.role.delete()
            self.instance.role = role
        return super(PositionForm, self).save(commit)


class BaseProjectFormset(forms.BaseInlineFormSet):
    """Project Inline Formset."""
    def clean(self):
        """Adds validation that each input skills are unique."""
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid
            # on its own
            return

        forms_with_data = 0

        for form in self.forms:
            if form.cleaned_data:
                forms_with_data += 1

        # If all forms with data were marked as deleted, raise an error
        if len(self.deleted_forms) == forms_with_data:
            raise forms.ValidationError(
                'Project must have at least one position.')


ProjectFormSet = forms.inlineformset_factory(
    models.Project,
    models.Position,
    form=PositionForm,
    formset=BaseProjectFormset,
    extra=0,
    max_num=10,
    min_num=1,
    validate_min=True,
    validate_max=True,
)


class UserProfileForm(forms.ModelForm):
    """UserProfile form."""
    avatar_data = forms.CharField(
        max_length=1000000,
        widget=forms.HiddenInput(
            attrs={'class': 'hidden-image-data'}
        )
    )

    class Meta:
        model = models.UserProfile
        fields = ('full_name', 'biography', 'avatar')
        widgets = {
            'full_name': forms.TextInput(
                attrs={'placeholder': 'Full Name',
                       'class': 'circle--input--h1'}),
            'biography': MarkdownxWidget(
                attrs={'placeholder': 'Tell us about yourself...'}),
            'avatar': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.fields['avatar'].required = False
        self.fields['avatar_data'].required = False

    def save(self, commit=True):
        if commit:
            if 'avatar_data' in self.cleaned_data:
                avatar_data = self.cleaned_data['avatar_data']
                if avatar_data:
                    avatar_data = avatar_data.replace(
                        "data:image/png;base64,", "")
                    binary_data = a2b_base64(avatar_data)
                    name = slugify(self.cleaned_data['full_name'])
                    if self.instance.avatar:
                        path = settings.MEDIA_ROOT + self.instance.avatar.name
                        if os.path.isfile(path):
                            os.remove(path)
                    path = default_storage.save(
                        settings.MEDIA_ROOT+settings.MEDIA_URL+name+'.png',
                        ContentFile(binary_data)
                    )
                    path = path.replace(settings.MEDIA_ROOT, '')
                    self.instance.avatar = path

        return super(UserProfileForm, self).save(commit)


class UserProfileSkillForm(forms.ModelForm):
    """UserProfile Skill form."""
    skill_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={'placeholder': 'Skill',
                   'data-list': '#skilllist',
                   'class': 'awesomplete'}
        )
    )

    class Meta:
        model = models.UserProfileSkill
        fields = ('skill_name',)

    def __init__(self, *args, **kwargs):
        super(UserProfileSkillForm, self).__init__(*args, **kwargs)
        self.fields['skill_name'].required = False
        if self.initial:
            self.fields['skill_name'].initial = self.instance.skill.name

    def save(self, commit=True):
        """If skill name has been changed and if new skill name was input,
        get or create a corresponding Skill object and assign it to a skill
        attribute of UserProfileSkill instance. While changing skill attribute,
        check that the old Skill is in use by any other UserProfileSkill or
        Position. If not the case, delete the old Skill object.
        """
        if 'skill_name' in self.cleaned_data and (
                'skill_name' in self.changed_data):
            value = self.cleaned_data['skill_name']
            skill, created = models.Skill.objects.get_or_create(
                name__iexact=value,
                defaults={'name': value}
            )
            if self.instance.skill:
                if self.instance.skill.positions.count() == 0 and (
                        self.instance.skill.users.count() == 1):
                    self.instance.skill.delete()
            self.instance.skill = skill
        return super(UserProfileSkillForm, self).save(commit)


class BaseUserProfileSkillFormset(forms.BaseInlineFormSet):
    """"UserProfileSkill Inline Formset."""
    def clean(self):
        """Adds validation that each input skills are unique."""
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid
            # on its own
            return

        skills = []

        for form in self.forms:
            if 'skill_name' in form.cleaned_data:
                skill = form.cleaned_data['skill_name'].lower()
                if skill in skills:
                    raise forms.ValidationError('Skills must be unique.')
                else:
                    skills.append(skill)


UserProfileSkillFormSet = forms.inlineformset_factory(
    models.UserProfile,
    models.UserProfile.skills.through,
    form=UserProfileSkillForm,
    formset=BaseUserProfileSkillFormset,
    extra=1,
)


class ApplicationForm(forms.ModelForm):
    """Form to create an application."""
    class Meta:
        model = models.Application
        fields = ('position',)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        super(ApplicationForm, self).__init__(*args, **kwargs)

    def clean(self):
        position = self.cleaned_data['position']
        # If an application for this position from this user already exists
        if models.Application.objects.filter(
                applicant=self.request.user,
                position=position
        ).exists():
            # Raise an error
            raise forms.ValidationError(
                'You have already applied for this position.')
        return self.cleaned_data
