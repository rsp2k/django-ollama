"""
URL configuration for django-ollama testing.
"""

from django.urls import path

def dummy_view(request):
    pass

urlpatterns = [
    path("test/", dummy_view, name="test"),
    path("products/<int:pk>/", dummy_view, name="product_detail"),
]