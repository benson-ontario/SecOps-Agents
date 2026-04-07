import os
import shutil
import uuid
import json
from werkzeug.utils import secure_filename
from wtforms import FileField, SubmitField
from flask_wtf import FlaskForm
from flask import (
    Flask, render_template, request,
    jsonify, Response, stream_with_context,
    session as flask_session)

from preprocessing import  retrieve_context, ingest_documents, purge_session
from utils import is_allowed_file, message_summary
from ollama_client import ollama_client
from config import SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Dictionary to store session ids per user (for demo) imitates database
session_messages: dict[str, list] = {}

class UploadFileForm(FlaskForm):
    file = FileField('File')
    submit = SubmitField('Upload')


def get_memory(session_id):
    """Return the message history list for a session. If no session exist, create it."""
    if session_id not in session_messages:
        session_messages[session_id] = []
    return session_messages[session_id]


@app.before_request
def ensure_session():
    """Assign a session ID if the cookie is missing or
       if the session ID is no longer present in in-memory store (after server restart).
    """
    if 'session_id' not in flask_session:
        new_session_id = str(uuid.uuid4())
        flask_session['session_id'] = new_session_id


@app.route('/', methods=['GET', 'POST'])
def index():
    print('current session', flask_session['session_id'])
    form = UploadFileForm()
    print('form is created')
#    file = is_allowed_file(form.file)
    print(form)
    if form.validate_on_submit():
        file = form.file.data

        if not is_allowed_file(file.filename):
            print('File type is not allowed')
            return render_template('index.html', form=form)
        
        save_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            app.config['UPLOAD_FOLDER'],
            flask_session['session_id']
        )

        os.makedirs(save_path, exist_ok=True)
        file.save(os.path.join(save_path, secure_filename(file.filename)))
        #rag part
        ingest_documents(os.path.join(save_path, secure_filename(file.filename)), flask_session['session_id'])
       # return 'Docs were ingested'       
    else:
        print(form.errors)
    return render_template('index.html', form=form)


@app.route('/get_response', methods=['POST'])
def get_response():
    global ollama_client
    session_id = flask_session['session_id']
    messages = get_memory(session_id)
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({'error':'Empty message'}), 400
    context_docs = retrieve_context(user_input, session_id)
    if context_docs:
        context_text = '\n\n'.join(context_docs)
        print(context_docs)
        prompt = f'You are helpful assistant. If the context below is relevant to the question, use it to answer. If the context if not relevant or does not contain enough information, answer using ONLY your knowledge. Mention sources and context ONLY if context is relevant to the question.\n\nContext: {context_docs}\n\nQuestion:{user_input}'
    else:
        prompt = user_input

    messages.append({'role': 'user', 'content': prompt})    
    def generate():
        content = ''

        stream = ollama_client.chat(model='deepseek-r1', messages=session_messages[session_id], stream=True)
        for chunk in stream:
            if chunk.message:
                response_chunk = chunk.message.content
                content += response_chunk
                print(response_chunk, end='', flush=True)
                yield f'data: {json.dumps({"content": response_chunk})}\n\n'
        last_message = messages[-1]['content']
        last_message = message_summary(last_message)
        messages.append({'role': 'assistant', 'content': message_summary(content)})
        print(messages)
        yield 'data: [DONE]\n\n'
    return Response(stream_with_context(generate()), mimetype='text/event-stream',headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering':'no'})


@app.route('/reset', methods=['POST'])
def reset_session():
    session_id = flask_session['session_id']
    purge_session(session_id)
    session_messages.pop(session_id, None)
    session_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'], session_id)
    if os.path.isdir(session_dir): # to delete files in /upload folder
        shutil.rmtree(session_dir)

    flask_session.clear()
    return jsonify({'status': 'reset'})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
