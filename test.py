from pyfscache import *
import os
import shutil
import zlib

class SystemCache:
    def __init__(self):
        pass

    @staticmethod
    def compress(data):
        return zlib.compress(data)

    @staticmethod
    def decompress(data):
        return zlib.decompress(data)


if os.path.exists('cache/dir'):
    shutil.rmtree('cache/dir')

c = FSCache('cache/dir', days=7)
c['some_key'] = SystemCache.compress(open('yourfile.txt', 'rb').read())
print(c['some_key'])
print(os.listdir('cache/dir'))
print(c.get_loaded())
print(c)
#.expire('some_key')
if 'some_key' in c:
    print("in here")




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



