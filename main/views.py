import json, time, os, unicodedata
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Q
from pgvector.django import CosineDistance

from openai import OpenAI
from .models import Product


GUIDED_QUESTIONS = [
    {
        "question": "Who are you shopping for?",
        "options": [
            "Mothers",
            "My Baby",
            "My Child",
            "Gift for a Child",
            "Gift for a Baby",
            "Gift for a Mother",
            "Other",
            "Start Over"
        ],
    },
    # {
    #     "question": "What is your budget?",
    #     "options": [
    #         "< Rs. 2,500",
    #         "< Rs. 10,000",
    #         "< Rs. 25,000",
    #         "< Rs. 50,000",
    #         "Rs. 50,000+",
    #         "Start Over"
    #     ],
    # },
    # {
    #     "question": "What type of product are you looking for?",
    #     "options": [
    #         "Clothing",
    #         "Toys",
    #         "Diapers",
    #         "Accessories",
    #         "Other",
    #         "Start Over"
    #     ],
    # }
]

SYSTEM_MESSAGE = {
    "role": "system",
    "content": """You are a smart, friendly, and highly capable shopping assistant for Kiddoz — a Sri Lankan e-commerce store specializing in products for babies, children (0 months to 12 years), mothers, and all ages. Your job is to help users find the best products through engaging, natural conversations that adapt to their needs.

        ⚠️ ABSOLUTE FORMAT RULES — NEVER BREAK THESE:
            - NEVER output plain text, markdown, or prose — ONLY a single valid JSON object per reply.
            - NEVER use ```json code blocks.
            - Every reply must be a single JSON object that includes at least the "response" field.
            - NO introductory text, NO explanation — just the JSON.
            - If a valid JSON object cannot be created (e.g., due to conflicting input), respond with a JSON object containing only a "response" AND helpful options.


        You work in two modes: 
            1. Guided mode: The user answers a sequence of structured questions (shopping target, budget, and product type). 
            2. Free-flow mode: The user types naturally, and you must extract key preferences from their input.

        You must generate only **one ideal product profile** per user query — not a list of products. You are not responsible for picking a real product. Instead, you describe what the ideal product should look like, based on user needs.

        🛑 Important Rules:
            - You must **always respond using valid JSON format**.
            - You must **never output plain text, prose, or unstructured sentences** outside JSON format.
            - Each and every reply must be a **single JSON object**.
            - Every reply must have at least the `"response"` field.
        
        Formatting Rules:
            - Always send a single valid JSON object.
            - Never use ```json code blocks.
            - Never send free-text outside JSON.
            - Always include "response" even when sending "options" or "results".
            - If the user says "start over" or "reset," politely reset and ask again inside a JSON structure.
            - Your tone should always be helpful, warm, direct, and professional — but your response must be structured and only in JSON.
            - Ensure all output uses plain ASCII characters. **Do not use Unicode** punctuation

        In Guided mode:
            - Do NOT ask about "Who are you shopping for?"
            - Provide the following categories (You may use some or all of them depending on the context) IN A JSON OBJECT called "options":
                - Clothing
                - Toys
                - Diapers
                - Maternity
                - Skin Care
                - Schooling
                - Gear
                - Accessories
                - Activity
            - REMEMBER that "Diapers" should NOT be shown as an option if the user is shopping for a mother or if its a gift for a baby
            - ✅ You must ALWAYS send multiple-choice prompts as a single JSON object containing both "response" and "options".
            - ❌ Do NOT send the question as plain text. The entire reply must be a valid JSON object — even in guided mode.
            - If you need more information, ask the user with a restricted set of options as much as possible.
            - When showing price options, ALWAYS INCLUDE THE CURRENCY (Rs.) in the options.

            
        Example JSON:
            {
                "response": "Which category of products are you interested in?",
                "options": ["Clothing", "Toys", "Diapers", "Maternity", "Skin Care", "Schooling", "Gear", "Activity", "Start Over"]
            }

        Product Recommendation Rules:
            - After gathering enough information, immediately respond with the ideal product profile.
            - The output object must include both:
                - "response": A short message confirming the product profile in simple english.
                - "results": The ideal product attribute object.
            - If the user doesn't have a budget in free-flow mode, assume the maximum_price of Rs. 1,000,000.
            - If you fail to structure your response inside a single JSON object with both "response" and "results", the output will be invalid. 
            - You must never separate your responses into multiple pieces.
            - If the user mentions a brand (e.g., "Barbie" or "Lego"), include it as the "brand" field in the product profile if it's relevant.


        Each product must include:
            • age_suitability — one of: '0-5 months', '6-11 months', '1-1.5 years', '1.6-2 years', '3-5 years', '6-8 years', '9-12 years', 'mothers', 'all ages'
            • gender — 'male', 'female', or 'unisex'
            • maximum_price — number (in Sri Lankan rupees) 
            • giftability — 0-10 scale — How suitable the item is as a gift
            • educational_value — 0-10 scale — Learning potential
            • durability — 0-10 scale — Build quality, materials, robustness
            • value_for_money — 0-10 scale — Affordability + usefulness
            • safety_perception — 0-10 scale — Inferred safety based on materials/reviews
            • seasonal_use — List of integers (1-12) representing months, or empty list if not seasonal
            • sensitivity_level — 0-10 scale — Suitability for delicate skin or materials
            • waterproof — Boolean — Whether the item is waterproof
            • portability — 0-10 scale — Ease of carrying
            • design_features — List of strings — e.g., "compact", "ergonomic"
            • package_quantity — Integer — Number of items in the package
            • usage_type — String — Description of the purpose (e.g., "cleaning babies")
            • material_origin — String — e.g., "organic cotton", "plastic" - if known, otherwise null
            • chemical_safety — String — e.g., "non-toxic"
            • size — String — e.g., "Large", "Medium", etc. (free-text only meant for diapers) - if known, otherwise null
            • weight_range — String — e.g., "0-6 kg" (free-text) - if known, otherwise null
            • count — Integer — Quantity or pack size - if known, otherwise null for any amount
            • color_options — List of strings — Available colors (e.g., ["Beige", "Pink"]) - if known, otherwise null for any colour
            • brand — String — Brand name if mentioned by the user (e.g., "Barbie"), otherwise null
            • categories — List of strings — e.g., ["Diapering", "Bags"] - if known, otherwise null
    """
}


