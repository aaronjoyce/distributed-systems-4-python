import base64
import md5
import datetime
import json
import hashlib
import flask
import sys
import math
import os
import threading
import requests
import zlib
import uuid
import Queue
from pyfscache import *
import os
import shutil

from flask import Flask
from flask import request
from flask import jsonify
from flask import Response
from flask_pymongo import PyMongo
from pymongo import MongoClient
from Crypto.Cipher import AES

application = Flask(__name__)
mongo = PyMongo(application)
write_lock = threading.Lock()
write_queue = Queue.Queue(maxsize=100)

'''
Set up global variables here
'''

mongo_server = "0.0.0.0"
mongo_port = "27017"
connect_string = "mongodb://" + mongo_server + ":" + mongo_port

connection = MongoClient(connect_string)
db = connection.project # equal to > use test_database
servers = db.servers

# constants
AUTH_SERVER_STORAGE_SERVER_KEY = "d41d8cd98f00b204e9800998ecf8427e"
SERVER_HOST = None
SERVER_PORT = None


def reset():
    db.directories.drop()
    db.files.drop()


def upload_async(file, client_request, options):
    cache_reference = options['cache_reference']
    with application.app_context():
        servers = db.servers.find()

        server_quorum = math.ceil(servers.count() * 0.5)

        server_success = 0
        # if number of successful less than quorum, then remove...
        transactions = {}
        for server in servers:
            host = server["host"]
            port = server["port"]
            if (host == SERVER_HOST and port == SERVER_PORT):
                continue
            # make POST request to upload file to server, using
            # same client request
            data = cache.get(cache_reference)

            headers = {'ticket': client_request['ticket'],
                       'directory': client_request['directory'],
                       'filename': client_request['filename']}
            response = requests.post("http://" + host + ":" + port + "/server/file/upload", data=data, headers=headers)
            transactions[host + '-' + port] = response.json()['success']
            if (transactions[host + '-' + port]):
                server_success += 1

        # roll back if necessary
        if (server_success < server_quorum):
            for transaction_key in transactions.iterkeys():
                if (transactions[transaction_key]):
                    host, port = transaction_key.split('-')
                    headers = {'ticket': client_request['ticket'],
                               'directory': client_request['directory'],
                               'filename': client_request['filename']}
                    r = requests.post("http://" + host + ":" + port + "/server/file/delete", data='', headers=headers)






def delete_async(file, client_request):
    with application.app_context():
        servers = db.servers.find()
        server_quorum = math.ceil(servers.count() * 0.5)

        server_success = 0
        # if number of successful less than quorum, then remove...
        transactions = {}

        for server in servers:
            host = server["host"]
            port = server["port"]
            if (host == SERVER_HOST and port == SERVER_PORT):
                continue
            # make POST request to delete file from server, using
            # same client request
            headers = {'ticket': client_request['ticket'],
                       'directory': client_request['directory'],
                       'filename': client_request['filename']}
            response = requests.post("http://" + host + ":" + port + "/server/file/delete", data='', headers=headers)
            transactions[host + '-' + port] = response.json()['success']
            if (transactions[host + '-' + port]):
                server_success += 1

        # roll back if necessary
        if (server_success < server_quorum):
            for transaction_key in transactions.iterkeys():
                if (transactions[transaction_key]):
                    host, port = transaction_key.split('-')
                    headers = {'ticket': client_request['ticket'],
                               'directory': client_request['directory'],
                               'filename': client_request['filename']}
                    r = requests.post("http://" + host + ":" + port + "/server/file/upload", data='', headers=headers)

def get_current_server():
    with application.app_context():
        return db.servers.find_one({"host":SERVER_HOST, "port": SERVER_PORT})


@application.route('/server/file/ready-to-commit', methods=['POST'])
def file_ready_to_commit():
    headers = request.headers

    filename_encoded = headers['filename']
    directory_name_encoded = headers['directory']
    ticket = headers['ticket']
    session_key = Authentication.decode(AUTH_SERVER_STORAGE_SERVER_KEY, ticket).strip()
    directory_name = Authentication.decode(session_key, directory_name_encoded)
    filename = Authentication.decode(session_key, filename_encoded)

    m = hashlib.md5()
    m.update(get_current_server()['reference'])
    pre_write_cache_reference = m.update(directory_name + "/" + filename)


    cache.create(pre_write_cache_reference, Cache.compress(request.get_data()))
    reference = str(uuid.uuid1())
    commit = Commit.create(reference, directory_name, filename, pre_write_cache_reference)
    return jsonify({"ready_to_commit":reference})

