import customtkinter as ctk
from tkinter import ttk
import json
import os
import random
import string

password_file = "passwords.json"

# create file if it does not exist at start
if not os.path.exists(password_file):
    with open(password_file, "w") as f:
        json.dump({}, f)

# function to load the data
def load_data():
    with open(password_file, "r") as f:
        return json.load(f)

# add new password
def add_password():
    service = entry_service.get()
    username = entry_user.get()
    password = entry_pass.get()

    if service and username and password:
        save_data(service, username, password)
        # In Treeview einfügen
        if service in tree_services:
            tree.item(tree_services[service], values=(service, username, password))
        else:
            item_id = tree.insert("", "end", values=(service, username, password))
            tree_services[service] = item_id

        entry_service.delete(0, "end")
        entry_user.delete(0, "end")
        entry_pass.delete(0, "end")

# delete selected entries
def delete_selected():
    selected_items = tree.selection() # list of selected items
    if not selected_items:
        return # if no items are selected do nothing
    
    for item_id in selected_items:
        service = tree.item(item_id)["values"][0] # selec the service from column 0
        tree.delete(item_id) # delete from treeview
        tree_services.pop(service, None) # remove from tree dictionary

        # refresh the json file
        data = load_data()
        if service in data:
            data.pop(service)
            with open(password_file, "w") as f:
                json.dump(data, f, indent=4)

# function to generate a random password
def generate_password(lenght=14): 
    if lenght < 14:
        raise Exception("please enter at least 14 characters for the password")

    letters = string.ascii_letters #with the string library its possible to get string constants like letters
    numbers = string.digits #digits
    special = string.punctuation # and special symbols
    
    all = letters + numbers + special #put all strings together

    password = "".join((random.choice(all) for i in range(lenght))) #.join the previous string and randomize them

    return password

# function to save the entered data
def save_data(service, username, password):
    data = load_data()
    data[service] = {"username": username, "password": password}
    with open(password_file, "w") as f:
        json.dump(data, f, indent=4)

# initiate the GUI
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("800x400")
app.title("Mini Password Manager")

# entry field
frame_top = ctk.CTkFrame(app)
frame_top.pack(pady=10, padx=10, fill="x")

entry_service = ctk.CTkEntry(frame_top, placeholder_text="Service/Website")
entry_service.grid(row=0, column=0, padx=5, pady=5)

entry_user = ctk.CTkEntry(frame_top, placeholder_text="Username")
entry_user.grid(row=0, column=1, padx=5, pady=5)

entry_pass = ctk.CTkEntry(frame_top, placeholder_text="Password")
entry_pass.grid(row=0, column=2, padx=5, pady=5)

btn_add = ctk.CTkButton(frame_top, text="Add", command=add_password)
btn_add.grid(row=0, column=3, padx=5, pady=5)

btn_delete = ctk.CTkButton(frame_top, text="Delete", command=delete_selected)
btn_delete.grid(row=0, column=4, padx=5, pady=5)

# Treeview for password table
frame_tree = ctk.CTkFrame(app)
frame_tree.pack(padx=10, pady=10, fill="both", expand=True)

tree = ttk.Treeview(frame_tree, columns=("Service", "Username", "Password"), show="headings", selectmode="extended") # with extended we can select multiple rows (important for deleting)
tree.heading("Service", text="Service/Website")
tree.heading("Username", text="Username")
tree.heading("Password", text="Password")

tree.column("Service", width=200)
tree.column("Username", width=150)
tree.column("Password", width=150)

tree.pack(fill="both", expand=True, side="left")

# Scrollbar
scrollbar = ctk.CTkScrollbar(frame_tree, orientation="vertical", command=tree.yview)
scrollbar.pack(side="right", fill="y")
tree.configure(yscrollcommand=scrollbar.set)

# Dictionary to remember Item-IDs
tree_services = {}

# load data at start
for service, creds in load_data().items():
    item_id = tree.insert("", "end", values=(service, creds["username"], creds["password"]))
    tree_services[service] = item_id

app.mainloop()