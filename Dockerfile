FROM python:3.5-stretch

ADD . .
RUN pip install -r requirements.txt

ENTRYPOINT [ "python" ]
CMD ["app.py"]