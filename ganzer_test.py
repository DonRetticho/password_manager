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

    # service and username are required fields
    if not service or not username:
        #raise Exception("service and username are required")
        return
    
    # if no password is entered a random one is generated
    if not password:
        length = ask_password_length()

        if length is None:
            return
        
        password = generate_password(length)
        entry_pass.insert(0, password)

    save_data(service, username, password)

    # with multiple users and passwords per service we dont want to override the previous entry for a service
    #tree.insert("", "end", values=(service, username, password))

    # create (or get) parent (service)
    if service not in service_nodes:
        parent_id = tree.insert("", "end", text=service, open=True)
        service_nodes[service] = parent_id
    else:
        parent_id = service_nodes[service]

    # add child (account)
    tree.insert("", "end", values=(username, password))

    entry_service.delete(0, "end")
    entry_user.delete(0, "end")
    entry_pass.delete(0, "end")

# delete selected entries
def delete_selected():
    selected_items = tree.selection() # list of selected items
    if not selected_items:
        show_info_dialog("Warning", "No entry selected!")
        return # if no items are selected do nothing

    # refresh the json file
    data = load_data()

    for item_id in selected_items:
        parent = tree.parent(item_id)

        if not parent:
            service = tree.item(item_id)["text"]
            tree.delete(item_id)
            data.pop(service, None)
        else:
            service = tree.item(parent)["text"]
            username, password = tree.item(item_id)["values"]

            # remove from tree
            tree.delete(item_id)

            # remove from json file
            if service in data:
                data[service] = [
                    acc for acc in data[service]
                    if not (acc["username"] == username and acc["password"] == password)
                ]
            
                if not data[service]:
                    data.pop(service)
            
    with open(password_file, "w") as f:
        json.dump(data, f, indent=4)

    show_info_dialog("Info", "Selected entries deleted!")

# function to generate a random password
def generate_password(lenght=14):
    letters = string.ascii_letters #with the string library its possible to get string constants like letters
    numbers = string.digits #digits
    special = string.punctuation # and special symbols
    
    all = letters + numbers + special #put all strings together

    password = "".join((random.choice(all) for i in range(lenght))) #.join the previous string and randomize them

    return password

# function to save the entered data
def save_data(service, username, password):
    data = load_data()

    if service not in data:
        data[service] = []

    # we want to be able to save multiple users and passwords for the same service
    # so we make a list and inside that list we add the username and password

    data[service].append({
        "username": username, 
        "password": password
        })
    
    with open(password_file, "w") as f:
        json.dump(data, f, indent=4)

def ask_password_length():
    """
    Öffnet ein kleines Fenster, um die gewünschte Passwortlänge abzufragen.
    Nutzt show_info_dialog für Warnungen.
    Gibt die Länge als int zurück oder None, wenn abgebrochen.
    """
    dialog = ctk.CTkToplevel(app)
    dialog.title("Password Length")
    dialog.geometry("335x175")

    result = {"length": None}

    label = ctk.CTkLabel(dialog, text="Enter password length (14 - 40, recommended: 16 - 20):")
    label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

    entry = ctk.CTkEntry(dialog)
    entry.bind("<Return>", lambda event: confirm()) # allow return as input
    entry.insert(0, "16") # set default value for field
    entry.grid(row=1, column=0, columnspan=2, padx=10, pady=5)

    def confirm():
        value = entry.get()

        if not value.isdigit():
            show_info_dialog("Warning", "Please enter a number!")
            return
        
        length = int(value)

        if length < 14:
            show_info_dialog("Warning", "Minimum password length is 14!")
            return
        
        if length > 40:
            show_info_dialog("Warning", "Maximum password length is 40!")
            return
        
        result["length"] = length
        dialog.destroy()

    def cancel():
        dialog.destroy()

    btn_ok = ctk.CTkButton(dialog, text="OK", command=confirm)
    btn_ok.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

    btn_cancel = ctk.CTkButton(dialog, text="Cancel", command=cancel)
    btn_cancel.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

    dialog.wait_visibility()
    dialog.grab_set()
    app.wait_window(dialog)

    return result["length"]

# general purpose info dialog function
def show_info_dialog(title: str, message: str):
    """
    Zeigt ein modales Popup-Fenster mit einer Nachricht und einem OK-Button.
    
    title: Fenster-Titel
    message: Nachrichtstext
    """
    dialog = ctk.CTkToplevel(app)
    dialog.title(title)
    dialog.geometry("300x130")

    label = ctk.CTkLabel(dialog, text=message, wraplength=250)
    label.grid(row=0, column=0, columnspan=1, padx=20, pady=20)

    def close():
        dialog.destroy()

    btn_ok = ctk.CTkButton(dialog, text="OK", command=close)
    btn_ok.grid(row=1, column=0, padx=20, pady=20, sticky="ew")

    dialog.wait_visibility()
    dialog.grab_set()
    app.wait_window(dialog)

# initiate the GUI
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("800x400")
app.title("Mini Password Manager")

# entry field
frame_top = ctk.CTkFrame(app)
frame_top.pack(pady=10, padx=10, fill="x")

entry_lbl = ctk.CTkLabel(frame_top, text="Password entry")
entry_lbl.grid(row=0, column=0, padx=5, pady=5, columnspan=4, sticky="w")

note_lbl = ctk.CTkLabel(frame_top, text="If no password is entered it will be given by random")
note_lbl.grid(row=1, column=0, padx=5, pady=5, columnspan=4, sticky="w")

entry_service = ctk.CTkEntry(frame_top, placeholder_text="Service/Website")
entry_service.grid(row=2, column=0, padx=5, pady=5)

entry_user = ctk.CTkEntry(frame_top, placeholder_text="Username")
entry_user.grid(row=2, column=1, padx=5, pady=5)

entry_pass = ctk.CTkEntry(frame_top, placeholder_text="Password")
entry_pass.grid(row=2, column=2, padx=5, pady=5)

btn_add = ctk.CTkButton(frame_top, text="Add", command=add_password)
btn_add.grid(row=2, column=3, padx=5, pady=5)

btn_delete = ctk.CTkButton(frame_top, text="Delete", command=delete_selected)
btn_delete.grid(row=2, column=4, padx=5, pady=5)

# Treeview for password table
frame_tree = ctk.CTkFrame(app)
frame_tree.pack(padx=10, pady=10, fill="both", expand=True)

tree = ttk.Treeview(
    frame_tree, 
    columns=("Username", "Password"), 
    show="tree headings", 
    selectmode="extended") # with extended we can select multiple rows (important for deleting)
tree.heading("#0", text="Service/Website")
tree.heading("Username", text="Username")
tree.heading("Password", text="Password")

tree.column("#0", width=200)
tree.column("Username", width=150)
tree.column("Password", width=150)

tree.pack(fill="both", expand=True, side="left")

# Scrollbar
scrollbar = ctk.CTkScrollbar(frame_tree, orientation="vertical", command=tree.yview)
scrollbar.pack(side="right", fill="y")
tree.configure(yscrollcommand=scrollbar.set)

# to group usernames and passwords with the same service we need to save them in a dictionary
service_nodes = {}

# load data at start
for service, accounts in load_data().items():

    if isinstance(accounts, dict):
        accounts = [accounts]

    parent_id = tree.insert("", "end", text=service, open=True)
    service_nodes[service] = parent_id

    for acc in accounts:
        tree.insert(parent_id, "end", values=(acc["username"], acc["password"]))

app.mainloop()