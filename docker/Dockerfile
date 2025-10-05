FROM claude-code-sandbox:dev
#FROM claude-code-sandbox:latest
WORKDIR /app
RUN pip install claude-agent-sdk fastapi uvicorn

# Copy application files
COPY envd.py /app/envd.py
COPY sdk_compatibility_patch.py /app/
COPY tools /app/tools

EXPOSE 8000
