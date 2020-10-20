import json
import secrets
import urllib.request
from os import environ
import mysql.connector
from flask import Flask, render_template, request, redirect, session, url_for

from hasher import hasher

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
try:
    conn = mysql.connector.connect(host=environ.get('DB_HOST'),
                                   user=environ.get('DB_USERNAME'), password=environ.get('DB_PASSWORD'),
                                   database=environ.get('DB_NAME'))
    cursor = conn.cursor()
except:
    print("Error in Database")


@app.route('/')
def singnin():
    if 'email' in session:
        return redirect('/home')
    else:
        return render_template('homepage.html')


@app.route('/logout')
def logout():
    if 'id' in session:
        session.clear()
    return redirect('/')


@app.route('/register', defaults={'msg': "None"})
@app.route('/register/<msg>')
def register(msg):
    if msg != "None":
        if msg == "Oops! An user with the same email address is already registered.":
            return render_template('register.html', msg=msg)
    return render_template('register.html')


@app.route('/settings', defaults={'check': "False"})
@app.route('/settings/<check>')
def settings(check):
    if 'email' in session:
        cursor.execute("""SELECT `name`, `place` FROM `users` WHERE `email` LIKE '{}'""".format(session['email']))
        udata = cursor.fetchall()
        if check == "True":
            return render_template('settings.html', uname=session['name'], name=udata[0][0], city=udata[0][1],
                                   check="True")
        return render_template('settings.html', uname=session['name'], name=udata[0][0], city=udata[0][1])
    return redirect('/')


@app.route('/home', defaults={'nobal': "False"})
@app.route('/home/<nobal>')
def home(nobal):
    if 'id' in session:
        cursor.execute("""SELECT * FROM `expenses` WHERE `email` LIKE '{}'""".format(session['email']))
        exp = cursor.fetchall()
        total = exp[0][1]
        expenses = exp[0][2]
        bal = exp[0][3]
        cursor.execute("""SELECT * FROM `{}`""".format(session['email']))
        data = cursor.fetchall()
        conn.commit()
        api = environ.get('API_ID')
        place = str(session['place'])
        city = place.replace(" ", "+")
        source = urllib.request.urlopen(
            'https://api.openweathermap.org/data/2.5/weather?q=' + city + '&units=metric' + '&appid=' + api).read()
        list_of_data = json.loads(source)
        weather_data = {
            "country_code": str(list_of_data['sys']['country']),
            "pressure": str(list_of_data['main']['pressure']) + ' hpa',
            "temp_cel": str(list_of_data['main']['temp']) + 'ºC',
            "humidity": str(list_of_data['main']['humidity']) + '%',
            "cityname": str(session['place']),
        }
        if nobal == "True":
            return render_template('hometemp.html', uname=session['name'], total=total, expenses=expenses, balance=bal,
                                   data=data, wdata=weather_data, nobal=nobal)
        return render_template('hometemp.html', uname=session['name'], total=total, expenses=expenses, balance=bal,
                               data=data, wdata=weather_data)
    else:
        return redirect('/')


@app.route('/login_validation', methods=['POST', 'GET'])
def login_validation():
    email = request.form.get('email')
    password1 = request.form.get('password')
    password = hasher(password1)
    cursor.execute("""SELECT * FROM `users` WHERE `email` LIKE '{}' AND `password` = '{}'""".format(email, password))
    users = cursor.fetchall()
    if len(users) > 0:
        session['id'] = users[0][0]
        session['name'] = users[0][1]
        session['email'] = users[0][2]
        session['place'] = users[0][4]
        return redirect('/home')
    else:
        return render_template('homepage.html', text="No user is available with these credentials! Please register.")


@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form.get('uname')
    email = request.form.get('uemail')
    password1 = request.form.get('upassword')
    password = hasher(password1)
    place = request.form.get('place')
    cursor.execute("""SELECT `id` FROM `users` WHERE `email` LIKE '{}'""".format(email))
    dbemail = len(cursor.fetchall())
    if dbemail > 0:
        return redirect(url_for('register', msg="Oops! An user with the same email address is already registered."))
    cursor.execute(
        """INSERT INTO `users` (`id`, `name`, `email`, `password`, `place`) VALUES (NULL, '{}', '{}', '{}', '{}')""".format(
            name, email, password, place))
    cursor.execute(
        """INSERT INTO `expenses` (`email`, `total`, `expense`, `balance`) VALUES ('{}', 0, 0, 0)""".format(email))
    conn.commit()
    cursor.execute("""CREATE TABLE `{}` (`id` INT(30) AUTO_INCREMENT PRIMARY KEY, `purpose` VARCHAR(30),
    `amount` INT(30), `type` VARCHAR(30), `balance` INT(30))""".format(email))
    cursor.execute("""SELECT * FROM `users` WHERE `email` LIKE '{}'""".format(email))
    myuser = cursor.fetchall()
    session['id'] = myuser[0][0]
    session['name'] = myuser[0][1]
    session['email'] = myuser[0][2]
    session['place'] = myuser[0][4]
    return redirect('/')


