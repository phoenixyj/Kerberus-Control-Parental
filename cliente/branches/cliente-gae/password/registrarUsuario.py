#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
##
## Copyright (C) 2010 Riverbank Computing Limited.
## Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
## All rights reserved.
##
## This file is part of the examples of PyQt.
##
## $QT_BEGIN_LICENSE:BSD$
## You may use this file under the terms of the BSD license as follows:
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##   * Redistributions of source code must retain the above copyright
##     notice, this list of conditions and the following disclaimer.
##   * Redistributions in binary form must reproduce the above copyright
##     notice, this list of conditions and the following disclaimer in
##     the documentation and/or other materials provided with the
##     distribution.
##   * Neither the name of Nokia Corporation and its Subsidiary(-ies) nor
##     the names of its contributors may be used to endorse or promote
##     products derived from this software without specific prior written
##     permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
## $QT_END_LICENSE$
##
#############################################################################

import sys, os, re
from PyQt4.QtGui import *

sys.path.append('../clases')
sys.path.append('../conf')

import administradorDeUsuarios
import registrar
import config

class IntroPage(QWizardPage):

    def __init__(self):
        QWizardPage.__init__(self)

    def validatePage(self):
        password1=unicode(self.field("password1").toString().toUtf8(), 'utf-8')
        password2=unicode(self.field("password2").toString().toUtf8(), 'utf-8')
        if len(password1)<1:
            QMessageBox.critical(self,
                'Kerberus',
                u'Debe ingresar una contraseña!', QMessageBox.Ok)
            return False

        if (password1 <> password2):
            QMessageBox.critical(self,
                'Kerberus',
                u'Las contraseñas no coinciden!', QMessageBox.Ok)
            self.setField("password1","")
            self.setField("password2","")
            return False
        else:
            admUser=administradorDeUsuarios.AdministradorDeUsuarios()
            admUser.setPassword('admin', password1)
            return True


class RegistrationPage(QWizardPage):

    def __init__(self):
        QWizardPage.__init__(self)

    def emailValido(self, email):
        return re.match('^[(a-z0-9\_\-\.)]+@[(a-z0-9\_\-\.)]+\.[(a-z)]{2,4}$',
            email.lower())

    def validatePage(self):
        nombre=unicode(self.field("nombre").toString().toUtf8(), 'utf-8')
        email=unicode(self.field("email").toString().toUtf8(), 'utf-8')

        if len(nombre)<1:
            QMessageBox.critical(self,
                'Kerberus',
                'Debe ingresar su nombre', QMessageBox.Ok)
            return False
        elif self.emailValido(email):
            return True
        else:
            QMessageBox.critical(self,
                'Kerberus',
                u'Debe ingresar una dirección de correo electrónico válida',
                QMessageBox.Ok)
            return False


class ConclusionPage(QWizardPage):

    def __init__(self):
        QWizardPage.__init__(self)

    def initializePage(self):
        # Obtengo las variables
        nombre=unicode(self.field("nombre").toString().toUtf8(), 'utf-8')
        email=unicode(self.field("email").toString().toUtf8(), 'utf-8')
        password=unicode(self.field("password1").toString().toUtf8(), 'utf-8')
        registrador=registrar.Registradores()
        registrador.registrarLocalmente(nombre,email,password)
        titulo=u'Fin de la configuración'
        mensaje=u'Estimado %s,\n\nHemos registrado su contraseña '\
            u'correctamente.\nLe enviaremos un correo electrónico con la misma'\
            u' a %s de modo que la pueda tener presente.\n\n\nGracias por '\
            u'utilizar Kerberus Control Parental!' % (nombre, email)
        self.setTitle(titulo)
        self.setField("labelConclusion",mensaje)

# Clase principal

class RegistrarUsuario:

    def __init__(self):
        """Esta clase levanta una interfaz y solicita los datos del usuario"""
        self.lock()
        app = QApplication(sys.argv)
        wizard = QWizard()
        wizard.addPage(self.createIntroPage())
        wizard.addPage(self.createRegistrationPage())
        wizard.addPage(self.createConclusionPage())
        wizard.setWindowTitle(u'Contraseña de administrador')
        wizard.show()
        wizard.exec_()
        self.unlock()

    def lock(self):
        temp_file="%s/kerberus.lock" % config.PATH_COMMON
        if config.PLATAFORMA == 'Linux':
            os.open(temp_file,os.O_RDWR|os.O_CREAT)

    def unlock(self):
        temp_file="%s/kerberus.lock" % config.PATH_COMMON
        if config.PLATAFORMA == 'Linux':
            os.remove(temp_file)

    def createIntroPage(self):
        page = IntroPage()
        page.setTitle(u'Configure la contraseña de administrador')

        label = QLabel(u'Esta contraseña le permitirá deshabilitar '
            u'temporalmente la protección de Kerberus y le será requerida '
            u'para poder desinstalarlo.\n')
        label.setWordWrap(True)

        password1Label = QLabel(u'Contraseña:')
        password1LineEdit = QLineEdit()
        password1LineEdit.setEchoMode(QLineEdit.Password)

        password2Label = QLabel(u'Reingrese la contraseña:')
        password2LineEdit = QLineEdit()
        password2LineEdit.setEchoMode(QLineEdit.Password)

        mensajeErrorLabel = QLabel("Ingrese")

        page.registerField("password1*",password1LineEdit)
        page.registerField("password2*",password2LineEdit)

        layout = QGridLayout()
        layout.addWidget(label, 0,0,1,0)
        layout.addWidget(password1Label, 1, 0)
        layout.addWidget(password1LineEdit, 1, 1)
        layout.addWidget(password2Label, 2, 0)
        layout.addWidget(password2LineEdit, 2, 1)

        page.setLayout(layout)
        page.setButtonText(0,"Volver")
        page.setButtonText(1,"Siguiente")
        page.setButtonText(4,"Cancelar")

        return page


    def createRegistrationPage(self):
        page = RegistrationPage()
        page.setTitle("Registro")
        label = QLabel(u'Ingrese su nombre y dirección de correo electrónico,'
            u' de modo que \npodamos recordarle la contraseña que ingresó en el'
            u' paso anterior, \nen caso de que la olvide.\n')

        nameLabel = QLabel("Nombre:")
        nameLineEdit = QLineEdit()

        emailLabel = QLabel("Email:")
        emailLineEdit = QLineEdit()

        page.registerField("nombre*",nameLineEdit)
        page.registerField("email*",emailLineEdit)

        layout = QGridLayout()
        layout.addWidget(label,0,0,1,0)
        layout.addWidget(nameLabel, 1, 0)
        layout.addWidget(nameLineEdit, 1, 1)
        layout.addWidget(emailLabel, 2, 0)
        layout.addWidget(emailLineEdit, 2, 1)

        page.setLayout(layout)
        page.setButtonText(0,"Volver")
        page.setButtonText(1,"Siguiente")
        page.setButtonText(4,"Cancelar")

        return page


    def createConclusionPage(self):
        page = ConclusionPage()
        page.setTitle(u'Fin de la configuración')

        label = QLabel(u'Hemos registrado sus datos correctamente. \nGracias '
            u'por utilizar Kerberus Control Parental!')
        label.setWordWrap(True)
        page.registerField("labelConclusion",label,"text")

        layout = QVBoxLayout()
        layout.addWidget(label)
        page.setLayout(layout)
        page.setButtonText(0,"Volver")
        page.setButtonText(3,"Finalizar")
        page.setButtonText(4,"Cancelar")
        return page