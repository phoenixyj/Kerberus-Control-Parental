# -*- coding: utf-8 -*-

# Modulos externos
import sys, time, os, sqlite3, httplib, platform, logging, urllib2

# Modulos propios
sys.path.append('../conf')
sys.path.append('../password')

import config
import funciones
import registrar
import registrarUsuario
import peticion

# Logging
logger = funciones.logSetup (config.SYNC_LOG_FILENAME, config.SYNC_LOGLEVEL, config.SYNC_LOG_SIZE_MB, config.SYNC_LOG_CANT_ROTACIONES,"Sincronizador")

class Sincronizador:

    def __init__(self):
        self.registrador=registrar.Registradores()

        registradoLocalmente=self.registrador.checkRegistradoLocalmente()
        if not registradoLocalmente:
            logger.log(logging.INFO, "Iniciando proceso de solicitud de datos")
            reg=registrarUsuario.RegistrarUsuario()
        else:
            self.id, self.nombre, self.email, self.version, self.password = self.registrador.obtenerDatosRegistrados()
            logger.log(logging.INFO, "Esta registrado localmente")

        registradoRemotamente=self.registrador.checkRegistradoRemotamente()
        if not registradoRemotamente:
            logger.log(logging.INFO, "Iniciando proceso de registro remoto")
            self.registrador.registrarRemotamente()
        else:
            logger.log(logging.INFO, "Esta registrado remotamente")

        self.id, self.nombre, self.email, self.version, self.password = self.registrador.obtenerDatosRegistrados()
        self.peticionRemota=peticion.Peticion(self.id)

        self.conexion_db = sqlite3.connect(config.PATH_DB)
        self.cursor=self.conexion_db.cursor()
        self.ultima_actualizacion=self.cursor.execute('select ultima_actualizacion from sincronizador').fetchone()[0]
        self.ultima_recarga_completa=self.cursor.execute('select ultima_recarga_completa from sincronizador').fetchone()[0]

        self.periodo_expiracion=self.peticionRemota.obtenerPeriodoDeActualizacion()
        self.periodo_recarga_completa=self.peticionRemota.obtenerPeriodoDeRecargaCompleta()
        logger.log(logging.DEBUG, "Periodo de actualizacion: %s segundos" % self.periodo_expiracion)
        logger.log(logging.DEBUG, "Periodo de recarga completa: %s segundos" % self.periodo_recarga_completa)
        logger.log(logging.DEBUG, "Ultima actualizacion: %s"  % self.ultima_actualizacion)
        logger.log(logging.DEBUG, "Ultima recarga completa: %s"  % self.ultima_recarga_completa)

        self.recargar_todos_los_dominios = False

    def __del__(self):
       self.conexion_db.close()
       logger.log(logging.DEBUG, "Deteniendo el demonio de sincronizacion")


    def run(self):
        logger.log(logging.INFO, "Iniciando el demonio de sincronización")
        while True:
            hora_servidor=self.peticionRemota.obtenerHoraServidor()
            self.tiempo_actual=float(hora_servidor)
            tiempo_transcurrido=self.tiempo_actual - self.ultima_actualizacion
            tiempo_transcurrido_ultima_recarga=self.tiempo_actual - self.ultima_recarga_completa

            if (tiempo_transcurrido_ultima_recarga > self.periodo_recarga_completa):
                self.recargar_todos_los_dominios = True
                logger.log(logging.DEBUG,"Se recargaran todos los dominios permitidos/dengados con servidor...")

            if (tiempo_transcurrido > self.periodo_expiracion):
                logger.log(logging.DEBUG,"Sincronizando dominios permitidos/dengados con servidor...")
                self.sincronizarDominiosConServer()
            else:
                tiempo_restante=self.ultima_actualizacion + self.periodo_expiracion - self.tiempo_actual
                tiempo_proxima_recarga_completa=self.ultima_recarga_completa + self.periodo_recarga_completa - self.tiempo_actual
                logger.log(logging.DEBUG, "Faltan %s minutos para que se chequee si hay dominios nuevos, y %s minutos para recargar todos los dominios" % (tiempo_restante/60,tiempo_proxima_recarga_completa/60))
                time.sleep(tiempo_restante)
                logger.log(logging.DEBUG, "Chequeando nuevamente los dominios")


    def sincronizarDominiosPermitidos(self):
            if self.recargar_todos_los_dominios:
                self.ultima_actualizacion=0
            dominios = self.peticionRemota.obtenerDominiosPermitidos(self.ultima_actualizacion)
            if len(dominios):
                if dominios[-1]=="":
                        array_dominios=dominios.rsplit("\n")[0:-1]
                else:
                    array_dominios=dominios.rsplit("\n")
                if self.recargar_todos_los_dominios:
                    self.cursor.execute('delete from dominios_publicamente_permitidos')
                for fila in array_dominios:
                    if fila <> "":
                        #logger.log(logging.DEBUG, "Se agrego el dominio permitido: %s" % fila)
                        self.cursor.execute('insert into dominios_publicamente_permitidos(url) values(?)', (fila, ) )
                self.conexion_db.commit()
            else:
               logger.log(logging.DEBUG,"No hay dominios permitidos para actualizar")

    def sincronizarDominiosDenegados(self):
            if self.recargar_todos_los_dominios:
                self.ultima_actualizacion=0
            dominios = self.peticionRemota.obtenerDominiosDenegados(self.ultima_actualizacion)
            if len(dominios):
                if dominios[-1]=="":
                    array_dominios=dominios.rsplit("\n")[0:-1]
                else:
                    array_dominios=dominios.rsplit("\n")
                if self.recargar_todos_los_dominios:
                    self.cursor.execute('delete from dominios_publicamente_denegados')
                for fila in array_dominios:
                    if fila <> "":
                        #logger.log(logging.DEBUG, "Se agrego el dominio denegado: %s" % fila)
                        self.cursor.execute('insert into dominios_publicamente_denegados(url) values(?)',(fila, ) )
                self.conexion_db.commit()
            else:
               logger.log(logging.DEBUG,"No hay dominios denegados para actualizar")

    def sincronizarDominiosConServer(self):
            self.sincronizarDominiosPermitidos()
            self.sincronizarDominiosDenegados()
            logger.log(logging.DEBUG,"Se terminaron de sincronizar los dominios")
            if self.recargar_todos_los_dominios:
                self.cursor.execute('update sincronizador set ultima_actualizacion=?, ultima_recarga_completa=?', (self.tiempo_actual, self.tiempo_actual))
                self.recargar_todos_los_dominios = False
                self.ultima_actualizacion=self.tiempo_actual
            else:
                self.cursor.execute('update sincronizador set ultima_actualizacion=?', (self.tiempo_actual,))
            self.conexion_db.commit()
            logger.log(logging.INFO, "Se ha sincronizado la base de datos de dominios publicamente aceptados/denegados")

