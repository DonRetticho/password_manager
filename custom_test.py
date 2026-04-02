import customtkinter as ctk

def password_save():
    username = user_entry.get()
    password = password_entry.get()
    print(f"username: {username}, password: {password}")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("400x300")


# label definitions
label = ctk.CTkLabel(app, text="Mein Password Manager")

# button definitions
button = ctk.CTkButton(app, text="Klick mich", command=password_save)

# entry field definitions
user_entry = ctk.CTkEntry(app, placeholder_text="Username")
password_entry = ctk.CTkEntry(app, placeholder_text="Password")

# grid layout
label.grid(row=0, column=0, padx=10, pady=10)

user_entry.grid(row=1, column=0, padx=10, pady=10)
password_entry.grid(row=1, column=1, padx=10, pady=10)

button.grid(row=2, column=0, padx=10, pady=10)

app.mainloop()