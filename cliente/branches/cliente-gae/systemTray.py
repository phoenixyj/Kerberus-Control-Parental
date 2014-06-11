# -*- coding: utf-8 -*-

# Modulos externos
from PyQt4.QtGui import QWidget, QPixmap, QIcon, QSystemTrayIcon, QMenu
from PyQt4.QtGui import QStyle, QApplication, QCursor
from PyQt4.QtCore import QObject, SIGNAL
import sys
import os.path
import time
import httplib

sys.path.append('adminpanel')
# Modulos propios
import webbrowser
import adminPanel
import config

class KerberusSystray(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        icono = 'kerby-activo.ico'
        pixmap = QPixmap(icono)
        self.style = self.style()
        ##setear el nombre de la ventana
        self.setWindowTitle('Kerberus Control Parental')
        #colocar el icono cargado a la ventana
        self.setWindowIcon(self.style.standardIcon(
            QStyle.SP_DialogYesButton))
        ##creamos objeto Style para hacer uso de los iconos de Qt

        self.filtradoHabilitado = True

        if not os.path.isfile('dontShowMessage'):
            self.mostrarMensaje = True
            self.noMostrarMasMensaje()
        else:
            self.mostrarMensaje = False

        #Menu
        self.menu = QMenu('Kerberus')

        #accion configurar Dominios
        self.configurarDominiosAction = self.menu.addAction(
                            self.style.standardIcon(QStyle.SP_ArrowRight),
                            'Permitir/Denegar dominios'
                            )
        #accion deshabilitar filtrado
        self.deshabilitarFiltradoAction = self.menu.addAction(
                            self.style.standardIcon(QStyle.SP_DialogNoButton),
                            'Deshabilitar Filtrado'
                            )
        #accion habilitar filtrado
        self.habilitarFiltradoAction = self.menu.addAction(
                            self.style.standardIcon(QStyle.SP_DialogYesButton),
                            'Habilitar Filtrado'
                            )
        self.habilitarFiltradoAction.setVisible(False)
        #cambiar password
        self.cambiarPasswordAction = self.menu.addAction(
                self.style.standardIcon(QStyle.SP_BrowserReload),
                'Cambiar password de administrador'
                )
        #accion salir
        self.exitAction = self.menu.addAction(
                self.style.standardIcon(QStyle.SP_TitleBarCloseButton),
                'Salir')

        #SIGNAL->SLOT
        QObject.connect(
                self.exitAction,
                SIGNAL("triggered()"),
                lambda: sys.exit()
                )
        QObject.connect(
                self.menu, SIGNAL("clicked()"),
                lambda: self.menu.popup(QCursor.pos())
                )
        QObject.connect(
                self.deshabilitarFiltradoAction,
                SIGNAL("triggered()"),
                self.deshabilitarFiltradoWindow
                )
        QObject.connect(
                self.habilitarFiltradoAction,
                SIGNAL("triggered()"),
                self.habilitarFiltradoWindow
                )
        QObject.connect(
                self.cambiarPasswordAction,
                SIGNAL("triggered()"),
                self.cambiarPasswordWindow
                )
        QObject.connect(
                self.configurarDominiosAction,
                SIGNAL("triggered()"),
                self.configurarDominios
                )

        #SystemTray
        #self.tray = QSystemTrayIcon(QIcon(pixmap), self)
        self.tray = QSystemTrayIcon(self.style.standardIcon(
            QStyle.SP_DialogYesButton), self
            )
        self.tray.setToolTip('Kerberus Control Parental - Activado')
        self.tray.setContextMenu(self.menu)
        self.tray.setVisible(True)

        QObject.connect(
                self.tray,
                SIGNAL("messageClicked()"),
                self.noMostrarMasMensaje
                )

        if self.mostrarMensaje:
            self.tray.showMessage(
                    u'Kerberus Control Parental',
                    u'Filtro de Protección para menores de edad Activado',
                    2000
                    )

    def configurarDominios(self):
        admin = adminPanel.adminPanel()
        admin.show()

    def noMostrarMasMensaje(self):
        try:
            open('dontShowMessage', 'a').close()
        except IOError:
            print 'No se pudo crear el archivo dontShowMessage'

    def deshabilitarFiltradoWindow(self):
        url = 'http://%s:%s/!DeshabilitarFiltrado!' % ('inicio.kerberus.com.ar','80')
        webbrowser.open(
                url,
                new=2
                )
        self.habilitarFiltradoAction.setVisible(True)
        self.deshabilitarFiltradoAction.setVisible(False)
        self.tray.setIcon(self.style.standardIcon(
            QStyle.SP_DialogYesButton))
        self.tray.setToolTip('Kerberus Control Parental')


    def checkKerberusStatus(self):
        url = 'http://%s:%s/' % (config.BIND_ADDRESS,
                                                           config.BIND_PORT)
        con = httplib.HTTPConnection(config.BIND_ADDRESS,config.BIND_PORT)
        respuesta = con.request(method='KERBERUSESTADO', url=url)
        print respuesta
        return respuesta == 'Activo'

    def habilitarFiltradoWindow(self):
        url = "http://%s:%s/!HabilitarFiltrado!" % ('inicio.kerberus.com.ar','80')
        webbrowser.open(
                url,
                new=2
                )
        self.habilitarFiltradoAction.setVisible(False)
        self.deshabilitarFiltradoAction.setVisible(True)
        self.tray.setIcon(self.style.standardIcon(
            QStyle.SP_DialogYesButton))
        self.tray.setToolTip('Kerberus Control Parental - Activado')

    def cambiarPasswordWindow(self):
        url = "http:/%s:%s/!CambiarPassword!" % ('inicio.kerberus.com.ar','80')
        webbrowser.open(
                url,
                new=2
                )

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
pytest = KerberusSystray()
sys.exit(app.exec_())
