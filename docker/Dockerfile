FROM claude-code-sandbox:latest
WORKDIR /app
RUN pip install claude-code-sdk fastapi uvicorn
COPY envd.py /app/envd.py
EXPOSE 8000