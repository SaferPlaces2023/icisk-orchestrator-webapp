FROM python:3.11-slim

# WORKDIR /notebook
COPY . /app
WORKDIR /app

RUN apt-get update && apt-get install -y git
RUN pip install -e .
# RUN pip install -U "langgraph-cli[inmem]"
EXPOSE 8501

CMD ["streamlit", "run", "src/icisk_orchestrator_webapp/app.py", "--server.port=8501", "--server.address=0.0.0.0"]