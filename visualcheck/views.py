import base64
from typing import Any
from .utils.s3_upload import upload_bytes_to_s3

from django.http import JsonResponse, HttpRequest
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now
from .models import Employee, Attendance
from .services.visual_feedback_service import analyze_attire_from_two_images
from django.utils.timezone import now
from .models import Employee, Attendance

def bytes_to_base64(file_bytes: bytes) -> str:
    return base64.b64encode(file_bytes).decode("utf-8")


@method_decorator(csrf_exempt, name="dispatch")
class AnalyzeAttireView(View):

    def post(self, request):
        upper_file = request.FILES.get("upper_body")
        full_file = request.FILES.get("full_body")

        employee_name = request.POST.get("employee_name", "").strip()
        employee_id = request.POST.get("employee_id", "").strip()
        location_text = request.POST.get("location", "").strip()
        verify_type = request.POST.get("verify_type", "self")

        # 1️⃣ Validation
        if not upper_file or not full_file:
            return JsonResponse({"error": "Images required"}, status=400)

        if not employee_name or not employee_id:
            return JsonResponse({"error": "Employee details required"}, status=400)

        if not location_text:
            return JsonResponse({"error": "Location required"}, status=400)

        # 2️⃣ Read file bytes ONCE (CRITICAL)
        upper_bytes = upper_file.read()
        full_bytes = full_file.read()

        # 3️⃣ Convert to base64 for AI
        upper_b64 = bytes_to_base64(upper_bytes)
        full_b64 = bytes_to_base64(full_bytes)

        # 4️⃣ Upload bytes to S3
        upper_body_url = upload_bytes_to_s3(
            upper_bytes,
            "attendance/upper",
            upper_file.content_type
        )

        full_body_url = upload_bytes_to_s3(
            full_bytes,
            "attendance/full",
            full_file.content_type
        )

        # 5️⃣ Get or create employee
        employee, _ = Employee.objects.get_or_create(
            employee_id=employee_id,
            defaults={"name": employee_name}
        )

        # 6️⃣ Prevent multiple punches per day
        today = now().date()
        if Attendance.objects.filter(employee=employee, date=today).exists():
            return JsonResponse(
                {"status": "error", "message": "Already punched today"},
                status=400
            )

        status = "SELF_VERIFIED" if verify_type == "self" else "PENDING_ADMIN"

        # 7️⃣ Save attendance (URLs ONLY)
        attendance = Attendance.objects.create(
            employee=employee,
            upper_body_image_url=upper_body_url,
            full_body_image_url=full_body_url,
            location_text=location_text,
            status=status
        )

        # 8️⃣ AI analysis (ONLY for self verify)
        if verify_type == "self":
            ai_response = analyze_attire_from_two_images(
                upper_body_b64=upper_b64,
                full_body_b64=full_b64,
                candidate_name=employee_name,
                candidate_id=employee_id,
            )

            attendance.ai_response = ai_response
            attendance.verified_by = "SELF"
            attendance.verified_at = now()
            attendance.save()

        # 9️⃣ Final response
        return JsonResponse({
            "status": attendance.status,
            "attendance_id": attendance.id,
            "date": str(attendance.date),
            "punch_time": attendance.punch_time.strftime("%Y-%m-%d %H:%M:%S"),
            "location": attendance.location_text,
            "upper_body_image_url": attendance.upper_body_image_url,
            "full_body_image_url": attendance.full_body_image_url,
            "ai_analysis": attendance.ai_response
        })



class DailyAttendanceView(View):
    def get(self, request):
        date = request.GET.get("date")

        records = Attendance.objects.filter(date=date).values(
            "employee__employee_id",
            "employee__name",
            "punch_time",
            "status"
        )

        return JsonResponse(list(records), safe=False)



class AdminVerifyAttendanceView(View):

    def post(self, request, attendance_id):
        action = request.POST.get("action")  # approve / reject
        admin_name = request.POST.get("admin_name")

        attendance = Attendance.objects.get(id=attendance_id)

        if attendance.status != "PENDING_ADMIN":
            return JsonResponse({"error": "Already verified"}, status=400)

        if action == "approve":
            attendance.status = "ADMIN_VERIFIED"
        else:
            attendance.status = "REJECTED"

        attendance.verified_by = admin_name
        attendance.verified_at = now()
        attendance.save()

        return JsonResponse({"status": attendance.status})



#================ admin  check pending Employee

class AdminPendingAttendanceView(View):

    def get(self, request):
        records = Attendance.objects.filter(
            status="PENDING_ADMIN"
        ).order_by("-punch_time")

        data = []
        for a in records:
            data.append({
                "attendance_id": a.id,
                "employee_id": a.employee.employee_id,
                "employee_name": a.employee.name,
                "date": str(a.date),
                "punch_time": str(a.punch_time),
                "location": a.location_text,
                "upper_body_image": a.upper_body_image_url,
                "full_body_image": a.full_body_image_url,
                "status": a.status
            })

        return JsonResponse(data, safe=False)




#================ admin  check verify Employee

class AdminVerifiedAttendanceView(View):

    def get(self, request):
        records = Attendance.objects.filter(
            status__in=["SELF_VERIFIED", "ADMIN_VERIFIED"]
        ).order_by("-punch_time")

        data = []
        for a in records:
            data.append({
                "attendance_id": a.id,
                "employee_id": a.employee.employee_id,
                "employee_name": a.employee.name,
                "date": str(a.date),
                "punch_time": str(a.punch_time),
                "location": a.location_text,
                "verified_by": a.verified_by,
                "verified_at": str(a.verified_at),
                "status": a.status
            })

        return JsonResponse(data, safe=False)
