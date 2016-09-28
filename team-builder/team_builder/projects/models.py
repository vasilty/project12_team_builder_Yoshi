import os
import re


from django.conf import settings
from django.db import models
from django.db.models.signals import (m2m_changed, post_save, post_delete,
                                      pre_delete, pre_save)


class Skill(models.Model):
    """Skill model class."""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Role(models.Model):
    """Role model class."""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    """Project model class."""
    name = models.CharField(max_length=255)
    description = models.TextField(default='')
    timeline = models.CharField(max_length=100)
    requirements = models.TextField()
    url = models.URLField()
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE,
                              related_name='projects')
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Position(models.Model):
    """Position model class."""
    role = models.ForeignKey(Role, related_name='positions',
                             on_delete=models.SET_NULL, null=True)
    description = models.TextField(default='')
    related_skills = models.ManyToManyField(Skill, related_name='positions')
    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                related_name='positions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.SET_NULL, blank=True,
                             null=True, related_name='positions')
    involvement = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.role.name


class UserProfile(models.Model):
    """User profile model class."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                related_name='userprofile')
    full_name = models.CharField(max_length=100, default='')
    biography = models.TextField(default='')
    avatar = models.ImageField(upload_to='uploads/',
                               default='')
    skills = models.ManyToManyField(Skill, through='UserProfileSkill',
                                    related_name='users')

    def __str__(self):
        if self.full_name:
            return self.full_name
        else:
            return super().__str__()


class UserProfileSkill(models.Model):
    """Link between UserProfile and Skill."""
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.SET_NULL, null=True)


class Application(models.Model):
    """Application model class."""
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL,
                                  on_delete=models.CASCADE,
                                  related_name='applications')
    position = models.ForeignKey(Position, on_delete=models.CASCADE,
                                 related_name='applications')
    status = models.CharField(
        max_length=1,
        default='n',
        choices=(
            ('n', 'new'),
            ('a', 'accepted'),
            ('r', 'rejected'),
        )
    )


def create_profile(sender, **kwargs):
    """Create UserProfile instance whenever User is created."""
    user = kwargs["instance"]
    if kwargs["created"]:
        user_profile = UserProfile(user=user)
        user_profile.save()

post_save.connect(create_profile, sender=settings.AUTH_USER_MODEL)


def cascade_delete_skill(sender, instance, **kwargs):
    """Delete Skill instances that are not connected to any UserProfile and
    Position."""
    if kwargs['action'] == 'post_remove':
        for pk in kwargs['pk_set']:
            skill = Skill.objects.get(pk=pk)
            if skill.users.count() == 0 and skill.positions.count() == 0:
                skill.delete()

m2m_changed.connect(cascade_delete_skill,
                    sender=Position.related_skills.through)


def cascade_delete_userprofileskill(sender, instance, **kwargs):
    """Delete Skill instances that are not connected to any UserProfile and
    Position.
    """
    skill = Skill.objects.get(id=instance.skill_id)
    if skill.users.count() == 0 and skill.positions.count() == 0:
        skill.delete()

post_delete.connect(cascade_delete_userprofileskill,
                    sender=UserProfileSkill)


def cascade_delete_position(sender, instance, **kwargs):
    """Cleans up when Position instance is deleted."""

    # Delete Role instances that are not connected to any Position.
    try:
        role = Role.objects.get(id=instance.role_id)
    except Role.objects.DoesNotExist:
        pass
    else:
        if role.positions.count() == 1:
            role.delete()

    # Delete Skill instances that are not connected to any UserProfile and
    # Position.
    skill_ids = instance.related_skills.values_list('id', flat=True)
    for skill_id in skill_ids:
        try:
            skill = Skill.objects.get(id=skill_id)
        except Skill.objects.DoesNotExist:
            pass
        else:
            if skill.users.count() == 0 and skill.positions.count() == 1:
                skill.delete()

    # Delete images from Markdown description field.
    pattern = r'!\[\]\((?P<file>[-\w/.]+)\)'
    files = re.findall(pattern, sender.objects.get(id=instance.id).description)
    for file in files:
        path = settings.BASE_DIR + file
        if os.path.isfile(path):
            os.remove(path)

pre_delete.connect(cascade_delete_position, sender=Position)


def cascade_delete_project(sender, instance, **kwargs):
    """Delete images from Markdown description field."""
    pattern = r'!\[\]\((?P<file>[-\w/.]+)\)'
    files = re.findall(pattern, sender.objects.get(id=instance.id).description)
    for file in files:
        path = settings.BASE_DIR + file
        if os.path.isfile(path):
            os.remove(path)

pre_delete.connect(cascade_delete_project, sender=Project)


def manage_markup_images(sender, instance, **kwargs):
    """Deletes unnecessary images from Markup fields."""
    pattern = r'!\[\]\((?P<file>[-\w/.]+)\)'
    old_files = []
    if isinstance(instance, UserProfile):
        if instance.id:
            old_files = re.findall(pattern,
                                   sender.objects.get(
                                       id=instance.id).biography)
        new_files = re.findall(pattern, instance.biography)
    else:
        if instance.id:
            old_files = re.findall(
                pattern,
                sender.objects.get(id=instance.id).description
            )
        new_files = re.findall(pattern, instance.description)
    files_to_delete = [file for file in old_files if file not in new_files]
    for file in files_to_delete:
        path = settings.BASE_DIR + file
        if os.path.isfile(path):
            os.remove(path)

pre_save.connect(manage_markup_images, sender=UserProfile)
pre_save.connect(manage_markup_images, sender=Project)
pre_save.connect(manage_markup_images, sender=Position)
