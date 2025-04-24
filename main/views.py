import json, time
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.http import JsonResponse

is_free_flow = False 
guided_questions = [
    {
        "question": "Who are you shopping for?",
        "options": [
            "Mothers",
            "Your Baby",
            "Gift for a Baby",
            "Gift for a Mother",
            "Other"
        ],
    }
]

# Create your views here.
def home(request):
    return render(request, "main/home.html")

@require_POST
def set_choice(request):
    global is_free_flow
    try:
        data = json.loads(request.body)
        message = data.get("message", "")
        if message == "Free Flow":
            is_free_flow = True
            return JsonResponse({"success": True, "message": "Go Ahead, type what you want and I will try my best to help you!"})
        elif message == "Guided Questions":
            return JsonResponse({"success": True, "message":["Let's get started", guided_questions[0]["question"]], "options": guided_questions[0]["options"]})
        else:
            return JsonResponse({"success": False, "error": "Invalid choice"}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)


@require_POST
def chat(request):
    return JsonResponse({"message": "Chat response"})
