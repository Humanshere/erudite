from django.db import connection
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.apps import apps
import os
import re
import requests
import json
import time
import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from accounts.models import User

logger = logging.getLogger(__name__)

GEMINI_URL = os.environ.get("GEMINI_API_URL")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

_SCHEMA_CACHE = None

def introspect_schema_text():
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is not None:
        return _SCHEMA_CACHE
    lines = []
    for model in apps.get_models():
        table = model._meta.db_table
        cols = [f"{f.column}:{f.get_internal_type()}" for f in model._meta.fields]
        lines.append(f"TABLE {table}: " + ", ".join(cols))
    _SCHEMA_CACHE = "\n".join(lines)
    return _SCHEMA_CACHE


def call_gemini(prompt_text):
    gemini_url = os.environ.get("GEMINI_API_URL") or GEMINI_URL
    gemini_key = os.environ.get("GEMINI_API_KEY") or GEMINI_KEY

    if not gemini_url:
        raise RuntimeError("GEMINI_API_URL not configured")

    body = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }
    headers = {"Content-Type": "application/json"}

    split = urlsplit(gemini_url)
    query_pairs = parse_qsl(split.query, keep_blank_values=True)
    has_url_key = any(k.lower() == "key" and bool(v) for k, v in query_pairs)

    if has_url_key:
        cleaned_query = split.query
    else:
        cleaned_query = urlencode([(k, v) for k, v in query_pairs if k.lower() != "key"])
        if gemini_key:
            headers["X-goog-api-key"] = gemini_key

    url = urlunsplit((split.scheme, split.netloc, split.path, cleaned_query, split.fragment))

    last_error = None
    data = None

    for attempt in range(3):
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            break
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            body_preview = exc.response.text[:600] if exc.response is not None else ""
            last_error = RuntimeError(f"Gemini HTTP {status_code}: {body_preview}")
            logger.warning("Gemini HTTP error %s on attempt %d", status_code, attempt + 1)
            if status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(0.6 * (attempt + 1))
                continue
            break
        except requests.RequestException as exc:
            last_error = RuntimeError(f"Gemini request failed: {exc}")
            logger.warning("Gemini request exception on attempt %d: %s", attempt + 1, exc)
            if attempt < 2:
                time.sleep(0.6 * (attempt + 1))
                continue
            break

    if data is None:
        raise last_error or RuntimeError("Gemini request failed after retries")

    candidates = data.get("candidates") if isinstance(data, dict) else None
    if isinstance(candidates, list):
        texts = []
        for cand in candidates:
            if not isinstance(cand, dict):
                continue
            content = cand.get("content")
            if isinstance(content, dict):
                parts = content.get("parts")
                if isinstance(parts, list):
                    for part in parts:
                        if isinstance(part, dict) and isinstance(part.get("text"), str):
                            texts.append(part["text"])
        if texts:
            return "\n".join(texts)

    logger.error("Unexpected Gemini response shape: %s", json.dumps(data)[:400])
    raise RuntimeError(f"Could not extract text from Gemini response: {json.dumps(data)[:300]}")


def extract_sql_from_text(text):
    if not isinstance(text, str):
        return ""

    # Strip markdown fences
    text = re.sub(r"```(?:sql)?", "", text, flags=re.IGNORECASE).replace("```", "").strip()

    # Match any SQL statement starting with a known keyword
    m = re.search(
        r"((?:SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TRUNCATE|WITH)\b[\s\S]+?);?\s*$",
        text, re.IGNORECASE
    )
    if m:
        return m.group(1).strip()

    # Fallback: first line that starts with a SQL keyword
    for line in text.splitlines():
        if re.match(r"\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TRUNCATE|WITH)\b", line, re.IGNORECASE):
            return line.strip()

    return ""


def tables_in_sql(sql):
    tbls = set()
    for m in re.finditer(
        r"(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+([\w.\"]+)", sql, re.IGNORECASE
    ):
        t = m.group(1).strip().strip('"').strip("'")
        if "." in t:
            t = t.split(".")[-1]
        tbls.add(t.lower())
    return tbls


class ChatbotQueryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        prompt = request.data.get("prompt", "")
        if not prompt:
            return JsonResponse({"error": "prompt is required"}, status=400)

        if len(prompt) > 1000:
            return JsonResponse({"error": "prompt too long (max 1000 characters)"}, status=400)

        schema_text = introspect_schema_text()
        role = request.user.role if hasattr(request.user, "role") else User.Role.STUDENT

        # Gemini must return either a valid SQL query or the exact sentinel INVALID QUESTION.
        # No prose, no explanation, no markdown — nothing else is acceptable.
        system_prompt = (
            "You are a database assistant. Given the database schema and a user question, "
            "you must respond with EXACTLY one of two things:\n"
            "  1. A single valid SQL query ending with a semicolon, with no extra text, "
            "no markdown, no explanation — raw SQL only.\n"
            "  2. The exact string INVALID QUESTION (all caps, no punctuation) if the input "
            "is not a database question or cannot be expressed as an SQL query.\n"
            "Do not output anything else under any circumstances.\n\n"
        )

        if role == User.Role.ADMIN:
            role_note = "User role: admin. All tables are allowed."
        elif role == User.Role.FACULTY:
            role_note = (
                "User role: faculty. Allowed tables: tables whose name contains "
                "'academics', 'attendance', 'courses', or 'enroll'. "
                "Do not access accounts_user sensitive fields."
            )
        else:
            role_note = (
                f"User role: student. You may only query:\n"
                f"  - accounts_user WHERE id = {request.user.id} (this user only)\n"
                f"  - attendance_attendancerecord WHERE student_id = {request.user.id}\n"
                f"Any query accessing other users' data must instead output: INVALID QUESTION"
            )

        full_prompt = "\n".join([
            system_prompt,
            role_note,
            "SCHEMA:\n" + schema_text,
            "QUESTION:\n" + prompt,
            "ANSWER (SQL or INVALID QUESTION):",
        ])

        try:
            model_text = call_gemini(full_prompt)
        except Exception as e:
            msg = str(e)
            logger.error("Gemini call failed: %s", msg)
            http_status = 502
            m = re.search(r"Gemini HTTP\s+(\d{3})", msg)
            if m:
                http_status = int(m.group(1))
            return JsonResponse({"error": "upstream generation failed", "detail": msg}, status=http_status)

        # Check for the sentinel before any SQL extraction.
        if model_text.strip().upper() == "INVALID QUESTION":
            logger.info("Gemini returned INVALID QUESTION for prompt: %s", prompt[:200])
            return JsonResponse({"error": "INVALID QUESTION"}, status=400)

        sql = extract_sql_from_text(model_text)
        if not sql:
            return JsonResponse({"error": "model did not return a valid SQL query", "raw": model_text}, status=400)

        referenced = tables_in_sql(sql)
        all_tables = {m._meta.db_table.lower() for m in apps.get_models()}

        def is_allowed(tbl):
            tbl = tbl.lower()
            if role == User.Role.ADMIN:
                return True
            if role == User.Role.FACULTY:
                return True
            if role == User.Role.STUDENT:
                return tbl in {"accounts_user", "attendance_attendancerecord"}
            return False

        for t in referenced:
            if t not in all_tables:
                return JsonResponse({"error": "referenced unknown table", "table": t, "sql": sql}, status=400)
            if not is_allowed(t):
                return JsonResponse({"error": "access to table not allowed for role", "table": t, "role": role}, status=403)

        # Student scope check
        if role == User.Role.STUDENT and "accounts_user" in referenced:
            user_id = str(request.user.id)
            user_email = request.user.email
            scoped_by_id = re.search(
                r"\bwhere\b[\s\S]+\b(id|user_id)\b\s*=\s*" + re.escape(user_id),
                sql, re.IGNORECASE
            )
            scoped_by_email = re.search(re.escape(user_email), sql, re.IGNORECASE)
            if not scoped_by_id and not scoped_by_email:
                return JsonResponse({"error": "student queries must be scoped to the requesting user"}, status=403)

        ROW_LIMIT = 200
        if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
            sql = sql.rstrip(";").rstrip() + f" LIMIT {ROW_LIMIT}"

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                cols = [col[0] for col in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
        except Exception as e:
            logger.error("Query execution failed: %s | SQL: %s", e, sql[:300])
            return JsonResponse({"error": "query execution failed", "detail": str(e), "sql": sql}, status=400)

        return JsonResponse({"query": sql, "columns": cols, "rows": rows})