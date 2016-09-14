from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase

# from django_webtest import WebTest

from . import forms
from . import models


class ModelTests(TestCase):
    def setUp(self):
        # Create 2 users.
        self.user1 = get_user_model().objects.create_user(
            email='user1@example.com',
            password='password'
        )

        self.user2 = get_user_model().objects.create_user(
            email='user2@example.com',
            password='password'
        )

        # Create 2 projects.
        self.project1 = models.Project.objects.create(
            name='Project1',
            timeline='1 day',
            requirements='Requirements1',
            owner=self.user1,
        )

        self.project2 = models.Project.objects.create(
            name='Project2',
            timeline='2 days',
            requirements='Requirements2',
            owner=self.user1,
        )

        # Create 5 skills.
        self.skill1 = models.Skill.objects.create(
            name='Skill1'
        )

        self.skill2 = models.Skill.objects.create(
            name='Skill2'
        )

        self.skill3 = models.Skill.objects.create(
            name='Skill3'
        )

        self.skill4 = models.Skill.objects.create(
            name='Skill4'
        )

        self.skill5 = models.Skill.objects.create(
            name='Skill5'
        )

        # Create 3 roles.
        self.role1 = models.Role.objects.create(
            name='Role1'
        )

        self.role2 = models.Role.objects.create(
            name='Role2'
        )

        self.role3 = models.Role.objects.create(
            name='Role3'
        )

        # Create 1 position linked with project1 and with 3 skills: skill1,
        # skill2 and skill4.
        self.position1 = models.Position.objects.create(
            role=self.role1,
            project=self.project1,
        )
        self.position1.related_skills = [self.skill1, self.skill2, self.skill4]
        self.position1.save()


        # Link UserProfile 1 with 3 skills: skill1, skill2 and skill3.
        self.userprofile1 = self.user1.userprofile
        self.userprofile1.full_name = 'Full Name1'
        self.userprofile1.save()
        models.UserProfileSkill.objects.create(
            user_profile=self.userprofile1,
            skill=self.skill1
        )
        models.UserProfileSkill.objects.create(
            user_profile=self.userprofile1,
            skill=self.skill2
        )
        models.UserProfileSkill.objects.create(
            user_profile=self.userprofile1,
            skill=self.skill3
        )

    def test_userprofile_creation_after_user_creation(self):
        self.assertEqual(models.UserProfile.objects.count(),
                         get_user_model().objects.count())

    def test_userprofileskill_creation(self):
        self.assertEqual(self.userprofile1.skills.count(), 3)

    def test_skill_deletion_after_it_was_removed_from_position(self):
        self.position1.related_skills.remove(self.skill4)
        with self.assertRaises(models.Skill.DoesNotExist):
            models.Skill.objects.get(id=4)

    def test_skill_deletion_after_userprofileskill_deletion(self):
        models.UserProfileSkill.objects.get(
            user_profile=self.userprofile1,
            skill=self.skill3
        ).delete()
        with self.assertRaises(models.Skill.DoesNotExist):
            models.Skill.objects.get(id=3)

    def test_skill_deletion_after_position_deletion(self):
        self.position1.delete()
        with self.assertRaises(models.Skill.DoesNotExist):
            models.Skill.objects.get(id=4)
        self.assertTrue(models.Skill.objects.filter(id=1).exists())
        self.assertTrue(models.Skill.objects.filter(id=2).exists())

    def test_role_deletion_after_position_deletion(self):
        self.position1.delete()
        with self.assertRaises(models.Role.DoesNotExist):
            models.Role.objects.get(id=1)

