import os # needed to check if the file exists
import json # needed to load and dump to/from the json file in which the passwords are saved

password_file = "passwords.json" #name of the password file

if not os.path.exists(password_file): # check if the file is not present. if not present create it
    with open(password_file, "w") as f:
        json.dump({}, f) # insert empty data into the json file so that no JSONDecodeError will appear

def load_data(): # function to load data from the json file
    with open(password_file, "r") as f:
        return json.load(f)

def save_password(service, username, password):
    data = load_data() # load the data from the json file


    # the passwords will be saved in the following structure:
    #
    # {
    #   "service": {
    #       "username": user entry,
    #       "password": user entry,
    #   }
    # }

    data[service] = {
        "username": username,
        "password": password
    }

    with open(password_file, "w") as f: # save the data into the json file
        json.dump(data, f, indent=4)