import customtkinter as ctk
from tkinter import ttk, messagebox
import json
import os
import string
import pyperclip
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

password_file = "passwords.json"
salt_file = "salt.bin"

if not os.path.exists(salt_file):
    salt = os.urandom(16)
    with open(salt_file, "wb") as f:
        f.write(salt)
else:
    with open(salt_file, "rb") as f:
        salt = f.read()

# create file if it does not exist at start
if not os.path.exists(password_file):
    with open(password_file, "w") as f:
        json.dump({}, f)

###### Classes
# refactor: remove global and set them in seperate things
class UIState:
    def __init__(self):
        self.tree = None
        self.entry_service = None
        self.entry_user = None
        self.entry_pass = None
        self.status_lbl = None
        self.service_nodes = {}

# password manager class
class PasswordManager():
    def __init__(self, file_path, fernet):
        self.file_path = file_path
        self.fernet = fernet

# function to load the data
    def load_data(self):
        data = self._load_data_raw()

        for service, accounts in data.items():
            for acc in accounts:
                acc["password"] = self._decrypt_password(acc["password"])

        return data
    
    # function to save the entered data
    def save_data(self, service, username, password):
        data = self._load_data_raw()
        encrypted_password = self._encrypt_password(password)

        if service not in data:
            data[service] = []

        # we want to be able to save multiple users and passwords for the same service
        # so we make a list and inside that list we add the username and password

        data[service].append({
            "username": username, 
            "password": encrypted_password
            })
        
        with open(password_file, "w") as f:
            json.dump(data, f, indent=4)

    def _load_data_raw(self):
        if not os.path.exists(password_file):
            return {}
        with open(password_file, "r") as f:
            return json.load(f)
        
    def _write(self, data):
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=4)

    def _encrypt_password(self, password: str) -> str:
        return self.fernet.encrypt(password.encode()).decode()

    def _decrypt_password(self, password: str) -> str:
        try:
            return self.fernet.decrypt(password.encode()).decode()
        except Exception:
            return password # fallback if not encrypted
        
    def delete_entry(self, service, username, password):
        data = self._load_data_raw()

        if service in data:
            data[service] = [
                acc for acc in data[service]
                if not (
                    acc["username"] == username and
                    self._decrypt_password(acc["username"]) == password
                )
            ]

            if not data[service]:
                del data[service]

        self._write(data)

    def update_entry(self, service, old_username, old_password, new_username, new_password):
        data = self._load_data_raw()

        if service in data:
            for acc in data[service]:
                if (
                    acc["username"] == old_username and
                    self._decrypt_password(acc["password"]) == old_password
                ):
                    acc["username"] = new_username
                    acc["password"] = self._encrypt_password(new_password)

        self._write(data)

# add new password
def add_password(ui, manager):
    service = ui.entry_service.get()
    username = ui.entry_user.get()
    password = ui.entry_pass.get()

    # service and username are required fields
    error = validate_inputs(service, username)
    if error:
        set_status(ui, error, text_color="red")
        return
    
    # check for duplicates
    data = manager.load_data()
    if service in data:
        if any(acc["username"] == username for acc in data[service]):
            ui.status_lbl.configure(text="This username already exists for this service!", text_color="red")
            return
    
    # if no password is entered a random one is generated
    password = get_or_create_password(password)
    if password is None:
        return
        
    if not ui.entry_pass.get():
        ui.entry_pass.insert(0, password)

    manager.save_data(service, username, password)

    # with multiple users and passwords per service we dont want to override the previous entry for a service
    #tree.insert("", "end", values=(service, username, password))

    # create (or get) parent (service)
    insert_into_tree(ui, service, username, password)

    clear_inputs(ui)

    set_status(ui, "Entry added!")

# refactor function: instead of add_password doing all things we are splitting it up into smaller functions
# firsts function is to validate that service and username are required
def validate_inputs(service, username):
    if not service:
        return "Service/Website is required!"
    if not username:
        return "Username is required!"
    
# second refactor: the password generation or if entered manually
def get_or_create_password(password):
    if password:
        return password
    
    length = ask_password_length()
    if length is None:
        return None
    
    return generate_password(length)

