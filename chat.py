from customtkinter import *
from socket import socket, AF_INET, SOCK_STREAM
import threading
import base64
import io
from PIL import Image

HOST = "5.tcp.eu.ngrok.io"
PORT = 16781
DEFAULT_USERNAME = "Guest"

def bytes_to_mb(n: int) -> float:
    return n / (1024 * 1024)

class App(CTk):
  def __init__(self):
    super().__init__()
    self.title("LogiTalk")
    self.geometry("800x600")
    self.minsize(600, 400)
    self.username = DEFAULT_USERNAME

    self.menu_width_min = 0
    self.menu_width_max = 200
    self.menu_width_current = self.menu_width_min
    self.menu_expanded = False

    # Layout 
    self.grid_columnconfigure(1, weight=1)
    self.grid_rowconfigure(0, weight=1)
    self.grid_rowconfigure(1, weight=0)

    # Menu
    self.menu_frame = CTkFrame(self)
    self.menu_frame.grid(row=0, column=0, rowspan=2, sticky="ns")
    self.menu_frame.grid_propagate(False)

    self.menu_button = CTkButton(self.menu_frame, text="☰", width=30, command=self.toggle_menu)
    self.menu_button.pack(padx=5, pady=5, anchor="ne")

    self.nickname_label = CTkLabel(self.menu_frame, text=f"Нікнейм:\n{self.username}", justify="center")

    # Chat
    self.chat_frame = CTkScrollableFrame(self)
    self.chat_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=5)

    # Input
    self.input_frame = CTkFrame(self)
    self.input_frame.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
    self.input_frame.grid_columnconfigure(0, weight=1)

    self.message_entry = CTkEntry(self.input_frame, placeholder_text="Введіть повідомлення...")
    self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0,5))

    self.open_img_button = CTkButton(self.input_frame, text="📂", width=50, command=self.open_image)
    self.open_img_button.grid(row=0, column=1, padx=(0,5))

    self.send_button = CTkButton(self.input_frame, text="Відправити", command=self.send_message)
    self.send_button.grid(row=0, column=2)

    # Підключення до серверу
    self.sock = None
    try: 
      self.sock = socket(AF_INET, SOCK_STREAM)
      self.sock.connect((HOST, PORT))
      hello = f"TEXT@{self.username} приєднався(лась) до чату."
      self.sock.send(hello.encode('utf-8'))
      threading.Thread(target=self.ressive_message, daemon=True).start()
    except Exception as e:
      self.add_message(f"Не вдалося підключитися до серверу: {e}")

  # Розкривання меню
  def toggle_menu(self):
    self.menu_expanded = not self.menu_expanded
    self.menu_button.configure(text="✕" if self.menu_expanded else "☰")
    self.animate_menu()

    for widget in self.menu_frame.winfo_children():
      if widget not in (self.menu_button, self.nickname_label):
        widget.destroy()
    
    if self.menu_expanded:
      self.nickname_label.configure(text=f"Нікнейм:\n{self.username}")
      self.nickname_label.pack(pady=(40,10))
      label = CTkLabel(self.menu_frame, text="Меню", font=("Arial", 16))
      label.pack(pady=10)
      label_nickname = CTkLabel(self.menu_frame, text="Змінити нікнейм:")
      label_nickname.pack(pady=(20,5))
      self.nickname_entry = CTkEntry(self.menu_frame, placeholder_text="Ваш нік...")
      self.nickname_entry.pack(pady=5, padx=10)
      change_button = CTkButton(self.menu_frame, text="Змінити", command=self.change_nickname)
      change_button.pack(pady=5)
  
  def animate_menu(self):
    if self.menu_expanded and self.menu_width_current < self.menu_width_max:
      self.menu_width_current += 10
      self.menu_button.configure(width=self.menu_width_current)
      self.grid_columnconfigure(0, minsize=self.menu_width_current)
      self.after(10, self.animate_menu)
    elif not self.menu_expanded and self.menu_width_current > self.menu_width_min:
      self.menu_width_current -= 10
      self.menu_button.configure(width=self.menu_width_current)
      self.grid_columnconfigure(0, minsize=self.menu_width_current)
      self.after(10, self.animate_menu)

  def send_message(self):
    message = self.message_entry.get().strip()
    if message:
      self.add_message(f"{self.username}: {message}", side="right")
      data = f"TEXT@{self.username}@{message}\n"
      try:
         if self.sock:
            self.sock.sendall(data.encode('utf-8'))
      except Exception as e:
         self.add_message(f"Не вдалося надіслати повідомлення: {e}")
    self.message_entry.delete(0, 'end')

  def _calc_wraplength(self):
    # запас 100 пікселів під падінги/кнопки + ширина меню
    return max(200, self.winfo_width() - self.menu_width_current - 100)

  def add_message(self, message, side="left", img=None):
    wraplength = self._calc_wraplength()
    frame = CTkFrame(self.chat_frame, fg_color="#410E84", corner_radius=10)
    frame.pack(pady=5, anchor="w", padx=10)
    if img:
       label = CTkLabel(frame, text=message, image=img, wraplength=wraplength, justify="left", text_color="#ffffff", anchor="w", compound="top")
    else:
      label = CTkLabel(frame, text=message, wraplength=wraplength, justify="left", text_color="#ffffff", anchor="w")
    label.pack(padx=10, pady=5)
    if side == "right":
      frame.pack_configure(anchor="e")
  
  def ressive_message(self):
    buffer = ""
    try:
      while True:
        data = self.sock.recv(4096)
        if not data:
          break
        buffer += data.decode('utf-8', errors='ignore')
        while '\n' in buffer:
          message, buffer = buffer.split('\n', 1)
          self.handle_line(message.strip())
    except Exception:
      pass
    finally:
      try:
        if self.sock:
          self.sock.close()
      except Exception:
        pass
      self.add_message("Відключено від серверу.")

  def handle_line(self, line):
       if not line:
           return
       parts = line.split("@", 3)
       msg_type = parts[0]

       if msg_type == "TEXT":
           if len(parts) >= 3:
               author = parts[1]
               message = parts[2]
               self.add_message(f"{author}: {message}")
       elif msg_type == "IMAGE":
           if len(parts) >= 4:
               author = parts[1]
               filename = parts[2]
               b64_img = parts[3]
               try:
                   img_data = base64.b64decode(b64_img)
                   pil_img = Image.open(io.BytesIO(img_data))
                   ctk_img = CTkImage(pil_img, size=(300, 300))
                   self.add_message(f"{author} надіслав(ла) зображення: {filename}", img=ctk_img)
               except Exception as e:
                   self.add_message(f"Помилка відображення зображення: {e}")
       else:
           self.add_message(line)
  
  def open_image(self):
     file_name = filedialog.askopenfilename(title="Виберіть зображення", filetypes=[("Image Files", "*.jpg;*.jpeg;")])
     if not file_name:
        return
     try:
        with open(file_name, "rb") as f:
           raw = f.read()
        
        size_mb = bytes_to_mb(len(raw))
        if size_mb > 5:
           self.add_message("Розмір зображення перевищує 5 МБ.")
           return

        b64_data = base64.b64encode(raw).decode()
        short_name = os.path.basename(file_name)
        data = f"IMAGE@{self.username}@{short_name}@{b64_data}\n"

        if self.sock:
           self.sock.sendall(data.encode('utf-8'))
        
        with Image.open(io.BytesIO(raw)) as pil_img:
           pil_img.thumbnail((800, 800))
           ctk_img = CTkImage(pil_img, size=(min(300, pil_img.width), min(300, pil_img.height)))
        
        self.add_message(f"Ви надіслали зображення: {short_name}", img=ctk_img, side="right")
     except Exception as e:
        self.add_message(f"Не вдалося надіслати зображення: {e}")

  def change_nickname(self):
     new_nick = self.nickname_entry.get().strip()
     if new_nick:
       old_nick = self.username
       self.username = new_nick
       self.nickname_label.configure(text=f"Нікнейм:\n{self.username}")
       notice = f"TEXT@{old_nick} змінив(ла) нікнейм на {self.username}."
       try:
         if self.sock:
           self.sock.sendall(notice.encode('utf-8'))
       except Exception as e:
         self.add_message(f"Не вдалося повідомити про зміну ніку: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
    