@application.route('/server/file/commit', methods=['POST'])
def file_commit():
    headers = request.headers

    commit_reference = request.get_data('commit_reference')
    commit = db.commits.find_one(commit_reference)
    if not(commit):
        return jsonify({"success":False})

    directory_name = commit["directory_name"]
    filename = commit["file_name"]
    cache_reference = commit["cache_reference"]

    m = hashlib.md5()
    m.update(directory_name)
    server = get_current_server()

    """
        @reference
        @directory_name
        @file_name
        @cache_reference
    """
    if not db.directories.find_one(
            {"name": directory_name, "reference": m.hexdigest(), "server": get_current_server()["reference"]}):
        directory = Directory.create(directory_name, server["reference"])
    else:
        directory = db.directories.find_one(
            {"name": directory_name, "reference": m.hexdigest(), "server": get_current_server()["reference"]})

    if not db.files.find_one(
            {"name": filename, "directory": directory['reference'], "server": get_current_server()["reference"]}):
        file = File.create(filename, directory['name'], directory['reference'], get_current_server()["reference"])
    else:
        file = db.files.find_one(
            {"name": filename, "directory": directory['reference'], "server": get_current_server()["reference"]})

    transaction = Transaction(write_lock, file['reference'], directory['reference'], cache_reference)
    transaction.start()

    return jsonify({"ready_to_commit"})





@application.route('/server/file/upload', methods=['POST'])
def file_upload():
    # Need to update cached record (if exists)
    # pre_write_cache_reference = uuid.uuid4()
    # cache.create(pre_write_cache_reference, Cache.compress(request.get_data()))

    headers = request.headers

    filename_encoded = headers['filename']
    directory_name_encoded = headers['directory']
    ticket = headers['ticket']
    session_key = Authentication.decode(AUTH_SERVER_STORAGE_SERVER_KEY, ticket).strip()
    directory_name = Authentication.decode(session_key, directory_name_encoded)
    filename = Authentication.decode(session_key, filename_encoded)

    m = hashlib.md5()
    pre_write_cache_reference = m.update(directory_name + "/" + filename)

    cache.create(pre_write_cache_reference, Cache.compress(request.get_data()))

    m = hashlib.md5()
    m.update(directory_name)
    server = get_current_server()

    if not db.directories.find_one({"name": directory_name, "reference": m.hexdigest(), "server":get_current_server()["reference"]}):
        directory = Directory.create(directory_name, server["reference"])
    else:
        directory = db.directories.find_one({"name": directory_name, "reference": m.hexdigest(), "server":get_current_server()["reference"]})

    if not db.files.find_one({"name": filename, "directory": directory['reference'], "server":get_current_server()["reference"]}):
        file = File.create(filename, directory['name'], directory['reference'], get_current_server()["reference"])
    else:
        file = db.files.find_one({"name": filename, "directory": directory['reference'], "server": get_current_server()["reference"]})

    transaction = Transaction(write_lock, file['reference'], directory['reference'], pre_write_cache_reference)
    transaction.start()

    options = {}
    options['cache_reference'] = pre_write_cache_reference
    if (get_current_server()["is_master"]):
        thr = threading.Thread(target=upload_async, args=(file, headers, options), kwargs={})
        thr.start()
    return jsonify({'success':True})


