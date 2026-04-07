import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
MODEL_EMBED = ('MODEL_EMBED', 'all-minilm:latest')
SIM_THRESHOLD = os.getenv('SIM_THRESHOLD', 0.8)

UPLOAD_FOLDER = './uploads/'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'md', 'csv', 'json'}