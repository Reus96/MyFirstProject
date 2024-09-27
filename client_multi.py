import asyncio
import logging
from datetime import datetime
import os

# 设置基本日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 创建一个文件处理器用于错误日志
error_log_file = 'error_log.txt'
file_handler = logging.FileHandler(error_log_file)
file_handler.setLevel(logging.ERROR)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# 获取根日志记录器并添加文件处理器
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)

class ModbusClient:
    def __init__(self, client_id, host, port):
        self.client_id = client_id
        self.host = host
        self.port = port
        self.base_folder = f'Temperature_Logs_{client_id}'
        self.connection_status = "Disconnected"  # 新增：连接状态标识符

    async def run(self):
            while True:
                try:
                    self.connection_status = "Connecting"
                    reader, writer = await asyncio.open_connection(self.host, self.port)
                    self.connection_status = "Connected"
                    logging.info(f"Client {self.client_id} connected to {self.host}:{self.port}")
                    
                    while True:
                        writer.write(b'\xFE\x04\x00\x00\x00\x04\xE5\xC6')
                        await writer.drain()
                        
                        data = await reader.read(1024)
                        if data:
                            temperatures = self.process_reply(data)
                            if temperatures:
                                self.log_temp_data(temperatures)
                        else:
                            self.connection_status = "No Data"
                            break
                        
                        await asyncio.sleep(1)
                
                except Exception as e:
                    self.connection_status = "Error"
                    error_msg = f"Client {self.client_id} error: {e}"
                    logging.error(error_msg)  # 这会同时记录到控制台和错误日志文件
                    await asyncio.sleep(5)
                finally:
                    self.connection_status = "Disconnected"

    def process_reply(self, reply):
        if len(reply) < 5:
            return None
        data = reply[3:-2]
        return [((data[i] << 8 | data[i+1]) - 65536 if (data[i] << 8 | data[i+1]) > 32767 else (data[i] << 8 | data[i+1])) / 10 for i in range(0, len(data), 2)]

    def log_temp_data(self, temp_data):
        current_time = datetime.now()
        date_folder = os.path.join(self.base_folder, current_time.strftime("%Y-%m-%d"))
        os.makedirs(date_folder, exist_ok=True)
        
        file_path = os.path.join(date_folder, f"temp_log_{current_time.strftime('%Y-%m-%d_%H')}.csv")
        
        with open(file_path, 'a') as f:
            temp_str = ",".join(f"{t:.2f}" for t in temp_data)
            f.write(f"{current_time.strftime('%Y-%m-%d %H:%M:%S')},{temp_str}\n")
        
        logging.info(f"Client {self.client_id} status: {self.connection_status}, temperatures: {temp_str}")


async def main():
    clients = [
        ModbusClient(1, "192.168.30.100", 9000),
        ModbusClient(2, "192.168.1.200", 10000),
        ModbusClient(3, "192.168.31.300", 10000),
    ]
    await asyncio.gather(*(client.run() for client in clients))

if __name__ == "__main__":
    asyncio.run(main())
