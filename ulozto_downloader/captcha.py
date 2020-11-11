import requests

# Imports for GUI:
import tkinter as tk
from PIL import Image, ImageTk
from io import BytesIO


def tkinter_user_prompt(img_url):
    """Display captcha from given URL and ask user for input in GUI window.

        Arguments:
            img_url (str): URL of the image with CAPTCHA

        Returns:
            str: User answer to the CAPTCHA
    """

    root = tk.Tk()
    root.focus_force()
    root.title("Opiš kód z obrázku")
    root.geometry("300x140")  # use width x height + x_offset + y_offset (no spaces!)

    def disable_event():
        pass

    root.protocol("WM_DELETE_WINDOW", disable_event)

    u = requests.get(img_url)
    raw_data = u.content

    im = Image.open(BytesIO(raw_data))
    photo = ImageTk.PhotoImage(im)
    label = tk.Label(image=photo)
    label.image = photo
    label.pack()

    entry = tk.Entry(root)
    entry.pack()
    entry.bind('<Return>', lambda event: root.quit())
    entry.focus()

    tk.Button(root, text='Send', command=root.quit).pack()

    root.mainloop()  # Wait for user input
    value = entry.get()
    root.destroy()
    return value
