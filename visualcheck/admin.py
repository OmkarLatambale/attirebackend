from django.contrib import admin
from .models import Employee, Attendance

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "name")
    search_fields = ("employee_id", "name")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "date",
        "punch_time",
        "status",
        "verified_by",
        "verified_at",
    )
    list_filter = ("status", "date")
    search_fields = ("employee__employee_id", "employee__name")