# third refactor: remove the insertion in the tree from add_password
def insert_into_tree(ui, service, username, password):
    if service not in ui.service_nodes:
        parent_id = ui.tree.insert("", "end", text=service, open=True)
        ui.service_nodes[service] = parent_id
    else:
        parent_id = ui.service_nodes[service]

    ui.tree.insert(parent_id, "end", values=(username, password))

# fourth refactor: remove the reset of the entry fields from add_password
def clear_inputs(ui):
    ui.entry_service.delete(0, "end")
    ui.entry_pass.delete(0, "end")
    ui.entry_user.delete(0, "end")

# fifth refactor: remove the status label configuration from add_password
def set_status(ui, message, color="green"):
    ui.status_lbl.configure(text=message, text_color=color)
    ui.status_lbl.after(2000, lambda: ui.status_lbl.configure(text=""))

# delete selected entries
def delete_selected(ui, manager):
    selected_items = ui.tree.selection() # list of selected items
    if not selected_items:
        show_info_dialog("Warning", "No entry selected!")
        return # if no items are selected do nothing

    confirm = messagebox.askyesno(
        "Confirm Delete", "Are you sure you want to delete the entries?"
    )
    if not confirm:
        return

    # refresh the json file
    data = manager.load_data()

    for item_id in selected_items:
        parent = ui.tree.parent(item_id)

        if not parent:
            service = ui.tree.item(item_id)["text"]
            ui.tree.delete(item_id)
        else:
            service = ui.tree.item(parent)["text"]
            username, password = ui.tree.item(item_id)["values"]

            # remove from tree
            ui.tree.delete(item_id)

            # remove from json file
            manager.delete_entry(service, username, password)

    show_info_dialog("Info", "Selected entries deleted!")

# function to generate a random password
def generate_password(lenght=14):
    letters = string.ascii_letters #with the string library its possible to get string constants like letters
    numbers = string.digits #digits
    special = string.punctuation # and special symbols
    
    all = letters + numbers + special #put all strings together

    password = "".join((secrets.choice(all) for i in range(lenght))) #.join the previous string and randomize them

    return password





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

# to make the fields in the table editable we need a new function as ttk doesnt support it
def start_edit(event, ui):
    item_id = ui.tree.focus()
    column = ui.tree.identify_column(event.x)

    if not item_id:
        return
    
    if column == "#0":
        return

    parent = ui.tree.parent(item_id)
    if not parent:
        return
    
    col_index = int(column.replace("#", "")) - 1

    x, y, width, height = ui.tree.bbox(item_id, column) # get the bounding box of the selected cell

    value = ui.tree.item(item_id, "values")[col_index]

    entry = ctk.CTkEntry(ui.tree, width=width, height=height)
    entry.place(x=x, y=y)
    entry.insert(0, value)
    entry.focus()
    entry.bind("<Escape>", lambda e: entry.destroy())
    entry.select_range(0, "end")

    def save_edit(event=None):
        new_value = entry.get()
        values = list(ui.tree.item(item_id, "values"))
        values[col_index] = new_value
        ui.tree.item(item_id, values=values)

        update_json_after_edit(ui, manager, item_id, values)

        entry.destroy()
    
    entry.bind("<Return>", save_edit)
    entry.bind("<FocusOut>", lambda e: entry.destroy())

def update_json_after_edit(ui, manager, item_id, new_values):
    parent = ui.tree.parent(item_id)
    service = ui.tree.item(parent)["text"]

    old_values = ui.tree.item(item_id)["values"]

    old_username, old_password = old_values
    new_username, new_password = new_values

    manager.update_entry(
        service,
        old_username,
        old_password,
        new_username,
        new_password
    )

# function to copy the password directly to clipboard
def copy_to_clipboard(event):
    item_id = ui.tree.focus()
    column = ui.tree.identify_column(event.x)

    parent = ui.tree.parent(item_id)
    if not parent:
        return
    
    values = ui.tree.item(item_id)["values"]

    if len(values) < 2:
        return
    
    text = None

    if column == "#1":
        text = values[0]
        ui.status_lbl.configure(text="Username copied!")

    elif column == "#2":
        text = values[1]
        ui.status_lbl.configure(text="Password copied!")

    if text is None:
        return
    
    pyperclip.copy(text) # use pyperclip to copy to clipboard

    ui.status_lbl.after(2000, lambda: ui.status_lbl.configure(text="")) # set the status label empty after 2 seconds

