import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import messagebox
import os
import subprocess
from threading import Thread
from datetime import datetime
import re
import webbrowser
import time
import sys
import json

MAX_LINES = 100
MAX_CMD_HISTORY_LEN = 20

proc_list = []
proc_list_id = 1

def gen_id():
	global proc_list_id
	ret = proc_list_id
	proc_list_id += 1
	return ret

def get_app_dir():
	return os.path.dirname(os.path.abspath(__file__))

class CommandEntry(tk.Frame):
	def __init__(self, master, click_launch_button):
		super().__init__(master)
		self.label = tk.Label(self, text='command: ')
		self.label.pack(side=tk.LEFT)
		self.entry = tk.Entry(self)
		self.entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
		self.btn = tk.Button(self, text='起動する', command=lambda: click_launch_button(self.entry.get()))
		self.btn.pack(side=tk.LEFT)

	def set_entry_value(self, value):
		self.entry.delete(0, tk.END)
		self.entry.insert(tk.END, value)

class CommandList(tk.Listbox):
	def __init__(self, master, select_cmd_list_item, double_click_cmd_list_item):
		super().__init__(master)

		self.bind('<<ListboxSelect>>', self.select_cmd_list_item)
		self.bind('<Double-Button-1>', self.double_click_cmd_list_item)

		self._select_cmd_list_item = select_cmd_list_item
		self._double_click_cmd_list_item = double_click_cmd_list_item

	def add(self, item):
		self.insert(tk.END, item)

	def select_cmd_list_item(self, ev):
		selection = self.curselection()

		if selection:
			index = selection[0]
			value = self.get(index)
			self._select_cmd_list_item(value)

	def double_click_cmd_list_item(self, ev):
		selection = self.curselection()

		if selection:
			index = selection[0]
			value = self.get(index)
			self._double_click_cmd_list_item(value)

