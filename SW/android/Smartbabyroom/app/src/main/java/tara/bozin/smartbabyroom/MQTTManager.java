package tara.bozin.smartbabyroom;

import android.util.Log;

import org.eclipse.paho.client.mqttv3.MqttCallback;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.json.JSONObject;

public class MQTTManager
{

    private static final String TAG = "MqttManager";
    private static final String BROKER_URI = "tcp://10.22.193.129:1883";
    private static final String CLIENT_ID = "android_parent_01";
    public static final String TOPIC_PARENT_CONTROL = "baby/parent/control";
    public static final String TOPIC_PARENT_STATE = "baby/parent/control/state";
    public static final String TOPIC_PARENT_NOTIFICATIONS = "baby/parent/notifications";
    public static final String TOPIC_PARENT_ALERTS = "baby/parent/alerts";
    public static final String PARENT_USN = "uuid:parent_01::urn:babymonitor:device:Parent:1";
    private static MQTTManager instance;
    private MqttClient client;
    private JSONObject lastState;
    public JSONObject getLastState()
    {
        return lastState;
    }
    private String lastNotification = "None";
    private String lastAlert = "None";
    public String getLastNotification()
    {
        return lastNotification;
    }
    public String getLastAlert()
    {
        return lastAlert;
    }
    private ParentStateListener listener;
    public interface ParentStateListener
    {
        void onParentState(JSONObject state);
    }
    private NotificationListener notificationListener;
    public interface NotificationListener
    {
        void onNotificationChanged(String notification, String alert);
    }
    public void setNotificationListener(NotificationListener listener)
    {
        this.notificationListener = listener;
    }

    private MQTTManager() {}

    public static MQTTManager getInstance()
    {
        if (instance == null)
        {
            instance = new MQTTManager();
        }
        return instance;
    }

    public void setParentStateListener(ParentStateListener listener) {
        this.listener = listener;
    }

    public void connect()
    {
        new Thread(() ->
        {
            try
            {
                if (client != null && client.isConnected())
                {
                    return;
                }

                client = new MqttClient(BROKER_URI, CLIENT_ID, null);

                client.setCallback(new MqttCallback()
                {
                    @Override
                    public void connectionLost(Throwable cause) {
                        Log.e(TAG, "Connection lost");
                    }

                    @Override
                    public void messageArrived(String topic, MqttMessage message)
                    {
                        try
                        {
                            String payload = new String(message.getPayload());
                            Log.d(TAG, "Message from " + topic + ": " + payload);

                            if (topic.equals(TOPIC_PARENT_STATE))
                            {
                                lastState = new JSONObject(payload);
                                if (listener != null)
                                {
                                    listener.onParentState(lastState);
                                }
                            }
                            if (topic.equals(TOPIC_PARENT_NOTIFICATIONS))
                            {
                                lastNotification = payload;
                                if (notificationListener != null)
                                {
                                    notificationListener.onNotificationChanged(lastNotification, lastAlert);
                                }
                            }

                            if (topic.equals(TOPIC_PARENT_ALERTS))
                            {
                                lastAlert = payload;
                                if (notificationListener != null)
                                {
                                    notificationListener.onNotificationChanged(lastNotification, lastAlert);
                                }
                            }

                        }
                        catch(Exception e)
                        {
                            Log.e(TAG, "Message error: " + e.getMessage());
                        }
                    }

                    @Override
                    public void deliveryComplete(org.eclipse.paho.client.mqttv3.IMqttDeliveryToken token) {}
                });

                MqttConnectOptions options = new MqttConnectOptions();
                options.setCleanSession(true);
                options.setAutomaticReconnect(true);

                client.connect(options);
                client.subscribe(TOPIC_PARENT_STATE);
                client.subscribe(TOPIC_PARENT_NOTIFICATIONS);
                client.subscribe(TOPIC_PARENT_ALERTS);

                Log.d(TAG, "Connected and subscribed to " + TOPIC_PARENT_STATE);

            }
            catch(Exception e)
            {
                Log.e(TAG, "MQTT connect error: " + e.getMessage());
            }
        }).start();
    }

    public void publishParentCommand(String cmd)
    {
        try
        {
            JSONObject json = new JSONObject();
            json.put("usn", PARENT_USN);
            json.put("device_id", "parent_01");
            json.put("cmd", cmd);
            json.put("timestamp", System.currentTimeMillis());
            publish(TOPIC_PARENT_CONTROL, json);

        }
        catch(Exception e)
        {
            Log.e(TAG, "Publish command error: " + e.getMessage());
        }
    }

    public void publishParentCommand(String cmd, int value)
    {
        try
        {
            JSONObject json = new JSONObject();
            json.put("usn", PARENT_USN);
            json.put("device_id", "parent_01");
            json.put("cmd", cmd);
            json.put("value", value);
            json.put("timestamp", System.currentTimeMillis());
            publish(TOPIC_PARENT_CONTROL, json);

        }
        catch(Exception e)
        {
            Log.e(TAG, "Publish command with value error: " + e.getMessage());
        }
    }
    private void publish(String topic, JSONObject json)
    {
        new Thread(() ->
        {
            try
            {
                if (client == null || !client.isConnected())
                {
                    connect();
                    Thread.sleep(700);
                }

                MqttMessage message = new MqttMessage(json.toString().getBytes());
                message.setQos(1);

                client.publish(topic, message);
                Log.d(TAG, "Published to " + topic + ": " + json);

            }
            catch(Exception e)
            {
                Log.e(TAG, "MQTT publish error: " + e.getMessage());
            }
        }).start();
    }
}