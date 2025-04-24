import json, time
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.http import JsonResponse

is_free_flow = False 
GUIDED_QUESTIONS = [
    {
        "question": "Who are you shopping for?",
        "options": [
            "Mothers",
            "Your Baby",
            "Gift for a Baby",
            "Gift for a Mother",
            "Other",
            "Start Over"
        ],
    },
    {
        "question": "What is your budget?",
        "options": [
            "$0 - $50",
            "$50 - $100",
            "$100 - $200",
            "$200+",
            "Start Over"
        ],
    },
    {
        "question": "What type of product are you looking for?",
        "options": [
            "Clothing",
            "Toys",
            "Diapers",
            "Accessories",
            "Other",
            "Start Over"
        ],
    }
]
question_counter = 0

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
]

# Create your views here.
def home(request):
    reset_chat()  # Reset chat when the home page is loaded
    return render(request, "main/home.html")

@require_POST
def set_choice(request):
    global is_free_flow, messages, question_counter
    try:
        print(messages, is_free_flow, question_counter)
        data = json.loads(request.body)
        message = data.get("message", "")
        if message == "Free Flow":
            is_free_flow = True
            response = "Go Ahead, type what you want and I will try my best to help you!"
            add_message("assistant", response)
            return JsonResponse({"success": True, "response": response})
        
        elif message == "Guided Questions":
            add_message("assistant", "Let's get started")
            add_message("assistant", GUIDED_QUESTIONS[question_counter]["question"])
            return JsonResponse({"success": True, 
                                 "response":["Let's get started", GUIDED_QUESTIONS[question_counter]["question"]], 
                                 "options": GUIDED_QUESTIONS[question_counter]["options"]
                                })
        else:
            return HttpResponse(status=400, content="Invalid choice")
        
    except json.JSONDecodeError:
        return HttpResponse(status=400, content="Invalid JSON format")


@require_POST
def chat(request):
    global is_free_flow, messages, question_counter
    time.sleep(1)  # Simulate processing time
    try:
        data = json.loads(request.body)
        message = data.get("message", "")
        add_message("user", message)
        if message.lower() in ["reset", "clear", "restart", "start over", "new", "new chat", "new conversation"]:
            reset_chat()
            return JsonResponse({"success": True, "response": "Chat reset. You can start over."})

        if is_free_flow:
            # Handle free flow chat logic here
            response = {"success": True, "response": "This is a free flow response."}
        else:
            # Handle guided questions logic here
            response = handle_guided_questions(message)
        print(messages, is_free_flow, question_counter)
        return JsonResponse(response)
    except json.JSONDecodeError:
        return HttpResponse(status=400, content="Invalid JSON format")
    
    
def handle_guided_questions(message):
    global GUIDED_QUESTIONS, question_counter
    if question_counter < len(GUIDED_QUESTIONS)-1:
        question_counter += 1
        response = GUIDED_QUESTIONS[question_counter]["question"]
        options = GUIDED_QUESTIONS[question_counter]["options"]
        add_message("assistant", response)
        return {"success": True, "response": response, "options": options}
    else:
        response = "Thank you for answering the questions!"
        add_message("assistant", response)
        return {"success": True, "response": response}
    

def reset_chat():
    global is_free_flow, messages, question_counter

    question_counter = 0
    is_free_flow = False
    messages = [messages[0]]  # Keep the system message only

def add_message(role, content):
    global messages
    messages.append({"role": role, "content": content})

