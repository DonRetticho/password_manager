import customtkinter as ctk
from tkinter import ttk, messagebox
import os
import json
import pyperclip
from cryptography.fernet import Fernet
from manager import PasswordManager, generate_key
from ui import UIState, add_password, delete_selected, start_edit, copy_to_clipboard, treeview_sort_column, populate_tree, on_change_search

# ------------------- CONFIG -------------------
PASSWORD_FILE = "passwords.json"
SALT_FILE = "salt.bin"

# Ensure salt exists
if not os.path.exists(SALT_FILE):
    with open(SALT_FILE, "wb") as f:
        f.write(os.urandom(16))

with open(SALT_FILE, "rb") as f:
    salt = f.read()


# ------------------- APP INIT -------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("800x450")
app.title("Mini Password Manager")

ui = UIState()

# ------------------- MASTER PASSWORD -------------------
def is_password_file_empty():
    if not os.path.exists(PASSWORD_FILE):
        return True
    with open(PASSWORD_FILE, "r") as f:
        try:
            data = json.load(f)
            return not bool(data)
        except json.JSONDecodeError:
            return True

def setup_master_password():
    if is_password_file_empty():
        dialog = ctk.CTkToplevel(app)
        dialog.title("Set Master Password")
        dialog.geometry("300x180")
        result = {"password": None}

        ctk.CTkLabel(dialog, text="Set a Master Password:").pack(pady=10)
        entry1 = ctk.CTkEntry(dialog, show="*")
        entry1.pack(pady=5)
        entry1.focus()

        ctk.CTkLabel(dialog, text="Confirm Master Password:").pack(pady=5)
        entry2 = ctk.CTkEntry(dialog, show="*")
        entry2.pack(pady=5)

        def confirm():
            pwd1 = entry1.get().strip()
            pwd2 = entry2.get().strip()
            if not pwd1:
                messagebox.showwarning("Warning", "Password cannot be empty!")
                return
            if pwd1 != pwd2:
                messagebox.showwarning("Warning", "Passwords do not match!")
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
        entry.pack(pady=5)
        entry.focus()

        def confirm():
            pwd = entry.get().strip()
            if not pwd:
                messagebox.showwarning("Warning", "Password cannot be empty!")
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
            key_test = generate_key(result["password"], salt)
            Fernet(key_test)
            return result["password"]
        except Exception:
            attempts += 1
            if attempts >= max_attempts:
                messagebox.showerror("Error", "Maximum attempts reached! Closing app.")
                return None
            messagebox.showwarning("Warning", f"Wrong Password! {max_attempts - attempts} attempts left.")
    return None

master_password = setup_master_password()
if not master_password:
    app.destroy()
    exit()

key = generate_key(master_password, salt)
fernet = Fernet(key)

manager = PasswordManager(PASSWORD_FILE, fernet)

# ------------------- UI LAYOUT -------------------
# Top Frame
frame_top = ctk.CTkFrame(app)
frame_top.pack(pady=10, padx=10, fill="x")

# Entries
ui.entry_service = ctk.CTkEntry(frame_top, placeholder_text="Service/Website")
ui.entry_service.grid(row=0, column=0, padx=5, pady=5)

ui.entry_user = ctk.CTkEntry(frame_top, placeholder_text="Username")
ui.entry_user.grid(row=0, column=1, padx=5, pady=5)

ui.entry_pass = ctk.CTkEntry(frame_top, placeholder_text="Password")
ui.entry_pass.grid(row=0, column=2, padx=5, pady=5)

# Buttons
btn_add = ctk.CTkButton(frame_top, text="Add", command=lambda: add_password(ui, manager))
btn_add.grid(row=0, column=3, padx=5, pady=5)

btn_delete = ctk.CTkButton(frame_top, text="Delete", command=lambda: delete_selected(ui, manager))
btn_delete.grid(row=0, column=4, padx=5, pady=5)

# Status Label
ui.status_lbl = ctk.CTkLabel(frame_top, text="", text_color="green")
ui.status_lbl.grid(row=1, column=0, columnspan=5, sticky="w")

# Search
ui.search_var = ctk.StringVar()
ui.search_var.trace_add("write", lambda *args: on_change_search(*args, ui=ui))

ctk.CTkLabel(frame_top, text="Search Service:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
search_entry = ctk.CTkEntry(frame_top, textvariable=ui.search_var)
search_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w", columnspan=2)

# Tree Frame
frame_tree = ctk.CTkFrame(app)
frame_tree.pack(padx=10, pady=10, fill="both", expand=True)

ui.tree = ttk.Treeview(frame_tree, columns=("Username", "Password"), show="tree headings", selectmode="extended")
ui.tree.heading("#0", text="Service", command=lambda: treeview_sort_column(ui.tree, "#0"))
ui.tree.heading("Username", text="Username", command=lambda: treeview_sort_column(ui.tree, "Username"))
ui.tree.heading("Password", text="Password", command=lambda: treeview_sort_column(ui.tree, "Password"))

ui.tree.column("#0", width=200)
ui.tree.column("Username", width=150)
ui.tree.column("Password", width=150)
ui.tree.pack(fill="both", expand=True, side="left")

# Scrollbar
scrollbar = ctk.CTkScrollbar(frame_tree, orientation="vertical", command=ui.tree.yview)
scrollbar.pack(side="right", fill="y")
ui.tree.configure(yscrollcommand=scrollbar.set)

# Bindings
ui.tree.bind("<F2>", lambda e: start_edit(e, ui, manager))
ui.tree.bind("<Double-1>", lambda e: copy_to_clipboard(e, ui))

# Populate Tree
populate_tree(ui, manager)

# ------------------- START APP -------------------
app.mainloop()