class FormSaveTests(TestCase):
    def setUp(self):
        ModelTests.setUp(self)

    def test_position_form_save_create_skill(self):
        form = forms.PositionForm(
            instance=self.position1,
            data={
                'related_skills': 'Skill1, NewSkill',
                'role_name': self.role1.name,
                'description': 'Description',
                'involvement': ''
            }
        )
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(models.Skill.objects.filter(name='NewSkill').exists())

    def test_position_form_save_create_role(self):
        form = forms.PositionForm(
            instance=self.position1,
            data={
                'related_skills': 'Skill1, Skill2',
                'role_name': 'NewRole',
                'description': 'Description',
                'involvement': ''
            }
        )
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(models.Role.objects.filter(name='NewRole').exists())

    def test_position_form_save_delete_unused_role(self):
        form = forms.PositionForm(
            instance=self.position1,
            data={
                'related_skills': 'Skill1, Skill2',
                'role_name': 'NewRole',
                'description': 'Description',
                'involvement': ''
            }
        )
        self.assertTrue(form.is_valid())
        form.save()
        with self.assertRaises(models.Role.DoesNotExist):
            models.Role.objects.get(id=1)

    def test_userprofileskill_form_save_create_skill(self):
        form = forms.UserProfileSkillForm(
            data={
                'skill_name': 'NewSkill'
            }
        )
        self.assertTrue(form.is_valid())
        userprofileskill = form.save(commit=False)
        userprofileskill.user_profile = self.userprofile1
        userprofileskill.save()
        self.assertTrue(models.Skill.objects.filter(name='NewSkill').exists())

    def test_userprofileskill_form_save_delete_skill(self):
        userprofileskill = models.UserProfileSkill.objects.get(
            user_profile=self.userprofile1,
            skill=self.skill3
        )
        form = forms.UserProfileSkillForm(
            instance=userprofileskill,
            data={
                'skill_name': 'NewSkill'
            }
        )
        self.assertTrue(form.is_valid())
        form.save()
        with self.assertRaises(models.Skill.DoesNotExist):
            models.Skill.objects.get(id=3)

