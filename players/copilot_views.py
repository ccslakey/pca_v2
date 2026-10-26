"""Prototype endpoints for the Compare-page chat. Throwaway code."""
from __future__ import annotations

import json

from django.http import HttpRequest, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .copilot import COPILOT_TOOLS, SYSTEM, run_agui, run_copilot_tool, validate_call


class _CopilotThrottle(ScopedRateThrottle):
    scope = "copilot"


@api_view(["GET"])
def copilot_tools(request: Request) -> Response:
    return Response({"tools": COPILOT_TOOLS, "system": SYSTEM})


@api_view(["POST"])
@throttle_classes([_CopilotThrottle])
def copilot_tool(request: Request) -> Response:
    name, args = request.data.get("name"), request.data.get("args", {})
    err = validate_call(name, args)
    if err:
        return Response({"error": err}, status=400)
    return Response(run_copilot_tool(name, args, {}))


@csrf_exempt
def copilot_agui(request: HttpRequest) -> StreamingHttpResponse | JsonResponse:
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    try:
        body = json.loads(request.body)
    except ValueError:
        return JsonResponse({"error": "invalid JSON"}, status=400)
    if not isinstance(body, dict) or not isinstance(body.get("messages", []), list):
        return JsonResponse({"error": "expected an AG-UI RunAgentInput"}, status=400)
    resp = StreamingHttpResponse(run_agui(body), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp
