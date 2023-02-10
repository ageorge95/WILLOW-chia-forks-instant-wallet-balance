import tkinter as tk
from time import sleep
from queue import Empty
from os import path
import webbrowser
import sys
from PIL import Image
from signal import signal,\
    SIGINT
from threading import Thread
from logging import getLogger
from ttkwidgets.frames import Tooltip
from tkinter.scrolledtext import ScrolledText
from tkinter import Tk, ttk,\
    N, S, E, W,\
    END, NONE,\
    Label, Entry,\
    Text, Scrollbar
from traceback import format_exc
import asyncio
from WeepingWillow.base import configure_logger_and_queue,\
    config_handler
from WeepingWillow.back_end import WILLOW_back_end

class buttons_label_state_change():
    combobox_coin_to_use: ttk.Combobox
    combobox_method_to_use: ttk.Combobox
    button_show_balance: ttk.Button
    button_show_CATs: ttk.Button
    button_show_INFO: ttk.Button
    label_backend_status: Label
    _log: getLogger

    def __init__(self):

        super(buttons_label_state_change, self).__init__()

    def get_buttons_reference(self):

        self.buttons = [self.combobox_coin_to_use,
                        self.combobox_method_to_use,
                        self.button_show_balance,
                        self.button_show_CATs,
                        self.button_show_INFO
                        ]
    def disable_all_buttons(self):
        self.get_buttons_reference()
        [button.configure(state='disabled') for button in self.buttons]
        self._log.info('Controls are now disabled until the operation is done. Please wait ...')

    def enable_all_buttons(self):
        self.get_buttons_reference()
        [button.configure(state='enabled') for button in self.buttons]
        self._log.info('Controls are now enabled')

    def backend_label_free(self):
        self.label_backend_status.configure(text="Doing nothing ...",
                                            fg='#33cc33')

    def backend_label_busy(self,
                           text: str):
        self.label_backend_status.configure(text=text,
                                            fg='#ff3300')

class sponsor_reminder():
    def __init__(self, frame):
        self.frame = frame

        self.label_sponsor_logo = Label(self.frame, text='Sponsor')
        self.label_sponsor_logo.grid(column=0, row=0)
        donation_img = 'donation.gif' if path.isfile('../media/donation.gif') else path.join(sys._MEIPASS,
                                                                                             '../media/donation.gif')
        info = Image.open(donation_img)
        self.frameCnt = info.n_frames-3
        self.sleep_between_frames = 0.1
        self.frames = [tk.PhotoImage(file=donation_img, format='gif -index %i' % (i)) for i in range(self.frameCnt)]

        self.label_sponsor_text = Label(self.frame,
                                        text='Found this tool helpful?'
                                             '\n\nWant to contribute to its development ?'
                                             '\n\nYou can make a donation to the author.'
                                             '\n\nClick this text for more info. Thank you :)',
                                        font=10)
        self.label_sponsor_text.grid(column=1, row=0)
        self.label_sponsor_text.bind("<Button-1>", self.sponsor_link)

        Thread(target=self.sponsor_gif_animation).start()

    def sponsor_link(self,
                     *args):
        webbrowser.open_new('https://github.com/ageorge95/WILLOW-chia-forks-offline-wallet-balance#support')

    def sponsor_gif_animation(self):
        while True:
            for frame_index in range(self.frameCnt):
                frame = self.frames[frame_index]
                self.label_sponsor_logo.configure(image=frame)
                sleep(self.sleep_between_frames)
            sleep(self.sleep_between_frames)

class ConsoleUi(configure_logger_and_queue):
    """Poll messages from a logging queue and display them in a scrolled text widget"""

    def __init__(self, frame):

        super(ConsoleUi, self).__init__()

        self.frame = frame

        # add a button to clear the text
        self.button_clear_console = ttk.Button(self.frame, text='CLEAR CONSOLE', command=self.clear_console)
        self.button_clear_console.grid(column=0, row=0, sticky=W)
        self.tip_clear_console = Tooltip(self.button_clear_console,
                                         text="Will clear the text from the console frame.")

        # Create a ScrolledText wdiget
        self.h_scroll = Scrollbar(self.frame, orient='horizontal')
        self.h_scroll.grid(row=2, column=0, sticky=(W, E))
        self.v_scroll = Scrollbar(self.frame, orient='vertical')
        self.v_scroll.grid(row=1, column=1, sticky=(N, S))

        self.scrolled_text = Text(frame, state='disabled', width=110, height=49, wrap=NONE, xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.scrolled_text.grid(row=1, column=0, sticky=(N, S, W, E))
        self.scrolled_text.configure(font=('Consolas', 10))
        self.scrolled_text.tag_config('INFO', foreground='black')
        self.scrolled_text.tag_config('DEBUG', foreground='gray')
        self.scrolled_text.tag_config('WARNING', foreground='orange')
        self.scrolled_text.tag_config('ERROR', foreground='red')
        self.scrolled_text.tag_config('CRITICAL', foreground='red', underline=1)
        self.scrolled_text.tag_config("bold_green", foreground="green", font=('Consolas', 10, 'bold'))
        self.scrolled_text.tag_config("bold_red", foreground="red", font=('Consolas', 10, 'bold'))
        self.current_line = 1
        self.color_tags_map = []

        self.h_scroll.config(command=self.scrolled_text.xview)
        self.v_scroll.config(command=self.scrolled_text.yview)

        # Start polling messages from the queue
        self.frame.after(100, self.poll_log_queue)

    def display(self, record):
        msg = self.queue_handler.format(record)

        # add new data to the colored tags map
        msg_as_lines = msg.split('\n')
        for index, line in enumerate(msg_as_lines, self.current_line):
            found_green = line.find('\x1b[32;1m')
            line = line.replace('\x1b[32;1m', '')

            found_red = line.find('\x1b[31;1m')
            line = line.replace('\x1b[31;1m', '')

            if found_green > -1:
                self.color_tags_map.append({'line': index,
                                            'tag_type': 'bold_green',
                                            'start_char': found_green,
                                            'end_char': line.find('\x1b[0m')})
            if found_red > -1:
                self.color_tags_map.append({'line': index,
                                            'tag_type': 'bold_red',
                                            'start_char': found_red,
                                            'end_char': line.find('\x1b[0m')})
        self.current_line += len(msg_as_lines)

        msg = msg.replace('\x1b[32;1m', '')
        msg = msg.replace('\x1b[31;1m', '')
        msg = msg.replace('\x1b[0m', '')

        self.scrolled_text.configure(state='normal')
        self.scrolled_text.insert(tk.END, msg + '\n', record.levelname)
        for color_tag in self.color_tags_map:
            self.scrolled_text.tag_add(f"{color_tag['tag_type']}",
                                       f"{color_tag['line']}.{color_tag['start_char']}",
                                       f"{color_tag['line']}.{color_tag['end_char']}")
        self.scrolled_text.configure(state='disabled')

        # Autoscroll to the bottom
        self.scrolled_text.yview(tk.END)

    def poll_log_queue(self):
        # Check every 100ms if there is a new message in the queue to display
        while True:
            try:
                record = self.log_queue.get(block=False)
            except Empty:
                break
            else:
                self.display(record)
        self.frame.after(100, self.poll_log_queue)

    def clear_console(self):
        self.scrolled_text.configure(state='normal')
        self.scrolled_text.delete('1.0', END)
        self.scrolled_text.configure(state='disabled')

        # clear the variables holding the colored tags map
        self.current_line = 1
        self.color_tags_map = []

class FormInput():

    def __init__(self, frame):
        self.frame = frame

        self.scrolled_text_input = ScrolledText(self.frame, width=60, height=28)
        self.scrolled_text_input.grid(row=0, column=0, sticky=(N, S, W, E))
        self.scrolled_text_input.configure(font='TkFixedFont')
        self.tip_text_input = Tooltip(self.scrolled_text_input,
                                      text="Insert here the mnemonic (1 mnemonic 1 line) or the wallet addresses (x addresses 1 line).")

    def return_input(self):
        return self.scrolled_text_input.get("1.0", END).split('\n')

class FormControls(buttons_label_state_change,
                   configure_logger_and_queue,
                   config_handler):

    def __init__(self,
                 frame,
                 input_frame):
        super(FormControls, self).__init__()

        self.frame = frame
        self.input_frame = input_frame

        def coin_to_filter(*args):
            self.combobox_coin_to_use.configure(values=list(filter(lambda x:self.coin_filter_entry.get().lower() in x.lower(),
                                                                   ['{}__{}'.format(entry[0], entry[1]['friendly_name']) for entry in self.config['assets'].items()])))
        self.coin_filter_entry = Entry(self.frame)
        self.coin_filter_entry.grid(column=0, row=1, sticky='W')
        self.coin_filter_entry.bind("<KeyRelease>", coin_to_filter)

        self.label_coin_to_use = Label(self.frame, text='Coin to be used:')
        self.coin_to_use = tk.StringVar()
        self.combobox_coin_to_use = ttk.Combobox(
            self.frame,
            textvariable=self.coin_to_use,
            width=15,
            state='readonly',
            values=['{}__{}'.format(entry[0], entry[1]['friendly_name']) for entry in self.config['assets'].items()]
        )
        self.combobox_coin_to_use.set('SELECT A COIN')
        self.label_coin_to_use.grid(column=0, row=0, sticky=W)
        self.combobox_coin_to_use.grid(column=0, row=2, sticky=W)

        self.addresses_to_use_entry = Entry(self.frame)
        self.addresses_to_use_entry.insert(END, '10')
        self.addresses_to_use_entry.grid(column=1, row=1, sticky='W')

        self.label_addresses_to_use = Label(self.frame, text='Addresses to generate:')
        self.label_addresses_to_use.grid(column=1, row=0, sticky=W)

        self.label_method_to_use = Label(self.frame, text='Method to be used:')
        self.method_to_use = tk.StringVar()
        self.combobox_method_to_use = ttk.Combobox(
            self.frame,
            textvariable=self.method_to_use,
            width=15,
            state='readonly',
            values=['via_mnemonic',
                    'via_wallet_addresses']
        )
        self.combobox_method_to_use.set('SELECT A METHOD')
        self.label_method_to_use.grid(column=0, row=4, sticky=W)
        self.combobox_method_to_use.grid(column=0, row=5, sticky=W)

        self.label_backend_status_notify = Label(self.frame, text='Back-end status:')
        self.label_backend_status_notify.grid(column=4, row=1)
        self.label_backend_status = Label(self.frame, text="Doing nothing ...", fg='#33cc33')
        self.label_backend_status.grid(column=4, row=2)

        self.separator_filtering_v = ttk.Separator(self.frame, orient='vertical')
        self.separator_filtering_v.grid(column=3, row=0, rowspan=10, sticky=(N, S))

        self.separator_filtering_h = ttk.Separator(self.frame, orient='horizontal')
        self.separator_filtering_h.grid(column=0, row=6, columnspan=4, sticky=(W, E))

        self.label_hover_hints = Label(self.frame, text='NOTE: Hover on the buttons below for more info.')
        self.label_hover_hints.grid(column=0, row=7, columnspan=2)

        self.button_show_balance = ttk.Button(self.frame, text='Show balance', command=(lambda :self.master_show_balance(False)))
        self.button_show_balance.grid(column=0, row=8, sticky=W)
        self.tip_show_balance = Tooltip(self.button_show_balance,
                                        text="Will display the balance of all the provided addresses OR the first x addresses of a provided mnemonic.")

        self.button_show_CATs = ttk.Button(self.frame, text='Show CATs (V1)', command=(lambda :self.master_show_balance(True)))
        self.button_show_CATs.grid(column=1, row=8, sticky=W)
        self.tip_show_balance = Tooltip(self.button_show_CATs,
                                        text="Will display the V1 CATs in all the provided addresses OR the first x addresses of a provided mnemonic.")

        self.button_show_INFO = ttk.Button(self.frame, text='Show INFO', command=(lambda: self.mnemonic_info()))
        self.button_show_INFO.grid(column=2, row=8, sticky=W)
        self.tip_show_balance = Tooltip(self.button_show_INFO,
                                        text="Will display various info for a given mnemonic.")

    def check_coin_selection(self):
        if self.coin_to_use.get() == 'SELECT A COIN':
            self._log.warning('Please select a coin !')
            return False
        return True

    def check_method_selection(self):
        if self.method_to_use.get() == 'SELECT A METHOD':
            self._log.warning('Please select a method !')
            return False
        return True

    def check_addresses_to_use_input(self):
        try:
            int(self.addresses_to_use_entry.get())
        except:
            self._log.warning(f"{ self.addresses_to_use_entry.get() } does not seem to be an integer ...")
            return False
        return True

    def master_show_balance(self,
                            cats_only: bool):
        if self.check_coin_selection() and self.check_method_selection() and self.check_addresses_to_use_input():
            async def action():
                self.disable_all_buttons()
                self.backend_label_busy(text='Computing the balance')

                try:
                    WILLOW_back_end().exec_full_cycle(mnemonic=' '.join(self.input_frame.return_input()[:-1]) if self.method_to_use.get() == 'via_mnemonic' else '',
                                                      prefix=self.coin_to_use.get().split('__')[0].lower(),
                                                      asset=self.coin_to_use.get().split('__')[0],
                                                      cats_only=cats_only,
                                                      nr_of_addresses=int(self.addresses_to_use_entry.get()),
                                                      custom_addresses=self.input_frame.return_input()[:-1] if self.method_to_use.get() == 'via_wallet_addresses' else '')
                except:
                    self._log.error(f"Failed to parse the balance !\n{format_exc(chain=False)}")

                self.enable_all_buttons()
                self.backend_label_free()
                
            loop = asyncio.get_event_loop()
            loop.run_until_complete(action())
            # using threading would cause clvm to "panick"
            # Thread(target=action).start()

    def mnemonic_info(self):
        if self.check_coin_selection() and self.check_addresses_to_use_input():
            self.disable_all_buttons()
            self.backend_label_busy(text='Computing mnemonic info')

            try:
                data_to_display = WILLOW_back_end().return_addresses(mnemonic=' '.join(self.input_frame.return_input()[:-1]),
                                                                     prefix=self.coin_to_use.get().split('__')[0].lower(),
                                                                     asset=self.coin_to_use.get().split('__')[0],
                                                                     nr_of_addresses=int(self.addresses_to_use_entry.get()))

                hardened_str = '\n'.join(data_to_display['hardened'])
                unhardened_str = '\n'.join(data_to_display['unhardened'])
                self._log.info(f"Generated hardened addresses:\n{hardened_str}\n\n")
                self._log.info(f"Generated unhardened addresses:\n{unhardened_str}\n\n")
                self._log.info(f"Generated farmer address (aka staking address):\n{data_to_display['farmeraddr']}\n\n")

            except:
                self._log.error(f"Failed to create the info data !\n{format_exc(chain=False)}")

            self.enable_all_buttons()
            self.backend_label_free()

class App():

    def __init__(self, root):
        self.root = root
        self.root.title('WILLOW-chia-forks-offline-wallet-balance | ' + open(path.join(path.dirname(__file__),
                                                                                       'version.txt'), 'r').read())
        self.root.iconbitmap(path.join(path.dirname(__file__), '../media/icon.ico'))

        sponsor_frame = ttk.Labelframe(text="Sponsor")
        sponsor_frame.grid(row=0, column=0, sticky="nsw")
        self.sponsor_frame = sponsor_reminder(sponsor_frame)

        input_frame = ttk.Labelframe(text="Input")
        input_frame.grid(row=2, column=0, sticky="nsew")
        self.input_frame = FormInput(input_frame)

        controls_frame = ttk.Labelframe(text="Controls")
        controls_frame.grid(row=1, column=0, sticky="nsew")
        self.controls_frame = FormControls(controls_frame,
                                           self.input_frame)

        console_frame = ttk.Labelframe(text="Console")
        console_frame.grid(row=0, column=1, sticky="nsew", rowspan=3)
        self.console_frame = ConsoleUi(console_frame)

        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        self.root.bind('<Control-q>', self.quit)
        signal(SIGINT, self.quit)

    def quit(self):
        # self.root.destroy()
        sys.exit()

def main():
    root = Tk()
    root.resizable(False, False)
    app = App(root)
    app.root.mainloop()

if __name__ == '__main__':
    main()