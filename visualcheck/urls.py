from django.urls import path
from .views import AnalyzeAttireView,AdminPendingAttendanceView,AdminVerifiedAttendanceView

urlpatterns = [
    path("analyze-attire/", AnalyzeAttireView.as_view(), name="analyze_attire"),
    path("attendance/admin/pending/", AdminPendingAttendanceView.as_view()),
    path("attendance/admin/verified/", AdminVerifiedAttendanceView.as_view()),
  

]
