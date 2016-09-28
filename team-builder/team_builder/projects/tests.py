from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase


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
            description='Description1',
            owner=self.user1,
        )

        self.project2 = models.Project.objects.create(
            name='Project2',
            timeline='2 days',
            requirements='Requirements2',
            description='Description2',
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
            reverse('projects:user-profile-update')
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
            reverse('projects:user-profile-update'),
            post_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'projects:user-profile-detail',
                kwargs={'pk': self.user1.id}
            )
        )

        userprofile = models.UserProfile.objects.get(
            id=self.user1.userprofile.id)
        self.assertEqual(userprofile.full_name, 'New Full Name1')
        self.assertEqual(userprofile.biography, 'New biography1')
        self.assertIn(self.skill1, userprofile.skills.all())
        self.assertIn(self.skill2, userprofile.skills.all())
        self.assertIn(self.skill5, userprofile.skills.all())
        self.assertNotIn(self.skill3, userprofile.skills.all())

    def test_userprofile_update_view_post_change_skill_to_blank(self):
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
            'userprofileskill_set-2-skill_name': '',
        }

        response = self.client.post(
            reverse('projects:user-profile-update'),
            post_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'projects:user-profile-detail',
                kwargs={'pk': self.user1.id}
            )
        )

        userprofile = models.UserProfile.objects.get(
            id=self.user1.userprofile.id)
        self.assertEqual(userprofile.full_name, 'New Full Name1')
        self.assertEqual(userprofile.biography, 'New biography1')
        self.assertEqual(2, userprofile.skills.all().count())
        self.assertIn(self.skill1, userprofile.skills.all())
        self.assertIn(self.skill2, userprofile.skills.all())
        self.assertNotIn(self.skill3, userprofile.skills.all())

    def test_userprofile_update_view_post_remove_skill(self):
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
            'userprofileskill_set-2-skill_name': self.skill3.name,
            'userprofileskill_set-2-DELETE': 'on',
        }

        response = self.client.post(
            reverse('projects:user-profile-update'),
            post_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'projects:user-profile-detail',
                kwargs={'pk': self.user1.id}
            )
        )

        userprofile = models.UserProfile.objects.get(
            id=self.user1.userprofile.id)
        self.assertEqual(userprofile.full_name, 'New Full Name1')
        self.assertEqual(userprofile.biography, 'New biography1')
        self.assertEqual(2, userprofile.skills.all().count())
        self.assertIn(self.skill1, userprofile.skills.all())
        self.assertIn(self.skill2, userprofile.skills.all())
        self.assertNotIn(self.skill3, userprofile.skills.all())

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
            reverse('projects:user-profile-update'),
            post_data,
        )
        self.assertFormsetError(
            response,
            formset='skill_formset',
            form_index=None,
            field=None,
            errors='Skills must be unique.',
        )

    def test_userprofile_update_view_new_skill(self):
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
            'userprofileskill_set-2-skill_name': 'New Skill',
        }

        response = self.client.post(
            reverse('projects:user-profile-update'),
            post_data,
        )
        self.assertRedirects(
            response,
            reverse(
                'projects:user-profile-detail',
                kwargs={'pk': self.user1.id}
            )
        )

        userprofile = models.UserProfile.objects.get(
            id=self.user1.userprofile.id)
        new_skill = models.Skill.objects.get(name='New Skill')
        self.assertIn(self.skill1, userprofile.skills.all())
        self.assertIn(self.skill2, userprofile.skills.all())
        self.assertIn(new_skill, userprofile.skills.all())
        self.assertNotIn(self.skill3, userprofile.skills.all())

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
            'userprofileskill_set-2-skill_name': self.skill3.name,
        }

        response = self.client.post(
            reverse('projects:user-profile-update'),
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
            'userprofileskill_set-2-skill_name': self.skill3.name,
        }

        response = self.client.post(
            reverse('projects:user-profile-update'),
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
            'userprofileskill_set-0-id': str(self.skill1.id),
            'userprofileskill_set-0-skill_name': self.skill1.name,
            'userprofileskill_set-1-id': str(self.skill2.id),
            'userprofileskill_set-1-skill_name': self.skill2.name,
            'userprofileskill_set-2-id': str(self.skill3.id),
            'userprofileskill_set-2-skill_name': self.skill3.name,
        }

        response = self.client.post(
            reverse('projects:user-profile-update'),
            post_data,
        )

        expected_url = (reverse('accounts:sign-in') + '?next=' +
                        reverse('projects:user-profile-update'))
        self.assertRedirects(response, expected_url)

    def test_userprofile_update_view_get_unauthenticated(self):
        response = self.client.get(
            reverse('projects:user-profile-update'),
        )

        expected_url = (reverse('accounts:sign-in') + '?next=' +
                        reverse('projects:user-profile-update'))
        self.assertRedirects(response, expected_url)


