from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase

from . import forms


class UserModelTests(TestCase):
    def test_user_creation(self):
        user = get_user_model()
        user.objects.create_user(email="user@example.com")
        self.assertEqual(user.objects.count(), 1)
        new_user = user.objects.get(id=1)
        self.assertEqual(new_user.email, "user@example.com")
        self.assertTrue(new_user.is_active)
        self.assertFalse(new_user.is_staff)
        self.assertFalse(new_user.is_superuser)

    def test_user_creation_without_email(self):
        user = get_user_model()
        with self.assertRaises(TypeError):
            user.objects.create_user()

    def test_superuser_creation(self):
        user = get_user_model()
        user.objects.create_superuser(email="user@example.com",
                                      password="password")
        self.assertEqual(user.objects.count(), 1)
        new_user = user.objects.get(id=1)
        self.assertEqual(new_user.email, "user@example.com")
        self.assertTrue(new_user.is_active)
        self.assertTrue(new_user.is_staff)
        self.assertTrue(new_user.is_superuser)

    def test_superuser_creation_without_password(self):
        user = get_user_model()
        with self.assertRaises(TypeError):
            user.objects.create_superuser(email="user@example.com")


class FormTests(TestCase):
    def setUp(self):
        self.user1 = get_user_model().objects.create_user(
            email="user@example.com",
            password='password'
        )

    def test_custom_authentication_form_success(self):
        form = forms.CustomAuthenticationForm(
            data={
                'email': 'user@example.com',
                'password': 'password'
            }
        )
        self.assertTrue(form.is_valid())

    def test_custom_authentication_form_wrong_email(self):
        form = forms.CustomAuthenticationForm(
            data={
                'email': 'wrong-email@example.com',
                'password': 'password'
            }
        )
        self.assertFalse(form.is_valid())

    def test_custom_authentication_form_wrong_password(self):
        form = forms.CustomAuthenticationForm(
            data={
                'email': 'user@example.com',
                'password': 'wrong-password'
            }
        )
        self.assertFalse(form.is_valid())

    def test_custom_authentication_form_no_email(self):
        form = forms.CustomAuthenticationForm(
            data={
                'email': '',
                'password': 'password'
            }
        )
        self.assertFalse(form.is_valid())

    def test_custom_authentication_form_no_password(self):
        form = forms.CustomAuthenticationForm(
            data={
                'email': 'user@example.com',
                'password': ''
            }
        )
        self.assertFalse(form.is_valid())


class SignInViewTests(TestCase):
    def setUp(self):
        FormTests.setUp(self)

    def test_sign_in_view_get(self):
        url = reverse('accounts:sign-in')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/signin.html')

    def test_sign_in_view_post_success(self):
        url = reverse('accounts:sign-in')
        post_data = {
            'email': 'user@example.com',
            'password': 'password'
        }
        response = self.client.post(
            url,
            post_data,
            follow=True
        )
        self.assertRedirects(response, reverse('projects:home'))
        self.assertEqual(
            int(self.client.session['_auth_user_id']),
            self.user1.pk
        )

    def test_sign_in_view_post_wrong_email(self):
        url = reverse('accounts:sign-in')
        post_data = {
            'email': 'wronguser@example.com',
            'password': 'password'
        }
        response = self.client.post(
            url,
            post_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response=response,
            form='form',
            field=None,
            errors="Please enter a correct email and password. Note that both "
                   "fields may be case-sensitive.",
        )
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_sign_in_view_post_wrong_password(self):
        url = reverse('accounts:sign-in')
        post_data = {
            'email': 'user@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(
            url,
            post_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response=response,
            form='form',
            field=None,
            errors="Please enter a correct email and password. Note that both "
                   "fields may be case-sensitive.",
        )
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_sign_in_view_post_no_email(self):
        url = reverse('accounts:sign-in')
        post_data = {
            'email': '',
            'password': 'password'
        }
        response = self.client.post(
            url,
            post_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response=response,
            form='form',
            field='email',
            errors="This field is required.",
        )
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_sign_in_view_post_no_password(self):
        url = reverse('accounts:sign-in')
        post_data = {
            'email': 'user@example.com',
            'password': ''
        }
        response = self.client.post(
            url,
            post_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response=response,
            form='form',
            field='password',
            errors="This field is required.",
        )
        self.assertNotIn('_auth_user_id', self.client.session)


class SignOutViewTests(TestCase):
    def setUp(self):
        FormTests.setUp(self)

    def test_sign_out_view_success(self):
        self.client.force_login(self.user1)
        url = reverse('accounts:sign-out')
        response = self.client.get(url)
        self.assertRedirects(response, reverse('projects:home'))
        self.assertNotIn('_auth_user_id', self.client.session)


class SignUpViewTests(TestCase):
    def test_sign_up_view_get(self):
        url = reverse('accounts:sign-up')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/signup.html')

    def test_sign_up_view_post_success(self):
        url = reverse('accounts:sign-up')
        post_data = {
            'full_name': 'User Name',
            'email': 'user@example.com',
            'password1': 'testpassword',
            'password2': 'testpassword'
        }
        response = self.client.post(url, post_data, follow=True)
        user = get_user_model().objects.get(email='user@example.com')
        self.assertEqual(user.userprofile.full_name, 'User Name')
        self.assertEqual(user.is_active, False)
