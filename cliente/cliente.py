#!/usr/bin/python

__version__ = "0.3"

import BaseHTTPServer, select, socket, SocketServer, urlparse
import logging
import logging.handlers
import getopt
import sys
import os
import signal
import threading
from types import FrameType, CodeType
from time import sleep
import ftplib
import re
import base64

sys.path.append('../consultor')

from consultor import *

BIND_ADDRESS = "0.0.0.0"
BIND_PORT = 3128
LOG_FILENAME ="/var/log/securedfamily-cliente.log"
LOG_SIZE_MB =20
LOG_CANT_ROTACIONES =5

consultor=Consultor()

class ProxyHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    __base = BaseHTTPServer.BaseHTTPRequestHandler
    __base_handle = __base.handle
    
    server_version = "Familia Segura - Cliente /" + __version__
    rbufsize = 0                        # self.rfile Be unbuffered
    global consultor
    
    
    def handle(self):
        # Paso 1: autenticacion de ip origen
        (ip, port) =  self.client_address
        self.server.logger.log (logging.INFO, "Request from '%s'", ip)
        if hasattr(self, 'allowed_clients') and ip not in self.allowed_clients:
            self.raw_requestline = self.rfile.readline()
            if self.parse_request(): 
                self.send_error(403)
        else:
            self.__base_handle()
    
    def pedirUsuario(self, motivo):
        self.send_response(407, motivo)
        self.send_header('Proxy-Authenticate', 'Basic realm="Familia Segura"')
        self.send_header('Conection', 'close')
        self.end_headers()    

    def denegar(self, motivo):
        msg="<html><h1>Sitio no permitido</h1><br><h2>Familia Segura</h2><br><h3>Motivo: %s</h3></html>\r\n" % motivo
        self.wfile.write(self.protocol_version + " 200 Connection established\r\n")
        self.wfile.write("Proxy-agent: %s\r\n" % self.version_string())
        self.wfile.write("\r\n")
        self.wfile.write(msg)
        
    def _connect_to(self, netloc, soc):
        i = netloc.find(':')
        if i >= 0:
            host_port = netloc[:i], int(netloc[i+1:])
        else:
            host_port = netloc, 80

        proxy_user=self.headers.getheader('Proxy-Authorization')
        if proxy_user:
            usuario, password=base64.b64decode(proxy_user.split(' ')[1]).split(':')
        else:
            self.pedirUsuario("Se requiere un usuario")
            return False
        if not usuario:
            self.pedirUsuario("Se requiere un usuario")
            return False
        else:
            permitido, motivo=consultor.validarUrl(usuario, password, self.path)
            if not permitido:
                self.pedirUsuario("Usuario invalido")
                #self.denegar(motivo)
                return False

        self.server.logger.log (logging.INFO, "connect to %s:%d", host_port[0], host_port[1])
        try: 
            soc.connect(host_port)
        except socket.error, arg:
            try: 
                msg = arg[1]
            except: 
                msg = arg
                self.send_error(404, msg)
            return False
        return True

    def do_CONNECT(self):
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self._connect_to(self.path, soc):
                self.log_request(200)
                self.wfile.write(self.protocol_version +
                                 " 200 Connection established\r\n")
                self.wfile.write("Proxy-agent: %s\r\n" % self.version_string())
                self.wfile.write("\r\n")
                self._read_write(soc, 300)
        finally:
            soc.close()
            self.connection.close()

    def do_GET(self):
        # Paso 3: peticion del recurso
        (scm, netloc, path, params, query, fragment) = urlparse.urlparse(
            self.path, 'http')
        if scm not in ('http', 'ftp') or fragment or not netloc:
            self.send_error(400, "bad url %s" % self.path)
            return
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if scm == 'http':
                if self._connect_to(netloc, soc):
                    self.log_request()
                    try:
                        soc.send("%s %s %s\r\n" % (self.command, urlparse.urlunparse(('', '', path, params, query,'')),self.request_version))
                        self.headers['Connection'] = 'close'
                        del self.headers['Proxy-Connection']
                        for key_val in self.headers.items():
                            soc.send("%s: %s\r\n" % key_val)
                        soc.send("\r\n")
                        self._read_write(soc)
                    except:
                        print "Hubo un error en el metodo do_GET"
                                             
            elif scm == 'ftp':
                # fish out user and password information
                i = netloc.find ('@')
                if i >= 0:
                    login_info, netloc = netloc[:i], netloc[i+1:]
                    try: user, passwd = login_info.split (':', 1)
                    except ValueError: user, passwd = "anonymous", None
                else: user, passwd ="anonymous", None
                self.log_request ()
                try:
                    ftp = ftplib.FTP (netloc)
                    ftp.login (user, passwd)
                    if self.command == "GET":
                        ftp.retrbinary ("RETR %s"%path, self.connection.send)
                    ftp.quit ()
                except Exception, e:
                    self.server.logger.log (logging.WARNING, "FTP Exception: %s",
                                            e)
        finally:
            soc.close() 
            self.connection.close()

    def _read_write(self, soc, max_idling=20, local=False):
        iw = [self.connection, soc]
        local_data = ""
        ow = []
        count = 0
        while 1:
            count += 1
            (ins, _, exs) = select.select(iw, ow, iw, 1)
            if exs: break
            if ins:
                for i in ins:
                    if i is soc: out = self.connection
                    else: out = soc
                    data = i.recv(8192)
                    if data:
                        if local: local_data += data
                        else: out.send(data)
                        count = 0
            if count == max_idling: break
        if local: return local_data
        return None

    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT  = do_GET
    do_DELETE=do_GET

    def log_message (self, format, *args):
        self.server.logger.log (logging.INFO, "%s %s", self.address_string (),
                                format % args)
        
    def log_error (self, format, *args):
        self.server.logger.log (logging.ERROR, "%s %s", self.address_string (),
                                format % args)

