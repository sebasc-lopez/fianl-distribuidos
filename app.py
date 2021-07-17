from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_socketio import SocketIO, close_room, emit, join_room, leave_room, send
from flask_mysqldb import MySQL
import time
import bcrypt
from threading import Thread

app = Flask(__name__, template_folder='Templates/')
app.secret_key="appLogin"
#app.config['SECRET_KEY'] = 'secret'
app.config['MYSQL_HOST'] = 'us-cdbr-east-04.cleardb.com'
app.config['MYSQL_USER'] = 'ba7dac01c0008d'
app.config['MYSQL_PASSWORD'] = '8c4d9f42'
app.config['MYSQL_DB'] = 'heroku_daaa8b49d1664fa'

mysql = MySQL(app)

semilla = bcrypt.gensalt()

socketio = SocketIO(app)
thread = None

users = []

salas = []


def background_stuff():
     """ python code in main.py """
     print('In background_stuff')
     while True:
         time.sleep(1)
         t = str(time.perf_counter())
         print(t)
         socketio.emit('message2', {'data': 'This is data', 'time': t}, namespace='/test')


'''@app.route('/')
def index():
    global thread
    print(thread)
    if thread is None:
        thread = Thread(target=background_stuff)
        thread.start()
    return render_template('index.html')'''

@app.route('/')
def main():
    if 'nombre' in session:
        return render_template('inicio.html')
    else:
        return render_template('ingresar.html')


@app.route('/inicio')
def inicio():
    if 'nombre' in session:
        return render_template('inicio.html')
    else:
        return render_template('ingresar.html')

@app.route('/registrar', methods=["GET","POST"])
def registrar():
    if(request.method == 'GET'):
        if 'nombre' in session:
            return render_template('inicio.html')
        else:
            return render_template('ingresar.html')
    else:
        nombre = request.form['nmNombreRegistro']
        correo = request.form['nmCorreoRegistro']
        password = request.form['nmPasswordRegistro']
        password_encode = password.encode("utf-8")
        password_encriptada = bcrypt.hashpw(password_encode, semilla)

        sQuery = "INSERT into login (correo, password, nombre) VALUES ( %s, %s, %s)"

        cur = mysql.connection.cursor()

        cur.execute(sQuery,(correo, password_encriptada, nombre))

        mysql.connection.commit()

        session['nombre'] = nombre
        session['correo'] = correo
        if not(correo in users):
            user = [nombre, correo, '12345general12345',False]
            users.append(user)
        salas.append('12345general12345')

        return redirect(url_for('inicio'))

@app.route("/ingresar", methods=["GET","POST"])
def ingresar():
    if(request.method=="GET"):
        if 'nombre' in session:
            return render_template('inicio.html')
        else:
            return render_template('ingresar.html')
    else:
        correo = request.form['nmCorreoLogin']
        password = request.form['nmPasswordLogin']
        password_encode = password.encode("utf-8")

        cur = mysql.connection.cursor()

        sQuery = "SELECT correo, password, nombre FROM Login WHERE correo = %s"

        cur.execute(sQuery,[correo])

        usuario = cur.fetchone()

        cur.close()

        if (usuario != None):
            password_encriptada_encode = usuario[1].encode()

            if(bcrypt.checkpw(password_encode, password_encriptada_encode)):
                session['nombre'] = usuario[2]
                session['correo'] = correo
                if not(correo in users):
                    user = [usuario[2], correo, '12345general12345', False]
                    users.append(user)
                salas.append('12345general12345')

                return redirect(url_for('inicio'))

            else:
                flash("Contraseña Incorrecta","alert-warning")

                return render_template("ingresar.html")
        else:
            flash("El correo no existe", "alert-warning")

            return render_template('ingresar.html')


@app.route('/salir')
def salir():
    session.clear()
    return redirect(url_for('ingresar'))


def comprobar(nombreSala):
    print('usuarios',users)
    for user in users:
        print('nombre usuario', user[2])
        print('nombre sala', nombreSala)
        if user[2] == nombreSala:
            return False
    return True

def modificarSala(nombreSala, usuario, propietario):
    global users
    for user in users:
        if user[0] == usuario:
            user[2]=nombreSala
            user[3]=propietario
        
def esPropietario(data):
    for user in users:
        if user[0] == data['user']:
            if user[2] == data['room']:
                if user[3] == True:
                    return True
                else:
                    return False
    return False



def cerrarSala(sala):
    for user in users:
        if user[2] == sala:
            user[2]='12345general12345'
            user[3] = False



@socketio.on('change')
def change(user):
    print('entro')
    on_join({'room':'12345general12345','user': user})

    



