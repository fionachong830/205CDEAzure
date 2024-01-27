from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bootstrap import Bootstrap
import os 
from flask_mail import Mail, Message
from ShoppingCart import ShoppingCart 
from distutils.log import debug
import pymysql 
from fileinput import filename
import mysql.connector
from mysql.connector import errorcode
from azure.storage.fileshare import ShareServiceClient, ShareFileClient
from azure.storage.blob import BlobServiceClient

app = Flask(__name__)
cart=[]

connect_str = os.environ.get('AZURE_STORAGEFILE_CONNECTIONSTRING')
# retrieve the connection string from the environment variable

container_product = "product" # container name in which images will be store in the storage account

blob_service_client_product = BlobServiceClient.from_connection_string(conn_str=connect_str) # create a blob service client to interact with the storage account
try:
    container_client_product = blob_service_client_product.get_container_client(container=container_product) # get container client to interact with the container in which images will be stored
    container_client_product.get_container_properties() # get properties of the container to force exception to be thrown if container does not exist
except Exception as e:
    container_client_product = blob_service_client_product.create_container(container_product) # create a container in the storage account if it does not exist

container_doc = "uploaddoc" # container name in which images will be store in the storage account

blob_service_client_doc = BlobServiceClient.from_connection_string(conn_str=connect_str) # create a blob service client to interact with the storage account
try:
    container_client_doc = blob_service_client_doc.get_container_client(container=container_doc) # get container client to interact with the container in which images will be stored
    container_client_doc.get_container_properties() # get properties of the container to force exception to be thrown if container does not exist
except Exception as e:
    container_client_doc = blob_service_client_doc.create_container(container_doc) # create a container in the storage account if it does not exist

app.config['SECRET_KEY'] = 'top-secret!'
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') 
app.config['MAIL_DEFAULT_SENDER'] = 'worktestacc02@gmail.com'
mail = Mail(app)
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

bootstrap = Bootstrap(app)

try:
   connection = pymysql.connect(user=os.environ.get('AZURE_MYSQL_USER'), password=os.environ.get('AZURE_MYSQL_PASSWORD'), host=os.environ.get('AZURE_MYSQL_HOST'), port=3306, database="205cde", ssl_ca="DigiCertGlobalRootCA.crt.pem", ssl_disabled=False, local_infile = 1, cursorclass=pymysql.cursors.DictCursor)
   print("Connection established")
except mysql.connector.Error as err:
  if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
    print("Something is wrong with the user name or password")
  elif err.errno == errorcode.ER_BAD_DB_ERROR:
    print("Database does not exist")
  else:
    print(err)
else:
  cursor = connection.cursor()

def sendemail(email, subject, message):
    msg = Message(
        subject=subject,
        recipients=[email],
        html=message
        )
    mail.send(msg)    

def initial(id):
    product = getProduct()
    for e in product:
        cart.append(ShoppingCart(id, e['prodID'], e['productName'], 0, e['prodPrice']))    

def checkLoginStatus(id):
    sql = 'SELECT loginStatus from userInfo WHERE userID={id}'
    cursor.execute(sql.format(id=id))
    data = cursor.fetchall()
    for e in data:
        if e['loginStatus']== 1:
            return True
        else: 
            return False

def getProduct():
    cursor.execute('SELECT * FROM product WHERE deletedInd="N"')
    product = cursor.fetchall()
    return product 
        
def updateStatus():
    cursor.execute('UPDATE subscription SET subStatus="Expired" WHERE subEnd < curdate()')
    connection.commit()
 
def getUserInfo(id):
    updateStatus()
    sql = 'SELECT *, SUBSTRING(name, 1, 1) AS sName from userInfo WHERE userID={id}'
    cursor.execute(sql.format(id=id))
    user = cursor.fetchall()
    return user

@app.route("/")
def home():
    print('Request for home page received')
    return render_template('home.html')

@app.route("/login", methods=['POST', 'GET'])
def login():
    print('Request for login page received')
    if request.method == 'POST':
        userName = request.form['userName']
        password = request.form['password']
        accType = request.form['accType']
        sql = 'SELECT userID, password from userInfo WHERE userName="{userName}" and role="{accType}"'
        cursor.execute(sql.format(userName=userName, accType=accType))
        result = cursor.fetchall()
        for i in result: 
            if i['password'] == password:
                id = i['userID']
                sql = 'UPDATE userInfo set loginStatus=1 where userID={id};'
                cursor.execute(sql.format(id=id))
                connection.commit()
                if accType=="C":
                    initial(id)
                    return redirect('/customer/{id}/dashboard'.format(id=id))
                else: 
                    return redirect('/staff/{id}/dashboard'.format(id=id))
            else: 
                return render_template('login.html', status='fail')
        return render_template('login.html', status='fail')
    else:
        return render_template('login.html')

