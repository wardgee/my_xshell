# -*- ecoding: utf-8 -*-
# @ModuleName: project
# @Function: 
# @Author: liweijia
# @Time: 2024/5/22 15:21
# #!/usr/bin/python
import os
import re

import paramiko
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
import ttkbootstrap as ttk
import json


class MySSH:
    def __init__(self):

        self.servers = []  # 读取server.json。  选择/添加/删除
        self.server = {}
        # 服务器是否连接
        self.connected = False
        # 用来保存当前路径
        self.path = ""
        # 实例化并且建立一个sshclient对象
        self.ssh = paramiko.SSHClient()
        # 将信任的主机自动加入到host_allow列表，需放在connect方法前面
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        self.cpu_percent = 0.0
        self.memory_percent = 0.0
        self.file_name = None
        self.processes = []
        self.load_server()

        # 此线程用于vim文件编辑功能
        t = threading.Thread(target=self.file_save)
        t.start()

    def load_server(self):
        # 打开文件
        with open("server.json", encoding='utf-8') as fp:
            self.servers = json.load(fp)

    def connect(self):
        # 调用connect方法连接服务器
        self.connected = None
        try:
            # 通过用户名和密码进行连接
            self.ssh.connect(hostname=self.server["ip"], port=self.server["port"], username=self.server["username"],
                             password=self.server["password"])
            print(f'连接到服务器{self.server["ip"]}成功！！！')
            self.connected = True

            # 创建一个交互式的shell窗口
            self.chan = self.ssh.invoke_shell()
            self.chan.settimeout(1000)
            # 刚进入linux服务器等待一会，否则直接通过chan.recv获取的信息不完整
            time.sleep(0.6)
            self.endSymbol = ['# ', '$ ', '> ', '* ']  # 设置我们定义的结束符

        except Exception as e:
            self.connected = False
            print(f"连接到服务器【{self.server['ip']}】失败，失败的原因：{e}")

    def transport(self, server_path, local_path, num):

        '''
        文件上传 如果传入num==1文件上传 num==0文件下载
        server_path：服务器路径
        local_path：本地路径
        num：1为上传操作 0为下载操作
        '''

        sftp = self.ssh.open_sftp()  # 初始化sftp
        file_name = ''
        pattern = r'[^\\\/]+(?=\.[^\\\/.]*$|$)'  # 正则表达式用于将文件名称从路径里抽取出来

        if num == 1:
            try:
                file_name = re.search(pattern, local_path).group(
                    0)
            except Exception as e:
                print(e)
            print(f"{server_path}/{file_name}")
            sftp.put(local_path, f"{server_path}/{file_name}")

        if num == 0:
            try:
                file_name = re.search(pattern, server_path).group(
                    0)
            except Exception as e:
                print(e)

            print(f'{server_path}')
            sftp.get(server_path, f'{local_path}/{file_name}')

    def more_transport(self, local_dir):
        sftp = self.ssh.open_sftp()  # 初始化sftp
        try:
            # 获取服务器的日志文件
            stdin, stdout, stderr = self.ssh.exec_command("ls /var/log/*.log | xargs -I {} basename '{}'")
            file_list = stdout.read().decode("utf-8").strip().split('\n')
            # 遍历文件列表并下载
            for file_name in file_list:
                remote_path = f"/var/log/{file_name}"
                local_path = f"{local_dir}/{file_name}"
                print(f"Downloading {remote_path} to {local_path}")
                sftp.get(remote_path, local_path)
        finally:
            # 关闭SFTP和SSH连接
            sftp.close()


    def runCommand(self, chanT, command, endSymbol):
        # 指令后加 '\n' 表示换行
        chanT.send(command + '\n')
        results = ''
        while True:

            result = chanT.recv(1024).decode('utf-8')
            if 'Last login:' in result: # 如果指令里包含Last...字段就再发送一次请求
                result = chanT.recv(1024).decode('utf-8')

            results += result
            # 判断最后两个字符是否是我们定义的结束符
            if results[-2:] in endSymbol:
                break

        re1 = results.split('\n')[1:]  # 第一行是我们输入的指令，丢弃
        re1 = '\n'.join(re1)

        clean_string = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', re1)  # 由于我们的GUI只能展示纯文本信息所以选择 通过正则表达式对返回结果的ANSI进行匹配去除

        return clean_string+'\n'


    def vim_cat(self, command):
        '''
        :param command:
        用户编辑文件自动下载到本地，再自动打开本地编辑
        '''
        self.file_name = command.split(' ')[-1]
        self.chan.send('pwd'+'\n')
        path = ''
        while True:
            # 读取一行输出
            result = self.chan.recv(1024).decode('utf-8')
            if 'Last login:' in result:  # 如果指令里包含Last...字段就再发送一次请求
                result = self.chan.recv(1024).decode('utf-8')

            path += result
            # 判断最后两个字符是否是我们定义的结束符
            if path[-2:] in path:
                break

        re1 = path.split('\n')[1:]  # 第一行是我们输入的指令，丢弃
        re1 = re1[:-1]

        self.path = r'\n'.join(re1)
        self.path = self.path.replace('\r','')  # 将pwd返回结果中包含的\r去掉
        path_name=(self.path+'/'+self.file_name)
        ''
        self.transport(path_name,'C:/Users/Public/Documents',0) # 每个微软用户都有的路径
        time.sleep(0.3)
        os.startfile(f'C:\\Users\\Public\\Documents\\{self.file_name}') # 用系统默认软件打开这个可编辑的文件


    def send_file(self):
        '''
        用户点击编辑自动将文件上传到服务器
        :return:
        '''
        local_path = f'C:/Users/Public/Documents/{self.file_name}'
        self.transport(self.path,local_path,1)
        time.sleep(0.2)
        # print('文件已上传')

    def file_save(self):
        '''
        通过当前获取当前时间和文件最后修改时间，判断是否一致，如果一致的话自动上传文件到服务器上
        :return:
        '''
        while True:
            if self.file_name != None:

                file_time = int(os.path.getmtime(f'C:/Users/Public/Documents/{self.file_name}'))
                cur_time = int(time.time())

                if file_time == cur_time:
                    self.send_file()

            time.sleep(0.2)



    def exec2(self, command):
        if command == 'quit':
            print('Bye Bye!')
            exit(0)

            # 如果输入的是vim命令
        elif command[:3] == 'vim':
            # 调用函数查看文件的内容
            self.vim_cat(command)
            return
        else:
            return self.runCommand(self.chan, command, self.endSymbol)

    def close(self):
        # 关闭连接
        self.ssh.close()
        print(f"关闭到服务器【{self.server['ip']}】的连接")
        self.connected = False
        self.server = {}

    def get_cpu_usage(self):
        # 获取cpu使用情况
        # stdin, stdout, stderr = self.ssh.exec_command("top -bn1 | grep 'Cpu(s)'")
        stdin, stdout, stderr = self.ssh.exec_command("top -bn1 | grep 'load' | awk '{print $(NF-2)}'")
        output = stdout.read().decode("utf-8")
        # cpu_usage = re.search(r"\d+.\d+%? us", output).group()
        cpu_usage = output.strip().strip(',')
        return f'{cpu_usage}%'

    def get_memory_usage(self):
        # 获取内存情况
        # stdin, stdout, stderr = self.ssh.exec_command("free -m | grep Mem")
        stdin, stdout, stderr = self.ssh.exec_command("free | grep Mem | awk '{print $3/$2 * 100.0}'")
        output = stdout.read().decode("utf-8")
        # memory_usage = output.split()[2] + " MB"
        memory_usage = output.strip()[:4]
        return f'{memory_usage}%'

    def get_disk_usage(self):
        # 获取磁盘情况
        # stdin, stdout, stderr = self.ssh.exec_command("free -m | grep Mem")
        stdin, stdout, stderr = self.ssh.exec_command("df -h | grep '^/dev/.*/$' | awk '{print $5}'")
        output = stdout.read().decode("utf-8")
        # memory_usage = output.split()[2] + " MB"
        disk_usage = output.strip().strip('%')
        return f'{disk_usage}%'

    def get_processes(self):
        # 获取进程情况
        stdin, stdout, stderr = self.ssh.exec_command("ps aux")
        output = stdout.read().decode("utf-8")
        return output

    def get_network_status(self):
        # 获取网络延迟情况
        stdin, stdout, stderr = self.ssh.exec_command(f"ping -c 4 8.8.8.8")
        output = stdout.read().decode()

        # Extracting min/avg/max/mdev from ping output
        match = re.search(r"min/avg/max/mdev = (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)", output)
        if match:
            min_latency, avg_latency, max_latency, mdev_latency = match.groups()
            return {
                "最小延迟": float(min_latency),
                "平均延迟": float(avg_latency),
                "最大延迟": float(max_latency),
                "延迟抖动": float(mdev_latency)
            }
        else:
            return None