@socketio.on('message')
def handleMessage(data):
    print("Message: " + data['msg'])
    print(type(data['msg']))
    if data['msg'][0] == '#':
        if data['msg'][2] == 'R':
            if data['msg'][1:3] == 'cR':
                nombreSala = data['msg'][4:]
                salaExistente = comprobar(nombreSala)
                if salaExistente:
                    modificarSala(nombreSala, data['user'], True)
                    on_leave({'room':data['room'], 'user': data['user']})
                    on_join({'room':nombreSala,'user':data['user']})
                    salas.remove(data['room'])
                    salas.append(nombreSala)
                else:
                    send('La sala ya se encuentra creada!...')
            elif data['msg'][1:3] == 'gR':
                nombreSala = data['msg'][4:]
                salaExistente = comprobar(nombreSala)
                if not salaExistente:
                    modificarSala(nombreSala, data['user'], False)
                    on_leave({'room':data['room'], 'user': data['user']})
                    on_join({'room':nombreSala,'user':data['user']})
                    salas.remove(data['room'])
                    salas.append(nombreSala)
                else:
                    send('La sala a la que intentas intrar no existe!!!...')
            elif data['msg'][1:3] == 'eR':
                if not (data['room'] == '12345general12345'):
                    respuesta = esPropietario(data)
                    if respuesta:
                        emit('cerrarSala', to = data['room'])
                        cerrarSala(data['room'])
                        send('La sala se ha cerrado', to = data['room'])
                        close_room(data['room'])
                        cantidad = salas.count(data['room'])
                        for i in range(cantidad):
                            salas.remove(data['room'])
                            salas.append('12345general12345')
            elif data['msg'][1:3] == 'IR':
                revisado = []
                respuesta = ""
                for sala in salas:
                    if not(sala in revisado):
                        cantidad = salas.count(sala)
                        revisado.append(sala)
                        if(respuesta == ""):
                            respuesta = sala + ":" + str(cantidad)
                        else:
                            respuesta = respuesta + "," + sala + ":" + str(cantidad)
                print(respuesta)
                emit('respuestaCantidad', respuesta)
            elif data['msg'][1:3] == 'dR':
                nombreSala = data['msg'][4:]
                if not (data['room'] == '12345general12345'):
                    respuesta = esPropietario(data)
                    if respuesta:
                        emit('cerrarSala', to = data['room'])
                        cerrarSala(data['room'])
                        send('La sala se ha cerrado', to = data['room'])
                        close_room(data['room'])
                        cantidad = salas.count(data['room'])
                        for i in range(cantidad):
                            salas.remove(data['room'])
                            salas.append('12345general12345')
        elif data['msg'][1:5] == "exit":
            if not (data['room'] == '12345general12345'):
                respuesta = esPropietario(data)
                if respuesta:
                    emit('cerrarSala', to = data['room'])
                    cerrarSala(data['room'])
                    send('La sala se ha cerrado', to = data['room'])
                    close_room(data['room'])
                    cantidad = salas.count(data['room'])
                    for i in range(cantidad):
                        salas.remove(data['room'])
                        salas.append('12345general12345')
                    for user in users:
                        if user[0] == data['user']:
                            users.remove(user)
                    salas.remove(data['room'])
                    session.clear()
                    emit('salir', url_for('salir'))
                else:
                    for user in users:
                        if user[0] == data['user']:
                            users.remove(user)
                    salas.remove(data['room'])
                    session.clear()
                    emit('salir', url_for('salir'))
            else:
                for user in users:
                    if user[0] == data['user']:
                        users.remove(user)
                salas.remove(data['room'])
                print(session['nombre'])
                session.clear()
                emit('salir', url_for('salir'))
        elif data['msg'][1:11] == "show users":
            usuarioAux = ""
            for user in users:
                if usuarioAux == "":
                    usuarioAux = user[0]
                else:
                    usuarioAux = usuarioAux + "," + user[0]
            send(usuarioAux)
            





    '''if(data['msg'] == '1'):
        on_leave({'room':data['room'], 'user': data['user']})
        on_join({'room':'prueba','user':data['user']})'''
    send(data['msg'], to = data['room'])
    print(data['room'])
    print(users)

@socketio.on('salaExiste')
def salaExiste(sala):
    print('entro')
    respuesta = comprobar(sala)
    emit('respuestaC',respuesta)

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    send("Te encuentras en la sala " + room)
    send(data['user'] + ' ha ingresado a la sala', to = room)


@socketio.on('leave')
def on_leave(data):
    username = data['user']
    room = data['room']
    leave_room(room)
    send(username + ' has left the room.', to=room)


'''@socketio.on('message')
def handleMessage(msg):
    print("Message: " + msg)
    send(msg, broadcast = True)'''


if __name__ == '__main__':
    socketio.run(app)