class CwdEntry(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.label = tk.Label(self, text='cwd: ')
        self.label.pack(side=tk.LEFT)

        self.entry = tk.Entry(self)
        self.entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.entry.insert(tk.END, os.path.expanduser('~'))

        self.bookmark_btn = tk.Button(
            self,
            text='お気に入り',
            command=self.toggle_bookmark,
        )
        self.bookmark_btn.pack(side=tk.RIGHT)

    def get_bookmark_file(self):
        return os.path.join(
            get_app_dir(),
            'bookmarks.json',
        )

    def load_bookmarks(self):
        bookmark_file = self.get_bookmark_file()

        if not os.path.exists(bookmark_file):
            return []

        try:
            with open(bookmark_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def save_bookmarks(self, bookmarks):
        bookmark_file = self.get_bookmark_file()

        with open(bookmark_file, 'w', encoding='utf-8') as f:
            json.dump(
                bookmarks,
                f,
                ensure_ascii=False,
                indent=2,
            )

    def toggle_bookmark(self):
        cwd = self.entry.get()
        bookmarks = self.load_bookmarks()

        if cwd in bookmarks:
            # 登録済み → 削除確認
            result = messagebox.askyesno(
                'お気に入り',
                f'「{cwd}」をお気に入りから削除しますか？',
            )

            if not result:
                return

            bookmarks.remove(cwd)
            self.save_bookmarks(bookmarks)

            messagebox.showinfo(
                'お気に入り',
                'お気に入りから削除しました。',
            )

        else:
            # 未登録 → 追加
            bookmarks.append(cwd)
            self.save_bookmarks(bookmarks)

            messagebox.showinfo(
                'お気に入り',
                'お気に入りに追加しました。',
            )

class LeftFrame(tk.Frame):
	def __init__(
		self,
		master,
		click_launch_button,
		select_cmd_list_item,
		double_click_cmd_list_item,
		click_stop_button,
	):
		super().__init__(master)

		self._click_launch_button = click_launch_button

		self.cwd_entry = CwdEntry(self)
		self.cwd_entry.pack(side=tk.TOP, fill=tk.X)

		self.cmd_entry = CommandEntry(self, self.click_launch_button)
		self.cmd_entry.pack(side=tk.TOP, fill=tk.X)

		self.cmd_list = CommandList(
			self,
			select_cmd_list_item,
			double_click_cmd_list_item,
		)
		self.cmd_list.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

		self.stop_btn = tk.Button(
			self,
			text='停止する',
			command=click_stop_button
		)
		self.stop_btn.pack(side=tk.TOP, fill=tk.X)

	def click_launch_button(self, cmd):
		self._click_launch_button(self.cwd_entry.entry.get(), cmd)

class RightFrame(tk.Frame):
	def __init__(self, master):
		super().__init__(master)
		self.log_text = ScrolledText(self)
		self.log_text.pack(expand=True, fill=tk.BOTH)

class MainFrame(tk.Frame):
	def __init__(
		self,
		master,
		click_launch_button,
		click_stop_button,
		select_cmd_list_item,
		double_click_cmd_list_item,
	):
		super().__init__(master)

		self.paned_window = tk.PanedWindow(
			self,
			orient=tk.HORIZONTAL,
			sashrelief=tk.RAISED,
			sashwidth=5,
		)
		self.paned_window.pack(
			expand=True,
			fill=tk.BOTH
		)

		self.left_frame = LeftFrame(
			self,
			click_launch_button=click_launch_button,
			click_stop_button=click_stop_button,
			select_cmd_list_item=select_cmd_list_item,
			double_click_cmd_list_item=double_click_cmd_list_item,
		)

		self.right_frame = RightFrame(self)

		self.paned_window.add(
			self.left_frame,
			stretch='always',
			width=400,
		)
		self.paned_window.add(
			self.right_frame,
			stretch='always',
		)

class App(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title('devservs 1.0.0')

		self.current_cmd_id = None

		# メニュー
		menubar = tk.Menu(self)

		self.bookmark_menu = tk.Menu(
			menubar,
			tearoff=False,
		)
		self.bookmark_menu.configure(
			postcommand=self.load_bookmarks,
		)
		menubar.add_cascade(
			label='ブックマーク',
			menu=self.bookmark_menu,
			command=self.load_bookmarks,
		)

		self.cmd_history_menu = tk.Menu(
			menubar,
			tearoff=False,
		)
		self.cmd_history_menu.configure(
			postcommand=self.load_cmd_history,
		)
		menubar.add_cascade(
			label='コマンド履歴',
			menu=self.cmd_history_menu,
			command=self.load_cmd_history,
		)

		self.config(menu=menubar)

		self.main_frame = MainFrame(
			self,
			click_launch_button=self.click_launch_button,
			click_stop_button=self.click_stop_button,
			select_cmd_list_item=self.select_cmd_list_item,
			double_click_cmd_list_item=self.double_click_cmd_list_item,
		)
		self.main_frame.pack(
			expand=True,
			fill=tk.BOTH,
			pady=10,
			padx=10,
		)

		self.after(100, self.update)

	def set_cwd(self, path):
		self.main_frame.left_frame.cwd_entry.entry.delete(
			0,
			tk.END,
		)
		self.main_frame.left_frame.cwd_entry.entry.insert(
			0,
			path,
		)
		
	def load_cmd_history(self):
		fname = os.path.join(
			get_app_dir(),
			'command_history.json',
		)

		# メニューを一旦クリア
		self.cmd_history_menu.delete(0, tk.END)

		if not os.path.exists(fname):
			self.cmd_history_menu.add_command(
				label='履歴なし',
				state=tk.DISABLED,
			)
			return

		try:
			with open(fname, 'r', encoding='utf-8') as f:
				cmd_history = json.load(f)
		except (json.JSONDecodeError, OSError):
			self.cmd_history_menu.add_command(
				label='読み込みエラー',
				state=tk.DISABLED,
			)
			return

		for cmd in reversed(cmd_history):
			self.cmd_history_menu.add_command(
				label=cmd,
				command=lambda cmd=cmd: self.set_cmd_entry_value(cmd),
			)

	def set_cmd_entry_value(self, cmd):
		self.main_frame.left_frame.cmd_entry.set_entry_value(cmd)	

	def load_bookmarks(self):
		bookmark_file = os.path.join(
			get_app_dir(),
			'bookmarks.json',
		)

		# メニューを一旦クリア
		self.bookmark_menu.delete(0, tk.END)

		if not os.path.exists(bookmark_file):
			self.bookmark_menu.add_command(
				label='ブックマークなし',
				state=tk.DISABLED,
			)
			return

		try:
			with open(bookmark_file, 'r', encoding='utf-8') as f:
				bookmarks = json.load(f)
		except (json.JSONDecodeError, OSError):
			self.bookmark_menu.add_command(
				label='読み込みエラー',
				state=tk.DISABLED,
			)
			return

		for bookmark in bookmarks:
			self.bookmark_menu.add_command(
				label=bookmark,
				command=lambda path=bookmark: self.set_cwd(path),
			)

	def update(self):
		global proc_list
		cid = self.current_cmd_id
		log_text = self.main_frame.right_frame.log_text

		for data in proc_list:
			if data['id'] == cid:
				log = log_text.get('1.0', tk.END)
				if data['log'].strip() != log.strip():
					log_text.delete('1.0', tk.END)
					log_text.insert(tk.END, data['log'])
					log_text.see(tk.END)
					print('see', datetime.now())

		self.after(100, self.update)

	def worker(self, id_):
		global proc_list, MAX_LINES
		data = None

		for item in proc_list:
			if item['id'] == id_:
				data = item
				break

		if data is None:
			print('not found data')
			return

		while True:
			print('worker', id_)
			time.sleep(20)

			proc = data['proc']
			log = data['log']

			for line in proc.stdout:
				log += line
				print(line)

				lines = log.replace('\r\n', '\n').split('\n')
				while len(lines) >= MAX_LINES:
					lines.pop(0)

				log = '\n'.join(lines)
				data['log'] = log

	def get_port_from_command(self, cmd):
		# --port 5173
		match = re.search(r'--port[=\s]+(\d+)', cmd)
		if match:
			return int(match.group(1))

		# -p 5173
		match = re.search(r'(?:^|\s)-p\s+(\d+)(?:\s|$)', cmd)
		if match:
			return int(match.group(1))

		# * 8888
		match = re.search(r'\D*(\d+)$', cmd)
		if match:
			return int(match.group(1))

		# php -S localhost:8080
		# php -S 127.0.0.1:8080
		match = re.search(r'(?:^|\s)-S\s+[^\s:]+:(\d+)(?:\s|$)', cmd)
		if match:
			return int(match.group(1))

		return None

	def get_data_from_cmd(self, cmd):
		global proc_list

		for data in proc_list:
			if data['cmd'] == cmd:
				return data

		return None

	def double_click_cmd_list_item(self, cmd):
		data = self.get_data_from_cmd(cmd)
		if data is None:
			return

		port = data['port']

		if port is None:
			print('ポート番号を取得できません:', cmd)
			return

		url = f'http://localhost:{port}'
		print('open:', url)

		webbrowser.open(url)

	def click_stop_button(self):
		global proc_list
		id_ = self.current_cmd_id
		del_idx = None
		del_cmd_item = None
		print('stop id', id_)

		for i, data in enumerate(proc_list):
			if data['id'] == id_:
				data['proc'].terminate()
				del_idx = i
				del_cmd_item = data['cmd']
				print('found', i, data['cmd'])
				break

		if del_idx is not None:
			proc_list.pop(del_idx)

		self.delete_cmd_list_item(del_cmd_item)

	def delete_cmd_list_item(self, item):
		cmd_list = self.main_frame.left_frame.cmd_list

		for i in range(cmd_list.size()):
			if cmd_list.get(i) == item:
				cmd_list.delete(i)
				break

	def add_cmd_history_item(self, cmd):
		path = os.path.join(get_app_dir(), 'command_history.json')

		if os.path.exists(path):
			with open(path, 'r', encoding='utf-8') as fin:
				cmd_history = json.load(fin)
		else:
			cmd_history = []

		cmd_history.append(cmd)

		while len(cmd_history) >= MAX_CMD_HISTORY_LEN:
			cmd_history.pop(0)

		with open(path, 'w', encoding='utf-8') as fout:
			fout.write(json.dumps(cmd_history))

	def click_launch_button(self, cwd, cmd):
		global proc_list
		
		id_ = gen_id()

		self.current_cmd_id = id_
		self.main_frame.left_frame.cmd_list.add(cmd)
		self.add_cmd_history_item(cmd)

		cmd_ = cmd.split(' ')
		print('cwd:', cwd)
		print('cmd:', cmd_)
		proc = subprocess.Popen(
			cmd_,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			text=True,
			cwd=cwd,
			bufsize=1,
		)
		thread = Thread(target=self.worker, daemon=True, args=(id_, ))

		proc_list.append({
			'id': id_,
			'cmd': cmd,
			'proc': proc,
			'thread': thread,
			'log': '',
			'port': self.get_port_from_command(cmd),
		})

		thread.start()

	def select_cmd_list_item(self, item):
		global proc_list

		for data in proc_list:
			if data['cmd'] == item:
				self.current_cmd_id = data['id']
				break

		self.main_frame.left_frame.cmd_entry.set_entry_value(item)

App().mainloop()
