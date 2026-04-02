import random
import string

def generate_password(): #function to generate a random password
    letters = string.ascii_letters #with the string library its possible to get string constants like letters
    numbers = string.digits #digits
    special = string.punctuation # and special symbols
    
    all = letters + numbers + special #put all strings together

    password = "".join((random.choice(all) for i in range(14))) #.join the previous string and randomize them
                                                                # for now set with a fixed number of characters for the password

    return password

