import binascii
from flask import Flask, render_template, jsonify
import paho.mqtt.client as mqtt
import base64
import json

app = Flask(__name__)

error_messages = []

# MQTT Settings
MQTT_BROKER = "192.168.1.10"
MQTT_TOPIC_PREFIX = "Detections/"

# Dictionary to store the last witnessed images from each camera
last_images = {}

@app.route('/add_error_message/<message>')
def add_error_message(message):
    error_messages.append(message)
    return "Message added successfully"

@app.route('/get_error_messages')
def get_error_messages():
    return jsonify(error_messages)

# MQTT Setup
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe(MQTT_TOPIC_PREFIX + "#")

def on_message(client, userdata, msg):
    global error_messages
    topic_parts = msg.topic.split("/")
    if len(topic_parts) < 4:
        # Invalid topic format, skip processing
        return
    
    if not topic_parts[3] == 'IMAGE':
        return

    group = topic_parts[1]
    camera_name = topic_parts[2]
    
    if group not in last_images:
        last_images[group] = {}
    
        
    image_data = msg.payload  # Extract the base64-encoded image data    
    data = binascii.b2a_base64(msg.payload)
    # Decode the base64-encoded image data
    try:
        image_bytes = base64.b64decode(image_data)
        image_string = image_data.decode("utf-8")
        last_images[group][camera_name] = {
            "base64_image": image_string,
            "camera_name": camera_name,
            "group" : group
        }
    except Exception as e:
        print("An Error occured",e)
        error_messages.append(e)
    finally:
        error_messages.append("had an error with: " + camera_name + " on topic: " + msg.topic)
        
    

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.loop_start()

@app.route('/')
def index():
    return render_template('index.html', data=last_images)

@app.route('/get_images')
def get_images():
    images_array = []

    for group, cameras in last_images.items():
        for camera_name, image_data in cameras.items():
            images_array.append(image_data)

    # Sort images dynamically based on camera names
    try:
        sorted_images = sorted(images_array, key=lambda x: x["camera_name"])
        serializable_images = [
            {"base64_image": item["base64_image"], "camera_name": item["camera_name"], "group": item["group"]} 
            for item in sorted_images
        ]
    except Exception as e:
        print("Error sorting images:", e)
        serializable_images = []
    
    return json.dumps(serializable_images)#jsonify(serializable_images.toJJSON())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
