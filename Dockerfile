FROM python

EXPOSE 6066

RUN pip install requests

ADD LoxoneWeather.py .

CMD ["python","LoxoneWeather.py"]