@app.route("/signup", methods=['POST', 'GET'])
def signup():
    print('Request for signup page received')
    if request.method == 'POST':
        name = request.form['name']
        phoneNo = request.form['phoneNo'].strip()
        email = request.form['email'].strip()
        userName = request.form['userName']
        password = request.form['password']
        confirmPassword = request.form['confirmPassword']
        if confirmPassword == password:
            cursor.execute('SELECT * FROM userInfo')
            result = cursor.fetchall()
            for i in result:
                if i['userName'] == userName:
                    return render_template('signup.html', status='usernamedup')
                if int(i['phoneNo']) == int(phoneNo):
                    return render_template('signup.html', status='phoneNodup')
                if i['email'] == email:
                    return render_template('signup.html', status='emaildup')                
            insertsql='INSERT INTO userInfo(userName, password, name, phoneNo, email, role, loginStatus) VALUES ("{userName}", "{password}", "{name}", "{phoneNo}", "{email}", "C", 1)'
            cursor.execute(insertsql.format(userName=userName, password=password, name=name, phoneNo=phoneNo, email=email))
            connection.commit()
            sql = 'SELECT userID from userInfo WHERE userName="{userName}"'
            cursor.execute(sql.format(userName=userName))
            result = cursor.fetchall()
            for i in result: 
                id = i['userID']
            initial(id)
            return redirect('/customer/{id}/dashboard'.format(id=id))
        else:
            return render_template('signup.html', status='invalidConfirmPassword')
    else:
        return render_template('signup.html', status=None)

@app.route("/forgotPassword")
def forgotPassword():
    print('Request for forgot password page received')
    return render_template('forgotPassword.html')

@app.route("/forgotPassword/email", methods=['POST'])
def password():
    print('Request for forgot password email received')
    phoneNo = request.form['phoneNo'].strip()
    email = request.form['email'].strip()
    cursor.execute('SELECT * from userInfo')
    result = cursor.fetchall()
    for i in result: 
        if int(i['phoneNo']) == int(phoneNo):   
            if i['email'] == email:
                subject = 'Forget password'
                message = 'Your Username: {username} <br> <br>' \
                    'Your Password: {password}<br> <br>'. format(username=i['userName'] , password=i['password'] )
                sendemail(email, subject, message)
                return render_template('forgotPassword.html', status='sent')  
    return render_template('forgotPassword.html', status='fail')
        
@app.route("/product")
def productGuest():
    print('Request for guest product page received')
    product = getProduct()
    return render_template('productGuest.html', product=product)

@app.route("/<int:id>/logout", methods=['GET'])
def logout(id):
    print('Request for logout page received')
    global cart 
    sql = 'UPDATE userInfo set loginStatus=0 where userID={id};'
    cursor.execute(sql.format(id=id))
    connection.commit()
    cart=[]
    return render_template('login.html')

"Customer app route" 
@app.route("/customer/<int:id>/dashboard", methods=['POST', 'GET'])
def cusDashboard(id):
    print('Request for customer dashboard page received')
    if checkLoginStatus(id) == True:
        sql = '''    
        select *, DATEDIFF(subscription.subEnd, CURDATE()) as remaining 
        from product, subscription, userInfo
        where product.prodID=subscription.prodID and userInfo.userID=subscription.userID and userInfo.userID={id} and product.deletedInd='N' and subscription.subEnd>=CURDATE()
        '''
        cursor.execute(sql.format(id=id))
        data = cursor.fetchall()
        product = getProduct()
        user = getUserInfo(id)
        if request.method == 'POST':
            prodID = request.form['prodID']
            days = request.form['days']
            for e in cart:
                if e.cid == id: 
                    if int(e.id) == int(prodID):
                        e.add(days)        
        return render_template('cusDashboard.html', product=product, data=data, user=user)
    else: 
        return render_template('404.html'), 404

@app.route("/customer/<int:id>/dashboard/<int:prodid>", methods=['GET'])
def cusDashboardDetails(id, prodid):
    print('Request for customer dashboard details page received')
    if checkLoginStatus(id) == True:
        sql = '''    
        select * from subHistory, product, payment 
        where product.prodID=subHistory.prodID and subHistory.payID=payment.payID and subHistory.userID={id} and subHistory.prodID={prodid}
        '''
        cursor.execute(sql.format(id=id, prodid=prodid))
        data = cursor.fetchall()  
        cursor.execute('SELECT productName from product where prodID={prodid}'.format(prodid=prodid))
        prodName = cursor.fetchall() 
        user = getUserInfo(id)
        return render_template('cusDashboardDetails.html', data=data, user=user, prodName=prodName)
    else: 
        return render_template('404.html'), 404

@app.route("/customer/<int:id>/product", methods=['POST', 'GET'])
def cusProduct(id):
    print('Request for customer product page received')
    if checkLoginStatus(id) == True:    
        product = getProduct()
        user = getUserInfo(id)
        if request.method == 'POST':
            prodID = request.form['prodID']
            days = request.form['days']
            for e in cart:
                if e.cid == id:
                    if int(e.id) == int(prodID):
                        e.add(days)
        return render_template('cusProduct.html', product=product, user=user)
    else: 
        return render_template('404.html'), 404

