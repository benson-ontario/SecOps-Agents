FROM python:3.11
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .
EXPOSE 5000

RUN useradd app
USER root

CMD ["python3", "app.py"]
