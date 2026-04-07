from ollama import Client

from config import OLLAMA_BASE_URL

ollama_client = Client(host=OLLAMA_BASE_URL)