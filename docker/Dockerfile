FROM claude-code-sandbox:dev
#FROM claude-code-sandbox:latest
WORKDIR /app

# Switch to root to install global npm packages
USER root
RUN pip install claude-agent-sdk fastapi uvicorn

# Install claude-trace for HTML report generation
RUN npm install -g @mariozechner/claude-trace@latest

# Switch back to claude user
USER claude

# Copy application files
COPY envd.py /app/envd.py
COPY sdk_compatibility_patch.py /app/
COPY lain_tracer.py /app/
COPY tools /app/tools

EXPOSE 8000
