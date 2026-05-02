FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install flask==3.0.3 pymongo==4.7.3 flasgger==0.9.7.1
CMD ["python", "app.py"]
