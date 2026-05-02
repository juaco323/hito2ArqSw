FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install paho-mqtt==1.6.1 pymongo==4.7.3
CMD ["python", "subscriber.py"]
