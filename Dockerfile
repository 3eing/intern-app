FROM python:3.14-alpine
LABEL authors="Loup Letac, ing - 3E ing"

ADD main.py .

RUN pip install -r requirements.txt

CMD ["python", "./main.py"]