@app.route("/customer/<int:id>/buy", methods=['POST', 'GET'])
def cusBuy(id):
    print('Request for buy items received')
    if checkLoginStatus(id) == True:    
        if request.method == 'POST':
            cursor.execute('SELECT money from userInfo where userID={id}'.format(id=id))
            money = cursor.fetchall()
            for a in money:
                x = a["money"]
                if x >= 0:
                    if x >= ShoppingCart.total:
                        amount = 0
                        sql = 'insert into payment(payAmount,userID,payStatus,confirmDate) values ({amount}, {id}, "Approved",curdate())'
                        cursor.execute(sql.format(amount=ShoppingCart.total, id=id))
                        connection.commit()
                        cursor.execute("SELECT payID FROM payment ORDER BY payID DESC LIMIT 1")
                        payInfo=cursor.fetchall()
                        for e in payInfo:
                            payID = e['payID']
                            for e in cart:
                                if e.cid == id:
                                    if e.count != 0:
                                        sql = 'insert into subHistory(subHDay, payID, subAmount,userID,prodID,subHstatus) values({subHDay}, {payID}, {subAmount}, {userID}, {prodID},"Approved");'
                                        cursor.execute(sql.format(subHDay=e.count, payID=payID, subAmount=e.subtotal(), userID=id, prodID=e.id))
                                        connection.commit()
                            sql = 'UPDATE userInfo SET money={money} WHERE userID={id}'
                            cursor.execute(sql.format(money=(x-ShoppingCart.total), id=id))
                            connection.commit()
                            sql = 'SELECT * FROM subHistory WHERE payID={payID}'
                            cursor.execute(sql.format(payID=payID))
                            sub = cursor.fetchall()
                            for e in sub:
                                sql = 'SELECT * FROM subscription WHERE userID={id} AND prodID={prodID}'
                                cursor.execute(sql.format(prodID=e['prodID'], id=e['userID']))
                                current = cursor.fetchall()
                                if current == ():
                                    sql = 'UPDATE subHistory SET subHStart=curdate(), subHEnd=DATE_ADD(curdate(), INTERVAL subHDay DAY) WHERE subHID={subHID}'
                                    cursor.execute(sql.format(subHID=e['subHID']))
                                    connection.commit()
                                    sql = "INSERT INTO subscription(subStart, subEnd, subStatus, userID, prodID) VALUES (curdate(), DATE_ADD(curdate(), INTERVAL {days} DAY), 'Ongoing', {id}, {prodID})"
                                    cursor.execute(sql.format(days=e['subHDay'], id=e['userID'], prodID=e['prodID']))
                                    connection.commit()
                                else:
                                    for c in current:
                                        if c['subStatus'] == 'Expired':
                                            sql = 'UPDATE subHistory SET subHStart=curdate(), subHEnd=DATE_ADD(curdate(), INTERVAL subHDay DAY) WHERE subHID={subHID}'
                                            cursor.execute(sql.format(subHID=e['subHID']))
                                            connection.commit()
                                            sql = 'UPDATE subscription SET subStart=curdate(), subEnd=DATE_ADD(curdate(), INTERVAL {days} DAY), subStatus="Ongoing" WHERE subID={subID}'
                                            cursor.execute(sql.format(days=e['subHDay'] , subID=c['subID']))
                                            connection.commit()
                                        elif c['subStatus'] == 'Ongoing':
                                            sql = 'UPDATE subHistory SET subHStart="{subEnd}", subHEnd=DATE_ADD("{subEnd}", INTERVAL {days} DAY) WHERE subHID={subHID}'
                                            cursor.execute(sql.format(days=e['subHDay'], subHID=e['subHID'], subEnd=c['subEnd']))
                                            connection.commit()
                                            sql = 'UPDATE subscription SET subEnd=DATE_ADD("{subEnd}", INTERVAL {days} DAY), subStatus="Ongoing" WHERE subID={subID}'
                                            cursor.execute(sql.format(days=e['subHDay'] , subID=c['subID'], subEnd=c['subEnd']))
                                            connection.commit()                        
                    else:
                        amount=ShoppingCart.total-x
                        sql = 'insert into payment(payAmount,userID) values ({amount}, {id})'
                        cursor.execute(sql.format(amount=amount, id=id))
                        connection.commit()        
                        cursor.execute("SELECT payID FROM payment ORDER BY payID DESC LIMIT 1")
                        payInfo=cursor.fetchall()
                        for e in payInfo:
                            payID = e['payID']
                            for e in cart:
                                if e.cid == id:
                                    if e.count != 0:
                                        sql = 'insert into subHistory(subHDay, payID, subAmount,userID, prodID) values({subHDay}, {payID}, {subAmount}, {userID}, {prodID});'
                                        cursor.execute(sql.format(subHDay=e.count, payID=payID, subAmount=e.subtotal(), userID=id, prodID=e.id))
                                        connection.commit() 
                        sql = 'UPDATE userInfo SET money={money} WHERE userID={id}'
                        cursor.execute(sql.format(money=0, id=id))
                else:
                    amount = ShoppingCart.total
                    sql = 'insert into payment(payAmount,userID) values ({amount}, {id})'
                    cursor.execute(sql.format(amount=amount, id=id))
                    connection.commit()
                    cursor.execute("SELECT payID FROM payment ORDER BY payID DESC LIMIT 1")
                    payInfo=cursor.fetchall()
                    for e in payInfo:
                        payID = e['payID']
                        for e in cart:
                            if e.cid == id:
                                if e.count != 0:
                                    sql = 'insert into subHistory(subHDay, payID, subAmount,userID, prodID) values({subHDay}, {payID}, {subAmount}, {userID}, {prodID});'
                                    cursor.execute(sql.format(subHDay=e.count, payID=payID, subAmount=e.subtotal(), userID=id, prodID=e.id))
                                    connection.commit()
            for e in cart:
                e.clear()
            sql = '''    
            select * from subHistory, product, payment
            where product.prodID=subHistory.prodID and subHistory.payID=payment.payID and payment.payID={pid}
            '''
            cursor.execute(sql.format(pid=payID))
            data = cursor.fetchall()   
            user = getUserInfo(id)
            return render_template('cusUploadDocumentDetails.html', data=data, user=user, amount=amount)
        else: 
            product = getProduct()
            user = getUserInfo(id)
            return render_template('cusProduct.html', product=product, user=user)
    else: 
        return render_template('404.html'), 404

