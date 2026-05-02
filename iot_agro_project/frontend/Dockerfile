FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install streamlit==1.35.0 requests==2.32.3 pandas==2.2.2 plotly==5.22.0 streamlit-autorefresh==1.0.1
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
