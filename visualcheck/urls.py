from django.urls import path
from .views import AnalyzeAttireView,AdminPendingAttendanceView,AdminVerifiedAttendanceView,AdminVerifyAttendanceView
from .views import AdminLoginJWTView
urlpatterns = [
    path("analyze-attire/", AnalyzeAttireView.as_view(), name="analyze_attire"),
    path("attendance/admin/pending/", AdminPendingAttendanceView.as_view()),
    path("attendance/admin/verified/", AdminVerifiedAttendanceView.as_view()),
    path(
    "attendance/admin/verify/<int:attendance_id>/",
    AdminVerifyAttendanceView.as_view(),
    name="admin_verify_attendance"
),

path("admin/login/jwt/", AdminLoginJWTView.as_view(), name="admin_login_jwt"),



  

]
