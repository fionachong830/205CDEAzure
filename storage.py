from flask import Flask, render_template, request, redirect, url_for, flash
import os
from azure.storage.blob import BlobServiceClient

connect_str = 'DefaultEndpointsProtocol=https;AccountName=wpstorage77be0ae4f2;AccountKey=1aPUATJlKBRUg5gEAh0/DuGLtIeflB3lWZ/wlIkHqk6b5ZvAAbyxGHkY+ZXOBL6wFqiV5ZTJctHP+AStCayHqA==;EndpointSuffix=core.windows.net'
# retrieve the connection string from the environment variable
container_name = "photos" # container name in which images will be store in the storage account

blob_service_client = BlobServiceClient.from_connection_string(conn_str=connect_str) # create a blob service client to interact with the storage account
try:
    container_client = blob_service_client.get_container_client(container=container_name) # get container client to interact with the container in which images will be stored
    container_client.get_container_properties() # get properties of the container to force exception to be thrown if container does not exist
except Exception as e:
    container_client = blob_service_client.create_container(container_name) # create a container in the storage account if it does not exist

app = Flask(__name__)
@app.route("/")  
def view_photos():  
    blob_items = container_client.list_blobs() # list all the blobs in the container

    img_html = ""

    for blob in blob_items:
        print(blob)
        
        blob_client = container_client.get_blob_client(blob=blob.name) # get blob client to interact with the blob and get blob url
        print(blob_client.url)
        img_html += "<img src='{}' width='auto' height='200'/>".format(blob_client.url) # get the blob url and append it to the html
    
    # return the html with the images
    return """
        <h1>Upload new File</h1>
        <form method="post" action="/upload-photos" 
            enctype="multipart/form-data">
            <input type="file" name="photos" multiple >
            <input type="submit">
        </form>
    """ + img_html

#flask endpoint to upload a photo  
@app.route("/upload-photos", methods=["POST"])
def upload_photos():
    filenames = ""

    for file in request.files.getlist("photos"):
        try:
            container_client.upload_blob(file.filename, file) # upload the file to the container using the filename as the blob name
            filenames += file.filename + "<br /> "
        except Exception as e:
            print(e)
            print("Ignoring duplicate filenames") # ignore duplicate filenames
        
    return "<p>Uploaded: <br />{}</p>".format(filenames) 

if __name__=='__main__':
    app.run(debug=True)