from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^sign-in/$', views.SignInView.as_view(), name='sign-in'),
    url(r'^sign-out/$', views.SignOutView.as_view(), name='sign-out'),
    url(r'^sign-up/$', views.SignUpView.as_view(), name='sign-up'),
    url(r'^registration-complete/$', views.RegistrationCompleteView.as_view(),
        name='registration-complete'),
    url(r'^activate/(?P<activation_key>[-:\w]+)/$',
        views.AccountActivateView.as_view(),
        name='registration-activate'),
    url(r'^activation-complete/$',
        views.AccountActivationCompleteView.as_view(),
        name='registration-activation-complete'),
]