import time
import threading


# 进行图形化界面的ui
class MyUI:
    def __init__(self, ssh):
        # 服务器操作类的实例
        self.ssh = ssh
        # 应用程序的主窗口
        self.root = ttk.Window(themename="solar")
        # 实例化Frame -框架控件
        self.frame = ttk.Frame(self.root)
        # 网格布局
        self.frame.grid()
        # 输入指令的控件
        self.entry_command = ttk.Entry(self.frame, width=50)
        self.entry_command.grid(row=0, column=0,sticky='w')
        self.entry_command.bind("<Return>", self.ok2)  # 添加一个与该输入框绑定的回车事件，在调用函数中也需要有个对应的参数
        # 执行按钮
        self.btn_ok = ttk.Button(self.frame, text='执行', command=self.ok2, bootstyle="outline", width=7)
        self.btn_ok.grid(row=0, column=1,sticky='w')
        # 显示服务连接信息
        self.label_info = ttk.Label(self.frame, text='服务器无连接')
        self.label_info.grid(row=0, column=2,sticky='w')

        # 结果展示-显示指令返回的结果
        self.result_txt = ttk.Text(self.frame)
        self.result_txt.grid(row=5, columnspan=2)
        # 菜单
        self.init_menu()


        thread_info = threading.Thread(target=self.update_info)
        thread_info.start()
        # -----------------------------------------------------------------------------------------
        # 创建单独的线程更新监视服务器状态
        # thread_monitor = threading.Thread(target=self.monitor)
        # thread_monitor.start()

        self.module_is = True
        # 将程序进行挂起
        self.root.mainloop()

    def ok2(self, event=''): # event作用：用于绑定回车要求的默认形参（在函数中无作用）
        command = self.entry_command.get()
        if self.ssh.connected:
            result = ''
            if command == 'clear':
                self.result_txt.delete('1.0', tk.END)  # 输入 clear 清屏

            try:
                result = self.ssh.exec2(command)
                print(result)
            except Exception as e:
                messagebox.showinfo("", str(e))

            try:
                self.result_txt.insert(tk.END, result)
            except:
                pass
        else:
            messagebox.showinfo("", "服务器尚未连接!")


    # 更新服务器状态
    def update_info(self):
        while True:

            # print(f"更新info：{self.ssh.server}  {self.ssh.connected}")
            if "ip" not in self.ssh.server:
                info = (f"服务器无连接", "white")
            else:
                if self.ssh.connected == None:
                    info = (f"服务器{self.ssh.server['ip']}连接中...", "red")
                elif self.ssh.connected:
                    info = (f"服务器{self.ssh.server['ip']}连接成功", "green")
                    self.module()

                else:
                    info = (f"服务器{self.ssh.server['ip']}连接失败", "red")
            self.label_info.config(text=info[0], foreground=info[1])
            time.sleep(1)

    # 菜单栏
    def init_menu(self):
        menu_top = tk.Menu(self.root)
        # 创建第一个一级菜单 "连接"
        menu_link = tk.Menu(menu_top, tearoff=0)
        menu_top.add_cascade(label='连接', menu=menu_link)
        menu_link.add_command(label="新建", command=self.add_win)
        menu_link.add_command(label="打开", command=self.open_win)
        menu_link.add_command(label="断开连接", command=self.close)
        menu_link.add_separator()

        # 创建第二个一级菜单 "文件"
        file_menu = tk.Menu(menu_top, tearoff=0)
        menu_link.add_cascade(label='文件', menu=file_menu)
        file_menu.add_command(label="文件上传", command=lambda: self.interact_file(1))
        file_menu.add_command(label="文件下载", command=lambda: self.interact_file(0))
        # 创建第二个一级菜单 "文件"
        file_log_menu = tk.Menu(menu_top, tearoff=0)
        menu_link.add_cascade(label='日志文件下载', menu=file_log_menu)
        file_log_menu.add_command(label="批量文件下载", command=self.more_file_log)
        # 将菜单应用到应用程序的主窗口上
        self.root.config(menu=menu_top)


    def more_file_log(self):
        messagebox.showinfo("warning", "请选择你要下载到的文件夹")
        local_dir=filedialog.askdirectory()
        self.ssh.more_transport(local_dir)
        messagebox.showinfo("Success", "日志文件上传成功")
    def change_server_file(self,server):

        # 打开子窗口
        self.ow = tk.Toplevel(self.root)
        frame = tk.Frame(self.ow)
        frame.grid()
        ttk.Label(frame,text='请输输入要修改的内容',bootstyle="warning").pack()

        ip = ttk.Label(frame, text=f"您正在修改的ip为{server['ip']}的服务器",bootstyle="warning") # 按照正常逻辑来说修改不会改变主机ip
        ip.pack()

        ttk.Label(frame).pack()

        port = tk.Label(frame, text="请输入端口号")
        port.pack()
        # 创建一个Entry文本框供用户输入
        self.entry_port = tk.Entry(frame)
        self.entry_port.insert(0, server['port'])
        self.entry_port.pack()

        username = tk.Label(frame, text="请输入用户名")
        username.pack()
        # 创建一个Entry文本框供用户输入
        self.entry_username = tk.Entry(frame)
        self.entry_username.insert(0, server['username'])
        self.entry_username.pack()

        password = tk.Label(frame, text="请输入密码")
        password.pack()
        # 创建一个Entry文本框供用户输入
        self.entry_password = tk.Entry(frame)
        self.entry_password.insert(0, server['password'])
        self.entry_password.pack()

        ds = tk.Label(frame, text="请输入描述")
        ds.pack()
        # 创建一个Entry文本框供用户输入
        self.entry_descript = tk.Entry(frame)
        self.entry_descript.insert(0, server['description'])
        self.entry_descript.pack()

        dict_data = {"ip": server['ip'],
                    "port": int(self.entry_port.get()),
                    "username": self.entry_username.get(),
                    "password": self.entry_password.get(),
                    "description": self.entry_descript.get()
                    }

        # 创建一个 Button 控件，当点击时调用 on_submit 函数
        submit_button = tk.Button(frame, text="提交", command=lambda :self.on_submit_change(dict_data))
        submit_button.pack()

    def on_submit_change(self,dict_data):
        '''
        更改文件内容：
        self.ssh.servers.index(self.entry_ip.get())
        根据ip获取到要修改内容的下标
        :return:
        '''
        with open('server.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        server_index = self.ssh.servers.index(dict_data) # 确定文件下标
        data[server_index]['port'] = int(self.entry_port.get())
        data[server_index]['username'] = self.entry_username.get()
        data[server_index]['password'] = self.entry_password.get()
        data[server_index]['description'] = self.entry_descript.get()

        with open('server.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=6)


        self.ow.destroy()
        self.ow2.destroy()
        self.ssh.load_server()
        messagebox.showinfo('', '文件修改成功！')
    def interact_file(self, n):

        '''
        n=0 下载文件  n=1 上传文件
        '''

        if self.ssh.connected:
            # 打开子窗口
            self.ow = tk.Toplevel(self.root)
            frame = tk.Frame(self.ow)
            frame.grid()

            if n == 0:
                label = tk.Label(frame, text="文件下载", fg='red')
                label.pack()

                label1 = tk.Label(frame, text="服务器的完整路径（文件）")
                label1.pack()
                # 创建一个Entry文本框供用户输入
                self.entry_server = tk.Entry(frame)
                self.entry_server.pack()

                # 创建一个Button按钮，当点击时调用函数
                button = tk.Button(frame, text="保存文件的本地的路径",
                                   command=lambda: self.operate_file(n=0))  # 这里必须使用lambda才能在函数里传参数
                button.pack()

            if n == 1:
                label = tk.Label(frame, text="文件上传", fg='red')
                label.pack()

                label1 = tk.Label(frame, text="服务器的路径（文件夹）")
                label1.pack()
                # 创建一个Entry文本框供用户输入
                self.entry_server = tk.Entry(frame)
                self.entry_server.pack()

                # 创建一个Button按钮，当点击时调用函数
                button = tk.Button(frame, text="请选择文件在本地的路径", command=lambda: self.operate_file(n=1))
                button.pack()

            if n != 0 and n != 1:
                raise Exception("n only is 1 or 0 !")

        else:
            messagebox.showinfo("", "服务器尚未连接!")

    def operate_file(self, n):

        '''
        上传下载文件
        '''

        try:
            if n == 0:
                self.chose_local_path = filedialog.askdirectory()  # askdirectory()返回文件夹路径
            if n == 1:
                self.chose_local_path = filedialog.askopenfilename()  # 返回文件路径

            self.ssh.transport(server_path=self.entry_server.get(), local_path=self.chose_local_path, num=n)
            messagebox.showinfo("Success", "文件传送成功!")
        except Exception as e:
            messagebox.showinfo('提示', str(e))

        self.ow.destroy()

    def close(self):
        if self.ssh.connected == False:
            messagebox.showinfo("", "服务器尚未连接!")
        else:
            self.ssh.close()

            messagebox.showinfo("Success", "主机已连接关闭")

    def add_win(self):
        print('调用了add_win函数')

        # 打开子窗口
        self.ow = tk.Toplevel(self.root)
        frame = tk.Frame(self.ow)
        frame.grid()

        ip = tk.Label(frame, text="请输入ip")
        ip.pack()
        # 创建一个Entry文本框供用户输入
        self.entry_ip = tk.Entry(frame)
        self.entry_ip.pack()

        port = tk.Label(frame, text="请输入端口号")
        port.pack()
        # 创建一个Entry文本框供用户输入
        self.entry_port = tk.Entry(frame)
        self.entry_port.pack()

        username = tk.Label(frame, text="请输入用户名")
        username.pack()
        # 创建一个Entry文本框供用户输入
        self.entry_username = tk.Entry(frame)
        self.entry_username.pack()

        password = tk.Label(frame, text="请输入密码")
        password.pack()
        # 创建一个Entry文本框供用户输入
        self.entry_password = tk.Entry(frame, show='*')
        self.entry_password.pack()

        ds = tk.Label(frame, text="请输入描述")
        ds.pack()
        # 创建一个Entry文本框供用户输入
        self.entry_descript = tk.Entry(frame)
        self.entry_descript.pack()
        # 创建一个 Button 控件，当点击时调用 on_submit 函数 command=lambda item=item: self.connect(item)
        submit_button = tk.Button(frame, text="提交", command=self.on_submit)
        submit_button.pack()


    def on_submit(self):
        # 获取 Entry 控件中的文本
        ip = self.entry_ip.get()
        port = int(self.entry_port.get())
        username = self.entry_username.get()
        password = self.entry_password.get()
        ds = self.entry_descript.get()
        if ip == '' or port == '' or username == '' or password == '':
            messagebox.showinfo("Error", "请输入ip或者用户名或者密码或者端口!")
        else:
            # 添加服务器
            self.add()

    def add(self):
        '''
        添加服务器信息
        '''
        with open('server.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        new_data = {"ip": self.entry_ip.get(),
                    "port": self.entry_port.get(),
                    "username": self.entry_username.get(),
                    "password": self.entry_password.get(),
                    "description": self.entry_descript.get()
                    }

        with open('server.json', 'w', encoding='utf-8') as f:
            data.append(new_data)
            json.dump(data, f, indent=6)

        print('添加成功')
        time.sleep(0.6)
        # 自动销毁子窗口
        self.ow.destroy()

        self.ssh.load_server()  # 更新一下server.json文件
        messagebox.showinfo("Success", "主机添加成功!")

    def open_win(self):
        print('调用了open_win函数')
        # 打开子窗口
        self.ow2 = tk.Toplevel(self.root)
        frame = tk.Frame(self.ow2)
        # 网格布局
        frame.grid()
        row = 0
        for item in self.ssh.servers:
            tk.Label(frame, text=item).grid(row=row, column=0)
            ttk.Button(frame, text='连接', command=lambda item=item: self.connect(item), bootstyle="outline").grid(
                row=row, column=1)
            ttk.Button(frame, text='删除', command=lambda item=item: self.delete(item), bootstyle="outline").grid(
                row=row, column=2)
            ttk.Button(frame, text='修改', command=lambda item=item:self.change_server_file(item), bootstyle="outline").grid(
                row=row, column=3)

            row = row + 1

    def delete(self, server):
        # 打开文件
        with open('server.json', 'w', encoding='utf-8') as f:
            # 存入文件内容,覆盖内容
            delete_host = self.ssh.servers.pop(self.ssh.servers.index(server))
            # servers:列表 server：字典
            # 使用列表的index（）方法获取字典的下标再通过列表的pop方法删除
            json.dump(self.ssh.servers, f)
            messagebox.showinfo("Success", "主机ip:" + delete_host["ip"] + "已经删除!")

        self.ssh.load_server()  # 重新加载一下json文件
        self.ow2.destroy()

    def connect(self, server):
        # 连接到对应的服务器
        # 给server赋值
        self.ssh.server = server
        # self.ssh.connect()
        # 连接失败的超时会导致GUI界面无响应,通过多线程或者多进程处理
        thread_connect = threading.Thread(target=self.ssh.connect)
        thread_connect.start()

        # 启动线程实时更新服务器状态
        time.sleep(0.3)
        if self.ssh.connected:
            thread_monitor = threading.Thread(target=self.monitor)
            thread_monitor.start()
        self.ow2.destroy()

    def update_monitor(self):
        # 调用cup，内存，网络延迟，进程的函数对他们进程赋值
        cpu_usage = self.ssh.get_cpu_usage()
        memory_usage = self.ssh.get_memory_usage()
        processes = self.ssh.get_processes()
        network = self.ssh.get_network_status()
        disk = self.ssh.get_disk_usage()

        # 再键赋值的变量插入到这些标签中
        self.cpu_percent_label.config(text=cpu_usage)
        self.memory_percent_label.config(text=memory_usage)
        self.network_percent_label.config(text=network)
        self.disk_percent_label.config(text=disk)
        self.processes_text.delete(1.0, tk.END)
        self.processes_text.insert(tk.END, processes)

    def monitor(self):
        while True:
            if self.ssh.connected:
                self.update_monitor()
                time.sleep(1)
                self.monitor()
            else:
                time.sleep(1)
                continue

    def module(self):
        '''
        展开监控服务器的信息
        :return:
        '''
        if self.module_is:
            # CPU使用情况:
            self.cpu_label = ttk.Label(self.frame, text="CPU使用情况:")
            self.cpu_label.grid(row=3, column=2)

            self.cpu_percent_label = ttk.Label(self.frame, text="")
            self.cpu_percent_label.grid(row=3, column=3)

            # 内存使用情况:
            self.memory_label = ttk.Label(self.frame, text="内存使用情况:")
            self.memory_label.grid(row=4, column=2)

            self.memory_percent_label = ttk.Label(self.frame, text="")

            self.memory_percent_label.grid(row=4, column=3)

            # 运行中的进程:
            # 创建Treeview来显示进程列表
            self.processes_label = ttk.Label(self.frame, text="运行中的进程:")
            self.processes_label.grid(row=5, column=2)

            self.processes_text = tk.Text(self.frame, height=10, width=85, bg='black')
            self.processes_text.grid(row=5, column=3)

            # 网络情况:
            self.network_label = ttk.Label(self.frame, text="网络情况:")
            self.network_label.grid(row=6, column=2)

            self.network_percent_label = ttk.Label(self.frame, text="")
            self.network_percent_label.grid(row=6, column=3)

            # 磁盘情况:
            self.disk_label = ttk.Label(self.frame, text="磁盘情况:")
            self.disk_label.grid(row=7, column=2)

            self.disk_percent_label = ttk.Label(self.frame, text="")
            self.disk_percent_label.grid(row=7, column=3)
            self.module_is = False  #



if __name__ == '__main__':
    ssh = MySSH()
    ui = MyUI(ssh)
