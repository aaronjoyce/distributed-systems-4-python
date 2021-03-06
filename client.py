import requests
import base64
import json
import time
import sys
import hashlib
from Crypto.Cipher import AES
from pymongo import MongoClient

PUBLIC_KEY = "0123456789abcdef0123456789abcdef"
client_id = "1"
decrypted_password = "0dP1jO2zS7111111"

headers = {'Content-type': 'application/json'}
payload = {'client_id': client_id, 'password': decrypted_password, 'public_key':PUBLIC_KEY}
r = requests.post("http://127.0.0.1:5001/client/create", data=json.dumps(payload), headers=headers)



def pad(s):
    return s + b" " * (AES.block_size - len(s) % AES.block_size)

# ESTABLISHING CONNECTION WITH AUTHENTICATION SERVER
cipher = AES.new(PUBLIC_KEY, AES.MODE_ECB)  # never use ECB in strong systems obviously
encrypted_password = base64.b64encode(cipher.encrypt(decrypted_password))

headers = {'Content-type': 'application/json'}
payload = {'client_id': client_id, 'password': decrypted_password, 'public_key':PUBLIC_KEY}
r = requests.post("http://127.0.0.1:5001/client/auth", data=json.dumps(payload), headers=headers)
response_body = r.text
encoded_token = json.loads(response_body)["token"]

cipher = AES.new(PUBLIC_KEY, AES.MODE_ECB)  # never use ECB in strong systems obviously
decoded = cipher.decrypt(base64.b64decode(encoded_token))
decoded_data = json.loads(decoded.strip())

session_key = decoded_data["session_key"]
print("SESSION KEY DECODED")
ticket = decoded_data["ticket"]
server_host = decoded_data["server_host"]
server_port = decoded_data["server_port"]



# UPLOADING FILE TO FILE SERVER, USING AUTHENTICATED DATA
cipher = AES.new(session_key, AES.MODE_ECB)  # never use ECB in strong systems obviously
encrypted_directory = base64.b64encode(cipher.encrypt(pad("/home/great")))
encrypted_filename = base64.b64encode(cipher.encrypt(pad("sample.txt")))

data = open('yourfile.txt', 'rb').read()

headers = {'ticket':ticket, 'directory':encrypted_directory, 'filename':encrypted_filename}
write = requests.post("http://" + server_host + ":" + server_port + "/server/file/ready-to-commit", data=data, headers=headers)
print(write.text)


sys.exit()
time.sleep(10)


headers = {'ticket':ticket, 'directory':encrypted_directory, 'filename':encrypted_filename}
write = requests.post("http://" + server_host + ":" + server_port + "/server/file/upload", data=data, headers=headers)


time.sleep(10)
read = requests.post("http://" + server_host + ":" + server_port + "/server/file/download", data="", headers=headers)
print(read.text)
time.sleep(10)
download = requests.post("http://" + server_host + ":" + server_port + "/server/file/delete", headers=headers)
print(write.text)
print(download.text)