# function to sort the columns
def treeview_sort_column(tv, col, reverse=False):
    # read all items from the treeview
    l = [(tv.set(k, col) if col != "#0" else tv.item(k, "text"), k) for k in tv.get_children('')]

    # sort numerical
    try:
        l.sort(key=lambda t: float(t[0]) if t[0] != "" else float('-inf'), reverse=reverse)
    except ValueError: # fallback to alphabetical
        l.sort(key=lambda t: t[0].lower(), reverse=reverse)

    # adjust order in treeview
    for index, (val, k) in enumerate(l):
        tv.move(k, '', index)

    # clikcing switches order
    tv.heading(col, command=lambda: treeview_sort_column(tv, col, not reverse))

# functions to enable searching for services via strings
def filter_tree(search_text):
    search_text = search_text.lower().strip()

    if search_text == "":
        # if field is empty show everything
        for parent_id in ui.service_nodes.values():
            ui.tree.reattach(parent_id, '', 'end')

        return
    
    # apply filter
    for service, parent_id in ui.service_nodes.items():
        if search_text in service.lower():
            ui.tree.reattach(parent_id, '', 'end')
        else:
            ui.tree.detach(parent_id)

def on_change_search(*args):
    filter_tree(search_var.get())

# functions for cryptography that the json file is encrypted
def generate_key(master_password: str, salt: bytes):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390_000
    )

    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))



def is_password_file_empty():
    if not os.path.exists(password_file):
        return True
    with open(password_file, "r") as f:
        try:
            data = json.load(f)
            return not bool(data)
        except json.JSONDecodeError:
            return True
        
def setup_master_password():
    if is_password_file_empty():
        # new user, set new password
        dialog = ctk.CTkToplevel(app)#
        dialog.title("Set Master Password")
        dialog.geometry("300x180")


        result = {"password": None}

        ctk.CTkLabel(dialog, text="Set a Master Password:").pack(pady=10)
        entry1 = ctk.CTkEntry(dialog, show="*")
        entry1.pack(pady=5, padx=10)
        entry1.focus()

        ctk.CTkLabel(dialog, text="Confirm Master Password:").pack(pady=5)
        entry2 = ctk.CTkEntry(dialog, show="*")
        entry2.pack(pady=5, padx=10)

        def confirm():
            pwd1 = entry1.get().strip()
            pwd2 = entry2.get().strip()

            if not pwd1:
                show_info_dialog("Warning", "Passwords cannot be empty!")
                return
            if pwd1 != pwd2:
                show_info_dialog("Warning", "Passwords do not match!")
                return

            result["password"] = pwd1
            dialog.destroy()

        ctk.CTkButton(dialog, text="Set Password", command=confirm).pack(pady=10)
        dialog.wait_visibility()
        dialog.grab_set()
        app.wait_window(dialog)
        return result["password"]
    
    else:
        return ask_master_password()
    

def ask_master_password(max_attempts=3):
    attempts = 0
    while attempts < max_attempts:
        dialog = ctk.CTkToplevel(app)
        dialog.title("Master Password")
        dialog.geometry("300x150")
        

        result = {"password": None}

        ctk.CTkLabel(dialog, text="Enter Master Password:").pack(pady=10)
        entry = ctk.CTkEntry(dialog, show="*")
        entry.pack(pady=5, padx=10)
        entry.focus()

        def confirm():
            pwd = entry.get().strip()

            if not pwd:
                show_info_dialog("Warning", "Password cannot be empty!")
                return
            result["password"] = pwd
            dialog.destroy()

        ctk.CTkButton(dialog, text="OK", command=confirm).pack(pady=10)

        dialog.wait_visibility()
        dialog.grab_set()
        app.wait_window(dialog)

        if not result["password"]:
            attempts += 1
            continue

        try:
            key = generate_key(result["password"], salt)
            fernet_test = Fernet(key)

            if os.path.exists(password_file):
                with open(password_file, "r") as f:
                    data = json.load(f)

                for service, accounts in data.items():
                    for acc in accounts:
                        fernet_test.decrypt(acc["password"].encode())
                        break
                    break
        except Exception:
            attempts += 1
            if attempts < max_attempts:
                show_info_dialog("Warning", f"Wrong Password! {max_attempts-attempts} attempts left.")
                continue
            else:
                show_info_dialog("Error", "Maximum attempts reached! Closing app")
                return None
        
        return result["password"]
    return None