@app.route('/addmoney', methods=['POST'])
def addmoney():
    purpose = request.form.get('purpose')
    amount = int(request.form.get('amount'))
    cursor.execute("""SELECT `total`, `expense` FROM `expenses` WHERE `email` LIKE '{}'""".format(session['email']))
    cur = cursor.fetchall()
    total = cur[0][0]
    expense = cur[0][1]
    total = total + amount
    balance = total - expense
    cursor.execute(
        """UPDATE `expenses` SET `total` = {}, `balance` = {} WHERE `email` LIKE '{}'""".format(total, balance,
                                                                                                session['email']))
    cursor.execute("""INSERT INTO `{}` (`id`, `purpose`, `amount`, `type`, `balance`) VALUES (NULL, '{}',
    {}, '{}', {})""".format(session['email'], purpose, amount, "Deposit", balance))
    conn.commit()
    return redirect('/home')


@app.route('/changename', methods=['POST'])
def changename():
    name = request.form.get('cname')
    cursor.execute("""UPDATE `users` SET `name` = '{}' WHERE `email` LIKE '{}'""".format(name, session['email']))
    conn.commit()
    session['name'] = name
    return redirect('/settings')


@app.route('/changeplace', methods=['POST'])
def changeplace():
    place = request.form.get('cplace')
    cursor.execute("""UPDATE `users` SET `place` = '{}' WHERE `email` LIKE '{}'""".format(place, session['email']))
    conn.commit()
    session['place'] = place
    return redirect('/settings')


@app.route('/resetall', methods=['POST'])
def resetall():
    password1 = request.form.get('password')
    password = hasher(password1)
    cursor.execute("""SELECT `password` FROM `users` WHERE `email` LIKE '{}'""".format(session['email']))
    dbpass = str(cursor.fetchall()[0][0])
    if password == dbpass:
        cursor.execute(
            """UPDATE `expenses` SET `total` = 0, `expense` = 0, `balance` = 0 WHERE `email` LIKE '{}'""".format(
                session['email']))
        cursor.execute("""TRUNCATE TABLE `{}`""".format(session['email']))
        conn.commit()
        return redirect('/home')
    else:
        return redirect(url_for('settings', check="True"))


@app.route('/deleteaccount', methods=['POST'])
def deleteaccount():
    password1 = request.form.get('password')
    password = hasher(password1)
    cursor.execute("""SELECT `password` FROM `users` WHERE `email` LIKE '{}'""".format(session['email']))
    dbpass = str(cursor.fetchall()[0][0])
    if password == dbpass:
        cursor.execute("""DROP TABLE `{}`""".format(session['email']))
        cursor.execute("""DELETE FROM `expenses` WHERE `email` LIKE '{}'""".format(session['email']))
        cursor.execute("""DELETE FROM `users` WHERE `email` LIKE '{}'""".format(session['email']))
        conn.commit()
        return redirect('/logout')
    return redirect(url_for('settings', check=True))


@app.route('/expense', methods=['POST'])
def expense():
    purpose = request.form.get('purposeexp')
    amount = int(request.form.get('amountexp'))
    cursor.execute("""SELECT `total`, `expense` FROM `expenses` WHERE `email` LIKE '{}'""".format(session['email']))
    cur = cursor.fetchall()
    total = cur[0][0]
    expense = cur[0][1]
    if (total - amount) >= 0:
        balance = total - expense - amount
        expense = expense + amount
        cursor.execute(
            """UPDATE `expenses` SET `expense` = {}, `balance` = {} WHERE `email` LIKE '{}'""".format(
                expense, balance,
                session['email']))
        cursor.execute("""INSERT INTO `{}` (`id`, `purpose`, `amount`, `type`, `balance`) VALUES (NULL, '{}',
            {}, '{}', {})""".format(session['email'], purpose, amount, "Withdraw", balance))
        conn.commit()
        return redirect('/home')
    return redirect(url_for('home', nobal="True"))


if __name__ == '__main__':
    app.debug = True
    app.run()
