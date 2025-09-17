FROM claude-code-sandbox:dev
#FROM claude-code-sandbox:latest
WORKDIR /app
RUN pip install claude-code-sdk fastapi uvicorn

# Copy application files
COPY envd.py /app/envd.py
COPY tools /app/tools

EXPOSE 8000
