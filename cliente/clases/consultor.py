"""Modulo encargado de verificar la aptitud de una url"""

#Modulos externos
import time, re

#Modulos propios
import administradorDeUsuarios
import manejadorUrls
import usuario
import config

#Excepciones
class ConsultorError(Exception): pass
#class nombre(ConsultorError): pass

# Clase
class Consultor:
    def __init__(self):
        self.usuarios=administradorDeUsuarios.AdministradorDeUsuarios()        
        
    def debug(self, texto, activo):
        if activo:
            fin=time.time()
            tiempototal=fin-self.inicio
            if tiempototal >=config.LOG_TIEMPOS_MAYORES_A:
                print  texto
                print "Tiempo: %s segs.\n" % tiempototal
            
    def extensionValida(self, url):
        url=url.lower()
        return re.match(".*\.(gif|jpeg|jpg|png|js|css|swf|ico|json|mp3|wav|rss|rar|zip|pdf|xml)$",url)   
        
    def validarUrl(self, username, password, url):
        if not self.usuarios.usuario_valido(username, password):
            return False, "Usuario no valido"
            
        usuario=self.usuarios.obtenerUsuario(username)
        self.inicio=time.time()
        if usuario.es_admin:
            mensaje= "Usuario administrador"
            return True, mensaje
            self.debug(mensaje, config.DEBUG_IS_ADMIN)
            
        elif usuario.dominioDenegado(url):
            mensaje="Dominio denegado: " + url
            self.debug(mensaje, config.DEBUG_DOM_DENG)
            return False, mensaje
            
        elif usuario.dominioPermitido(url):
            mensaje = "Dominio permitido: " + url
            self.debug(mensaje, config.DEBUG_DOM_PERM)
            return True,  mensaje
            
        elif usuario.dominioPublicamentePermitido(url):
            mensaje = "Dominio publicamente permitido: " + url
            self.debug(mensaje, config.DEBUG_DOM_PUB_PERM)
            return True, mensaje
            
        elif usuario.dominioPublicamenteDenegado(url):
            mensaje = "Dominio publicamente denegado: " + url
            self.debug(mensaje, config.DEBUG_DOM_PUB_DENG)
            return False, mensaje
            
        elif self.extensionValida(url):
            mensaje = "Exension valida: " + url
            self.debug(mensaje , config.DEBUG_EXTENSIONES)
            return True, mensaje
            
        elif usuario.cacheAceptadas(url):
            mensaje = "CACHEADA, Autorizada: " + url
            self.debug(mensaje, config.DEBUG_CACHEADA_PERM)
            return True, mensaje
            
        elif usuario.cacheDenegadas(url):
            mensaje = "CACHEADA, Denegada: " + url
            self.debug(mensaje, config.DEBUG_CACHEADA_PERM)
            return False, mensaje
        else:
            valido, razon= usuario.validarRemotamente(url)
            if valido:
                mensaje = "Url validada remotamente : " + url
                self.debug(mensaje, config.DEBUG_VALIDA_REM)
                return True,  ""
            else:
                mensaje = "URL: %s <br>Motivo: %s" % (url,  razon)
                self.debug(mensaje, config.DEBUG_NO_VALIDA_REM)
                return False, mensaje