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
    prompt = f"""
You are analyzing {len(valid_images)} photos of {candidate_display} taken before an interview.
One is usually an upper-body selfie and one is a full-body photo.

Your job is to evaluate if the candidate is visually ready for a **formal job interview**.

⚙️ INSTRUCTIONS (VERY IMPORTANT):
- Use **simple, clear language**.
- Use **bullet points** in the arrays.
- Each point should be **10–18 words**, short and focused.
- Be **honest but polite** and constructive.
- Focus specifically on: facial grooming, clothing, clothing style/formality, and shoes.

Analyze and return feedback under these EXACT categories:

1. FACIAL GROOMING
   - Hair neatness, beard/moustache trimming, face cleanliness, overall grooming of face and head.

2. CLOTHING & APPEARANCE
   - Type of clothes (shirt, t-shirt, blazer, etc.), neatness, wrinkles, color choices, overall impression.

3. CLOTHING STYLE & FORMALITY
   - How formal the outfit looks (casual, semi-formal, formal), suitability for a professional interview.

4. FOOTWEAR / SHOES
   - Type of shoes (formal shoes, sneakers, sandals, slippers, no shoes visible), cleanliness, appropriateness.

5. OVERALL SUMMARY & RECOMMENDATION
   - Short summary sentence and recommended level:
     - "proper_interview_attire" (good for interview)
     - "needs_minor_improvement"
     - "not_appropriate_for_interview"

Return ONLY valid JSON with these exact keys:

{{
  "facial_grooming": ["• point 1", "• point 2", "..."],
  "clothing_appearance": ["• point 1", "• point 2", "..."],
  "clothing_style_formality": ["• point 1", "• point 2", "..."],
  "footwear_shoes": ["• point 1", "• point 2", "..."],
  "overall_summary": "one short sentence summarizing readiness",
  "attire_recommendation": "proper_interview_attire | needs_minor_improvement | not_appropriate_for_interview"
}}
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
