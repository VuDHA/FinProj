---
trigger: glob
globs: "**/*.py,**/models.py,**/views.py,**/serializers.py,**/admin.py,**/urls.py,**/settings.py,**/manage.py,**/migrations/*.py"
---

# Django Development Rules

Invoke the `django-expert` skill when working on any Python/Django file.

- Use `select_related` for ForeignKey/OneToOne, `prefetch_related` for ManyToMany — never query inside loops
- Define `__str__`, `Meta.ordering`, and proper `db_index` on all models
- Use DRF `ModelSerializer` + `ViewSet` + `router.register` as the default pattern
- JWT authentication via `djangorestframework-simplejwt`
- Migrations: never edit existing migrations; always `makemigrations` + `migrate`
- Use `get_object_or_404` instead of raw `.get()` in views
- Keep business logic in services/managers, not in views or serializers
