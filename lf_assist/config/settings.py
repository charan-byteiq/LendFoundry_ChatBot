# config/settings.py
import os

QDRANT_URL = "https://dbc589fa-30ef-4b49-bf73-f9c7a19fef5f.us-east4-0.gcp.cloud.qdrant.io"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.-3-pdidG0Ej8pyRTAQGKYLXnhLxcbbbqenbF9mlQJdw"
QDRANT_COLLECTION = "lms_chunks"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"       
#2.5 flash

