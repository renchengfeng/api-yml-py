"""把 lowcode 当作外部库启动服务。

    python main.py
    PORT=9000 python main.py
    gunicorn -w 4 'main:server'

配置目录通过 Lowcode 的参数指定；host / port 缺省读 conf/server.yaml。
"""
from lowcode import Lowcode

server = Lowcode("conf")

if __name__ == "__main__":
    server.run()
