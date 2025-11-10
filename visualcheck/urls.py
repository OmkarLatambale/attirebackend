from django.urls import path
from .views import AnalyzeAttireView

urlpatterns = [
    path("analyze-attire/", AnalyzeAttireView.as_view(), name="analyze_attire"),
]