@app.route("/customer/<int:id>/subscriptionHistory", methods=['GET'])
def cusSubscriptionHistory(id):
    print('Request for customer subscription history page received')
    if checkLoginStatus(id) == True: 
        sql = '''    
        select * from subHistory, product, payment
        where product.prodID=subHistory.prodID and subHistory.payID=payment.payID and subHistory.userID={id}
        order by subHID
        '''
        cursor.execute(sql.format(id=id))
        data = cursor.fetchall()   
        user = getUserInfo(id)
        return render_template('cusSubscriptionHistory.html', data=data, user=user)

@app.route("/customer/<int:id>/uploadDocument", methods=['GET'])
def cusUploadDocument(id): 
    print('Request for customer upload document page received')
    if checkLoginStatus(id) == True:  
        sql = '''    
        select * from payment
        where userID={id} and payStatus != "Approved"
        '''
        cursor.execute(sql.format(id=id))
        data = cursor.fetchall() 
        user = getUserInfo(id)
        return render_template('cusUploadDocument.html', data=data, user=user, status=None)
    else: 
        return render_template('404.html'), 404

@app.route("/customer/<int:id>/uploadDocument/submit", methods=['POST','GET'])
def cusUploadDocumentSubmit(id):
    print('Request for upload document received')
    if checkLoginStatus(id) == True:  
        user = getUserInfo(id)
        if request.method == 'POST':
            payID = request.form['payID']
            payDoc = request.files['payDoc']
            filenames = ""            
            sql = 'SELECT payStatus from payment where payID={payID}'
            cursor.execute(sql.format(payID=payID))
            paystatus = cursor.fetchall()  
            for e in paystatus: 
                if e['payStatus'] != "Approved":
                    for file in request.files.getlist("payDoc"):
                        try:
                            container_client_doc.upload_blob(file.filename, file) # upload the file to the container using the filename as the blob name
                            filenames += file.filename + "<br /> "
                            sql = 'UPDATE payment SET payDoc="{doc}", payStatus="Pending for Approval" WHERE payID={payID}'
                            cursor.execute(sql.format(payID=payID, doc=payDoc.filename))
                            connection.commit()
                            sql = 'UPDATE subHistory SET subHstatus="Pending for Approval" WHERE payID={payID}'
                            cursor.execute(sql.format(payID=payID))
                            connection.commit()
                            status='success'                            
                        except Exception as e:
                            print(e)
                            print("Ignoring duplicate filenames") # ignore duplicate filenames
                            status='NameDup'
                else:
                    status='fail_status'
        sql = '''    
        select * from payment
        where userID={id} and payStatus != "Approved"
        '''
        cursor.execute(sql.format(id=id))
        data = cursor.fetchall() 
        return render_template('cusUploadDocument.html', data=data, user=user, status=status)
    else: 
        return render_template('404.html'), 404
    
@app.route("/customer/<int:id>/uploadDocument/<int:pid>", methods=['GET'])
def cusSubscriptionDetails(id, pid):
    print('Request for upload document details page received')
    if checkLoginStatus(id) == True: 
        sql = 'SELECT payAmount FROM payment WHERE payID={pid}'
        cursor.execute(sql.format(pid=pid))
        payAmount = cursor.fetchall() 
        for x in payAmount:
            amount = x['payAmount']
        sql = '''    
        select * from subHistory, product, payment
        where product.prodID=subHistory.prodID and subHistory.payID=payment.payID and payment.payID={pid}
        '''
        cursor.execute(sql.format(pid=pid))
        data = cursor.fetchall()   
        user = getUserInfo(id)
        return render_template('cusUploadDocumentDetails.html', data=data, user=user, amount=amount)
    
