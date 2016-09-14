import bleach
from django import template
from django.conf import settings
import markdown2

from projects import models

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
    attrs = {
        '*': ['class'],
        'a': ['href', 'rel'],
        'img': ['alt', 'src'],
    }
    return bleach.clean(markdown2.markdown(content), attributes=attrs)


@register.inclusion_tag('projects/awesomplete_list.html')
def awesomplete_list():
    """Creates a list of options for awesomplete input."""
    skills = models.Skill.objects.all().values_list('name', flat=True)
    roles = models.Role.objects.all().values_list('name', flat=True)
    return {'skills': skills, 'roles': roles}


@register.simple_tag
def make_url(**kwargs):
    """Makes GET query to search by whatever kwargs are passed."""
    alls = ['all needs', 'all applications', 'all projects']
    url = ''
    for key, value in kwargs.items():
        if value and value not in alls:
            value = value.lower()
            if not url:
                url += '?'
            else:
                url += '&'
            url += key + '=' + value
    return url


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
