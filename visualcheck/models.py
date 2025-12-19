from django.db import models

class Employee(models.Model):
    employee_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.employee_id} - {self.name}"

# class Attendance(models.Model):
#     employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

#     date = models.DateField(auto_now_add=True)          # ✅ ADD THIS
#     punch_time = models.DateTimeField(auto_now_add=True)  # ✅ ADD THIS

#     upper_body_image = models.ImageField(upload_to="attendance/upper/")
#     full_body_image = models.ImageField(upload_to="attendance/full/")

#     location_text = models.CharField(max_length=255)

#     ai_response = models.JSONField(null=True, blank=True)

#     STATUS_CHOICES = (
#         ("SELF_VERIFIED", "Self Verified"),
#         ("PENDING_ADMIN", "Pending Admin"),
#         ("ADMIN_VERIFIED", "Admin Verified"),
#         ("REJECTED", "Rejected"),
#     )

#     status = models.CharField(max_length=20, choices=STATUS_CHOICES)
#     verified_by = models.CharField(max_length=50, null=True, blank=True)
#     verified_at = models.DateTimeField(null=True, blank=True)




class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    date = models.DateField(auto_now_add=True)
    punch_time = models.DateTimeField(auto_now_add=True)

    upper_body_image_url = models.URLField(max_length=500)
    full_body_image_url = models.URLField(max_length=500)

    location_text = models.CharField(max_length=255)

    ai_response = models.JSONField(null=True, blank=True)

    STATUS_CHOICES = (
        ("SELF_VERIFIED", "Self Verified"),
        ("PENDING_ADMIN", "Pending Admin"),
        ("ADMIN_VERIFIED", "Admin Verified"),
        ("REJECTED", "Rejected"),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    verified_by = models.CharField(max_length=50, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