class UserProfileUpdateViewTests(TestCase):
    def setUp(self):
        ModelTests.setUp(self)

    def test_userprofile_update_view_get(self):
        self.client.force_login(self.user1)
        response = self.client.get(
            reverse(
                'projects:user-profile-update',
                kwargs={'pk': self.user1.userprofile.id}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/profile_edit.html')

    def test_userprofile_update_view_post(self):
        self.client.force_login(self.user1)

        post_data = {
            'full_name': 'New Full Name1',
            'biography': 'New biography1',
            'userprofileskill_set-TOTAL_FORMS': '3',
            'userprofileskill_set-INITIAL_FORMS': '3',
            'form-MIN_NUM_FORMS': '',
            'form-MAX_NUM_FORMS': '',
            'userprofileskill_set-0-id': '1',
            'userprofileskill_set-0-skill_name': self.skill1.name,
            'userprofileskill_set-1-id': '2',
            'userprofileskill_set-1-skill_name': self.skill2.name,
            'userprofileskill_set-2-id': '3',
            'userprofileskill_set-2-skill_name': self.skill5.name,
        }

        response = self.client.post(
            reverse(
                'projects:user-profile-update',
                kwargs={'pk': self.user1.userprofile.id}
            ),
            post_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'projects:user-profile-detail',
                kwargs={'pk': self.user1.userprofile.id}
            )
        )
        self.assertEqual(response.context['userprofile'].full_name,
                         'New Full Name1')
        self.assertEqual(response.context['userprofile'].biography,
                         'New biography1')
        self.assertIn(self.skill1,
                      response.context['userprofile'].skills.all())
        self.assertIn(self.skill2,
                      response.context['userprofile'].skills.all())
        self.assertIn(self.skill5,
                      response.context['userprofile'].skills.all())
        self.assertNotIn(self.skill3,
                      response.context['userprofile'].skills.all())


    def test_userprofile_update_not_yours_profile_view_post(self):
        self.client.force_login(self.user2)

        post_data = {
            'full_name': 'New Full Name1',
            'biography': 'New biography1',
            'userprofileskill_set-TOTAL_FORMS': '3',
            'userprofileskill_set-INITIAL_FORMS': '3',
            'form-MIN_NUM_FORMS': '',
            'form-MAX_NUM_FORMS': '',
            'userprofileskill_set-0-id': '1',
            'userprofileskill_set-0-skill_name': self.skill1.name,
            'userprofileskill_set-1-id': '2',
            'userprofileskill_set-1-skill_name': self.skill2.name,
            'userprofileskill_set-2-id': '3',
            'userprofileskill_set-2-skill_name': self.skill5.name,
        }

        response = self.client.post(
            reverse(
                'projects:user-profile-update',
                kwargs={'pk': self.user1.userprofile.id}
            ),
            post_data,
            follow=True,
        )
        self.assertEqual(response.status_code, 404)

    def test_userprofile_update_view_post_repetitive_skills(self):
        self.client.force_login(self.user1)

        post_data = {
            'full_name': 'New Full Name1',
            'biography': 'New biography1',
            'userprofileskill_set-TOTAL_FORMS': '3',
            'userprofileskill_set-INITIAL_FORMS': '3',
            'form-MIN_NUM_FORMS': '',
            'form-MAX_NUM_FORMS': '',
            'userprofileskill_set-0-id': '1',
            'userprofileskill_set-0-skill_name': self.skill1.name,
            'userprofileskill_set-1-id': '2',
            'userprofileskill_set-1-skill_name': self.skill2.name,
            'userprofileskill_set-2-id': '3',
            'userprofileskill_set-2-skill_name': self.skill2.name,
        }

        response = self.client.post(
            reverse(
                'projects:user-profile-update',
                kwargs={'pk': self.user1.userprofile.id}
            ),
            post_data,
        )
        self.assertFormsetError(
            response,
            formset='skill_formset',
            form_index=None,
            field=None,
            errors='Skills must be unique.',
        )

    def test_userprofile_update_view_post_no_full_name(self):
        self.client.force_login(self.user1)

        post_data = {
            'full_name': '',
            'biography': 'New biography1',
            'userprofileskill_set-TOTAL_FORMS': '3',
            'userprofileskill_set-INITIAL_FORMS': '3',
            'form-MIN_NUM_FORMS': '',
            'form-MAX_NUM_FORMS': '',
            'userprofileskill_set-0-id': '1',
            'userprofileskill_set-0-skill_name': self.skill1.name,
            'userprofileskill_set-1-id': '2',
            'userprofileskill_set-1-skill_name': self.skill2.name,
            'userprofileskill_set-2-id': '3',
            'userprofileskill_set-2-skill_name': self.skill2.name,
        }

        response = self.client.post(
            reverse(
                'projects:user-profile-update',
                kwargs={'pk': self.user1.userprofile.id}
            ),
            post_data,
        )
        self.assertFormError(
            response,
            form='form',
            field='full_name',
            errors='This field is required.',
        )

    def test_userprofile_update_view_post_no_biography(self):
        self.client.force_login(self.user1)

        post_data = {
            'full_name': 'New Full Name1',
            'biography': '',
            'userprofileskill_set-TOTAL_FORMS': '3',
            'userprofileskill_set-INITIAL_FORMS': '3',
            'form-MIN_NUM_FORMS': '',
            'form-MAX_NUM_FORMS': '',
            'userprofileskill_set-0-id': '1',
            'userprofileskill_set-0-skill_name': self.skill1.name,
            'userprofileskill_set-1-id': '2',
            'userprofileskill_set-1-skill_name': self.skill2.name,
            'userprofileskill_set-2-id': '3',
            'userprofileskill_set-2-skill_name': self.skill2.name,
        }

        response = self.client.post(
            reverse(
                'projects:user-profile-update',
                kwargs={'pk': self.user1.userprofile.id}
            ),
            post_data,
        )
        self.assertFormError(
            response,
            form='form',
            field='biography',
            errors='This field is required.',
        )

    def test_userprofile_update_view_post_unauthenticated(self):
        post_data = {
            'full_name': 'New Full Name1',
            'biography': 'New biography1',
            'userprofileskill_set-TOTAL_FORMS': '3',
            'userprofileskill_set-INITIAL_FORMS': '3',
            'form-MIN_NUM_FORMS': '',
            'form-MAX_NUM_FORMS': '',
            'userprofileskill_set-0-id': '1',
            'userprofileskill_set-0-skill_name': self.skill1.name,
            'userprofileskill_set-1-id': '2',
            'userprofileskill_set-1-skill_name': self.skill2.name,
            'userprofileskill_set-2-id': '3',
            'userprofileskill_set-2-skill_name': self.skill2.name,
        }

        response = self.client.post(
            reverse(
                'projects:user-profile-update',
                kwargs={'pk': self.user1.userprofile.id}
            ),
            post_data,
        )

        expected_url = reverse('accounts:sign-in') + '?next=' + \
                       reverse('projects:user-profile-update',
                               kwargs={'pk': self.user1.userprofile.id})
        self.assertRedirects(response, expected_url)

    def test_userprofile_update_view_get_unauthenticated(self):
        response = self.client.get(
            reverse(
                'projects:user-profile-update',
                kwargs={'pk': self.user1.userprofile.id}
            ),
        )

        expected_url = reverse('accounts:sign-in') + '?next=' + \
                       reverse('projects:user-profile-update',
                               kwargs={'pk': self.user1.userprofile.id})
        self.assertRedirects(response, expected_url)