################################################################################
#
#
# initiate the GUI
#
#
################################################################################
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
ui = UIState()
app.geometry("800x400")
app.title("Mini Password Manager")

master_password = setup_master_password()
if not master_password:
    app.destroy()
    exit()

key = generate_key(master_password, salt)
fernet = Fernet(key)

manager = PasswordManager(password_file, fernet)

# frame for the entry field
frame_top = ctk.CTkFrame(app)
frame_top.pack(pady=10, padx=10, fill="x")

# label for the entry field
entry_lbl = ctk.CTkLabel(frame_top, text="Password entry")
entry_lbl.grid(row=0, column=0, padx=5, pady=5, columnspan=4, sticky="w")

note_lbl = ctk.CTkLabel(frame_top, text="If no password is entered it will be given by random")
note_lbl.grid(row=1, column=0, padx=5, pady=5, columnspan=4, sticky="w")

# entry fields
ui.entry_service = ctk.CTkEntry(frame_top, placeholder_text="Service/Website")
ui.entry_service.grid(row=2, column=0, padx=5, pady=5)

ui.entry_user = ctk.CTkEntry(frame_top, placeholder_text="Username")
ui.entry_user.grid(row=2, column=1, padx=5, pady=5)

ui.entry_pass = ctk.CTkEntry(frame_top, placeholder_text="Password")
ui.entry_pass.grid(row=2, column=2, padx=5, pady=5)

# buttons
btn_add = ctk.CTkButton(frame_top, text="Add", command=lambda: add_password(ui, manager))
btn_add.grid(row=2, column=3, padx=5, pady=5)

btn_delete = ctk.CTkButton(frame_top, text="Delete", command=lambda: delete_selected(ui, manager))
btn_delete.grid(row=2, column=4, padx=5, pady=5)

# status label
ui.status_lbl = ctk.CTkLabel(frame_top, text="", text_color="green")
ui.status_lbl.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky="w")

# search block
search_var = ctk.StringVar()

search_var.trace_add("write", on_change_search)

ctk.CTkLabel(frame_top, text="Search Service/Website:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
search_entry = ctk.CTkEntry(frame_top, textvariable=search_var)
search_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w", columnspan=2)

# optional search button
# ctk.CTkButton(frame_top, text="Search", command= lambda: filter_tree(search_var.get())).grid(row=4, column=3, padx=5, pady=5)

# Treeview for password table
frame_tree = ctk.CTkFrame(app)
frame_tree.pack(padx=10, pady=10, fill="both", expand=True)

ui.tree = ttk.Treeview(
    frame_tree, 
    columns=("Username", "Password"), 
    show="tree headings", 
    selectmode="extended") # with extended we can select multiple rows (important for deleting)
ui.tree.heading("#0", text="Service/Website", command=lambda: treeview_sort_column(ui.tree, "#0", False))
ui.tree.heading("Username", text="Username", command=lambda: treeview_sort_column(ui.tree, "Username", False))
ui.tree.heading("Password", text="Password", command=lambda: treeview_sort_column(ui.tree, "Password", False))

ui.tree.column("#0", width=200)
ui.tree.column("Username", width=150)
ui.tree.column("Password", width=150)



ui.tree.pack(fill="both", expand=True, side="left")

ui.tree.bind("<F2>", lambda e: start_edit(e, ui, manager))
ui.tree.bind("<Double-1>", copy_to_clipboard)

# Scrollbar
scrollbar = ctk.CTkScrollbar(frame_tree, orientation="vertical", command=ui.tree.yview)
scrollbar.pack(side="right", fill="y")
ui.tree.configure(yscrollcommand=scrollbar.set)

# to group usernames and passwords with the same service we need to save them in a dictionary
ui.service_nodes = {}

# load data at start
for service, accounts in manager.load_data().items():

    if isinstance(accounts, dict):
        accounts = [accounts]

    parent_id = ui.tree.insert("", "end", text=service, open=True)
    ui.service_nodes[service] = parent_id

    for acc in accounts:
        ui.tree.insert(parent_id, "end", values=(acc["username"], acc["password"]))

app.mainloop()