FROM ubuntu:14.04
FROM python:2.7

RUN apt-get update && apt-get install -y \
    apt-utils -y \
    php5-mcrypt \
    sudo \
    mongodb \
#    python \
#   python-distribute \
    mongodb \
    python-pip \
    libcurl3 \
    libcurl3-dev \
    php5-curl \
    python-dev # for python2.x installs


RUN mkdir -p /data/db
EXPOSE 27017

RUN sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv EA312927
RUN echo "deb http://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.2 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.2.list
RUN sudo apt-get update

RUN sudo apt-get install -y mongodb-org
RUN sudo apt-get install net-tools

RUN echo "" > /etc/mongod.conf
RUN echo "# mongod.conf" >> /etc/mongod.conf
RUN echo "storage:" >> /etc/mongod.conf
RUN echo "  dbPath: /var/lib/mongodb" >> /etc/mongod.conf
RUN echo "  journal:" >> /etc/mongod.conf
RUN echo "  enabled: true" >> /etc/mongod.conf
RUN echo "systemLog:" >> /etc/mongod.conf
RUN echo "  destination: file" >> /etc/mongod.conf
RUN echo "  logAppend: true" >> /etc/mongod.conf
RUN echo "  path: /var/log/mongodb/mongod.log" >> /etc/mongod.conf
RUN echo "net:" >> /etc/mongod.conf
RUN echo "  port: 27017" >> /etc/mongod.conf
RUN echo "  bindIp: 0.0.0.0" >> /etc/mongod.conf

RUN sudo service mongodb restart

#RUN sudo cat /etc/mongod.conf

RUN pip install Flask
RUN pip install pyfscache
RUN pip install Flask-PyMongo
RUN pip install pycrypto
RUN pip install requests

RUN netstat -an | grep 27017

COPY directory-server.py /src/directory-server.py

CMD ["python","/src/directory-server.py"]