@app.route("/customer/<int:id>/shoppingCart", methods=['POST', 'GET'])
def cusShoppingCart(id):
    print('Request for add items to cart received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        if request.method == 'POST':
            prodID = request.form['prodID']
            days = request.form['days']
            for e in cart:
                if e.cid == id:
                    if int(e.id) == int(prodID):
                        e.update(days)        
        list=[]
        x = 0
        for e in cart:
            if e.cid == id:
                if e.count != 0:
                    list.append(e)
                    x += 1 
        total = ShoppingCart.total
        if x == 0:
            return render_template('cusShoppingCart.html', user=user, status='Empty')
        else:
            return render_template('cusShoppingCart.html', user=user, list=list, total=total)
    else: 
        return render_template('404.html'), 404

@app.route("/customer/<int:id>/personalInfo", methods=['POST','GET'])
def cusPersonalInfo(id):
    print('Request for personal info page received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        if request.method == 'POST':
            name = request.form['name']
            phoneNo = request.form['phoneNo']
            email = request.form['email']
            userName = request.form['userName']
            sql = 'SELECT * FROM userInfo WHERE userID!={id}'
            cursor.execute(sql.format(id=id))
            result = cursor.fetchall()
            for i in result:
                if i['userName'] == userName:
                    return render_template('cusPersonalInfo.html', user=user, status='usernamedup')
                if int(i['phoneNo']) == int(phoneNo):
                    return render_template('cusPersonalInfo.html', user=user, status='phoneNodup')
                if i['email'] == email:
                    return render_template('cusPersonalInfo.html', user=user, status='emaildup')                
            sql='UPDATE userInfo SET userName="{userName}", name="{name}", phoneNo={phoneNo}, email="{email}" WHERE userID={id}'
            cursor.execute(sql.format(userName=userName, name=name, phoneNo=phoneNo, email=email, id=id))
            connection.commit()
            user = getUserInfo(id)
            return render_template('cusPersonalInfo.html', user=user, status='success')
        else:
            return render_template('cusPersonalInfo.html', user=user, status='None')
    else: 
        return render_template('404.html'), 404

@app.route("/customer/<int:id>/changePassword", methods=['POST','GET'])
def cusChangePassword(id):
    print('Request for change password page received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        if request.method == 'POST':
            password = request.form['password']
            confirmPassword = request.form['confirmPassword']
            if password == confirmPassword:
                sql='UPDATE userInfo SET password="{password}" WHERE userID={id}'
                cursor.execute(sql.format(password=password, id=id))
                connection.commit()
                return render_template('cusChangePassword.html', user=user, status='success')   
            else: 
                return render_template('cusChangePassword.html', user=user, status='fail')         
        else:
            return render_template('cusChangePassword.html', user=user, status='None')
    else: 
        return render_template('404.html'), 404
    
@app.route("/customer/<int:id>/helpSupport",  methods=['POST','GET'])
def cusHelpSupport(id):
    print('Request for help and support page received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        product = getProduct()
        sql = '''    
        select * from subHistory where userID={id}
        '''
        cursor.execute(sql.format(id=id))
        data = cursor.fetchall()  
        if request.method == 'POST':
            session = request.form['session']
            question = request.form['question']
            subHID = request.form['subHID']
            if subHID == "None":
                insertsql='INSERT INTO inquiry(userID, session, question) VALUES ({id}, "{session}", "{question}")'
                cursor.execute(insertsql.format(id=id, session=session, question=question))
            else:
                insertsql='INSERT INTO inquiry(userID, session, question, subHID) VALUES ({id}, "{session}", "{question}", {subHID})'
                cursor.execute(insertsql.format(id=id, session=session, question=question, subHID=subHID))
            connection.commit()
            return render_template('cusHelpSupport.html', user=user, data=data, product=product, status='success')
        else:
            return render_template('cusHelpSupport.html', user=user, data=data, product=product)
    else: 
        return render_template('404.html'), 404
    
"Staff app route"
@app.route("/staff/<int:id>/dashboard", methods=['GET'])
def staffDashboard(id):
    print('Request for staff dashboard page received')
    if checkLoginStatus(id) == True:
        sql = '''    
        select *, DATEDIFF(subscription.subEnd, CURDATE()) as remaining 
        from product, subscription, userInfo
        where product.prodID=subscription.prodID and userInfo.userID=subscription.userID and product.deletedInd='N' and subscription.subEnd>=CURDATE()
        '''
        cursor.execute(sql)
        data = cursor.fetchall()
        product = getProduct()
        user = getUserInfo(id)
        return render_template('staffDashboard.html', product=product, data=data, user=user)
    else: 
        return render_template('404.html'), 404

@app.route("/staff/<int:id>/dashboard/<int:cid>/<int:prodid>", methods=['GET'])
def staffDashboardDetails(id, prodid, cid):
    print('Request for staff dashboard details page received')
    if checkLoginStatus(id) == True:
        sql = '''    
        select * from subHistory, product, payment
        where product.prodID=subHistory.prodID and subHistory.payID=payment.payID and subHistory.userID={cid} and subHistory.prodID={prodid}
        '''
        cursor.execute(sql.format(cid=cid, prodid=prodid))
        data = cursor.fetchall()  
        cursor.execute('SELECT productName from product where prodID={prodid}'.format(prodid=prodid))
        prodName = cursor.fetchall() 
        cursor.execute('SELECT name from userInfo where userID={cid}'.format(cid=cid))
        cusName = cursor.fetchall() 
        user = getUserInfo(id)
        return render_template('staffDashboardDetails.html', data=data, user=user, prodName=prodName, cusName=cusName)
    else: 
        return render_template('404.html'), 404

@app.route("/staff/<int:id>/buy", methods=['GET', 'POST'])
def staffExtend(id):
    print('Request for staff extend received')
    if checkLoginStatus(id) == True:
        if request.method == 'POST':
            userID = request.form['userID']
            prodID = request.form['prodID']
            days = request.form['days']
            sql = 'SELECT * FROM subscription WHERE userID={id} AND prodID={prodID}'
            cursor.execute(sql.format(prodID=prodID, id=userID))
            current = cursor.fetchall()
            for x in current:
                if x['subStatus'] == 'Expired':
                    sql = 'UPDATE subscription SET subStart=curdate(), subEnd=DATE_ADD(curdate(), INTERVAL {days} DAY), subStatus="Ongoing" WHERE subID={subID}'
                    cursor.execute(sql.format(days=days , subID=x['subID']))
                    connection.commit()
                elif x['subStatus'] == 'Ongoing':
                    sql = 'UPDATE subscription SET subEnd=DATE_ADD("{subEnd}", INTERVAL {days} DAY), subStatus="Ongoing" WHERE subID={subID}'
                    cursor.execute(sql.format(days=days , subID=x['subID'], subEnd=x['subEnd']))
                    connection.commit()
        sql = '''    
        select *, DATEDIFF(subscription.subEnd, CURDATE()) as remaining 
        from product, subscription, userInfo
        where product.prodID=subscription.prodID and userInfo.userID=subscription.userID and product.deletedInd='N' and subscription.subEnd>=CURDATE()
        '''
        cursor.execute(sql)
        data = cursor.fetchall()
        product = getProduct()
        user = getUserInfo(id)
        return render_template('staffDashboard.html', product=product, data=data, user=user)

@app.route("/staff/<int:id>/updateProduct", methods=['GET'])
def staffUpdateProduct(id):
    print('Request for update product page received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        product = getProduct()
        return render_template('staffUpdateProduct.html', user=user, product=product, status=None)
    else: 
        return render_template('404.html'), 404
    
@app.route("/staff/<int:id>/updateProduct/submit", methods=['POST', 'GET'])
def staffUpdateProductSubmit(id):
    print('Request for update product received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        if request.method == 'POST':
            prodID = request.form['prodID']
            productName = request.form['productName']
            prodDescr = request.form['prodDescr']
            prodLink = request.form['prodLink']
            prodPrice = request.form['prodPrice']  
            cursor.execute('SELECT * FROM product WHERE prodID != {prodID}'.format(prodID=prodID))
            existingName = cursor.fetchall()
            for e in existingName:
                if e['productName'] == productName:
                    product = getProduct()
                    return render_template('staffUpdateProduct.html', user=user, product=product, status='namedup')
            sql = 'UPDATE product SET productName="{productName}", prodDescr="{prodDescr}", prodLink="{prodLink}",prodPrice="{prodPrice}" WHERE prodID={prodID}'
            cursor.execute(sql.format(prodID=prodID, productName=productName, prodDescr=prodDescr, prodLink=prodLink, prodPrice=prodPrice))
            connection.commit()
        product = getProduct()
        return render_template('staffUpdateProduct.html', user=user, product=product, status='success')
    else: 
        return render_template('404.html'), 404

@app.route("/staff/<int:id>/updateProduct/submitpic", methods=['POST', 'GET'])
def staffUpdateProductSubmitPic(id):
    print('Request for update picture received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        if request.method == 'POST':
            prodID = request.form['prodID']
            prodImg = request.files['prodImg']
            for file in request.files.getlist("prodImg"):
                try:
                    container_client_product.upload_blob(file.filename, file) # upload the file to the container using the filename as the blob name
                    filenames += file.filename + "<br /> "
                except Exception as e:
                    print(e)
                    print("Ignoring duplicate filenames") # ignore duplicate filenames  
            sql = 'UPDATE product SET prodImg="{prodImg}" WHERE prodID={prodID}'
            cursor.execute(sql.format(prodID=prodID, prodImg=prodImg.filename))
            connection.commit()
        product = getProduct()
        return render_template('staffUpdateProduct.html', user=user, product=product, status='success')
    else: 
        return render_template('404.html'), 404

@app.route("/staff/<int:id>/updateProduct/delete", methods=['POST', 'GET'])
def staffUpdateProductDelete(id):
    print('Request for delete product received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        if request.method == 'POST':
            prodID = request.form['prodID']
            sql = 'SELECT prodPrice FROM product WHERE prodID={prodID}'
            cursor.execute(sql.format(prodID=prodID))
            prodPrice = cursor.fetchall()
            for e in prodPrice:
                price = e['prodPrice']
            sql = 'SELECT *, DATEDIFF(subscription.subEnd, CURDATE()) as remaining FROM subscription WHERE prodID={prodID}'
            cursor.execute(sql.format(prodID=prodID))
            data = cursor.fetchall()
            for e in data:
                if e['remaining'] > 0:
                    sql = 'UPDATE userInfo SET money=(money+{refund}) WHERE userID={userID}'
                    cursor.execute(sql.format(userID=e["userID"], refund=(e["remaining"]*price)))
                    connection.commit()
            sql = 'UPDATE product SET deletedInd="Y" WHERE prodID={prodID}'
            cursor.execute(sql.format(prodID=prodID))
            sql = 'UPDATE subhistory SET subHstatus="Refunded" WHERE prodID={prodID}'
            cursor.execute(sql.format(prodID=prodID))
            sql = 'UPDATE subscription SET subStatus="Expired", subEnd=curdate() WHERE prodID={prodID}'
            cursor.execute(sql.format(prodID=prodID))
            connection.commit()
        product = getProduct()
        return render_template('staffUpdateProduct.html', user=user, product=product, status='success')
    else: 
        return render_template('404.html'), 404

@app.route("/staff/<int:id>/addProduct", methods=['GET'])
def staffAddProduct(id):
    print('Request for add product page received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        return render_template('staffAddProduct.html', user=user)
    else: 
        return render_template('404.html'), 404

@app.route("/staff/<int:id>/addProduct/submit", methods=['POST', 'GET'])
def staffAddProductSubmit(id):
    print('Request for add product received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        if request.method == 'POST':
            productName = request.form['productName']
            prodDescr = request.form['prodDescr']
            prodLink = request.form['prodLink']
            prodPrice = request.form['prodPrice']  
            prodImg = request.files['prodImg']
            cursor.execute('SELECT productName FROM product')
            existingName = cursor.fetchall()
            for e in existingName:
                if e['productName'] == productName:
                    return render_template('staffAddProduct.html', user=user, status='namedup')
            for file in request.files.getlist("prodImg"):
                try:
                    container_client_product.upload_blob(file.filename, file) # upload the file to the container using the filename as the blob name
                    filenames += file.filename + "<br /> "
                except Exception as e:
                    print(e)
                    print("Ignoring duplicate filenames") # ignore duplicate filenames   
            sql = 'INSERT INTO product(productName,prodDescr, prodLink, prodPrice, prodImg) VALUES ("{productName}", "{prodDescr}", "{prodLink}", {prodPrice}, "{prodImg}")'
            cursor.execute(sql.format(productName=productName, prodDescr=prodDescr, prodLink=prodLink, prodPrice=prodPrice, prodImg=prodImg.filename))
            connection.commit()
        product = getProduct()
        return render_template('staffAddProduct.html', user=user, status='success')
    else: 
        return render_template('404.html'), 404

@app.route("/staff/<int:id>/history", methods=['GET'])
def staffHistory(id):
    print('Request for staff history received')
    if checkLoginStatus(id) == True: 
        sql = '''    
        select * from subHistory, product, payment
        where product.prodID=subHistory.prodID and subHistory.payID=payment.payID
        '''
        cursor.execute(sql)
        data = cursor.fetchall()   
        user = getUserInfo(id)
        return render_template('staffHistory.html', data=data, user=user)
    else: 
        return render_template('404.html'), 404
    
@app.route("/staff/<int:id>/approverCorner", methods=['GET'])
def staffApproverCorner(id):
    print('Request for approver corner page received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        cursor.execute('select * from payment where payDoc is not null and payStatus != "Approved"')
        data = cursor.fetchall() 
        return render_template('staffApproverCorner.html', user=user, data=data)
    else: 
        return render_template('404.html'), 404

@app.route("/staff/<int:id>/approverCorner/submit", methods=['POST', 'GET'])
def staffApproverCornerSubmit(id):
    print('Request for approve items received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        if request.method == 'POST':
            payID = request.form['payID']
            status = request.form['status']
            sql = 'UPDATE payment SET payStatus="{status}", confirmBy={id}, confirmDate=curdate() WHERE payID={payID}'
            cursor.execute(sql.format(payID=payID, status=status, id=id))
            connection.commit()
            sql = 'UPDATE subHistory SET subHstatus="{status}" WHERE payID={payID}'
            cursor.execute(sql.format(payID=payID, status=status))
            connection.commit()
            sql = 'SELECT * FROM subHistory WHERE payID={payID}'
            cursor.execute(sql.format(payID=payID))
            sub = cursor.fetchall()
            if status == "Approved":
                for e in sub:
                    sql = 'SELECT * FROM subscription WHERE userID={id} AND prodID={prodID}'
                    cursor.execute(sql.format(prodID=e['prodID'], id=e['userID']))
                    current = cursor.fetchall()
                    if current == ():
                        sql = 'UPDATE subHistory SET subHStart=curdate(), subHEnd=DATE_ADD(curdate(), INTERVAL subHDay DAY) WHERE subHID={subHID}'
                        cursor.execute(sql.format(subHID=e['subHID']))
                        connection.commit()
                        sql = "INSERT INTO subscription(subStart, subEnd, subStatus, userID, prodID) VALUES (curdate(), DATE_ADD(curdate(), INTERVAL {days} DAY), 'Ongoing', {id}, {prodID})"
                        cursor.execute(sql.format(days=e['subHDay'], id=e['userID'], prodID=e['prodID']))
                        connection.commit()
                    else:
                        for x in current:
                            if x['subStatus'] == 'Expired':
                                sql = 'UPDATE subHistory SET subHStart=curdate(), subHEnd=DATE_ADD(curdate(), INTERVAL subHDay DAY) WHERE subHID={subHID}'
                                cursor.execute(sql.format(subHID=e['subHID']))
                                connection.commit()
                                sql = 'UPDATE subscription SET subStart=curdate(), subEnd=DATE_ADD(curdate(), INTERVAL {days} DAY), subStatus="Ongoing" WHERE subID={subID}'
                                cursor.execute(sql.format(days=e['subHDay'] , subID=x['subID']))
                                connection.commit()
                            elif x['subStatus'] == 'Ongoing':
                                sql = 'UPDATE subHistory SET subHStart="{subEnd}", subHEnd=DATE_ADD("{subEnd}", INTERVAL {days} DAY) WHERE subHID={subHID}'
                                cursor.execute(sql.format(days=e['subHDay'], subHID=e['subHID'], subEnd=x['subEnd']))
                                connection.commit()
                                sql = 'UPDATE subscription SET subEnd=DATE_ADD("{subEnd}", INTERVAL {days} DAY), subStatus="Ongoing" WHERE subID={subID}'
                                cursor.execute(sql.format(days=e['subHDay'] , subID=x['subID'], subEnd=x['subEnd']))
                                connection.commit()
        cursor.execute('select * from payment where payDoc is not null and payStatus != "Approved"')
        data = cursor.fetchall() 
        return render_template('staffApproverCorner.html', user=user, data=data)
    else: 
        return render_template('404.html'), 404

@app.route("/staff/<int:id>/account", methods=['GET'])
def staffAccount(id):
    print('Request for account page received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)    
        cursor.execute('SELECT * FROM userInfo WHERE role="c"')
        data = cursor.fetchall()
        return render_template('staffAccount.html', user=user, data=data)
    else: 
        return render_template('404.html'), 404

@app.route("/staff/<int:id>/addAccount", methods=['POST', 'GET'])
def staffAddAccount(id):
    print('Request for add account page received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        if request.method == 'POST':
            accType = request.form['accType']
            name = request.form['name']
            phoneNo = request.form['phoneNo']
            email = request.form['email']
            userName = request.form['userName']
            password = request.form['password']
            confirmPassword = request.form['confirmPassword']
            if confirmPassword == password:
                cursor.execute('SELECT * FROM userInfo')
                result = cursor.fetchall()
                for i in result:
                    if i['userName'] == userName:
                        return render_template('staffAddAccount.html',user=user, status='usernamedup')
                    if int(i['phoneNo']) == int(phoneNo):
                        return render_template('staffAddAccount.html', user=user, status='phoneNodup')
                    if i['email'] == email:
                        return render_template('staffAddAccount.html', user=user, status='emaildup')   
                if accType == "C":             
                    insertsql='INSERT INTO userInfo(userName, password, name, phoneNo, email, role, loginStatus) VALUES ("{userName}", "{password}", "{name}", "{phoneNo}", "{email}", "C", 0)'
                    cursor.execute(insertsql.format(userName=userName, password=password, name=name, phoneNo=phoneNo, email=email))
                    connection.commit()
                elif accType == "S":             
                    insertsql='INSERT INTO userInfo(userName, password, name, phoneNo, email, role, loginStatus) VALUES ("{userName}", "{password}", "{name}", "{phoneNo}", "{email}", "S", 0)'
                    cursor.execute(insertsql.format(userName=userName, password=password, name=name, phoneNo=phoneNo, email=email))
                    connection.commit()
                sql = 'SELECT userID from userInfo WHERE userName="{userName}"'
                cursor.execute(sql.format(userName=userName))
                result = cursor.fetchall()
                for i in result: 
                    id = i['userID']
                return render_template('staffAddAccount.html', user=user, status='success')
            else:
                return render_template('staffAddAccount.html', user=user, status='invalidConfirmPassword')
        else: 
            return render_template('staffAddAccount.html', user=user, status=None)
    else: 
        return render_template('404.html'), 404

@app.route("/staff/<int:id>/inquiry", methods=['POST', 'GET'])
def staffInquiry(id):
    print('Request for inquiry page received')
    if checkLoginStatus(id) == True: 
        if request.method == 'POST':
            inquiryID = request.form['inquiryID']
            sql = 'UPDATE inquiry SET inquiryStatus="Closed", solvedBy={id} WHERE inquiryID={inquiryID}'
            cursor.execute(sql.format(inquiryID=inquiryID, id=id))
            connection.commit()        
        sql = '''   
        select * from inquiry, userInfo 
        where inquiry.userID=userInfo.userID
        order by inquiry.inquiryStatus
        '''
        cursor.execute(sql)
        data = cursor.fetchall()   
        user = getUserInfo(id)
        return render_template('staffInquiry.html', data=data, user=user)
    else: 
        return render_template('404.html'), 404
    
@app.route("/staff/<int:id>/personalInfo", methods=['POST','GET'])
def staffPersonalInfo(id):
    print('Request for personal info page received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        if request.method == 'POST':
            name = request.form['name']
            phoneNo = request.form['phoneNo']
            email = request.form['email']
            userName = request.form['userName']
            sql = 'SELECT * FROM userInfo WHERE userID!={id}'
            cursor.execute(sql.format(id=id))
            result = cursor.fetchall()
            for i in result:
                if i['userName'] == userName:
                    return render_template('staffPersonalInfo.html', user=user, status='usernamedup')
                if i['phoneNo'] == phoneNo:
                    return render_template('staffPersonalInfo.html', user=user, status='phoneNodup')
                if i['email'] == email:
                    return render_template('staffPersonalInfo.html', user=user, status='emaildup')                
            sql='UPDATE userInfo SET userName="{userName}", name="{name}", phoneNo={phoneNo}, email="{email}" WHERE userID={id}'
            cursor.execute(sql.format(userName=userName, name=name, phoneNo=phoneNo, email=email, id=id))
            connection.commit()
            user = getUserInfo(id)
            return render_template('staffPersonalInfo.html', user=user, status='success')
        else:
            return render_template('staffPersonalInfo.html', user=user, status='None')
    else: 
        return render_template('404.html'), 404
    
@app.route("/staff/<int:id>/changePassword", methods=['POST','GET'])
def staffChangePassword(id):
    print('Request for change password page received')
    if checkLoginStatus(id) == True:
        user = getUserInfo(id)
        if request.method == 'POST':
            password = request.form['password']
            confirmPassword = request.form['confirmPassword']
            if password == confirmPassword:
                sql='UPDATE userInfo SET password="{password}" WHERE userID={id}'
                cursor.execute(sql.format(password=password, id=id))
                connection.commit()
                return render_template('staffChangePassword.html', user=user, status='success')   
            else: 
                return render_template('staffChangePassword.html', user=user, status='fail')         
        else:
            return render_template('staffChangePassword.html', user=user, status='None')
    else: 
        return render_template('404.html'), 404

@app.errorhandler(404)
def page_not_found(e):
    print('Request for 404 page received')
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    print('Request for 505 page received')
    return render_template('500.html'), 500

if __name__=='__main__':
    app.run(debug=True)
