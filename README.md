# Kiddoz Chatbot Project 🤖

This is a Django-based AI-powered chatbot project developed for Kiddoz.lk - an e-commerce platform specialising in baby and children's products. The chatbot uses OpenAI's API to infer product attributes and make personalised recommendations.

## 🚀 Features

- Django 5.2 project running Python 3.12+
- Vector search using `pgvector` and PostgreSQL
- OpenAI integration for intelligent product label inference
- Designed for VPS or local VM deployment
- Modular logging, scraping, and chatbot components


## 🛠️ Requirements

- Python 3.10 or higher
- PostgreSQL 13 or later (with `pgvector` extension)
- OpenAI API Key


## 🐍 Setting Up (Step-by-Step)

### 1. Clone the Repository

```bash
git clone https://github.com/Najaaz/chatbot.git
cd chatbot
```

### 2. Set Up a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## 🔑 Configure Environment Variables

Add your OpenAI API key to the environment:

```bash
export OPENAI_API_KEY=your-openai-key-here
```
You can also place this in your shell config (e.g. `.bashrc` or `.zshrc`) for persistence.


## 🛢️ PostgreSQL Setup

### 1. Ensure PostgreSQL is installed:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

### 2. Log in as the postgres user and create your DB and user:
```bash
sudo -u postgres psql
```

```sql
CREATE USER admin WITH PASSWORD 'admin';
CREATE DATABASE kiddoz_db OWNER admin;
ALTER USER admin CREATEDB;
\q
```

### 3.Enable the `pgvector` extension:

```bash
psql -U admin -d kiddoz_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 4. Update settings.py if needed:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'kiddoz_db',
        'USER': 'admin',
        'PASSWORD': 'admin',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 📦 Data Pipeline: Scraping + GPT Inference
Before using the chatbot, the product database must be populated by running the following scripts in this order:

### 1. `webscrape_all_products.py`
Scrapes all product links from Kiddoz.lk, saving them for detailed scraping later.
```bash
python manage.py webscrape_all_products
```

### 2. `webscrape_products.py`
Visits each product link and extracts structured product data (title, price, description, images, etc.), saving them to your database.\
**⚠️ Note: This scraping has been conducted with full consent from the client (Kiddoz.lk) for research and development purposes.**
```bash
python manage.py webscrape_products
```

### 3. `infer_attributes.py`
Sends product descriptions to OpenAI’s API to infer deeper attributes (e.g., giftability, educational value, waterproofing) and updates your product records with those values using GPT-generated reasoning.
```bash
python manage.py infer_attributes
```



## ⚙️ Running the Project
Run migrations and start the development server:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

Visit http://127.0.0.1:8000/ to view the chatbot in your browser.


## 📂 Folder Structure Overview

```bash
chatbot/
├── kiddoz/ # Django project settings (WSGI, URLs, settings.py)
├── main/ # Core app: scraping, chatbot, models, views
│ ├── management/ # Custom management commands (web scraping, inference)
│ ├── migrations/ # Django model migrations
│ ├── static/ # Bootstrap / JS / custom assets
│ ├── templates/ # HTML templates
│ ├── urls.py
│ └── views.py
├── logs/ # Custom log directory
├── media/ # Uploaded media (images etc.)
├── manage.py # Django entry point
├── db.sqlite3 # Local DB fallback (can ignore if using Postgres)
├── requirements.txt # Python dependencies
└── README.md # This file
```

## 👤 Author

**Created by:** Najaaz Nabhan \
3rd Year Computer Science with AI \
University Of Sheffield 

**Supervised by:** Tahsinur Khan

