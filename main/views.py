import json, time, os
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from openai import OpenAI
from .models import Product


GUIDED_QUESTIONS = [
    {
        "question": "Who are you shopping for?",
        "options": [
            "Mothers",
            "My Baby",
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
    "content": """You are a smart, friendly, and highly capable shopping assistant for Kiddoz — a Sri Lankan e-commerce store specializing in products for babies, children (0 months to 12 years), mothers and all ages. Your job is to help users find the best products through engaging, natural conversations that adapt to their needs.

    You work in two modes: 
    1. Guided mode: The user answers a sequence of structured questions (shopping target, budget, and product type). 
    2. Free-flow mode: The user types naturally, and you must extract key preferences from their input.

    You must generate only **one ideal product profile** per user query — not a list of products. You are not responsible for picking a real product. Instead, you describe what the ideal product should look like, based on user needs.

    🛑 Important Rules for Guided Mode:
    - You do NOT need to ask "Who are you shopping for?" or "What is your budget?".
    - You must only ask: **"Which category of products are you interested in?"**
    - Provide the following available categories as options:
    - Clothing
    - Toys
    - Diapers
    - Maternity
    - Skin Care
    - Schooling
    - Gear
    - Activity
    - When offering these multiple-choice options, respond with a JSON object named **`options`** with whatever options are appropriate.
    - If there is no budget given by the user, provide the budget as Rs. 9,000,000

    In your recommendations, you MUST use the following inferred labels to ensure safety, relevance, and personalization:
    • age_suitability — one of: '0-5 months', '6-11 months', '1-1.5 years', '1.6-2 years', '3-5 years', '6-8 years', '9-12 years', 'mothers', 'all ages'
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


    🟢 When recommending products, always respond with a **list of attribute objects in JSON format**, which only includes all the above attributes for each item with the title as "results". I will show several products to the user - make it plural. 

    ❗ Do not reply with plain text when recommending — only structured JSON output for products.

    🟠 When asking the user questions (such as during guided flow), ask **only one simple and direct question at a time**.

    🚫 Never suggest products that are unsafe, inappropriate for the user’s age group, or mismatched in gender. Use all available attributes to make safe, relevant suggestions.

    If the user says "start over" or "reset", politely reset the conversation.

    When responding:
    - Only respond in a json format
    - If you send one message, use a plain string with the title "response". 
    - If you send multiple messages, respond with a list of strings in a single response with the title "response"
    - If there are restricted choices you expect the user to respond to have a list of strings with the title "options". Always have an option called "start over".
    - When sending results always send it in a JSON format with the title "results". Always 
    - Every message MUST have a "response".

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
            response = handle_free_flow(request, message)
        else:
            # Handle guided questions logic here
            response = handle_guided_questions(request, message)
        # print(request.session["messages"], request.session['is_free_flow'], request.session["question_counter"])
        return JsonResponse(response)
    except json.JSONDecodeError:
        return HttpResponse(status=400, content="Invalid JSON format")

    
def handle_free_flow(request, message):
    response = {
        "results": {
            "age_suitability": "3-5 years",
            "gender": "Male",
            "maximum_price": 9000000,
            "giftability": 10,
            "educational_value": 7,
            "durability": 9,
            "value_for_money": 8,
            "safety_perception": 9,
            "seasonal_use": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
            ],
            "sensitivity_level": 4,
            "waterproof": True,
            "portability": 7,
            "design_features": [
                "colorful",
                "easy-grip",
                "child-safe edges",
                "lightweight"
            ],
            "package_quantity": 1,
            "usage_type": "active play and physical development",
            "material_origin": "high-quality plastic",
            "chemical_safety": "non-toxic",
            "size": None,
            "weight_range": None,
            "count": None,
            "color_options": [
                "Blue",
                "Red",
                "Green"
            ],
            "brand": None
        },
            "response": "Here is an ideal activity gift for your nephew!"
    }
    
    output = {
        "success": True,
        "response": response.get("response"),
    }

    add_message(request, "assistant", response.get("response") , response.get("results"))

    # Need to query for products with the above attributes
    if response.get("results"):
        # Query the database for products matching the attributes
        products = query_products(response.get("results"))
        output["results"] = products

    if response.get("options"):
        output["output"] = response.get("output")
    
    return output
    
    
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
    
    
def query_products(attributes):
    # This function should query the database for products matching the given attributes
    # For now, we will just return a placeholder response
    products = Product.objects.filter(
        gender=attributes.get("gender")
    ).values('url', 'name', 'current_price', 'image_urls')[:5]
    products = list(products)  # Convert QuerySet to list for JSON serialization

    for product in products:
        # Make sure image_urls is a list
        image_list = []
        if isinstance(product['image_urls'], str):
            try:
                image_list = json.loads(product['image_urls'])
            except json.JSONDecodeError:
                image_list = []
        elif isinstance(product['image_urls'], list):
            image_list = product['image_urls']

        # Add new key 'image' with the first image if available
        product['image'] = image_list[0] if image_list else "/static/images/logo.png"

    print(products)
    return products  # Return the first 5 products for demonstration


def reset_chat(request):
    request.session["is_free_flow"] = False
    request.session["question_counter"] = 0
    request.session["messages"] = [SYSTEM_MESSAGE]


def add_message(request, role, content, results=None):
    messages = request.session.get("messages", [])
    messages.append({"role": role, "content": content})
    if results:
        messages.append({"role": "assistant", "content": results})
    request.session["messages"] = messages

