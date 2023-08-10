import os

try:
    import psutil
except ModuleNotFoundError:
    os.system("pip install psutil")
    import psutil
import time
import subprocess
from typing import Union
import socket
import logging
from datetime import datetime


class vpn_control:
    # xray_running: bool      # xray运行状态
    # one_running: bool       # one运行状态
    xray_process: Union     # xray的进程
    xray_core_path: str     # xray核心的路径
    one_path: str           # one的路径
    NIC_name: str           # 网卡名称
    last_addr: str          # 上次检索获取的ip地址
    logger: logging.Logger

    # 初始化
    def __init__(self, x_path: str, o_path: str):
        self.init_log()
        self.xray_core_path = x_path
        self.one_path = o_path
        self.NIC_name = "VPN by Google One"
        self.logger.info("get ip address...")
        self.last_addr = self.get_addr()
        while self.last_addr is None:
            self.logger.error("get address failed, retry after 5 sec")
            time.sleep(5)
            self.last_addr = self.get_addr()
        self.logger.info("get successfully")
        self.update_config()
        self.start()
        self.logger.info("xray start successfully")

    def init_log(self):
        if not os.path.exists("./logs"):
            os.mkdir("./logs")
        # 创建日志记录器
        self.logger = logging.getLogger('my_logger')
        self.logger.setLevel(logging.DEBUG)

        # 创建文件处理程序
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d_%H.%M.%S")
        file_handler = logging.FileHandler('./logs/log_{}.txt'.format(formatted_time))
        file_handler.setLevel(logging.DEBUG)

        # 创建控制台处理程序
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # 将格式化器添加到处理程序
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 将处理程序添加到日志记录器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def get_addr(self):
        try:
            for addr in psutil.net_if_addrs()[self.NIC_name]:
                if addr.family.value == 2:
                    return addr.address
        except KeyError:
            return None

    def update_config(self):
        with open(self.xray_core_path + "config_template.json", "r", encoding="utf-8") as f:
            config = f.read()

        config = config.replace("$ip_address", self.last_addr)

        with open(self.xray_core_path + "config.json", "w", encoding="utf-8") as f:
            f.write(config)

    def restart(self):
        self.xray_process.terminate()
        self.xray_process = subprocess.Popen(self.xray_core_path + "xray.exe", stdin=subprocess.PIPE,
                                             stdout=subprocess.PIPE)

    def start(self):
        self.xray_process = subprocess.Popen(self.xray_core_path + "xray.exe", stdin=subprocess.PIPE,
                                             stdout=subprocess.PIPE)

    def test_usable(self):
        local_ip = self.last_addr
        remote_ip = 'www.google.com'
        remote_port = 80

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock.bind((local_ip, 0))

        sock.settimeout(1)

        try:
            sock.connect((remote_ip, remote_port))

            sock.send(b'GET / HTTP/1.1\r\nHost: www.google.com\r\n\r\n')

            data = sock.recv(4096)

            sock.close()
            return True
        except socket.timeout:
            return False
        except Exception as e:
            self.logger.error(e)
            return False

    def run(self):
        self.logger.info("started")

        test_retry = 0

        while True:
            addr = self.get_addr()
            if addr is None:
                self.logger.error("get address failed, retry after 5 sec")
                time.sleep(5)
                continue
            self.logger.info("last_addr: {}, current_addr: {}".format(self.last_addr, addr))
            if addr != self.last_addr:
                self.logger.info("address changed, restarting xray core...")
                self.last_addr = addr
                self.update_config()
                self.restart()
                self.logger.info("restart completed")
            self.logger.info("begin test network")

            try:
                usable = self.test_usable()
            except OSError as e:
                self.logger.error("OSError: " + e.__str__())
                self.logger.error("Get New address...")
                addr = self.get_addr()
                self.last_addr = addr
                self.update_config()
                self.restart()
                self.logger.info("restart completed")
                # self.logger.error("OSError: " + e.__str__() + " ,reboot now")
                # os.system("shutdown /r /t 0")
                # return
                usable = False
            while not usable:
                test_retry += 1
                if test_retry >= 6:
                    self.logger.error("max retry times, reboot now")
                    os.system("shutdown /r /t 0")
                self.logger.error("network test failed, retry after 5 sec: {}".format(str(test_retry)))
                time.sleep(5)

                try:
                    usable = self.test_usable()
                except OSError as e:
                    self.logger.error("OSError: " + e.__str__())
                    self.logger.error("Get New address...")
                    addr = self.get_addr()
                    self.last_addr = addr
                    self.update_config()
                    self.restart()
                    self.logger.info("restart completed")
                    # self.logger.error("OSError: " + e.__str__() + " ,reboot now")
                    # os.system("shutdown /r /t 0")
                    # return
                    usable = False

            # if not self.test_usable():
            #     self.logger.error("test failed")
            # else:
            self.logger.info("test successful")
            test_retry = 0
            self.logger.info("pause 30 sec")
            time.sleep(30)

