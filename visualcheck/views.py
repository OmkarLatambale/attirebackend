import base64
from typing import Any

from django.http import JsonResponse, HttpRequest
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .services.visual_feedback_service import analyze_attire_from_two_images


def _file_to_base64(file_obj) -> str:
    """
    Convert an uploaded file (InMemoryUploadedFile) to base64 string.
    """
    if not file_obj:
        return ""

    file_bytes = file_obj.read()
    b64_bytes = base64.b64encode(file_bytes)
    return b64_bytes.decode("utf-8")


@method_decorator(csrf_exempt, name="dispatch")   # 👈 ADD THIS DECORATOR
class AnalyzeAttireView(View):
    """
    POST /api/analyze-attire/

    Expects multipart/form-data with:
      - upper_body: file (image)
      - full_body: file (image)
      - optional: candidate_name, candidate_id
    """

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        upper_file = request.FILES.get("upper_body")
        full_file = request.FILES.get("full_body")

        candidate_name = request.POST.get("candidate_name") or None
        candidate_id = request.POST.get("candidate_id") or None

        if not upper_file or not full_file:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Both 'upper_body' and 'full_body' image files are required.",
                },
                status=400,
            )

        try:
            upper_b64 = _file_to_base64(upper_file)
            full_b64 = _file_to_base64(full_file)

            raw_feedback = analyze_attire_from_two_images(
                upper_body_b64=upper_b64,
                full_body_b64=full_b64,
                candidate_name=candidate_name,
                candidate_id=candidate_id,
            )

            overall_msg = raw_feedback.get("overall_summary") or "Visual attire analysis completed."

            details = []
            for key in [
                "facial_grooming",
                "clothing_appearance",
                "clothing_style_formality",
                "footwear_shoes",
            ]:
                points = raw_feedback.get(key)
                if isinstance(points, list):
                    details.extend(points)

            return JsonResponse(
                {
                    "status": raw_feedback.get("status", "success"),
                    "overall": overall_msg,
                    "details": details,
                    "attire_recommendation": raw_feedback.get("attire_recommendation"),
                    "raw": raw_feedback,
                },
                status=200,
            )

        except Exception as e:
            print("AnalyzeAttireView error:", e)
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Server error while analyzing images: {str(e)[:200]}",
                },
                status=500,
            )
