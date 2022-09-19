"""UI module
"""

from threading import Thread
from pdb import set_trace

import tkinter as tk
from tkinter.ttk import Progressbar

from .proc import run_model


class ParcelGenUI:
    """ ParcelGen UI class
    """
    def __init__(self, args):
        """ParcelGenUI constructor

        :param args: Arguments to be passed to the run_model processing
        :type args: tuple
        """
        # Set graphics parameters
        self.width = 500
        self.height = 60

        # Create a GUI window
        self.root = tk.Tk()
        self.root.title("Progress Parcel Demand")
        self.root.geometry(f'{self.width}x{self.height}+0+200')
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height, bg='black')
        self.canvas.place(x=0, y=0)
        self.status_bar = tk.Label(self.root, text="", anchor='w', borderwidth=0, fg='black')
        self.status_bar.place(x=2, y=self.height-22, width=self.width, height=22)

        # Remove the default tkinter icon from the window
        # b64str = 'eJxjYGAEQgEBBiDJwZDBy''sAgxsDAoAHEQCEGBQaIOAg4sDIgACMUj4JRMApGwQgF/ykEAFXxQRc='
        # icon = zlib.decompress(base64.b64decode(b64str))
        # _, self.iconPath = tempfile.mkstemp()
        # with open(self.iconPath, 'wb') as iconFile:
        #     iconFile.write(icon)
        # self.root.iconbitmap(bitmap=self.iconPath)

        # Create a progress bar
        self.progress_bar = Progressbar(self.root, length=self.width-20)
        self.progress_bar.place(x=10, y=10)

        self.return_info = ""
        self.args = args

        set_trace()

        self.run_module()

        # Keep GUI active until closed
        self.root.mainloop()

    def update_statusbar(self, text):
        """Updates status bar with the text input.

        :param text: The input text
        :type text: str
        """
        self.status_bar.configure(text=text)

    def error_screen(self, text="", event=None, size=(800, 50), title='Error message'):
        """A screen to be displayed in the case of an error

        :param text: Text to be displayed, defaults to ""
        :type text: str, optional
        :param event: Event handler object, defaults to None
        :type event: _type_, optional
        :param size: The size of the window, defaults to (800, 50)
        :type size: tuple, optional
        :param title: The title text, defaults to 'Error message'
        :type title: str, optional
        """
        window_error = tk.Toplevel(self.root)
        window_error.title(title)
        window_error.geometry(f'{size[0]}x{size[1]}+0+{200+50+self.height}')
        window_error.minsize(width=size[0], height=size[1])
        # windowError.iconbitmap(default=self.iconPath)
        label_error = tk.Label(window_error, text=text, anchor='w', justify='left')
        label_error.place(x=10, y=10)

    def run_module(self, event=None):
        """Runs the simulation

        :param event: Event handler object, defaults to None
        :type event: str, optional
        """
        Thread(target=run_model, args=(self.args,), kwargs={'root': self}, daemon=True).start()
