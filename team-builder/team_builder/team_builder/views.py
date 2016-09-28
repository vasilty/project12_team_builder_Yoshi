from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView


class HomeView(RedirectView):
    """Home View."""
    url = reverse_lazy("projects:home")