class ThreadingHTTPServer (SocketServer.ThreadingMixIn,
                           BaseHTTPServer.HTTPServer):
    def __init__ (self, server_address, RequestHandlerClass, logger=None):
        BaseHTTPServer.HTTPServer.__init__ (self, server_address,
                                            RequestHandlerClass)
        self.logger = logger
        
def logSetup (logfile, logsize, cant_rotaciones):
    logger = logging.getLogger ("Cliente")
    #logger.setLevel (logging.INFO)
    logger.setLevel (logging.ERROR)
    handler = logging.handlers.RotatingFileHandler (logfile, maxBytes=(logsize*(1<<20)), backupCount=cant_rotaciones)
    fmt = logging.Formatter (
                                "[%(asctime)-12s.%(msecs)03d] "
                                "%(levelname)-4s {%(name)s %(threadName)s}"
                                " %(message)s",
                                "%Y-%m-%d %H:%M:%S")
    handler.setFormatter (fmt)
    logger.addHandler (handler)
    return logger
    

def handler (signo, frame):
    while frame and isinstance (frame, FrameType):
        if frame.f_code and isinstance (frame.f_code, CodeType):
            if "run_event" in frame.f_code.co_varnames:
                frame.f_locals["run_event"].set ()
                return
        frame = frame.f_back
    
def main ():
    run_event = threading.Event ()
    # setup the log file
    logger = logSetup (LOG_FILENAME, LOG_SIZE_MB, LOG_CANT_ROTACIONES)
    signal.signal (signal.SIGINT, handler)
    server_address = (BIND_ADDRESS, BIND_PORT)
    ProxyHandler.protocol = "HTTP/1.1"
    httpd = ThreadingHTTPServer (server_address, ProxyHandler, logger)
    sa = httpd.socket.getsockname ()
    print "Familia Segura - Cliente, atendiendo en ", sa[0], "puerto", sa[1]
    req_count = 0
    while not run_event.isSet ():
        try:
            httpd.handle_request ()
            req_count += 1
            if req_count == 1000:
                logger.log (logging.INFO, "Number of active threads: %s",
                            threading.activeCount ())
                req_count = 0
        except select.error, e:
            if e[0] == 4 and run_event.isSet (): pass
            else:
                logger.log (logging.CRITICAL, "Errno: %d - %s", e[0], e[1])
    logger.log (logging.INFO, "Server shutdown")
    return 0

if __name__ == '__main__':
    sys.exit (main ())