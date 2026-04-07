# Chatbot

## Start
```bash
docker-compose up --build -d
```

## Models
```bash
# Pull language model
docker exec -it ollama ollama pull mistral

# Pull embedding model
docker exec -it ollama ollama pull all-minilm:latest
```

## Observe
```bash
docker-compose logs -f
```

## Teardown
```bash
# Removes containers and volumes (deletes downloaded models)
docker-compose down -v
```