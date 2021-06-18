from PIL import Image, ImageTk
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from ttkthemes import ThemedStyle
from ctypes import windll


class AutoScrollbar(ttk.Scrollbar):
    ''' A scrollbar that hides itself if it's not needed.
        Works only if you use the grid geometry manager '''
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
        ttk.Scrollbar.set(self, lo, hi)

    def pack(self, **kw):
        raise tk.TclError('Cannot use pack with this widget')

    def place(self, **kw):
        raise tk.TclError('Cannot use place with this widget')

class Zoom(tk.Frame):

  def __init__(self, mainframe):
      ''' Initialize the main Frame '''
      ttk.Frame.__init__(self, master=mainframe)
      # Vertical and horizontal scrollbars for canvas
      vbar = AutoScrollbar(self.master, orient='vertical')
      hbar = AutoScrollbar(self.master, orient='horizontal')
      vbar.grid(row=0, column=1, sticky='ns')
      hbar.grid(row=1, column=0, sticky='we')
      # Open image
      self.image = None
      # Create canvas and put image on it
      self.canvas = tk.Canvas(self.master, highlightthickness=0,
                              xscrollcommand=hbar.set, yscrollcommand=vbar.set,
                              bg='grey')
      self.canvas.grid(row=0, column=0, sticky='nswe')
      vbar.configure(command=self.canvas.yview)  # bind scrollbars to the canvas
      hbar.configure(command=self.canvas.xview)
      # Make the canvas expandable
      self.master.rowconfigure(0, weight=1)
      self.master.columnconfigure(0, weight=1)

      # Bind events to the Canvas
      # move around
      self.canvas.bind('<ButtonPress-2>', self.move_from)
      self.canvas.bind('<B2-Motion>',     self.move_to)
      # zoom in
      self.canvas.bind('<MouseWheel>', self.wheel)  # with Windows and MacOS, but not Linux
      self.canvas.bind('<Button-5>',   self.wheel)  # only with Linux, wheel scroll down
      self.canvas.bind('<Button-4>',   self.wheel)  # only with Linux, wheel scroll up
      # selection
      self.canvas.bind('<ButtonPress-1>', self.__update_select)
      self.canvas.bind('<B1-Motion>',     self.__update_select)
      self.canvas.bind('<ButtonRelease-1>', self.__end_select)
      self.canvas.bind('<ButtonPress-3>', self.__delete_select)
      # cropping
      self.master.bind('<Control-s>', self.__crop)

      # variables for selection
      self.start = None
      self.item = None

      # Show image and plot
      self.imscale = 1.0
      self.imageid = None
      self.delta = 0.75
      self.bg = 'grey'
      # Text is used to set proper coordinates to the image. You can make it invisible.
      self.text = self.canvas.create_text(0, 0, anchor='nw', text='')
      self.canvas.configure(scrollregion=self.canvas.bbox('all'))

  # selection functions

  def draw(self, start, end):
    return self.canvas.create_rectangle(list(start)+list(end), dash=(3, 5))

  def __update_select(self, event):
    x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

    if not self.start:
      self.start = [x, y]
      return

    if self.item is not None:
      self.canvas.delete(self.item)
    
    self.item = self.draw(self.start, (x, y))
    
  def __end_select(self, event):
    self.start = None

  def __delete_select(self, event):
    self.start = None
    self.canvas.delete(self.item)
    self.item = None

  def __crop(self, event):
    truecoords = self.canvas.coords(self.text)
    rect_coords = self.canvas.coords(self.item)

    # there's some absolute black magic going on here
    # i realized it in a moment of divine revelation and even now, 2 minutes after writing this code,
    # can't tell you why it works
    offset_x = truecoords[0]/self.imscale
    offset_y = truecoords[1]/self.imscale
    crop_area = [c/self.imscale for c in rect_coords]
    crop_area[0] = crop_area[0] - offset_x
    crop_area[1] = crop_area[1] - offset_y
    crop_area[2] = crop_area[2] - offset_x
    crop_area[3] = crop_area[3] - offset_y

    image_copy = self.image
    image_copy = image_copy.crop(crop_area)
    
    save_path = filedialog.asksaveasfilename(filetypes=[('PNG image file', '.png'), ('all files', '.*')], defaultextension='.png')
    file_name = save_path.split('.')[0]
    image_copy.save(file_name+'.png')

  def move_from(self, event):
      ''' Remember previous coordinates for scrolling with the mouse '''
      self.canvas.scan_mark(event.x, event.y)
      self.show_image()

  def move_to(self, event):
      ''' Drag (move) canvas to the new position '''
      self.canvas.scan_dragto(event.x, event.y, gain=1)
      self.show_image()

  def wheel(self, event):
      ''' Zoom with mouse wheel '''
      self.__delete_select(None)
      scale = 1.0
      if self.imscale > 6 and event.delta == 120:
        return
      if event.delta == -120:
          scale        -= .5
          self.imscale -= .5
      if event.delta == 120:
          scale        += 1
          self.imscale += 1
      # Rescale all canvas objects
      x = self.canvas.canvasx(event.x)
      y = self.canvas.canvasy(event.y)
      self.canvas.scale('all', x, y, scale, scale)
      self.show_image()
      self.canvas.configure(scrollregion=self.canvas.bbox('all'))

  def show_image(self):
      ''' Show image on the Canvas '''
      if self.imageid:
          self.canvas.delete(self.imageid)
          self.imageid = None
          self.canvas.imagetk = None  # delete previous image from the canvas
      width, height = self.image.size
      new_size = int(self.imscale * width), int(self.imscale * height)
      imagetk = ImageTk.PhotoImage(self.image.resize(new_size, Image.NEAREST))
      # Use self.text object to set proper coordinates
      self.imageid = self.canvas.create_image(self.canvas.coords(self.text),
                                              anchor='nw', image=imagetk)
      self.canvas.lower(self.imageid)  # set it into background
      self.canvas.imagetk = imagetk  # keep an extra reference to prevent garbage-collection

  def set_image(self):
    path = filedialog.askopenfilename()
    self.image = Image.open(path)
    self.__delete_select(None)
    self.show_image()


if __name__ == '__main__':
  # set up tkInter basics
  windll.shcore.SetProcessDpiAwareness(1)
  root = tk.Tk()
  root.resizable(False, False)
  root.iconbitmap('icon.ico')
  root.wm_title('tecemma')

  # configure style
  style = ThemedStyle(root)
  style.theme_use("black")
  bg = style.lookup('TLabel', 'background')
  fg = style.lookup('TLabel', 'foreground')
  root.configure(bg=style.lookup('TLabel', 'background'))
  
  # load MainScreen
  app = Zoom(root)

  # create image selection button
  imageSelectButton = ttk.Button(root, text ='Select new image', command=app.set_image)
  imageSelectButton.grid()
  
  # set window size to screen size 
  width  = root.winfo_screenwidth()
  height = root.winfo_screenheight()
  root.geometry('775x450')

  root.mainloop()