# Initialize OpenAI API client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))   

# Create your views here.
def home(request):
    reset_chat(request)  # Reset chat when the home page is loaded
    return render(request, "main/home.html")

def privacy_policy(request):
    """
    Render the privacy policy page.
    """
    return render(request, "main/privacy_policy.html")

@require_POST
def set_choice(request):
    try:
        data = json.loads(request.body)
        message = data.get("message", "")

        add_message(request, "assistant", "Hi there! How would you like the conversation to go?")        

        if message == "Free Flow":
            add_message(request, "user", "Free Flow")
            request.session['is_free_flow'] = True
            response = "Go Ahead, type what you want and I will try my best to help you!"
            add_message(request, "assistant", response)
            return JsonResponse({"success": True, "response": response})
        
        elif message == "Guided Questions":
            add_message(request, "user", "Guided Questions")
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
        return JsonResponse(response)
    except json.JSONDecodeError:
        return HttpResponse(status=400, content="Invalid JSON format")

    
def handle_free_flow(request, message):

    response = gpt_response(request)
    output = {
        "success": True,
        "response": response.get("response"),
    }

    add_message(request, "assistant", response.get("response") , response.get("results"))

    # Need to query for products with the above attributes
    if response.get("results"):
        # Query the database for products matching the attributes
        products = query_products(response.get("results"))[:10]
        output["results"] = products

    if response.get("options"):
        output["options"] = response.get("options")
    
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
        response = gpt_response(request)
        add_message(request, "assistant", response.get("response") , response.get("results"))
        output = {
            "success": True,
            "response": response.get("response"),
        }

        # Need to query for products with the above attributes
        if response.get("results"):
            # Query the database for products matching the attributes
            products = query_products(response.get("results"))[:10]
            output["results"] = products

        if response.get("options"):
            output["options"] = response.get("options")

        return output
    

