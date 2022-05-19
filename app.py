from flask import Flask,request,jsonify, session
from flask_mysqldb import MySQL
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
import yaml
import jwt
import datetime
from functools import wraps
import json
from geopy.distance import geodesic
import string
import random

from paystack.resource import TransactionResource



app = Flask(__name__)

bcrypt = Bcrypt(app)
#Configure Database

user_credit=0

#with open(r'db.yaml') as file:
    # The FullLoader parameter handles the conversion from YAML
    # scalar values to Python the dictionary format
#    db_info = yaml.load(file, Loader=yaml.FullLoader)
db_info= yaml.load(open('db.yaml'),Loader= yaml.FullLoader)

app.config['MYSQL_HOST']=db_info['mysql_host']
app.config['MYSQL_USER']=db_info['mysql_user']
app.config['MYSQL_PASSWORD']=db_info['mysql_password']
app.config['MYSQL_DB']=db_info['mysql_db']
app.config['SECRET_KEY']= db_info['secret_key']



mysql= MySQL(app)



def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        session.pop('user', None) 
        token= session['token']
       
        if not token:
            return jsonify ({'message': 'Token is missing!'}), 403

        try:
            
            
                
            data= jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except:
                return jsonify({'message': 'Token is invalid!'}),403

        return f(*args, **kwargs)
    return decorated    



@app.route("/registration", methods=['GET','POST'])
def get_user_details():
        
       session.pop('user', None) 
       category=  request.form['category']
       email=  request.form['email']
      
       interest=  request.form['interest']
       location=  request.form['location']
       name=  request.form['name']
       password=bcrypt.generate_password_hash(request.form['password']).decode('utf-8')         #bcrypt.generate_password_hash(request.form['password']
       phoneNumber =  request.form['phoneNumber']
        # write to the database
#check if entry exist
        #create cursor
       cursor= mysql.connection.cursor()
            
       cursor.execute("INSERT INTO user_information (email, category,interest,location,name, password,phoneNumber) VALUES (%s, %s, %s, %s, %s, %s, %s)",(email, category,interest,location,name,password,phoneNumber))
       cursor.execute("INSERT INTO user_login (email, password, category) VALUES (%s, %s, %s)",(email, password, category)) 
       mysql.connection.commit()
       #Create web token
       token =jwt.encode({'user':email, 'exp':datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},app.config['SECRET_KEY'])
       session['email'] = email 
       session['token']= token
      

       cursor.close()
        


       return jsonify({"message":"All items were entered successfully", "data":{"token": token, "category": category,"email": email, "interest":interest,"location":location,"name":name,"password":password,"phoneNumber":phoneNumber }})
        
@app.route('/allusers')
def get_all_users():
     #create cursor
       cursor= mysql.connection.cursor()
            
       cursor.execute("SELECT * FROM user_information")
       rows= cursor.fetchall()
       cursor.close()
       return   jsonify(rows)
      
       

       
@app.route('/allusers/<int:userid>')
def get_one_user(userid):
     cursor= mysql.connection.cursor()
     cursor.execute("SELECT * FROM user_information WHERE id ='"+str(userid) +"'")
     rows= cursor.fetchall()
     cursor.close()
     
     return  jsonify(rows)


@app.route('/login', methods=['GET','POST'])
def login():
    #get user input values
   # email = request.form.get('email') # or request.form['email']
#auth holds the values for authentication
    session.pop('user', None) 
    email = request.form['email']
    
    password =request.form['password']
    
    cursor= mysql.connection.cursor()
    sql="SELECT password FROM user_login WHERE email ='"+email+"'"
    cursor.execute(sql)
    password_h= cursor.fetchone()
    password_hashed=password_h[0]

    if bcrypt.check_password_hash(password_hashed, password):
         #Create web token
         token =jwt.encode({'user':email, 'exp':datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},app.config['SECRET_KEY'])
         session['email'] = email 
         session['token']= token
        
         return jsonify({"message":"logging successfully","token":token })
    else:
       return jsonify({"message":"logging Failed"})
    

@app.route('/protected')
@token_required
def Protected_page():
    return jsonify({'message': 'Only logging in can see this'})
 
@app.route('/unprotected')
def unprotected_page():
    return jsonify({'message': 'Everyone can see this'})

#----------------------------------------Mailing system------------------------------------------------------------#
@app.route('/sendMessage', methods=['POST'])
def compose_message():
    subject= request.form.get('subject')
    to= request.form.get('to')
    body= request.form.get('body')
    addressfrom= session['email']
    #create datetime
    stamp_date= datetime.datetime.utcnow()

    
    if subject and to:
        #write to database
        cursor= mysql.connection.cursor()
       
      
        cursor.execute("INSERT INTO mailing_system (subject,addressto, addressfrom, body) VALUES (%s, %s, %s, %s)",(subject, to,addressfrom,body))
        mysql.connection.commit()

    return jsonify({"message": "Message successfully sent"})    

     
     
               
    
   

