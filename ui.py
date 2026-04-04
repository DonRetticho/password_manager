import customtkinter as ctk
from tkinter import ttk, messagebox
import pyperclip
from manager import PasswordManager, generate_key
from cryptography.fernet import Fernet
import os
import json
from manager import PasswordManager

# ------------------- UI STATE -------------------
class UIState:
    def __init__(self):
        self.tree = None
        self.entry_service = None
        self.entry_user = None
        self.entry_pass = None
        self.status_lbl = None
        self.service_nodes = {}
        self.search_var = None


# ------------------- STATUS -------------------
def set_status(ui: UIState, message: str, color="green"):
    ui.status_lbl.configure(text=message, text_color=color)
    ui.status_lbl.after(2000, lambda: ui.status_lbl.configure(text=""))


# ------------------- TREE INSERT -------------------
def insert_into_tree(ui: UIState, service, username, password):
    if service not in ui.service_nodes:
        parent_id = ui.tree.insert("", "end", text=service, open=True)
        ui.service_nodes[service] = parent_id
    else:
        parent_id = ui.service_nodes[service]
    ui.tree.insert(parent_id, "end", values=(username, password))


# ------------------- CLEAR INPUTS -------------------
def clear_inputs(ui: UIState):
    ui.entry_service.delete(0, "end")
    ui.entry_user.delete(0, "end")
    ui.entry_pass.delete(0, "end")


# ------------------- VALIDATION -------------------
def validate_inputs(service, username):
    if not service:
        return "Service/Website is required!"
    if not username:
        return "Username is required!"


# ------------------- ADD PASSWORD -------------------
def add_password(ui: UIState, manager: PasswordManager):
    service = ui.entry_service.get()
    username = ui.entry_user.get()
    password = ui.entry_pass.get()

    error = validate_inputs(service, username)
    if error:
        set_status(ui, error, "red")
        return

    data = manager.load_data()
    if service in data and any(acc["username"] == username for acc in data[service]):
        set_status(ui, "This username already exists!", "red")
        return

    if not password:
        password = manager.generate_password()
        ui.entry_pass.insert(0, password)

    manager.save_data(service, username, password)
    insert_into_tree(ui, service, username, password)
    clear_inputs(ui)
    set_status(ui, "Entry added!")


# ------------------- DELETE SELECTED -------------------
def delete_selected(ui: UIState, manager: PasswordManager):
    selected_items = ui.tree.selection()
    if not selected_items:
        messagebox.showinfo("Warning", "No entry selected!")
        return

    confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the entries?")
    if not confirm:
        return

    for item_id in selected_items:
        parent = ui.tree.parent(item_id)
        if not parent:
            service = ui.tree.item(item_id)["text"]
            ui.tree.delete(item_id)
        else:
            service = ui.tree.item(parent)["text"]
            username, password = ui.tree.item(item_id)["values"]
            manager.delete_entry(service, username, password)
            ui.tree.delete(item_id)

    messagebox.showinfo("Info", "Selected entries deleted!")


# ------------------- TREEVIEW EDIT -------------------
def start_edit(event, ui: UIState, manager: PasswordManager):
    item_id = ui.tree.focus()
    column = ui.tree.identify_column(event.x)
    if not item_id or column == "#0":
        return

    parent = ui.tree.parent(item_id)
    if not parent:
        return

    col_index = int(column.replace("#", "")) - 1
    x, y, width, height = ui.tree.bbox(item_id, column)
    value = ui.tree.item(item_id, "values")[col_index]

    entry = ctk.CTkEntry(ui.tree, width=width, height=height)
    entry.place(x=x, y=y)
    entry.insert(0, value)
    entry.focus()
    entry.select_range(0, "end")

    def save_edit(event=None):
        new_value = entry.get()
        values = list(ui.tree.item(item_id, "values"))
        old_username, old_password = values
        values[col_index] = new_value
        ui.tree.item(item_id, values=values)

        new_username, new_password = values
        service = ui.tree.item(parent)["text"]
        manager.update_entry(service, old_username, old_password, new_username, new_password)
        entry.destroy()

    entry.bind("<Return>", save_edit)
    entry.bind("<Escape>", lambda e: entry.destroy())
    entry.bind("<FocusOut>", lambda e: entry.destroy())


# ------------------- COPY TO CLIPBOARD -------------------
def copy_to_clipboard(event, ui: UIState):
    item_id = ui.tree.focus()
    column = ui.tree.identify_column(event.x)
    parent = ui.tree.parent(item_id)
    if not parent or not item_id:
        return

    values = ui.tree.item(item_id)["values"]
    if len(values) < 2:
        return

    text = values[0] if column == "#1" else values[1] if column == "#2" else None
    if not text:
        return

    pyperclip.copy(text)
    set_status(ui, "Username copied!" if column == "#1" else "Password copied!")


# ------------------- TREE SORT -------------------
def treeview_sort_column(tv, col, reverse=False):
    l = [(tv.set(k, col) if col != "#0" else tv.item(k, "text"), k) for k in tv.get_children('')]
    try:
        l.sort(key=lambda t: float(t[0]) if t[0] != "" else float('-inf'), reverse=reverse)
    except ValueError:
        l.sort(key=lambda t: t[0].lower(), reverse=reverse)

    for index, (_, k) in enumerate(l):
        tv.move(k, '', index)
    tv.heading(col, command=lambda: treeview_sort_column(tv, col, not reverse))


# ------------------- SEARCH FILTER -------------------
def filter_tree(ui: UIState, search_text: str):
    search_text = search_text.lower().strip()
    if search_text == "":
        for parent_id in ui.service_nodes.values():
            ui.tree.reattach(parent_id, '', 'end')
        return

    for service, parent_id in ui.service_nodes.items():
        if search_text in service.lower():
            ui.tree.reattach(parent_id, '', 'end')
        else:
            ui.tree.detach(parent_id)


def on_change_search(*args, ui: UIState = None):
    filter_tree(ui, ui.search_var.get())


# ------------------- INITIALIZE TREE -------------------
def populate_tree(ui: UIState, manager: PasswordManager):
    for service, accounts in manager.load_data().items():
        parent_id = ui.tree.insert("", "end", text=service, open=True)
        ui.service_nodes[service] = parent_id
        for acc in accounts:
            ui.tree.insert(parent_id, "end", values=(acc["username"], acc["password"]))