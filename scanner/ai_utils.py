import base64
import requests
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def analyze_chip_image_with_ai(image_path=None, image_file=None, raw_ocr_text=""):
    """
    Analyzes a chip image using OpenRouter Vision API to extract text and possible chip codes.
    Returns a dictionary of results. Never crashes and fails gracefully with fallback dictionary.
    """
    fallback_response = {
        "visible_text": "",
        "primary_chip_code": "",
        "possible_codes": [],
        "confidence": 0,
        "notes": "AI scan not available or failed"
    }

    # Fetch settings safely
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    model = getattr(settings, 'OPENROUTER_MODEL', 'your-vision-capable-openrouter-model')
    site_url = getattr(settings, 'OPENROUTER_SITE_URL', 'http://127.0.0.1:8000')
    app_name = getattr(settings, 'OPENROUTER_APP_NAME', 'ChipScanPH')

    if not api_key or api_key == 'your-openrouter-api-key-here':
        logger.warning("OpenRouter API key is missing or not configured. Skipping AI analysis.")
        fallback_response["notes"] = "OpenRouter API key is missing"
        return fallback_response

    try:
        # Get binary data of the image
        image_data = None
        if image_file:
            image_file.seek(0)
            image_data = image_file.read()
        elif image_path:
            with open(image_path, 'rb') as f:
                image_data = f.read()

        if not image_data:
            logger.error("No image data found for AI analysis.")
            return fallback_response

        # Determine MIME type (most uploads are png/jpg)
        mime_type = "image/png"
        file_name = getattr(image_file, 'name', '') or image_path or ''
        if file_name.lower().endswith(('.jpg', '.jpeg')):
            mime_type = "image/jpeg"

        base64_image = base64.b64encode(image_data).decode('utf-8')
        image_url = f"data:{mime_type};base64,{base64_image}"

        # Construct prompt focusing only on extraction
        system_instructions = (
            "You are a chip marking extraction assistant. Extract only visible chip text/codes from the image. "
            "Return valid JSON only. Do not return explanations, safety labels, markdown, or normal text. "
            "If unsure, return empty values. Do not invent chip information.\n"
            "Expected JSON only:\n"
            "{\n"
            "  \"visible_text\": \"\",\n"
            "  \"primary_chip_code\": \"\",\n"
            "  \"possible_codes\": [],\n"
            "  \"confidence\": 0,\n"
            "  \"notes\": \"\"\n"
            "}"
        )

        user_prompt = "Extract visible chip text/codes from the image according to the system instructions."
        if raw_ocr_text:
            user_prompt += f" Local OCR read hint: '{raw_ocr_text}'. Use it as a hint, but prioritize visual image markings."

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": site_url,
            "X-OpenRouter-Title": app_name
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_instructions
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ],
            "response_format": {"type": "json_object"}
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=25
        )

        if response.status_code == 404:
            logger.error("OpenRouter model not found or unavailable (404). Check OPENROUTER_MODEL in .env.")
            fallback_response["notes"] = "AI model unavailable. Check OPENROUTER_MODEL in .env. Using OCR-only matching."
            return fallback_response

        if response.status_code != 200:
            logger.error(f"OpenRouter returned status code {response.status_code}")
            fallback_response["notes"] = f"OpenRouter API error (status {response.status_code})"
            return fallback_response

        res_data = response.json()
        choices = res_data.get('choices', [])
        if not choices:
            logger.error("No choices returned from OpenRouter.")
            return fallback_response

        ai_message = choices[0].get('message', {}).get('content', '').strip()
        if not ai_message:
            logger.error("Empty message content from OpenRouter.")
            return fallback_response

        # Parse AI JSON response
        try:
            cleaned_message = ai_message
            if cleaned_message.startswith("```"):
                lines = cleaned_message.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned_message = "\n".join(lines).strip()
            
            parsed = json.loads(cleaned_message)
            
            # Ensure all keys are populated and correctly formatted
            output = {
                "ok": True,
                "visible_text": str(parsed.get("visible_text", "")),
                "primary_chip_code": str(parsed.get("primary_chip_code", "")),
                "possible_codes": [str(c) for c in parsed.get("possible_codes", []) if c],
                "confidence": int(parsed.get("confidence", 0)),
                "notes": str(parsed.get("notes", ""))
            }
            return output
        except Exception as parse_err:
            logger.error("Failed to parse AI response as valid JSON.")
            return {
                "ok": False,
                "ai_status": "AI returned invalid JSON. Using OCR-only matching.",
                "visible_text": "",
                "primary_chip_code": "",
                "possible_codes": [],
                "confidence": 0,
                "notes": "AI returned invalid response. Using OCR-only matching."
            }

    except Exception as e:
        logger.error(f"Error in analyze_chip_image_with_ai: {str(e)}")
        fallback_response["notes"] = f"Error: {str(e)}"
        return fallback_response
