#!/usr/bin/python
# -*- coding: utf-8 -*-
__version__ = "0.5"

# Modulos externos
import BaseHTTPServer, select, socket, SocketServer, urlparse
import sys
import signal
import threading
from types import FrameType, CodeType
import ftplib
import base64
import platform
import os
import time
import logging

sys.path.append('clases')
sys.path.append('conf')
sys.path.append('password')

#Modulos propios

import consultor
import manejadorUrls
import config
import funciones


if not os.path.exists(config.PATH_DB):
    funciones.crearDBCliente(config.PATH_DB)

logger = funciones.logSetup (config.LOG_FILENAME, config.LOGLEVEL, config.LOG_SIZE_MB, config.LOG_CANT_ROTACIONES,"cliente")
verificador=consultor.Consultor()
urls=manejadorUrls.ManejadorUrls()

class ProxyHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    __base = BaseHTTPServer.BaseHTTPRequestHandler
    __base_handle = __base.handle

    server_version = "Kerberus - Cliente /" + __version__
    rbufsize = 0                        # self.rfile Be unbuffered
    global verificador

    def pedirUsuario(self, motivo):
        self.send_response(407, motivo)
        self.send_header('Proxy-Authenticate', 'Basic realm="Kerberus"')
        self.send_header('Conection', 'close')
        self.end_headers()

    def mostrarPublicidad(self, url):
       msg="<html><head><title>Navegador protegido por Kerberus</title>\
        <meta http-equiv=\"REFRESH\" content=\"0;url=http://inicio.kerberus.com.ar\" > \
        </head> <body ></body> </html> "
       self.wfile.write(self.protocol_version + " 200 Connection established\r\n")
       self.wfile.write("Proxy-agent: %s\r\n" % self.version_string())
       self.wfile.write("\r\n")
       self.wfile.write(msg)


    def denegar(self, motivo, url):
        msg="<html><head><title>Sitio no permitido</title></head><body><iframe src='http://inicio.kerberus.com.ar/denegado.php?motivo=%s&url=%s' frameborder='0' width='100%%' height='100%%' scrolling='no'><h1>Sitio no permitido</h1><br><h2><a href='javascript:history.back()'> Volver </a></h2><br><h3>%s</h3><br><h3><a href='%s!DeshabilitarFiltrado!'>Deshabilitar filtrado temporalmente</a></h3><br><h3><a href=''>Agregar este sitio a dominios permitidos</a></h3></iframe></body></html>\r\n" % (motivo,url,  motivo, url)
        self.wfile.write(self.protocol_version + " 200 Connection established\r\n")
        self.wfile.write("Proxy-agent: %s\r\n" % self.version_string())
        self.wfile.write("\r\n")
        self.wfile.write(msg)
#

    def handle(self):
#        # Paso 1: autenticacion de ip origen
#        (ip, port) =  self.client_address
#        self.server.logger.log (logging.INFO, "Request from '%s'", ip)
#        if hasattr(self, 'allowed_clients') and ip not in self.allowed_clients:
#            self.raw_requestline = self.rfile.readline()
#            if self.parse_request():
#                self.send_error(403)
#        else:
        self.__base_handle()

    def _connect_to(self, netloc, soc):
        i = netloc.find(':')
        if i >= 0:
            host_port = netloc[:i], int(netloc[i+1:])
        else:
            host_port = netloc, 80
        self.server.logger.log (logging.DEBUG, "connect to %s:%d", host_port[0], host_port[1])
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
#                self.log_request(200)
                self.wfile.write(self.protocol_version +" 200 Connection established\r\n")
                self.wfile.write("Proxy-agent: %s\r\n" % self.version_string())
                self.wfile.write("\r\n")
                self._read_write(soc, 300)
        finally:
            soc.close()
            self.connection.close()

    def do_GET(self):
        # Paso 3: peticion del recurso
        # Verificacion del usuario y url
        url=self.path
        if verificador.primerUrl:
            verificador.primerUrl=False
            self.mostrarPublicidad(url)
            return False

        proxy_user=self.headers.getheader('Proxy-Authorization')
        if proxy_user:
            usuario, password=base64.b64decode(proxy_user.split(' ')[1]).split(':')
        else:
            usuario, password="NoBody", "NoBody"
            if "!DeshabilitarFiltrado!" in url:
                self.server.logger.log (logging.INFO, "Solicitando acceso para usuarios adultos")
                self.pedirUsuario("Acceso para usuarios adultos")
                return False

        if "!DeshabilitarFiltrado!" in url:
                url=url[:-22]
        # es para que muestre que kerberus esta activo, asi no lo muestra cuando se accede
        # a la pagina desde cualquier lugar
        if "http://inicio.kerberus.com.ar" in url and usuario == "NoBody" and "?kerberus_activado=1" not in url:
            url+="?kerberus_activado=1"

        permitido, motivo=verificador.validarUrl(usuario, password,url)
        if not permitido:
            self.denegar(motivo, url)
            return False

        if urls.soportaSafeSearch(url):
            url=urls.agregarSafeSearch(url)
            self.server.logger.log (logging.INFO, "La URL %s  soporta SafeSearch. Forzando su uso", url)

        (scm, netloc, path, params, query, fragment) = urlparse.urlparse(url,  'http')
        if scm not in ('http', 'ftp') or fragment or not netloc:
            self.send_error(400, "Url erronea: %s" % url)
            return False
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
                        self.server.logger.log (logging.ERROR, "Hubo un error en el metodo do_GET. URL: %s", url)

            elif scm == 'ftp':
                # fish out user and password information
                i = netloc.find ('@')
                if i >= 0:
                    login_info, netloc = netloc[:i], netloc[i+1:]
                    try:
                        user, passwd = login_info.split (':', 1)
                    except ValueError:
                        user, passwd = "anonymous", None
                else:
                    user, passwd ="anonymous", None
                self.log_request ()
                try:
                    ftp = ftplib.FTP (netloc)
                    ftp.login (user, passwd)
                    if self.command == "GET":
                        ftp.retrbinary ("RETR %s"%path, self.connection.send)
                    ftp.quit ()
                except Exception, e:
                    self.server.logger.log (logging.WARNING, "FTP Exception: %s", e)
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
            if exs:
                break
            if ins:
                for i in ins:
                    if i is soc:
                        out = self.connection
                    else:
                        out = soc
                    data = i.recv(8192)
                    if data:
                        if local:
                            local_data += data
                        else:
                            out.send(data)
                        count = 0
            if count == max_idling:
                break
        if local:
            return local_data
        return None

    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT  = do_GET
    do_DELETE=do_GET

    def log_message (self, format, *args):
        self.server.logger.log (logging.DEBUG, "%s %s", self.address_string (),
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
    signal.signal (signal.SIGINT, handler)
    server_address = (config.BIND_ADDRESS, config.BIND_PORT)
    ProxyHandler.protocol = "HTTP/1.1"
    if config.USAR_PROXY:
        logger.log(logging.INFO,"Usando kerberus a traves de proxy %s:%s" % (config.PROXY_IP,config.PROXY_PORT))
    httpd = ThreadingHTTPServer (server_address, ProxyHandler, logger)
    sa = httpd.socket.getsockname ()
    logger.log(logging.INFO,'Kerberus - Cliente Activo, atendiendo en %s puerto %s' % (sa[0],sa[1],))
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
    logger.log (logging.INFO, "Se ha detenido el cliente de Kerberus satisfactoriamente")
    return 0

if __name__ == '__main__':
    sys.exit (main ())
