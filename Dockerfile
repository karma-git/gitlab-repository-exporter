FROM python:3.10.1-alpine3.15

RUN addgroup --gid 10001 app \
  && adduser \
    --uid 10001 \
    --home /home/app \
    --shell /bin/ash \
    --ingroup app \
    --disabled-password \
    app

USER 10001

WORKDIR /home/app

COPY ./requirements.txt ./requirements.txt

RUN pip install --no-cache-dir \
  -r requirements.txt

COPY ./main.py ./

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/python3"]
CMD ["/home/app/main.py"]
