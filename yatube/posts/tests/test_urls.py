from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from http import HTTPStatus

from posts.models import Group, Post


User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.auth = User.objects.create_user(username='post_auth')
        cls.non_auth = User.objects.create_user(username='just_user')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug'
        )
        cls.post = Post.objects.create(
            author=cls.auth,
            text='Тестовый пост',
            group=cls.group
        )

        cls.templates_code_unauth = {
            '/': HTTPStatus.OK,
            f'/group/{cls.group.slug}/': HTTPStatus.OK,
            f'/profile/{cls.post.author.username}/': HTTPStatus.OK,
            f'/posts/{cls.post.pk}/': HTTPStatus.OK,
            f'/posts/{cls.post.pk}/edit/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.FOUND,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
            f'/posts/{cls.post.pk}/comment/': HTTPStatus.NOT_FOUND,
            '/follow/': HTTPStatus.NOT_FOUND,
            f'/profile/{cls.post.author.username}/follow/': HTTPStatus.NOT_FOUND,
            f'/profile/{cls.post.author.username}/unfollow/': HTTPStatus.NOT_FOUND,

        }

        cls.templates_code_auth = {
            '/': HTTPStatus.OK,
            f'/group/{cls.group.slug}/': HTTPStatus.OK,
            f'/profile/{cls.post.author.username}/': HTTPStatus.OK,
            f'/posts/{cls.post.pk}/': HTTPStatus.OK,
            f'/posts/{cls.post.pk}/edit/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
            f'/posts/{cls.post.pk}/comment/': HTTPStatus.FOUND,
            '/follow/': HTTPStatus.OK,
            f'/profile/{cls.post.author.username}/follow/': HTTPStatus.FOUND,
            f'/profile/{cls.post.author.username}/unfollow/': HTTPStatus.FOUND,
        }

        cls.templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.post.author.username}/': 'posts/profile.html',
            f'/posts/{cls.post.pk}/': 'posts/post_detail.html',
            f'/posts/{cls.post.pk}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/unexisting_page/': 'core/404.html'
        }

    def setUp(self):
        self.guest_client = Client()

        self.post_auth = Client()
        self.post_auth.force_login(StaticURLTests.auth)

        self.authorized_client = Client()
        self.authorized_client.force_login(StaticURLTests.non_auth)

    def test_guest_client_urls_status_code(self):
        """Проверка доступности страниц для неавторизованного пользователя."""
        for adress, response_code in self.templates_code_unauth.items():
            with self.subTest(adress=adress):
                status_code = self.guest_client.get(adress).status_code
                self.assertEqual(status_code, response_code)

    def test_guest_client_urls_status_code(self):
        """Проверка доступности страниц для авторизованного пользователя."""
        for adress, response_code in self.templates_code_auth.items():
            with self.subTest(adress=adress):
                status_code = self.authorized_client.get(adress).status_code
                self.assertEqual(status_code, response_code)

    def test_post_edit_url_redirect_not_auth(self):
        """Проверка доступности post/edit
        для авторизованного пользователя."""
        response = self.authorized_client.get(
            f'/posts/{StaticURLTests.post.pk}/edit/', follow=True
        )
        self.assertRedirects(response, f'/posts/{StaticURLTests.post.pk}/')

    def test_post_edit_auth(self):
        """Проверка доступности post/edit для автора поста."""
        response = self.post_auth.get(
            f'/posts/{StaticURLTests.post.pk}/edit/'
        ).status_code
        self.assertEqual(response, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """Провка названия шаблонов."""
        for adress, template in self.templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.post_auth.get(adress)
                self.assertTemplateUsed(response, template)
