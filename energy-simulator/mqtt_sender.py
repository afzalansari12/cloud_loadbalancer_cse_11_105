import paho.mqtt.client as mqtt
import json
import time

broker = "localhost"
topic = "senior/temp"

payload = {
    "device_id": "ESP32_001",
    "temperature": 25.4,
    "humidity": 60
}

client = mqtt.Client()

client.connect(broker, 1883)

start = time.time()

client.publish(topic, json.dumps(payload))

end = time.time()

print("time:", round((end - start) * 1000, 2), "ms")

client.disconnect()