import json, time, os
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from openai import OpenAI


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
            "Rs. 0 - Rs. 2,500",
            "Rs. 2,500 - Rs. 10,000",
            "Rs. 10,000 - Rs. 25,000",
            "Rs. 25,000 - Rs. 50,000",
            "Rs. 50,000+",
            "No Budget",
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

SYSTEM_MESSAGE = {
    "role": "system",
    "content": """You are a smart, friendly, and highly capable shopping assistant for Kiddoz — a Sri Lankan e-commerce store specializing in products for babies, children (0 months to 12 years), and mothers. Your job is to help users find the best products through engaging, natural conversations that adapt to their needs.

    You work in two modes: 
    1. Guided mode: The user answers a sequence of structured questions (shopping target, budget, and product type). 
    2. Free-flow mode: The user types naturally, and you must extract key preferences from their input.

    You must generate only **one ideal product profile** per user query — not a list of products. You are not responsible for picking a real product. Instead, you describe what the ideal product should look like, based on user needs.


    In your recommendations, you MUST use the following inferred labels to ensure safety, relevance, and personalization:
    • age_suitability — one of: '0-5 months', '6-11 months', '1-1.5 years', '1.6-2 years', '3-5 years', '6-8 years', '9-12 years', 'mothers'
    • gender — 'Male', 'Female', or 'Unisex'
    • maximum_price — number (in Sri Lankan rupees) 
    • giftability — 0–10 scale — How suitable the item is as a gift
    • educational_value — 0–10 scale — Learning potential
    • durability — 0–10 scale — Build quality, materials, robustness
    • value_for_money — 0–10 scale — Affordability + usefulness
    • safety_perception — 0–10 scale — Inferred safety based on materials/reviews
    • seasonal_use — List of relevant months (1–12)
    • sensitivity_level — 0–10 scale — Suitability for delicate skin or materials
    • waterproof — Boolean — Whether the item is waterproof
    • portability — 0–10 scale — Ease of carrying
    • design_features — List of strings — e.g., "compact", "ergonomic"
    • package_quantity — Integer — Number of items in the package
    • usage_type — String — Description of the purpose (e.g., "cleaning babies")
    • material_origin — String — e.g., "organic cotton", "plastic" - if known, otherwise null
    • chemical_safety — String — e.g., "non-toxic"
    • size — String — e.g., "Large", "Medium", etc. (free-text only meant for diapers) - if known, otherwise null
    • weight_range — String — e.g., "0–6 kg" (free-text) - if known, otherwise null
    • count — Integer — Quantity or pack size - if known, otherwise null for any amount
    • color_options — List of strings — Available colors (e.g., ["Beige", "Pink"]) - if known, otherwise null for any colour
    • brand — String — Brand name if known, otherwise null


    🟢 When recommending products, always respond with a **list of product objects in JSON format**, which only includes all the above attributes for each item.
    ❗ Do not reply with plain text when recommending — only structured JSON output for products.

    🟠 When asking the user questions (such as during guided flow), ask **only one simple and direct question at a time**.

    🚫 Never suggest products that are unsafe, inappropriate for the user’s age group, or mismatched in gender. Use all available attributes to make safe, relevant suggestions.

    If the user says "start over" or "reset", politely reset the conversation.

    When responding:
    - If you send one message, use a plain string.
    - If you send multiple messages, respond with a list of strings in a single response.

    Your goal is to be helpful, safe, fun and direct — like a helpful friend guiding someone through a gift shop. 
    """
}


# Initialize OpenAI API client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  

# Create your views here.
def home(request):
    reset_chat(request)  # Reset chat when the home page is loaded
    # response = client.chat.completions.create(
    #     model="gpt-3.5-turbo",
    #     messages=[SYSTEM_MESSAGE],
    #     max_tokens=100,
    #     temperature=0.7,
    # )
    # print(response.choices[0].message)
    return render(request, "main/home.html")

@require_POST
def set_choice(request):
    try:
        data = json.loads(request.body)
        message = data.get("message", "")

        if message == "Free Flow":
            request.session['is_free_flow'] = True
            response = "Go Ahead, type what you want and I will try my best to help you!"
            add_message(request, "assistant", response)
            return JsonResponse({"success": True, "response": response})
        
        elif message == "Guided Questions":
            add_message(request, "assistant", "Let's get started")
            add_message(request, "assistant", GUIDED_QUESTIONS[0]["question"])
            return JsonResponse({"success": True, 
                                 "response":["Let's get started", GUIDED_QUESTIONS[0]["question"]], 
                                 "options": GUIDED_QUESTIONS[0]["options"]
                                })
        else:
            return HttpResponse(status=400, content="Invalid choice")
        
    except json.JSONDecodeError:
        return HttpResponse(status=400, content="Invalid JSON format")


@require_POST
def chat(request):
    time.sleep(1)  # Simulate processing time
    try:
        data = json.loads(request.body)
        message = data.get("message", "")
        add_message(request, "user", message)

        if message.lower() in ["reset", "clear", "restart", "start over", "new", "new chat", "new conversation"]:
            reset_chat(request)
            return JsonResponse({"success": True, "response": "Chat reset. You can start over."})
            
        is_free_flow = request.session.get("is_free_flow", False)
        if is_free_flow:
            # Handle free flow chat logic here
            response = {"success": True, "response": "This is a free flow response."}
        else:
            # Handle guided questions logic here
            response = handle_guided_questions(request, message)
        print(request.session["messages"], request.session['is_free_flow'], request.session["question_counter"])
        return JsonResponse(response)
    except json.JSONDecodeError:
        return HttpResponse(status=400, content="Invalid JSON format")
    
    
def handle_guided_questions(request, message):
    question_counter = request.session.get("question_counter", 0)

    if question_counter < len(GUIDED_QUESTIONS)-1:
        question_counter += 1
        response = GUIDED_QUESTIONS[question_counter]["question"]
        options = GUIDED_QUESTIONS[question_counter]["options"]
        add_message(request, "assistant", response)
        request.session["question_counter"] = question_counter
        return {"success": True, "response": response, "options": options}
    else:
        response = "Thank you for answering the questions!"
        add_message(request, "assistant", response)
        return {"success": True, "response": response}
    

def reset_chat(request):
    request.session["is_free_flow"] = False
    request.session["question_counter"] = 0
    request.session["messages"] = [SYSTEM_MESSAGE]


def add_message(request, role, content):
    messages = request.session.get("messages", [])
    messages.append({"role": role, "content": content})
    request.session["messages"] = messages