class UserProfileDetailViewTests(TestCase):
    def setUp(self):
        ModelTests.setUp(self)

    def test_userprofile_detail_view_success(self):
        self.client.force_login(self.user1)
        response = self.client.get(
            reverse(
                'projects:user-profile-detail',
                kwargs={'pk': self.user1.id}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/profile.html')
        self.assertContains(response, self.user1.userprofile.full_name)

    def test_userprofile_detail_view_unauthenticated(self):
        url = reverse(
            'projects:user-profile-detail',
            kwargs={'pk': self.user1.id}
        )
        response = self.client.get(url)

        expected_url = (reverse('accounts:sign-in') + '?next=' + url)
        self.assertRedirects(response, expected_url)


class ProjectDetailViewTests(TestCase):
    def setUp(self):
        ModelTests.setUp(self)

    def test_project_detail_views_success(self):
        self.client.force_login(self.user1)
        response = self.client.get(
            reverse(
                'projects:project-detail',
                kwargs={'pk': self.project1.id}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/project.html')
        self.assertContains(response, self.project1.name)

    def test_project_detail_views_unauthenticated(self):
        url =reverse(
            'projects:project-detail',
            kwargs={'pk': self.project1.id}
        )
        response = self.client.get(url)
        expected_url = (reverse('accounts:sign-in') + '?next=' + url)
        self.assertRedirects(response, expected_url)


class ProjectUpdateViewTests(TestCase):
    def setUp(self):
        ModelTests.setUp(self)

    def test_project_update_view_get_success(self):
        self.client.force_login(self.user1)
        response = self.client.get(
            reverse(
                'projects:project-update',
                kwargs={'pk': self.project1.id}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/project_edit.html')
        self.assertContains(response, self.project1.name)

    def test_project_update_view_get_unauthenticated(self):
        url = reverse(
            'projects:project-update',
            kwargs={'pk': self.project1.id}
        )
        response = self.client.get(url)
        expected_url = (reverse('accounts:sign-in') + '?next=' + url)
        self.assertRedirects(response, expected_url)

    def test_project_update_view_post_success(self):
        self.client.force_login(self.user1)
        url = reverse(
            'projects:project-update',
            kwargs={'pk': self.project1.id}
        )

        post_data = {
            'name': 'New Project Name1',
            'description': 'New Project Description1',
            'timeline': 'New Project Timeline',
            'requirements': 'New Project Requirements',
            'positions-TOTAL_FORMS': '3',
            'positions-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '10',
            'positions-0-id': str(self.position1.id),
            'positions-0-role_name': self.role1.name,
            'positions-0-description': 'role1 description',
            'positions-1-id': '',
            'positions-1-role_name': self.role2.name,
            'positions-1-description': 'role2 description',
            'positions-2-id': '',
            'positions-2-role_name': self.role3.name,
            'positions-2-description': 'role3 description',
        }

        response = self.client.post(
            url,
            post_data,
            follow=True,
        )
        self.assertTemplateUsed(response, 'projects/project.html')
        self.assertRedirects(
            response,
            reverse(
                'projects:project-detail',
                kwargs={'pk': self.project1.id}
            )
        )
        project = models.Project.objects.get(id=1)

        self.assertEqual(models.Position.objects.count(), 3)
        self.assertEqual(project.name, 'New Project Name1')
        self.assertEqual(project.description, 'New Project Description1')
        self.assertEqual(project.timeline, 'New Project Timeline')
        self.assertEqual(project.requirements, 'New Project Requirements')
        self.assertIn(self.position1, project.positions.all())
        self.assertEqual(project.positions.all().count(), 3)

    def test_project_update_view_post_remove_position(self):
        self.client.force_login(self.user1)
        # Create a position linked with project1.
        self.position2 = models.Position.objects.create(
            role=self.role2,
            project=self.project1,
        )
        url = reverse(
            'projects:project-update',
            kwargs={'pk': self.project1.id}
        )

        post_data = {
            'name': 'New Project Name1',
            'description': 'New Project Description1',
            'timeline': 'New Project Timeline',
            'requirements': 'New Project Requirements',
            'positions-TOTAL_FORMS': '2',
            'positions-INITIAL_FORMS': '2',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '10',
            'positions-0-id': str(self.position1.id),
            'positions-0-role_name': self.role1.name,
            'positions-0-description': 'role1 description',
            'positions-0-DELETE': 'on',
            'positions-1-id': str(self.position2.id),
            'positions-1-role_name': self.role2.name,
            'positions-1-description': 'role2 description',
        }

        response = self.client.post(
            url,
            post_data,
            follow=True,
        )
        self.assertTemplateUsed(response, 'projects/project.html')
        self.assertRedirects(
            response,
            reverse(
                'projects:project-detail',
                kwargs={'pk': self.project1.id}
            )
        )
        project = models.Project.objects.get(id=1)

        self.assertEqual(project.positions.all().count(), 1)
        self.assertIn(self.position2, project.positions.all())
        self.assertNotIn(self.position1, project.positions.all())

    def test_project_update_view_post_remove_all_positions(self):
        self.client.force_login(self.user1)
        url = reverse(
            'projects:project-update',
            kwargs={'pk': self.project1.id}
        )

        post_data = {
            'name': 'New Project Name1',
            'description': 'New Project Description1',
            'timeline': 'New Project Timeline',
            'requirements': 'New Project Requirements',
            'positions-TOTAL_FORMS': '2',
            'positions-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '10',
            'positions-0-id': str(self.position1.id),
            'positions-0-role_name': self.role1.name,
            'positions-0-description': 'role1 description',
            'positions-0-DELETE': 'on',
            'positions-1-id': '',
            'positions-1-role_name': '',
            'positions-1-description': '',
            'positions-1-DELETE': '',
        }

        response = self.client.post(
            url,
            post_data,
            follow=True,
        )
        self.assertTemplateUsed(response, 'projects/project_edit.html')
        self.assertEqual(response.status_code, 200)
        self.assertFormsetError(
            response,
            formset='position_formset',
            form_index=None,
            field=None,
            errors='Project must have at least one position.',
        )

    def test_project_update_view_post_no_name(self):
        self.client.force_login(self.user1)
        url = reverse(
            'projects:project-update',
            kwargs={'pk': self.project1.id}
        )

        post_data = {
            'name': '',
            'description': 'New Project Description1',
            'timeline': 'New Project Timeline',
            'requirements': 'New Project Requirements',
            'positions-TOTAL_FORMS': '3',
            'positions-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '10',
            'positions-0-id': str(self.position1.id),
            'positions-0-role_name': self.role1.name,
            'positions-0-description': 'role1 description',
            'positions-1-id': '',
            'positions-1-role_name': self.role2.name,
            'positions-1-description': 'role2 description',
            'positions-2-id': '',
            'positions-2-role_name': self.role3.name,
            'positions-2-description': 'role3 description',
        }

        response = self.client.post(
            url,
            post_data,
            follow=True,
        )
        self.assertFormError(
            response,
            form='form',
            field='name',
            errors='This field is required.',
        )

    def test_project_update_view_post_no_description(self):
        self.client.force_login(self.user1)
        url = reverse(
            'projects:project-update',
            kwargs={'pk': self.project1.id}
        )

        post_data = {
            'name': 'New Project Name1',
            'description': '',
            'timeline': 'New Project Timeline',
            'requirements': 'New Project Requirements',
            'positions-TOTAL_FORMS': '3',
            'positions-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '10',
            'positions-0-id': str(self.position1.id),
            'positions-0-role_name': self.role1.name,
            'positions-0-description': 'role1 description',
            'positions-1-id': '',
            'positions-1-role_name': self.role2.name,
            'positions-1-description': 'role2 description',
            'positions-2-id': '',
            'positions-2-role_name': self.role3.name,
            'positions-2-description': 'role3 description',
        }

        response = self.client.post(
            url,
            post_data,
            follow=True,
        )
        self.assertFormError(
            response,
            form='form',
            field='description',
            errors='This field is required.',
        )

    def test_project_update_view_post_no_timeline(self):
        self.client.force_login(self.user1)
        url = reverse(
            'projects:project-update',
            kwargs={'pk': self.project1.id}
        )

        post_data = {
            'name': 'New Project Name1',
            'description': 'New Project Description1',
            'timeline': '',
            'requirements': 'New Project Requirements',
            'positions-TOTAL_FORMS': '3',
            'positions-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '10',
            'positions-0-id': str(self.position1.id),
            'positions-0-role_name': self.role1.name,
            'positions-0-description': 'role1 description',
            'positions-1-id': '',
            'positions-1-role_name': self.role2.name,
            'positions-1-description': 'role2 description',
            'positions-2-id': '',
            'positions-2-role_name': self.role3.name,
            'positions-2-description': 'role3 description',
        }

        response = self.client.post(
            url,
            post_data,
            follow=True,
        )
        self.assertFormError(
            response,
            form='form',
            field='timeline',
            errors='This field is required.',
        )

    def test_project_update_view_post_no_requirements(self):
        self.client.force_login(self.user1)
        url = reverse(
            'projects:project-update',
            kwargs={'pk': self.project1.id}
        )

        post_data = {
            'name': 'New Project Name1',
            'description': 'New Project Description1',
            'timeline': 'New Project Timeline1',
            'requirements': '',
            'positions-TOTAL_FORMS': '3',
            'positions-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '10',
            'positions-0-id': str(self.position1.id),
            'positions-0-role_name': self.role1.name,
            'positions-0-description': 'role1 description',
            'positions-1-id': '',
            'positions-1-role_name': self.role2.name,
            'positions-1-description': 'role2 description',
            'positions-2-id': '',
            'positions-2-role_name': self.role3.name,
            'positions-2-description': 'role3 description',
        }

        response = self.client.post(
            url,
            post_data,
            follow=True,
        )
        self.assertFormError(
            response,
            form='form',
            field='requirements',
            errors='This field is required.',
        )

    def test_project_update_view_post_no_project_name(self):
        self.client.force_login(self.user1)
        url = reverse(
            'projects:project-update',
            kwargs={'pk': self.project1.id}
        )

        post_data = {
            'name': 'New Project Name1',
            'description': 'New Project Description1',
            'timeline': 'New Project Timeline1',
            'requirements': 'New Project Requirements1',
            'positions-TOTAL_FORMS': '3',
            'positions-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '10',
            'positions-0-id': str(self.position1.id),
            'positions-0-role_name': self.role1.name,
            'positions-0-description': 'role1 description',
            'positions-1-id': '',
            'positions-1-role_name': self.role2.name,
            'positions-1-description': 'role2 description',
            'positions-2-id': '',
            'positions-2-role_name': '',
            'positions-2-description': 'role3 description',
        }

        response = self.client.post(
            url,
            post_data,
            follow=True,
        )
        self.assertFormsetError(
            response,
            formset='position_formset',
            form_index=2,
            field='role_name',
            errors='This field is required.',
        )

    def test_project_update_view_post_no_project_description(self):
        self.client.force_login(self.user1)
        url = reverse(
            'projects:project-update',
            kwargs={'pk': self.project1.id}
        )

        post_data = {
            'name': 'New Project Name1',
            'description': 'New Project Description1',
            'timeline': 'New Project Timeline1',
            'requirements': 'New Project Requirements1',
            'positions-TOTAL_FORMS': '3',
            'positions-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '10',
            'positions-0-id': str(self.position1.id),
            'positions-0-role_name': self.role1.name,
            'positions-0-description': 'role1 description',
            'positions-1-id': '',
            'positions-1-role_name': self.role2.name,
            'positions-1-description': 'role2 description',
            'positions-2-id': '',
            'positions-2-role_name': self.role3.name,
            'positions-2-description': '',
        }

        response = self.client.post(
            url,
            post_data,
            follow=True,
        )
        self.assertFormsetError(
            response,
            formset='position_formset',
            form_index=2,
            field='description',
            errors='This field is required.',
        )

    def test_project_update_view_post_position_skills(self):
        self.client.force_login(self.user1)
        url = reverse(
            'projects:project-update',
            kwargs={'pk': self.project1.id}
        )

        skills = self.skill1.name + ', ' + 'New Skill'

        post_data = {
            'name': 'New Project Name1',
            'description': 'New Project Description1',
            'timeline': 'New Project Timeline1',
            'requirements': 'New Project Requirements1',
            'positions-TOTAL_FORMS': '1',
            'positions-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '10',
            'positions-0-id': str(self.position1.id),
            'positions-0-role_name': self.role1.name,
            'positions-0-description': 'role1 description',
            'positions-0-related_skills': skills
        }

        response = self.client.post(
            url,
            post_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'projects:project-detail',
                kwargs={'pk': self.project1.id}
            )
        )
        project = models.Project.objects.get(id=1)
        position = models.Position.objects.get(project=project)

        self.assertEqual(position.related_skills.count(), 2)
        self.assertIn(self.skill1, position.related_skills.all())

        new_skill = models.Skill.objects.get(name='New Skill')
        self.assertIn(new_skill, position.related_skills.all())

    def test_project_update_view_post_unauthenticated(self):
        url = reverse(
            'projects:project-update',
            kwargs={'pk': self.project1.id}
        )

        post_data = {
            'name': 'New Project Name1',
            'description': 'New Project Description1',
            'timeline': 'New Project Timeline1',
            'requirements': 'New Project Requirements1',
            'positions-TOTAL_FORMS': '1',
            'positions-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '10',
            'positions-0-id': str(self.position1.id),
            'positions-0-role_name': self.role1.name,
            'positions-0-description': 'role1 description',
        }

        response = self.client.post(
            url,
            post_data,
            follow=True,
        )

        expected_url = (reverse('accounts:sign-in') + '?next=' + url)
        self.assertRedirects(response, expected_url)

    def test_project_update_view_post_user_not_project_owner(self):
        self.client.force_login(self.user2)
        url = reverse(
            'projects:project-update',
            kwargs={'pk': self.project1.id}
        )

        post_data = {
            'name': 'New Project Name1',
            'description': 'New Project Description1',
            'timeline': 'New Project Timeline1',
            'requirements': 'New Project Requirements1',
            'positions-TOTAL_FORMS': '1',
            'positions-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '10',
            'positions-0-id': str(self.position1.id),
            'positions-0-role_name': self.role1.name,
            'positions-0-description': 'role1 description',
        }

        response = self.client.post(
            url,
            post_data,
            follow=True,
        )
        self.assertEqual(response.status_code, 404)

    def test_project_create(self):
        self.client.force_login(self.user1)
        url = reverse('projects:project-create')

        post_data = {
            'name': 'New Project Name1',
            'description': 'New Project Description1',
            'timeline': 'New Project Timeline',
            'requirements': 'New Project Requirements',
            'positions-TOTAL_FORMS': '3',
            'positions-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '10',
            'positions-0-id': '',
            'positions-0-role_name': self.role1.name,
            'positions-0-description': 'role1 description',
            'positions-1-id': '',
            'positions-1-role_name': self.role2.name,
            'positions-1-description': 'role2 description',
            'positions-2-id': '',
            'positions-2-role_name': self.role3.name,
            'positions-2-description': 'role3 description',
        }

        response = self.client.post(
            url,
            post_data,
            follow=True,
        )
        self.assertTemplateUsed(response, 'projects/project.html')
        project = models.Project.objects.get(name='New Project Name1')
        self.assertRedirects(
            response,
            reverse(
                'projects:project-detail',
                kwargs={'pk': project.id}
            )
        )

        self.assertEqual(project.name, 'New Project Name1')
        self.assertEqual(project.description, 'New Project Description1')
        self.assertEqual(project.timeline, 'New Project Timeline')
        self.assertEqual(project.requirements, 'New Project Requirements')
        self.assertEqual(project.positions.all().count(), 3)


class IndexViewTests(TestCase):
    def setUp(self):
        ModelTests.setUp(self)
        # Create a position linked with project2 and with 2 skills: skill1, and
        # skill2.
        self.position2 = models.Position.objects.create(
            role=self.role2,
            project=self.project2,
        )
        self.position2.related_skills = [self.skill1, self.skill2]
        self.position2.save()

    def test_index_view_unauthenticated(self):
        response = self.client.get(reverse('projects:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/index.html')
        self.assertIn(self.project1, response.context['projects'])
        self.assertIn(self.project2, response.context['projects'])
        self.assertIn(self.position1.role.name.lower(),
                      response.context['needs'])
        self.assertIn(self.position2.role.name.lower(),
                      response.context['needs'])
        self.assertContains(response, self.project1.name)

    def test_index_view_authenticated(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('projects:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/index.html')
        self.assertIn(self.project1, response.context['projects'])
        self.assertIn(self.project2, response.context['projects'])
        self.assertContains(response, self.project1.name)

    def test_index_view_filter_by_name(self):
        self.client.force_login(self.user1)
        url = reverse('projects:home') + '?q=project1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/index.html')
        self.assertIn(self.project1, response.context['projects'])
        self.assertNotIn(self.project2, response.context['projects'])
        self.assertIn(self.position1.role.name.lower(),
                      response.context['needs'])
        self.assertNotIn(self.position2.role.name.lower(),
                      response.context['needs'])
        self.assertContains(response, self.project1.name)

    def test_index_view_filter_by_description(self):
        self.client.force_login(self.user1)
        url = reverse('projects:home') + '?q=description2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/index.html')
        self.assertIn(self.project2, response.context['projects'])
        self.assertNotIn(self.project1, response.context['projects'])
        self.assertNotIn(self.position1.role.name.lower(),
                      response.context['needs'])
        self.assertIn(self.position2.role.name.lower(),
                      response.context['needs'])
        self.assertContains(response, self.project2.name)

    def test_index_view_filter_by_position(self):
        self.client.force_login(self.user1)
        position_string = self.position1.role.name.lower()
        url = reverse('projects:home') + '?position=' + position_string
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/index.html')
        self.assertIn(self.project1, response.context['projects'])
        self.assertNotIn(self.project2, response.context['projects'])
        self.assertContains(response, self.project1.name)

    def test_index_view_filter_by_position_and_term(self):
        self.client.force_login(self.user1)
        position_string = self.position1.role.name.lower()
        url = (reverse('projects:home') + '?q=project2&position=' +
               position_string)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/index.html')
        self.assertNotIn(self.project1, response.context['projects'])
        self.assertNotIn(self.project2, response.context['projects'])


class ForMeViewTests(TestCase):
    def setUp(self):
        IndexViewTests.setUp(self)
        # Create a position linked with project2 and with 1 skills: skill5.
        self.position3 = models.Position.objects.create(
            role=self.role3,
            project=self.project2,
        )
        self.position3.related_skills = [self.skill5]
        self.position3.save()

    def test_for_me_view_unauthenticated(self):
        url = reverse('projects:projects-for-me')
        response = self.client.get(url)
        expected_url = (reverse('accounts:sign-in') + '?next=' + url)
        self.assertRedirects(response, expected_url)

    def test_index_view_authenticated(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('projects:projects-for-me'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/index.html')
        self.assertNotIn(self.project1, response.context['projects'])
        self.assertIn(self.project2, response.context['projects'])
        self.assertIn(self.position2.role.name.lower(),
                      response.context['needs'])
        self.assertIn(self.position3.role.name.lower(),
                      response.context['needs'])
        self.assertNotIn(self.position1.role.name.lower(),
                         response.context['needs'])
        self.assertContains(response, self.project2.name)

    def test_index_view_filter_by_position(self):
        self.client.force_login(self.user1)
        position_string = self.position3.role.name
        url = (reverse('projects:projects-for-me') + '?position=' +
               position_string)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/index.html')
        self.assertNotIn(self.project1, response.context['projects'])
        self.assertIn(self.project2, response.context['projects'])
        self.assertContains(response, self.project2.name)


class ProjectDeleteViewTests(TestCase):
    def setUp(self):
        ModelTests.setUp(self)

    def test_project_delete_view_unauthenticated(self):
        url = reverse('projects:project-delete', kwargs={'pk': 1})
        response = self.client.post(url)
        expected_url = (reverse('accounts:sign-in') + '?next=' + url)
        self.assertRedirects(response, expected_url)

    def test_project_delete_view_authenticated(self):
        self.client.force_login(self.user1)
        num_projects_initial = models.Project.objects.count()
        url = reverse('projects:project-delete', kwargs={'pk': 1})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(models.Project.objects.count(), num_projects_initial-1)
        with self.assertRaises(models.Project.DoesNotExist):
            models.Project.objects.get(id=1)

    def test_project_delete_view_user_not_project_owner(self):
        self.client.force_login(self.user2)
        url = reverse('projects:project-delete', kwargs={'pk': 1})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)


class ApplicationCreateViewTests(TestCase):
    def setUp(self):
        ForMeViewTests.setUp(self)

    def test_application_create_view_unauthenticated(self):
        url = reverse('projects:applications-create',
                      kwargs={'pk': self.project1.pk})
        response = self.client.post(url)
        expected_url = (reverse('accounts:sign-in') + '?next=' + url)
        self.assertRedirects(response, expected_url)

    def test_application_create_view_success(self):
        self.client.force_login(self.user1)
        url = reverse('projects:applications-create',
                      kwargs={'pk': self.project1.pk})
        post_data = {
            'position': self.position1.id
        }
        response = self.client.post(
            url,
            post_data,
            follow=True
        )
        self.assertRedirects(response, reverse('projects:project-detail',
                                               kwargs={'pk': self.project1.id}))
        self.assertEqual(models.Application.objects.count(), 1)
        application = models.Application.objects.get(id=1)
        self.assertEqual(application.applicant, self.user1)
        self.assertEqual(application.position, self.position1)
        self.assertTemplateUsed(response, 'projects/project.html')
        self.assertEqual(application.status, 'n')

    def test_application_create_view_repeated_application(self):
        self.client.force_login(self.user1)

        models.Application.objects.create(
            applicant=self.user1,
            position=self.position1
        )

        url = reverse('projects:applications-create',
                      kwargs={'pk': self.project1.pk})
        post_data = {
            'position': self.position1.id
        }
        response = self.client.post(
            url,
            post_data,
            follow=True
        )
        self.assertRedirects(response, reverse('projects:project-detail',
                                               kwargs={'pk': self.project1.id}))
        self.assertEqual(models.Application.objects.count(), 1)
        application = models.Application.objects.get(id=1)
        self.assertEqual(application.applicant, self.user1)
        self.assertEqual(application.position, self.position1)
        self.assertEqual(application.status, 'n')
        self.assertContains(response,
                            'An error occurred while sending your application.')


class ApplicationListViewTests(TestCase):
    def setUp(self):
        ForMeViewTests.setUp(self)

        self.project3 = models.Project.objects.create(
            name='Project2',
            timeline='2 days',
            requirements='Requirements2',
            description='Description2',
            owner=self.user2,
        )

        self.position3 = models.Position.objects.create(
            role=self.role3,
            project=self.project3,
        )
        self.position3.related_skills = [self.skill1, self.skill2]
        self.position3.save()

        self.position11 = models.Position.objects.create(
            role=self.role3,
            project=self.project1,
        )
        self.position11.save()

        # Create a third user
        self.user3 = get_user_model().objects.create_user(
            email='user3@example.com',
            password='password'
        )

        # Create applications
        self.application11 = models.Application.objects.create(
            applicant=self.user1,
            position=self.position1,
            status='a'
        )
        self.application12 = models.Application.objects.create(
            applicant=self.user1,
            position=self.position2
        )
        self.application13 = models.Application.objects.create(
            applicant=self.user1,
            position=self.position3
        )
        self.application21 = models.Application.objects.create(
            applicant=self.user2,
            position=self.position1
        )
        self.application22 = models.Application.objects.create(
            applicant=self.user2,
            position=self.position2,
            status='a'
        )
        self.application23 = models.Application.objects.create(
            applicant=self.user2,
            position=self.position3
        )
        self.application31 = models.Application.objects.create(
            applicant=self.user3,
            position=self.position1
        )
        self.application311 = models.Application.objects.create(
            applicant=self.user3,
            position=self.position11
        )
        self.application32 = models.Application.objects.create(
            applicant=self.user3,
            position=self.position2
        )
        self.application33 = models.Application.objects.create(
            applicant=self.user3,
            position=self.position3
        )

    def test_application_list_view_get_unauthenticated(self):
        url = reverse('projects:applications')
        response = self.client.get(url)
        expected_url = (reverse('accounts:sign-in') + '?next=' + url)
        self.assertRedirects(response, expected_url)

    def test_application_list_view_get_authenticated(self):
        self.client.force_login(self.user1)
        url = reverse('projects:applications')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/applications.html')
        self.assertEqual(response.context['applications'].count(), 7)
        self.assertIn(self.application11, response.context['applications'])
        self.assertIn(self.application12, response.context['applications'])
        self.assertIn(self.application21, response.context['applications'])
        self.assertIn(self.application22, response.context['applications'])
        self.assertIn(self.application31, response.context['applications'])
        self.assertIn(self.application32, response.context['applications'])
        self.assertIn(self.application311, response.context['applications'])

    def test_application_list_view_get_sorted_by_status(self):
        self.client.force_login(self.user1)

        url = reverse('projects:applications') + '?status=accepted'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/applications.html')
        self.assertEqual(response.context['applications'].count(), 2)
        self.assertIn(self.application11, response.context['applications'])
        self.assertIn(self.application22, response.context['applications'])

    def test_application_list_view_get_sorted_by_project(self):
        self.client.force_login(self.user1)
        project_string = self.project1.name.lower()
        url = reverse('projects:applications') + '?project=' + project_string
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/applications.html')
        self.assertEqual(response.context['applications'].count(), 4)
        self.assertIn(self.application11, response.context['applications'])
        self.assertIn(self.application21, response.context['applications'])
        self.assertIn(self.application31, response.context['applications'])
        self.assertIn(self.application311, response.context['applications'])

    def test_application_list_view_get_sorted_by_position(self):
        self.client.force_login(self.user1)
        position_string = self.role3.name.lower()
        url = reverse('projects:applications') + '?position=' + position_string
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/applications.html')
        self.assertEqual(response.context['applications'].count(), 1)
        self.assertIn(self.application311, response.context['applications'])

    def test_application_list_view_get_sorted_by_project_and_status(self):
        self.client.force_login(self.user1)
        project_string = self.project1.name.lower()
        url = (reverse('projects:applications') + '?project=' + project_string +
               '&status=accepted')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/applications.html')
        self.assertEqual(response.context['applications'].count(), 1)
        self.assertIn(self.application11, response.context['applications'])


class ApplicationsUpdateViewTests(TestCase):
    def setUp(self):
        ApplicationListViewTests.setUp(self)

    def test_applications_update_view_post_unauthenticated(self):
        url = reverse('projects:applications-update',
                      kwargs={'status': 'reject'})
        response = self.client.get(url)
        expected_url = (reverse('accounts:sign-in') + '?next=' + url)
        self.assertRedirects(response, expected_url)

    def test_applications_update_view_post_reject_success(self):
        self.client.force_login(self.user1)
        url = reverse('projects:applications-update',
                      kwargs={'status': 'reject'})
        post_data = {
            'id': self.application11.id
        }
        response = self.client.post(
            url,
            post_data,
            follow=True
        )
        self.assertRedirects(response, reverse('projects:applications'))
        self.assertTemplateUsed(response, 'projects/applications.html')
        application = models.Application.objects.get(id=self.application11.id)
        self.assertEqual(application.status, 'r')
        project = application.position.project
        self.assertTrue(project.active)

    def test_applications_update_view_post_accept_success(self):
        self.client.force_login(self.user1)
        url = reverse('projects:applications-update',
                      kwargs={'status': 'accept'})
        post_data = {
            'id': self.application12.id
        }
        response = self.client.post(
            url,
            post_data,
            follow=True
        )
        self.assertRedirects(response, reverse('projects:applications'))
        self.assertTemplateUsed(response, 'projects/applications.html')
        application = models.Application.objects.get(id=self.application12.id)
        self.assertEqual(application.status, 'a')
        self.assertEqual(
            models.Application.objects.get(id=self.application22.id).status,
            'r'
        )
        self.assertEqual(
            models.Application.objects.get(id=self.application32.id).status,
            'r'
        )
        project = self.application12.position.project
        self.assertTrue(project.active)
