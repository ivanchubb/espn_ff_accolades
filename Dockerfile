FROM python:alpine

RUN pip install espn_api flask && rm -rf /root/.cache/pip

WORKDIR /app

COPY . /app/

EXPOSE 5000

CMD ["python", "main.py"]