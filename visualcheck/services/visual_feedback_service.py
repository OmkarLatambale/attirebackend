import base64
import io
import os
import json
from typing import List, Optional

from PIL import Image
from openai import OpenAI

# Initialize OpenAI client (v1+ API)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _to_image_data_uri(base64_str: str) -> str:
    """
    Ensure base64 string is in proper data URI format for OpenAI Vision API.
    """
    # Already has data URI prefix
    if base64_str.startswith("data:image"):
        return base64_str

    # Extract just the base64 data
    if "base64," in base64_str:
        base64_str = base64_str.split("base64,", 1)[1]

    # Clean the base64 string - remove whitespace/newlines
    base64_str = base64_str.strip().replace("\n", "").replace("\r", "").replace(" ", "")

    return f"data:image/jpeg;base64,{base64_str}"


def _validate_and_resize_image(base64_str: str) -> str:
    """
    Validate and resize image if needed.
    Returns a data URI base64 string.
    """
    try:
        # Extract base64 data
        if "base64," in base64_str:
            prefix, data = base64_str.split("base64,", 1)
            prefix = prefix + "base64,"
        else:
            prefix = "data:image/jpeg;base64,"
            data = base64_str

        # Decode and validate
        img_data = base64.b64decode(data)
        img = Image.open(io.BytesIO(img_data))

        # Validate format
        if img.format and img.format.lower() not in ("jpeg", "jpg", "png", "gif", "webp"):
            raise ValueError(f"Unsupported format: {img.format}")

        # Resize if too large (save tokens)
        if img.width > 1024 or img.height > 1024:
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

            # Re-encode to base64
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            new_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return f"{prefix}{new_data}"

        return f"{prefix}{data}"

    except Exception as e:
        print(f"Image validation error: {e}")
        raise


def analyze_frames_aggregated(
    frames_b64: List[str],
    candidate_name: Optional[str] = None,
    candidate_id: Optional[str] = None,
) -> dict:
    """
    Analyze 2–5 frames (e.g., upper-body selfie + full-body photo)
    using GPT-4o Vision.

    Returns structured feedback: facial grooming, clothing, style, shoes, etc.
    """
    if not frames_b64:
        return {"status": "no_frames", "message": "No frames provided"}

    # Process up to 5 frames (we expect 2 for this usecase)
    frames = frames_b64[:5]
    valid_images = []

    for idx, b64 in enumerate(frames):
        try:
            validated = _validate_and_resize_image(b64)
            valid_images.append(validated)
        except Exception as e:
            print(f"Failed to process frame {idx}: {e}")
            continue

    if not valid_images:
        return {"status": "error", "message": "No valid images to analyze"}

    candidate_display = (
        candidate_name or f"Candidate {candidate_id}" if candidate_id else "the candidate"
    )

    # --- UPDATED PROMPT FOR GROOMING / CLOTHES / SHOES ---
        # --- UPDATED PROMPT FOR TABLE-FRIENDLY JSON + LOGO CHECK ---
        # --- PROMPT FOR TABLE-FRIENDLY JSON + GENERIC LOGO CHECK ---
    prompt = """
You are analyzing photos of a shop promoter.
Your job is to evaluate the candidate’s readiness for professional workplace attire.

You should ALSO carefully check if there is any visible BRAND LOGO on the
T-shirt / shirt / jacket / uniform (for example: Samsung, Apple, Nike, etc.).

You do NOT need to match any specific company name.
You only need to decide:
- Does any logo or brand mark seem to be present on the upper clothing?
- If yes, try to read the text (e.g., "Samsung") if it is visible.
- If not sure, treat it as "no_logo_detected".

Return ONLY valid JSON with this structure (keys must match exactly):

{
  "facial_grooming": {
    "Hair Style": "value",
    "Beard": "value",
    "Face Cleanliness": "value"
  },
  "clothing_appearance": {
    "Outfit Type": "value",
    "Neatness": "value",
    "Color Choice": "value"
  },
  "clothing_style_formality": {
    "Formality Level": "formal|semi-formal|casual",
    "Overall Impression": "value"
  },
  "footwear_shoes": {
    "Footwear Type": "value",
    "Cleanliness": "value",
    "Appropriateness": "value"
  },
  "uniform_logo": {
    "detected_logo_text": "brand name or short description like 'Samsung' or 'logo unclear' or 'no logo'",
    "match_status": "match_found|no_logo_detected",
    "match_confidence": "high|medium|low"
  },
  "overall_summary": "Short 1-line summary",
  "attire_recommendation": "proper_interview_attire | needs_minor_improvement | not_appropriate_for_interview"
}

Rules for the logo section:
- Set match_status to "match_found" if you clearly see ANY logo or brand mark
  on the T-shirt / shirt / jacket / uniform.
- Set match_status to "no_logo_detected" if you do not see a clear logo
  (plain clothing, or very unclear mark).
- detected_logo_text should be the brand text if readable (e.g., "Samsung"),
  otherwise "logo unclear" or "no logo".
- match_confidence is your confidence in whether a logo exists.
"""



    try:
        # Build message content with all images
        content = [{"type": "text", "text": prompt}]

        for img_b64 in valid_images:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": _to_image_data_uri(img_b64),
                        "detail": "low",  # use "low" for token + cost efficiency
                    },
                }
            )

        # Call OpenAI Vision API
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # or "gpt-4o" for higher quality
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            temperature=0.2,
            max_tokens=600,
        )

        text = response.choices[0].message.content.strip()

        # Clean markdown-style formatting if present
        if text.startswith("```"):
            lines = text.split("\n")
            # remove first and last ``` lines
            if len(lines) > 2:
                text = "\n".join(lines[1:-1])
            if text.startswith("json"):
                text = text[4:].strip()

        try:
            feedback = json.loads(text)
            feedback["status"] = "success"
            feedback["frames_analyzed"] = len(valid_images)
            feedback["analysis_type"] = "visual_gpt"
            feedback["candidate_name"] = candidate_name
            return feedback
        except json.JSONDecodeError as je:
            print(f"JSON parse error: {je}")
            print(f"Raw response: {text[:500]}")
            return {
                "status": "parse_error",
                "raw_analysis": text,
                "frames_analyzed": len(valid_images),
            }

    except Exception as e:
        import traceback

        print(f"OpenAI Vision API error: {e}")
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Analysis failed: {str(e)[:200]}",
            "frames_received": len(valid_images),
        }


def analyze_attire_from_two_images(
    upper_body_b64: str,
    full_body_b64: str,
    candidate_name: Optional[str] = None,
    candidate_id: Optional[str] = None,
) -> dict:
    """
    Convenience wrapper for our usecase:
    - upper_body_b64: base64 string of upper-body selfie
    - full_body_b64: base64 string of full-body photo
    """
    frames = [upper_body_b64, full_body_b64]
    return analyze_frames_aggregated(frames, candidate_name, candidate_id)
