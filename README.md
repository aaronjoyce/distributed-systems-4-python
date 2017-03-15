In order to run this project, you must execute the following steps:

1. Run the setup.py file: python setup.py
2. Run the authentication server: python auth-server.py
3. Create numerous server instances, which, for the purpose of testing, run on the same host with different ports. You may do this by running the directory server: python directory-server.py

The first server instance created as a result of running ```python directory-server.py``` represents the master copy. All servers subsequently started represent copies/replicas of the master copy.