@application.route('/server/file/download', methods=['POST'])
def file_download():
    headers = request.headers

    filename_encoded = headers['filename']
    directory_name_encoded = headers['directory']
    ticket = headers['ticket']
    session_key = Authentication.decode(AUTH_SERVER_STORAGE_SERVER_KEY, ticket).strip()
    directory_name = Authentication.decode(session_key, directory_name_encoded)
    filename = Authentication.decode(session_key, filename_encoded)

    m = hashlib.md5()
    m.update(directory_name)
    directory = db.directories.find_one({"name": directory_name, "reference": m.hexdigest(), "server": get_current_server()["reference"]})
    if not directory:
        return jsonify({"success":False})

    file = db.files.find_one({"name": filename, "directory": directory['reference'], "server": get_current_server()["reference"]})
    if not file:
        return jsonify({"success":False})

    if not(get_current_server()["is_master"]):
        cache_reference = directory["reference"] + "_" + file["reference"] + "_" + get_current_server()["reference"]
        if (cache.get(cache_reference)):
            return Cache.decompress(cache.get(cache_reference))
        else:
            return flask.send_file(file["reference"])

    # otherwise, it's the master server
    file_sources = db.files.find({"name": filename, "directory": directory['reference']})
    for file_source in file_sources:
        server_reference = file_source["server"];
        if (server_reference == get_current_server()["reference"]):
            continue
        server = db.servers.find_one({"reference": server_reference})
        read = requests.post("http://" + server['host'] + ":" + server['port'] + "/server/file/download", data="",
                             headers=request.headers)
        if (read.text):
            resp = flask.Response(read.text)
            resp.headers['Access-Control-Allow-Origin'] = '*'
            resp.headers["content-type"] = "text/plain"
            return resp

    cache_file_reference = directory['reference'] + "_" + file['reference'] + "_" + get_current_server()["reference"]
    if cache.exists(cache_file_reference):
        return Cache.decompress(cache.get(cache_file_reference))
    else:
        return flask.send_file(file["reference"])


@application.route('/server/file/delete', methods=['POST'])
def file_delete():
    headers = request.headers
    filename_encoded = headers['filename']
    directory_name_encoded = headers['directory']
    ticket = headers['ticket']
    session_key = Authentication.decode(AUTH_SERVER_STORAGE_SERVER_KEY, ticket).strip()
    directory_name = Authentication.decode(session_key, directory_name_encoded)
    filename = Authentication.decode(session_key, filename_encoded)

    m = hashlib.md5()
    m.update(directory_name)
    server = get_current_server()
    print(server)
    # check if the directory exists on current server
    if not db.directories.find_one({"name": directory_name, "reference": m.hexdigest(), "server": get_current_server()["reference"]}):
        return jsonify({"success": False})
    else:
        directory = db.directories.find_one({"name": directory_name, "reference": m.hexdigest(), "server": get_current_server()["reference"]})
    # check if the file exists on current server
    file = db.files.find_one({"name": filename, "directory": directory['reference'], "server": get_current_server()["reference"]})
    if not file:
        return jsonify({"success": False})

    delete_transaction = DeleteTransaction(write_lock, file["reference"], directory["reference"])
    delete_transaction.start()


    if (get_current_server()["is_master"]):
        thr = threading.Thread(target=delete_async, args=(file, headers), kwargs={})
        thr.start()  # will run "foo"
    return jsonify({'success':True})


class Transaction(threading.Thread):

    def __init__(self, lock, file_reference, directory_reference, cache_reference):
        threading.Thread.__init__(self)
        self.lock = lock
        self.file_reference = file_reference
        self.cache_reference = cache_reference
        self.directory_reference = directory_reference

    def run(self):
        self.lock.acquire()
        reference = db.writes.find_one({"file_reference":self.file_reference, "cache_reference":self.cache_reference})
        if (reference):
            # then, queue the write
            write_queue.put({"file_reference":self.file_reference, "cache_reference":self.cache_reference})
            self.lock.release()
            return
        self.lock.release()

        # now, write to the file on disk and pyfscache
        cache.create(self.directory_reference + "_" + self.file_reference + "_" + get_current_server()["reference"], cache.get(self.cache_reference))
        with open(self.file_reference, "wb") as fo:
            fo.write(cache.get(self.directory_reference + "_" + self.file_reference + "_" + get_current_server()["reference"]))

class DeleteTransaction(threading.Thread):
    def __init__(self, lock, file_reference, directory_reference):
        threading.Thread.__init__(self)
        self.lock = lock
        self.file_reference = file_reference
        self.directory_reference = directory_reference

    def run(self):
        self.lock.acquire()
        file = db.files.find_one({"reference":self.file_reference, "directory":self.directory_reference, "server": get_current_server()["reference"]})
        if file:
            cache.delete(self.file_reference + "_" + self.directory_reference + "_" + get_current_server()["reference"])
            os.remove(self.file_reference)
            db.files.remove({"reference":self.file_reference, "directory":self.directory_reference, "server": get_current_server()["reference"]})

        self.lock.release()