@app.route('/allMessages/')
def get_all_message():

    if not session['email']:
        return "No Session"
    else:
        email= session['email']    
        cursor= mysql.connection.cursor()
            
        cursor.execute("SELECT * FROM mailing_system WHERE addressto ='"+email +"'")
        rows= cursor.fetchall()
        all_address_from=[]
        all_subject=[]
        all_message_body=[]
        all_message_time=[]
        all_message_id=[]
        data=[]
        counter=0
        for row in rows:
            all_address_from.append(row[3])
            all_subject.append(row[1])
            all_message_body.append(row[4])
            all_message_time.append(row[5])
            all_message_id.append(row[0])
            retval=[{"id": all_message_id[counter],"subject":all_subject[counter] , "body":all_message_body[counter], "time":all_message_time[counter],"id":all_message_id[counter]} ]
            data.append(retval) 
            counter= counter + 1


       
          
        cursor.close()
       
        return  jsonify(data)
      


@app.route('/showMessages/<int:msgID>')
def get_one_message(msgID):
    if not session['email']:
        return jsonify({"message": "No session found"})
    else:
        email= session['email']    
        cursor= mysql.connection.cursor()
            
        cursor.execute("SELECT * FROM mailing_system WHERE addressto ='"+email +"' AND id ='"+ str(msgID) +"'")
        rows= cursor.fetchone()
       
          
        cursor.close() 
        return jsonify({"id": rows[0], "subject": rows[1], "addressto": rows[2], "addressfrom":rows[3], "body": rows[4], "time": rows[5]})      

       
        
 #_____________________________ HELP USER FIND EACH OTHER_____________________________________________#
 # ----------------------------------------------------------------------------------------------------#
@app.route('/findCustomer/<string:keyword>')
def get_all_customers(keyword):
    #get value to help improve search
    user_location = request.get_json()
    location= user_location['longLat']
    #get location from database
    cursor= mysql.connection.cursor()
            
    cursor.execute("SELECT * FROM user_information WHERE interest ='"+keyword +"'")
    rows= cursor.fetchall()
    dLocation=""
    counter=0
    closest_place_by_id=[]
    closest_place_by_name=[]
    closest_place_by_location=[]
    closest_place_by_category=[]
    closest_place_by_email=[]
    closest_place_by_distance=[]
    data=[]
    counter=0
    for row in rows:
        
        dLocation= row[4]
        distance=round(geodesic(location,dLocation).kilometers)
        #check if location is less than 50km
        if distance < 50 :
            closest_place_by_id.append(row[0])    
            closest_place_by_name.append(row[5])
            closest_place_by_location.append(row[4])
            closest_place_by_category.append(row[2])
            closest_place_by_email.append(row[1])
            closest_place_by_distance.append(str(distance) +"km")
            
            retval=[{"id": closest_place_by_id[counter],"name":closest_place_by_name[counter] , "location":closest_place_by_location[counter], "category":closest_place_by_category[counter],"email":closest_place_by_email[counter], "distance": closest_place_by_distance[counter]} ]
            data.append(retval) 
            counter= counter + 1  
    
   
    
    return jsonify(data)


@app.route('/payment/<int:amount>/<string:status>/<string:plan>/<string:date>')
def make_payment_for_units(amount, status, plan, date):
    #check if user is logged in
     if not session['email']:
            return "No Session"
     else:
         #get amount and status and email
         email =session['email']
         STATUS = status
         Plan =plan
         
         #check if status is successful
         if STATUS != "successful" :
             # end function, transaction was not successful
               
               return jsonify({"message": "transaction failed"})    

         else:
              # get transaction information and save to the database.(i.e update user credit)
              loaded_credit=0
        
              total_amount=amount
   
              
              loaded_credit= total_amount * 2
              payment_date=date

#variables
              user_credit= loaded_credit

    #UPDATE USER CREDIT(ENTER DATABASE)
              cursor= mysql.connection.cursor()
            
              cursor.execute("INSERT INTO user_payment (email, payment_date, total_payment, credit, plan) VALUES  (%s, %s, %s, %s, %s)",(email,  payment_date, total_amount  , int(user_credit), Plan))
              mysql.connection.commit()
              return jsonify({"message": "Message successfully sent"})    






   

 






   












   










if __name__ == "__main__":
    app.run(debug =True)