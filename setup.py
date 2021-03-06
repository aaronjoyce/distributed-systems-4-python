import requests
import base64
import json
import hashlib
from Crypto.Cipher import AES
from pymongo import MongoClient

'''
Set up global variables here
'''
mongo_server = "127.0.0.1"
mongo_port = "27017"
connect_string = "mongodb://" + mongo_server + ":" + mongo_port

connection = MongoClient(connect_string)
db = connection.project # equal to > use test_database
servers = db.servers

db.servers.drop()
db.directories.drop()
db.files.drop()
db.clients.drop()

m = hashlib.md5()
m.update("127.0.0.1" + ":" + "8092")
db.servers.insert({"reference": m.hexdigest(), "host": "127.0.0.1", "port": "8092", "is_master": True, "in_use": False})
m.update("127.0.0.1" + ":" + "8093")
db.servers.insert({"reference": m.hexdigest(), "host": "127.0.0.1", "port": "8093", "is_master": False, "in_use": False})
m.update("127.0.0.1" + ":" + "8094")
db.servers.insert({"reference": m.hexdigest(), "host": "127.0.0.1", "port": "8094", "is_master": False, "in_use": False})
m.update("127.0.0.1" + ":" + "8095")
db.servers.insert({"reference": m.hexdigest(), "host": "127.0.0.1", "port": "8095", "is_master": False, "in_use": False})
