import os
from pypdf import PdfReader
import json
import csv
import re
from flask import session as flask_session
import uuid

from config import ALLOWED_EXTENSIONS
from ollama_client import ollama_client



def message_summary(message, llm='deepseek-r1'):
    system_instruction = 'Describe the following conversation using only 3 keywords separated by coma'
    summary = ollama_client.generate(
        model=llm,
        prompt=system_instruction + '\n' + message
    )
    return summary['response']


def is_allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def dispatcher(file):
    extension = os.path.splitext(file)[1].lower()
    if extension == '.pdf':
        return convert_pdf_to_text(file)
    elif extension == '.json':
        return convert_json_to_text(file)
    elif extension == '.md':
        return convert_md_to_text(file)
    elif extension == '.csv':
        return convert_csv_to_text(file)
    elif extension == '.txt':
        with open(file, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return None


def convert_pdf_to_text(file):
    reader = PdfReader(file)
    page = reader.pages
    text = [page.extract_text() for page in reader.pages if page.extract_text()]
    return "\n".join(text)


def convert_json_to_text(file):
    with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    return json.dumps(data, indent=2)


def convert_md_to_text(file):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r'#+', '', content)  # headers
    content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # bold
    content = re.sub(r'\*(.*?)\*', r'\1', content)  # italics
    content = re.sub(r'`(.*?)`', r'\1', content)  # inline code
    return content


def convert_csv_to_text(file):
    rows = []
    with open(file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            if i > 1000:
                break
            else:
                row_text = ', '.join(f'{k}: {v}' for k, v in row.items())
                rows.append(f'Row {i + 1}: {row_text}')

    return '\n'.join(rows)
