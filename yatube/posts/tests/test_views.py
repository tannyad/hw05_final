from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django import forms

from django.core.cache import cache

from posts.models import Group, Post, Follow
from posts.views import POSTS_AMOUNT


User = get_user_model()


class StaticViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.auth = User.objects.create_user(username='post_auth')
        cls.user = User.objects.create_user(username='user')
        cls.dop_user = User.objects.create_user(username='dop_user')
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

    def setUp(self):
        self.guest_client = Client()

        self.post_auth = Client()
        self.post_auth.force_login(StaticViewsTests.auth)

        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        self.dop_authorized_client = Client()
        self.dop_authorized_client.force_login(self.dop_user)

    def test_pages_uses_correct_template(self):
        """Во view-функциях используются правильные html-шаблоны"""
        templates_pages_names = {
            reverse('posts:post'): 'posts/index.html',
            reverse(
                'posts:group_posts',
                kwargs={'slug': 'test-slug'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': 'post_auth'}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': StaticViewsTests.post.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': StaticViewsTests.post.pk}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html'
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.post_auth.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        """Список постов в шаблоне index соответствует ожидаемому контексту."""
        response = self.post_auth.get(reverse("posts:post"))
        first_post = response.context['page_obj'][0]
        first_post_text = first_post.text
        first_post_author = first_post.author
        first_post_group = first_post.group
        self.assertEqual(first_post_text, 'Тестовый пост')
        self.assertEqual(first_post_author, StaticViewsTests.auth)
        self.assertEqual(first_post_group, StaticViewsTests.group)

    def test_group_list_show_correct_context(self):
        """Список постов в шаблоне group_posts
        соответствует ожидаемому контексту."""
        response = self.post_auth.get(
            reverse("posts:group_posts",
                    kwargs={"slug": self.group.slug})
        )
        post_list = list(Post.objects.filter(
            group_id=self.group.id)[:POSTS_AMOUNT])
        first_post = response.context['page_obj'][0]
        first_post_title = first_post.group.title
        first_post_desc = first_post.group.description
        first_post_slug = first_post.group.slug
        self.assertEqual(first_post_title, StaticViewsTests.group.title)
        self.assertEqual(first_post_desc, StaticViewsTests.group.description)
        self.assertEqual(first_post_slug, StaticViewsTests.group.slug)
        self.assertEqual(list(response.context["page_obj"]), post_list)

    def test_profile_show_correct_context(self):
        """Список постов в шаблоне profile
        соответствует ожидаемому контексту."""
        response = self.post_auth.get(
            reverse("posts:profile", args=(self.post.author,))
        )
        first_post = response.context['page_obj'][0]
        first_post_auth = first_post.author
        expected = list(Post.objects.filter(
            author_id=self.auth.id)[:POSTS_AMOUNT])
        self.assertEqual(list(response.context["page_obj"]), expected)
        self.assertEqual(first_post_auth, StaticViewsTests.post.author)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail соответствует ожиданиям."""
        response = self.post_auth.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.id})
        )
        self.assertEqual(response.context.get("post").text, self.post.text)
        self.assertEqual(response.context.get("post").author, self.post.author)
        self.assertEqual(response.context.get("post").group, self.post.group)

    def test_create_edit_show_correct_context(self):
        """Шаблон редактирования create_post соответствует ожиданиям."""
        response = self.post_auth.get(
            reverse("posts:post_edit", kwargs={"post_id": self.post.id})
        )
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
            "image": forms.fields.ImageField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields[value]
                self.assertIsInstance(form_field, expected)
                self.assertTrue(response.context['is_edit'])

    def test_create_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.post_auth.get(reverse("posts:post_create"))
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
            "image": forms.fields.ImageField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_check_group_in_pages(self):
        """Проверяем отображение поста при добавлении группы."""
        form_fields = {
            reverse("posts:post"): Post.objects.get(group=self.post.group),
            reverse(
                "posts:group_posts", kwargs={"slug": self.group.slug}
            ): Post.objects.get(group=self.post.group),
            reverse(
                "posts:profile", kwargs={"username": self.post.author}
            ): Post.objects.get(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.post_auth.get(value)
                form_field = response.context["page_obj"]
                self.assertIn(expected, form_field)

    def test_img_response_correct_context(self):
        """Изображение передается на главную страницу,
        на страницу профайла, на страницы группы."""
        names = [reverse('posts:profile',
                         kwargs={'username': StaticViewsTests.auth}),
                 reverse('posts:group_posts',
                         kwargs={'slug': StaticViewsTests.group.slug}),
                 reverse('posts:post')
                 ]
        for name in names:
            response = self.post_auth.get(name)
            post = response.context["page_obj"][0]
            self.assertEqual(post.image, self.post.image)

    def test_img_response_correct_context(self):
        """Изображение передается на страницу поста."""
        response = self.post_auth.get(
            reverse('posts:post_detail', kwargs={
                'post_id': StaticViewsTests.post.pk
            })
        )
        post = response.context["post"]
        self.assertEqual(post.image, self.post.image)

    def test_cache_index(self):
        """Тестирование cache для главной страницы."""
        original = self.post_auth.get(reverse('posts:post'))
        posts = original.content
        Post.objects.get(id=1).delete()
        new = self.post_auth.get(reverse('posts:post'))
        new_posts = new.content
        self.assertEqual(new_posts, posts)
        cache.clear()
        response_new = self.post_auth.get(reverse('posts:post'))
        posts_after_clean = response_new.content
        self.assertNotEqual(new_posts, posts_after_clean)

    def test_following(self):
        no_follow = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(no_follow.context['page_obj']), 0)

        Follow.objects.create(author=self.auth, user=self.user)

        for_follower = self.authorized_client.get(
            reverse("posts:follow_index")
        )
        self.assertEqual(len(for_follower.context['page_obj']), 1)
        self.assertIn(self.post, for_follower.context['page_obj'])

        not_for_follower = self.dop_authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(self.post, not_for_follower.context['page_obj'])

        Follow.objects.all().delete()
        unfollow = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(unfollow.context['page_obj']), 0)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.auth = User.objects.create_user(username='post_auth')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug'
        )
        cls.posts = [Post(text='Тестовый текст',
                          author=cls.auth,
                          group=cls.group) for i in range(13)]
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.post_auth = Client()
        self.post_auth.force_login(PaginatorViewsTest.auth)

    def test(self):
        names = [reverse('posts:profile',
                         kwargs={'username': PaginatorViewsTest.auth}),
                 reverse('posts:group_posts',
                         kwargs={'slug': PaginatorViewsTest.group.slug}),
                 reverse('posts:post')
                 ]
        for name in names:
            response_first_page = self.client.get(name)
            response_second_page_page = self.client.get(name + '?page=2')
            self.assertEqual(len(response_first_page.context['page_obj']), 10)
            self.assertEqual(len(
                response_second_page_page.context['page_obj']), 3)