class QueuedWriteHandler(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        while True:
            file_write = write_queue.get()
            thread = Transaction(file_write["file_reference"], file_write["cache_reference"])
            thread.start()
            write_queue.task_done()


class Authentication:
    def __init__(self):
        pass

    @staticmethod
    def pad(s):
        return s + b"\0" * (AES.block_size - len(s) % AES.block_size)

    @staticmethod
    def encode(key, decoded):
        cipher = AES.new(key, AES.MODE_ECB)  # never use ECB in strong systems obviously
        encoded = base64.b64encode(cipher.encrypt(Authentication.pad(decoded)))
        return encoded

    @staticmethod
    def decode(key, encoded):
        cipher = AES.new(key, AES.MODE_ECB)  # never use ECB in strong systems obviously
        decoded = cipher.decrypt(base64.b64decode(encoded))
        return decoded.strip()


class SystemCache:
    def __init__(self):
        pass

    @staticmethod
    def compress(data):
        return zlib.compress(data)

    @staticmethod
    def decompress(data):
        return zlib.decompress(data)


class CacheSys:
    def __init__(self, directory, retention):
        self.directory = directory
        self.retention = retention # expressed in days
        self.instance = FSCache(self.directory, days=self.retention)

    def get_instance(self):
        return self.instance

    def get(self, key):
        return self.get_instance()[key]

    def create(self, key, data):
        self.get_instance()[key] = data

    def delete(self, key):
        self.get_instance().expire(key)

    def exists(self, key):
        if key in self.get_instance():
            return True
        else:
            return False

class Cache:
    def __init__(self, directory, retention):
        self.directory = directory
        self.retention = retention # expressed in days
        self.instance = FSCache(self.directory, days=self.retention)

    def get_instance(self):
        return self.instance

    def get(self, key):
        return self.get_instance()[key]

    def create(self, key, data):
        if self.exists(key):
            self.delete(key)
        self.get_instance()[key] = data

    def delete(self, key):
        if self.exists(key):
            self.get_instance().expire(key)

    def exists(self, key):
        return key in self.get_instance()

    @staticmethod
    def compress(data):
        return zlib.compress(data)

    @staticmethod
    def decompress(data):
        return zlib.decompress(data)

class File:
    def __init__(self):
        pass

    @staticmethod
    def create(name, directory_name, directory_reference, server_reference):
        m = hashlib.md5()
        m.update(directory_reference + "/" + directory_name + '-' + server_reference)
        db.files.insert({"name":name
            ,"directory": directory_reference
            ,"server": server_reference
            ,"reference": m.hexdigest()
            ,"updated_at": datetime.datetime.utcnow()})
        file = db.files.find_one({"reference":m.hexdigest()})
        return file

class Commit:
    def __init__(self):
        pass

    """
        @reference
        @directory_name
        @file_name
        @cache_reference
    """
    @staticmethod
    def create(reference, directory_name, file_name, cache_reference):
        db.commits.insert({
            "reference":reference,
            "directory_name":directory_name,
            "file_name":file_name,
            "cache_reference":cache_reference
        })
        return db.commits.find_one({"reference":reference})

    @staticmethod
    def delete(reference):
        db.commits.remove({"reference":reference})


class Directory:
    def __init__(self):
        pass

    @staticmethod
    def create(name, server):
        m = hashlib.md5()
        m.update(name)
        db.directories.insert({"name":name, "reference": m.hexdigest(), "server":server})
        directory = db.directories.find_one({"name":name, "reference": m.hexdigest()})
        return directory


cache = Cache('cache/dir', 7)

if __name__ == '__main__':
    print("This should have been included")
    with application.app_context():
        m = hashlib.md5()

        print(sys.version)

        servers = db.servers.find()
        for server in servers:
            print(server)
            if (server['in_use'] == False):
                server['in_use'] = True
                SERVER_PORT = server['port']
                SERVER_HOST = server['host']
                queued_write_handler = QueuedWriteHandler()
                queued_write_handler.setDaemon(True)
                queued_write_handler.start()
                db.servers.update({'reference': server['reference']}, server, upsert=True)
                application.run(host=server['host'],port=server['port'])