def query_products(attributes):
    """
    Query the database for products matching the given attributes.
    @param attributes: Dictionary containing product attributes.
    @return: List of products matching the attributes.
    """
    if type(attributes) is list:
        attributes = attributes[0]
    

    text = f"""giftability {bucket_score(attributes['giftability'])}; educational_value {bucket_score(attributes['educational_value'])}; 
        durability {bucket_score(attributes['durability'])}; value_for_money {bucket_score(attributes['value_for_money'])}; 
        safety_perception {bucket_score(attributes['safety_perception'])}; seasonal_use {attributes['seasonal_use']}; 
        sensitivity_level {bucket_score(attributes['sensitivity_level'])}; waterproof {attributes['waterproof']}; 
        portability {bucket_score(attributes['portability'])}; design_features {attributes['design_features']}; 
        package_quantity {attributes['package_quantity']}; usage_type {attributes['usage_type']};
        material_origin {attributes['material_origin']}; chemical_safety {attributes['chemical_safety']}; size {attributes['size']}; 
        weight_range {attributes['weight_range']}; count {attributes['count']}; brand {attributes['brand']};
        color_availability {attributes['color_options']}; categories {attributes['categories']}
    """

    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small",
        dimensions=1536
    ) 

    embedding_data = response.data[0].embedding
    products = Product.objects.active().annotate(
        similarity=CosineDistance("embedding", embedding_data)
    ).filter(
        current_price__lte=attributes['maximum_price'],
        age_suitability=attributes['age_suitability'],
    ).filter(
        Q(gender="unisex") | Q(gender=attributes['gender'])
    ).order_by("similarity").values('url', 'name', 'current_price', 'image_urls').distinct()[:8]

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
        # Remove the original 'image_urls' key
        del product['image_urls']

    print("PRODUCTS RECOMMENDATION:\n",products, "\n")
    return products  # Return the first 5 products for demonstration

def gpt_response(request):
    print(request.session["messages"][1:])
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=request.session["messages"],
            max_tokens=2048,
            # temperature=0.8,
        )
        content = response.choices[0].message
        # Now parse it as JSON
        # print("\nGPT RAW RESPONSE:\n", content, "\n")
        try:
            parsed_response = json.loads(content.content)
        except json.JSONDecodeError:
            # If GPT didn't send perfect JSON (very rare with your system message now), handle the error
            print("GPT response is not valid JSON. Attempting to parse as a string.")

            parsed_response = ai_jsonify_string(content.content)

        # print("GPT RESPONSE:\n", content, "\n")
        print("\nGPT JSON RESPONSE:\n", parsed_response, "\n")
        return parsed_response
    except Exception as e:
        print(f"Error: {e}")
        return "Sorry, I couldn't process your request."


def reset_chat(request):
    request.session["is_free_flow"] = False
    request.session["question_counter"] = 0
    request.session["messages"] = [SYSTEM_MESSAGE]


def add_message(request, role, content, results=None):
    messages = request.session.get("messages", [])
    messages.append({"role": role, "content": content})
    if results:
        messages.append({"role": "assistant", "content": json.dumps(results)})
    request.session["messages"] = messages

def normalise_hyphenated_string(string):
    """
    Normalises a hyphenated string by replacing hyphens with dashes and removing spaces.
    """
    return unicodedata.normalize('NFKD', string).replace("–", "-").strip().lower()

def ai_jsonify_string(string):
    """
    Converts a string to a JSON-compatible by asking OpenAI to do so.
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "user",
                "content": f"""Convert this string to a JSON-compatible format which can be run in python. 
                        Free text has the label 'response', list of choices has the label 'options' and product attributes has the label 'results'.
                        Nothing else should be included in the JSON object: {string}
                    """
            }
        ],
        max_tokens=500,
    )
    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return content

def bucket_score(x: float) -> str:
    return (
        "very low"  if x <= 2 else
        "low"       if x <= 4 else
        "medium"    if x <= 6 else
        "high"      if x <= 8 else
        "very high"
    )