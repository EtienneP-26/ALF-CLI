import ollama
import os

client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
