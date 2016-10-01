import bleach
from django import template
from django.conf import settings

from projects import models
from projects import utils

register = template.Library()

bleach.ALLOWED_TAGS.extend(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
                            'pre', 'img'])


@register.filter('qs_to_string')
def qs_to_string(qs):
    """Changes queryset to a string."""
    if not qs:
        return '--'
    else:
        value = ', '.join([str(obj) for obj in qs])
        return value


@register.filter('markdownify')
def markdownify(content):
    """Render Markdown formatted text."""
    return utils.markdownify(content)


@register.inclusion_tag('projects/awesomplete_list_roles.html')
def awesomplete_list_roles():
    """Creates a list of roles as options for awesomplete input."""
    roles = models.Role.objects.all().values_list('name', flat=True)
    return {'roles': roles}


@register.inclusion_tag('projects/awesomplete_list_skills.html')
def awesomplete_list_skills():
    """Creates a list of skills as options for awesomplete input."""
    skills = models.Skill.objects.all().values_list('name', flat=True)
    return {'skills': skills}


@register.simple_tag
def make_url(**kwargs):
    """Makes GET query to search by whatever kwargs are passed."""
    return utils.make_url(**kwargs)


@register.simple_tag
def avatarpath(userprofile):
    """Returns an avatar path for a user. If a user hasn't loaded the avatar,
    returns a path to a default image."""
    if not userprofile.avatar:
        return settings.MEDIA_URL + 'uploads/no_image.png'
    else:
        return userprofile.avatar.url


@register.simple_tag
def disablebutton(user, position):
    """Disables a button if a user has already applied for a position."""
    applications = position.applications.all()
    filtered_applications = [app for app in applications if
                             app.applicant == user]
    if filtered_applications:
        return 'disabled="disabled"'
