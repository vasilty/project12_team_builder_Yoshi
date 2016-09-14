from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^profiles/(?P<pk>\d+)/$', views.UserProfileDetailView.as_view(),
        name='user-profile-detail'),
    url(r'^profiles/edit/$', views.UserProfileUpdateView.as_view(),
        name='user-profile-update'),
    url(r'^projects/(?P<pk>\d+)/$', views.ProjectDetailView.as_view(),
        name='project-detail'),
    url(r'^projects/create/$', views.ProjectUpdateView.as_view(),
        name='project-create'),
    url(r'^projects/(?P<pk>\d+)/edit/$', views.ProjectUpdateView.as_view(),
        name='project-update'),
    url(r'^projects/(?P<pk>\d+)/delete/$', views.ProjectDeleteView.as_view(),
        name='project-delete'),
    url(r'^projects/search/$', views.IndexView.as_view(),
        name='search'),
    url(r'^projects/fitme/$', views.FitMeView.as_view(),
        name='project-fitme'),
    url(r'^projects/applications/$', views.ApplicationsListView.as_view(),
        name='applications'),
    url(r'^projects/(?P<pk>\d+)/applications/create/$',
        views.CreateApplicationView.as_view(), name='applications-create'),
    url(r'^projects/applications/(?P<status>accept|reject)$',
        views.ApplicationsUpdateView.as_view(), name='applications-update'),
    url(r'^$', views.IndexView.as_view(), name='home'),
]