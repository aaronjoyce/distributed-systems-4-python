FROM ubuntu:14.04

RUN apt-get update && apt-get install -y \
    php5-mcrypt \
    python-pip \
    libcurl3 \
    libcurl3-dev \
    php5-curl \
    python-dev  # for python2.x installs


RUN pip install Flask
RUN pip install pyfscache
RUN pip install Flask-PyMongo
RUN pip install pycrypto

EXPOSE 27017

COPY setup.py /scr/setup.py

CMD ["python", "/src/setup.py"]

COPY auth-server.py /src/auth-server.py

CMD ["python","/src/auth-server.py"]
