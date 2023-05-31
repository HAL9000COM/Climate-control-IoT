
//Network//
#include <WiFi.h>
#include <PubSubClient.h>


const char* ssid = "example_ssid";
const char* password = "wifi_password";
const char* mqtt_server = "example.com";
const char* access_key = "example_accesskey";
WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg = 0;
char msg[50];
int value = 0;
//Network//

//Sensors//
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_BME280.h>
#include <OneWire.h>
#include <DallasTemperature.h>

Adafruit_BME280 bme; // use I2C interface, needs to change the default address in the library

#define ONE_WIRE_BUS 15      //change from 2 to 15 since pin2 is led on esp32 
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);
DeviceAddress DSThermometer;
//Sensors//

//Data//
#include <ArduinoJson.h>
double globe_temp;
double air_vel;
double water_temp;
double air_temp;
double air_temp_offset = -0.66;
double RH;
double pressure;
//Data//

//Calc Func//
double saturated_air_velpor_pressure_hpa(double db_temp);
double utci(double air_temp, double globe_temp, double RH, double air_vel);
double mean_radiant_temperature(double globe_temp, double air_temp, double air_vel);
//Calc Func//

//Sensor Func//
double anemometer();
double DS_temp();
//Sensor Func//

//Ctrl Func//
void fan_con(int fan_speed);
int fan_log = 0;
int fan_speed = 0;
#define FAN 13
#define PUMP 32
boolean roof;
#define MIST 33
boolean mist_ctrl = 0;
boolean mist_log = 0;
boolean mode_log=0;
void mist_con(bool mist_ctrl);
double fan_po[4]={0,3,4,5};
//Ctrl Func//

//MQTT Func//
void setup_wifi();
void callback(char* topic, byte* message, unsigned int length);
void reconnect();
//MQTT Func//

void setup() {
  Serial.begin(115200);
  Serial2.begin(4800);//anemometer
  bme.begin();
  sensors.begin();
  sensors.getAddress(DSThermometer, 0);
  sensors.setResolution(DSThermometer, 12);
  pinMode(FAN, OUTPUT);
  pinMode(MIST, OUTPUT);
  pinMode(PUMP, OUTPUT);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  long now = millis();
  if (now - lastMsg > 5000) {
    lastMsg = now;
    double globe_buff = DS_temp();
    if (globe_buff > -127) { //handle error readings
      globe_temp = globe_buff;
    }

    air_vel = anemometer();
    air_temp = bme.readTemperature();
    air_temp = air_temp + air_temp_offset;
    RH = bme.readHumidity();
    pressure = bme.readPressure();


    DynamicJsonDocument sensor_data(1024);
    sensor_data["globe_temp"] = globe_temp;
    sensor_data["air_vel"] = air_vel;
    sensor_data["air_temp"] = air_temp;
    sensor_data["RH"] = RH;
    sensor_data["pressure"] = pressure;
    sensor_data["UTCI"] = utci(air_temp, globe_temp, RH, air_vel);
    sensor_data["fan"] = fan_log;
    sensor_data["roof"] = roof;
    sensor_data["mist"] = mist_log;
    sensor_data["mode"] = mode_log;
    sensor_data["power"] = fan_po[fan_log]+4*mist_log+6*roof+2;
    
    String msg_string;
    serializeJson(sensor_data, msg_string);
    Serial.println(msg_string);
    const char* msg_c = msg_string.c_str();

    if (!(air_temp > -273 & air_temp<100 & RH>0 & pressure > 0)) {
      bme.begin();
      Serial.println("reset");
    } else {
      client.publish("v1/devices/me/telemetry", msg_c );
    }
    //     Serial.print(air_temp);
    //    Serial.print(msg_c);
    //     Serial.println();
    //    client.publish(

    //  Serial.print("UTCI:");
    //  Serial.print(utci(air_temp, globe_temp, RH, air_vel));
    //  Serial.print("air_temp:");
    //Serial.print(air_temp);
    //  Serial.print("globe_temp:");
    //  Serial.print(globe_temp);
    //  Serial.print("RH:");
    //  Serial.print(RH);
    //  Serial.print("Wind_speed:");
    //  Serial.print(air_vel);
    //      Serial.print("\n");
  }
  //  Serial.print(fan_speed);
  //  Serial.print(fan_log);
  //  Serial.println();
}

void setup_wifi() {
  delay(10);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* message, unsigned int length) {
  //  Serial.print("Message arrived on topic: ");
  //  Serial.print(topic);
  //  Serial.print(". Message: ");
  String messageTemp;

  for (int i = 0; i < length; i++) {
    //    Serial.print((char)message[i]);
    messageTemp += (char)message[i];
  }
  //  Serial.println();

  DynamicJsonDocument ctrl_data(1024);
  deserializeJson(ctrl_data, messageTemp);

  char requestId[20];
  char response[50];
  char response_msg[10];

  //response with correct format
  strncpy(requestId, topic + 26, strlen(topic) - 26);
  requestId[strlen(topic) - 26] = '\0';
  strcpy(response, "v1/devices/me/rpc/response/");
  strcat(response, requestId);

  //handle method
  if (ctrl_data["method"] == "getFan") {
    dtostrf(fan_log, 1, 2, response_msg);
  }

  if (ctrl_data["method"] == "setFan") {
    fan_speed = ctrl_data["params"];
    fan_con(fan_speed);
    dtostrf(fan_log, 1, 2, response_msg);
  }

  if (ctrl_data["method"] == "getRoof") {
    dtostrf(roof, 1, 2, response_msg);
  }
  if (ctrl_data["method"] == "setRoof") {
    roof = ctrl_data["params"];
    digitalWrite(PUMP, roof);
    dtostrf(roof, 1, 2, response_msg);
  }
  if (ctrl_data["method"] == "getMist") {
    dtostrf(mist_log, 1, 2, response_msg);
  }
  if (ctrl_data["method"] == "setMist") {
    mist_ctrl = ctrl_data["params"];
    mist_con(mist_ctrl);
    dtostrf(mist_log, 1, 2, response_msg);
  }
  if (ctrl_data["method"] == "getMode") {
    dtostrf(mode_log, 1, 2, response_msg);
  }
  if (ctrl_data["method"] == "setMode") {
    mode_log = ctrl_data["params"];
    dtostrf(mode_log, 1, 2, response_msg);
  }

  client.publish(response, response_msg);
  Serial.println(response_msg);
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    if (client.connect("ESP32Client", access_key, "")) { //clientID,Username,Passwd
      Serial.println("connected");
      // Subscribe
      client.subscribe("v1/devices/me/rpc/request/+");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

double DS_temp()
{
  sensors.requestTemperatures(); // Send the command to get temperatures
  double temp = sensors.getTempCByIndex(0);
  return temp;
}

double anemometer()
{
  byte anemometer_ask[] = {0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A};
  byte anemometer_read[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
  Serial2.write(anemometer_ask, sizeof(anemometer_ask));
  Serial2.readBytes(anemometer_read, sizeof(anemometer_read));

  Serial.printf("%02x", anemometer_read[0]);
  Serial.printf("%02x", anemometer_read[1]);
  Serial.printf("%02x", anemometer_read[2]);
  Serial.printf("%02x", anemometer_read[3]);
  Serial.printf("%02x", anemometer_read[4]);
  Serial.printf("%02x", anemometer_read[5]);
  Serial.printf("%02x\n", anemometer_read[6]);
  double data = (anemometer_read[3] * 256.0 + anemometer_read[4]) / 10.0;
  return data;
}

void fan_con(int fan_speed)//For control the battery-powered fan using "ON" switch //May need to sync the fan at the begining
{
  int  i = fan_speed - fan_log;
  if (i < 0)
    i = i + 5;
  for (i = i; i > 0; i--) {
    digitalWrite(FAN, HIGH);
    delay(100);
    digitalWrite(FAN, LOW);
    delay(100);
  }
  fan_log = fan_speed;
}

void mist_con(boolean mist_ctrl)//For control the battery-powered mist generator using "ON" switch //May need to sync the fan at the begining
{
  if (mist_ctrl == 0 && mist_log == 1) {
    digitalWrite(MIST, HIGH);
    delay(100);
    digitalWrite(MIST, LOW);
    delay(100);
    digitalWrite(MIST, HIGH);
    delay(100);
    digitalWrite(MIST, LOW);
    delay(100);
  }
  if (mist_ctrl == 1 && mist_log == 0) {
    digitalWrite(MIST, HIGH);
    delay(100);
    digitalWrite(MIST, LOW);
    delay(100);
  }
  mist_log = mist_ctrl;
}

double mean_radiant_temperature(double globe_temp, double air_temp, double air_vel)
{
  double Dg = 0.16;
  double Epsilon = 0.95;
  double Tmrt = pow((pow(globe_temp + 273.15, 4) + (1.1e8 * pow(air_vel, 0.6) * (globe_temp - air_temp)) / Epsilon * pow(Dg, 0.4)), 0.25) - 273.15;
  return Tmrt;
}

double utci(double air_temp, double globe_temp, double RH, double air_vel)
{

  double Tmrt = mean_radiant_temperature(globe_temp, air_temp, air_vel);
  //   Calculate Universal Thermal Climate Index (UTCI) using a polynomial approximation.
  // set upper and lower limits of air velocity according to Fiala model scenarios
  double vel_10m = air_vel * 1.5;
  if (vel_10m < 0.5)
    vel_10m = 0.5;
  if (vel_10m > 17)
    vel_10m = 17;

  // metrics derived from the inputs used in the polynomial equation
  double eh_pa = saturated_air_velpor_pressure_hpa(air_temp) * (RH / 100.0); // partial air_velpor pressure
  double pa_pr = eh_pa / 10.0;                                               // convert air_velpour pressure to kPa
  double d_Tmrt = Tmrt - air_temp;                                           // difference between radiant and air temperature

  double utci_approx = air_temp +
                       0.607562052 +
                       -0.0227712343 * air_temp +
                       8.06470249e-4 * air_temp * air_temp +
                       -1.54271372e-4 * air_temp * air_temp * air_temp +
                       -3.24651735e-6 * air_temp * air_temp * air_temp * air_temp +
                       7.32602852e-8 * air_temp * air_temp * air_temp * air_temp * air_temp +
                       1.35959073e-9 * air_temp * air_temp * air_temp * air_temp * air_temp * air_temp +
                       -2.25836520 * vel_10m +
                       0.0880326035 * air_temp * vel_10m +
                       0.00216844454 * air_temp * air_temp * vel_10m +
                       -1.53347087e-5 * air_temp * air_temp * air_temp * vel_10m +
                       -5.72983704e-7 * air_temp * air_temp * air_temp * air_temp * vel_10m +
                       -2.55090145e-9 * air_temp * air_temp * air_temp * air_temp * air_temp * vel_10m +
                       -0.751269505 * vel_10m * vel_10m +
                       -0.00408350271 * air_temp * vel_10m * vel_10m +
                       -5.21670675e-5 * air_temp * air_temp * vel_10m * vel_10m +
                       1.94544667e-6 * air_temp * air_temp * air_temp * vel_10m * vel_10m +
                       1.14099531e-8 * air_temp * air_temp * air_temp * air_temp * vel_10m * vel_10m +
                       0.158137256 * vel_10m * vel_10m * vel_10m +
                       -6.57263143e-5 * air_temp * vel_10m * vel_10m * vel_10m +
                       2.22697524e-7 * air_temp * air_temp * vel_10m * vel_10m * vel_10m +
                       -4.16117031e-8 * air_temp * air_temp * air_temp * vel_10m * vel_10m * vel_10m +
                       -0.0127762753 * vel_10m * vel_10m * vel_10m * vel_10m +
                       9.66891875e-6 * air_temp * vel_10m * vel_10m * vel_10m * vel_10m +
                       2.52785852e-9 * air_temp * air_temp * vel_10m * vel_10m * vel_10m * vel_10m +
                       4.56306672e-4 * vel_10m * vel_10m * vel_10m * vel_10m * vel_10m +
                       -1.74202546e-7 * air_temp * vel_10m * vel_10m * vel_10m * vel_10m * vel_10m +
                       -5.91491269e-6 * vel_10m * vel_10m * vel_10m * vel_10m * vel_10m * vel_10m +
                       0.398374029 * d_Tmrt +
                       1.83945314e-4 * air_temp * d_Tmrt +
                       -1.73754510e-4 * air_temp * air_temp * d_Tmrt +
                       -7.60781159e-7 * air_temp * air_temp * air_temp * d_Tmrt +
                       3.77830287e-8 * air_temp * air_temp * air_temp * air_temp * d_Tmrt +
                       5.43079673e-10 * air_temp * air_temp * air_temp * air_temp * air_temp * d_Tmrt +
                       -0.0200518269 * vel_10m * d_Tmrt +
                       8.92859837e-4 * air_temp * vel_10m * d_Tmrt +
                       3.45433048e-6 * air_temp * air_temp * vel_10m * d_Tmrt +
                       -3.77925774e-7 * air_temp * air_temp * air_temp * vel_10m * d_Tmrt +
                       -1.69699377e-9 * air_temp * air_temp * air_temp * air_temp * vel_10m * d_Tmrt +
                       1.69992415e-4 * vel_10m * vel_10m * d_Tmrt +
                       -4.99204314e-5 * air_temp * vel_10m * vel_10m * d_Tmrt +
                       2.47417178e-7 * air_temp * air_temp * vel_10m * vel_10m * d_Tmrt +
                       1.07596466e-8 * air_temp * air_temp * air_temp * vel_10m * vel_10m * d_Tmrt +
                       8.49242932e-5 * vel_10m * vel_10m * vel_10m * d_Tmrt +
                       1.35191328e-6 * air_temp * vel_10m * vel_10m * vel_10m * d_Tmrt +
                       -6.21531254e-9 * air_temp * air_temp * vel_10m * vel_10m * vel_10m * d_Tmrt +
                       -4.99410301e-6 * vel_10m * vel_10m * vel_10m * vel_10m * d_Tmrt +
                       -1.89489258e-8 * air_temp * vel_10m * vel_10m * vel_10m * vel_10m * d_Tmrt +
                       8.15300114e-8 * vel_10m * vel_10m * vel_10m * vel_10m * vel_10m * d_Tmrt +
                       7.55043090e-4 * d_Tmrt * d_Tmrt +
                       -5.65095215e-5 * air_temp * d_Tmrt * d_Tmrt +
                       -4.52166564e-7 * air_temp * air_temp * d_Tmrt * d_Tmrt +
                       2.46688878e-8 * air_temp * air_temp * air_temp * d_Tmrt * d_Tmrt +
                       2.42674348e-10 * air_temp * air_temp * air_temp * air_temp * d_Tmrt * d_Tmrt +
                       1.54547250e-4 * vel_10m * d_Tmrt * d_Tmrt +
                       5.24110970e-6 * air_temp * vel_10m * d_Tmrt * d_Tmrt +
                       -8.75874982e-8 * air_temp * air_temp * vel_10m * d_Tmrt * d_Tmrt +
                       -1.50743064e-9 * air_temp * air_temp * air_temp * vel_10m * d_Tmrt * d_Tmrt +
                       -1.56236307e-5 * vel_10m * vel_10m * d_Tmrt * d_Tmrt +
                       -1.33895614e-7 * air_temp * vel_10m * vel_10m * d_Tmrt * d_Tmrt +
                       2.49709824e-9 * air_temp * air_temp * vel_10m * vel_10m * d_Tmrt * d_Tmrt +
                       6.51711721e-7 * vel_10m * vel_10m * vel_10m * d_Tmrt * d_Tmrt +
                       1.94960053e-9 * air_temp * vel_10m * vel_10m * vel_10m * d_Tmrt * d_Tmrt +
                       -1.00361113e-8 * vel_10m * vel_10m * vel_10m * vel_10m * d_Tmrt * d_Tmrt +
                       -1.21206673e-5 * d_Tmrt * d_Tmrt * d_Tmrt +
                       -2.18203660e-7 * air_temp * d_Tmrt * d_Tmrt * d_Tmrt +
                       7.51269482e-9 * air_temp * air_temp * d_Tmrt * d_Tmrt * d_Tmrt +
                       9.79063848e-11 * air_temp * air_temp * air_temp * d_Tmrt * d_Tmrt * d_Tmrt +
                       1.25006734e-6 * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt +
                       -1.81584736e-9 * air_temp * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt +
                       -3.52197671e-10 * air_temp * air_temp * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt +
                       -3.36514630e-8 * vel_10m * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt +
                       1.35908359e-10 * air_temp * vel_10m * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt +
                       4.17032620e-10 * vel_10m * vel_10m * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt +
                       -1.30369025e-9 * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt +
                       4.13908461e-10 * air_temp * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt +
                       9.22652254e-12 * air_temp * air_temp * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt +
                       -5.08220384e-9 * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt +
                       -2.24730961e-11 * air_temp * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt +
                       1.17139133e-10 * vel_10m * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt +
                       6.62154879e-10 * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt +
                       4.03863260e-13 * air_temp * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt +
                       1.95087203e-12 * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt +
                       -4.73602469e-12 * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt +
                       5.12733497 * pa_pr +
                       -0.312788561 * air_temp * pa_pr +
                       -0.0196701861 * air_temp * air_temp * pa_pr +
                       9.99690870e-4 * air_temp * air_temp * air_temp * pa_pr +
                       9.51738512e-6 * air_temp * air_temp * air_temp * air_temp * pa_pr +
                       -4.66426341e-7 * air_temp * air_temp * air_temp * air_temp * air_temp * pa_pr +
                       0.548050612 * vel_10m * pa_pr +
                       -0.00330552823 * air_temp * vel_10m * pa_pr +
                       -0.00164119440 * air_temp * air_temp * vel_10m * pa_pr +
                       -5.16670694e-6 * air_temp * air_temp * air_temp * vel_10m * pa_pr +
                       9.52692432e-7 * air_temp * air_temp * air_temp * air_temp * vel_10m * pa_pr +
                       -0.0429223622 * vel_10m * vel_10m * pa_pr +
                       0.00500845667 * air_temp * vel_10m * vel_10m * pa_pr +
                       1.00601257e-6 * air_temp * air_temp * vel_10m * vel_10m * pa_pr +
                       -1.81748644e-6 * air_temp * air_temp * air_temp * vel_10m * vel_10m * pa_pr +
                       -1.25813502e-3 * vel_10m * vel_10m * vel_10m * pa_pr +
                       -1.79330391e-4 * air_temp * vel_10m * vel_10m * vel_10m * pa_pr +
                       2.34994441e-6 * air_temp * air_temp * vel_10m * vel_10m * vel_10m * pa_pr +
                       1.29735808e-4 * vel_10m * vel_10m * vel_10m * vel_10m * pa_pr +
                       1.29064870e-6 * air_temp * vel_10m * vel_10m * vel_10m * vel_10m * pa_pr +
                       -2.28558686e-6 * vel_10m * vel_10m * vel_10m * vel_10m * vel_10m * pa_pr +
                       -0.0369476348 * d_Tmrt * pa_pr +
                       0.00162325322 * air_temp * d_Tmrt * pa_pr +
                       -3.14279680e-5 * air_temp * air_temp * d_Tmrt * pa_pr +
                       2.59835559e-6 * air_temp * air_temp * air_temp * d_Tmrt * pa_pr +
                       -4.77136523e-8 * air_temp * air_temp * air_temp * air_temp * d_Tmrt * pa_pr +
                       8.64203390e-3 * vel_10m * d_Tmrt * pa_pr +
                       -6.87405181e-4 * air_temp * vel_10m * d_Tmrt * pa_pr +
                       -9.13863872e-6 * air_temp * air_temp * vel_10m * d_Tmrt * pa_pr +
                       5.15916806e-7 * air_temp * air_temp * air_temp * vel_10m * d_Tmrt * pa_pr +
                       -3.59217476e-5 * vel_10m * vel_10m * d_Tmrt * pa_pr +
                       3.28696511e-5 * air_temp * vel_10m * vel_10m * d_Tmrt * pa_pr +
                       -7.10542454e-7 * air_temp * air_temp * vel_10m * vel_10m * d_Tmrt * pa_pr +
                       -1.24382300e-5 * vel_10m * vel_10m * vel_10m * d_Tmrt * pa_pr +
                       -7.38584400e-9 * air_temp * vel_10m * vel_10m * vel_10m * d_Tmrt * pa_pr +
                       2.20609296e-7 * vel_10m * vel_10m * vel_10m * vel_10m * d_Tmrt * pa_pr +
                       -7.32469180e-4 * d_Tmrt * d_Tmrt * pa_pr +
                       -1.87381964e-5 * air_temp * d_Tmrt * d_Tmrt * pa_pr +
                       4.80925239e-6 * air_temp * air_temp * d_Tmrt * d_Tmrt * pa_pr +
                       -8.75492040e-8 * air_temp * air_temp * air_temp * d_Tmrt * d_Tmrt * pa_pr +
                       2.77862930e-5 * vel_10m * d_Tmrt * d_Tmrt * pa_pr +
                       -5.06004592e-6 * air_temp * vel_10m * d_Tmrt * d_Tmrt * pa_pr +
                       1.14325367e-7 * air_temp * air_temp * vel_10m * d_Tmrt * d_Tmrt * pa_pr +
                       2.53016723e-6 * vel_10m * vel_10m * d_Tmrt * d_Tmrt * pa_pr +
                       -1.72857035e-8 * air_temp * vel_10m * vel_10m * d_Tmrt * d_Tmrt * pa_pr +
                       -3.95079398e-8 * vel_10m * vel_10m * vel_10m * d_Tmrt * d_Tmrt * pa_pr +
                       -3.59413173e-7 * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr +
                       7.04388046e-7 * air_temp * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr +
                       -1.89309167e-8 * air_temp * air_temp * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr +
                       -4.79768731e-7 * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr +
                       7.96079978e-9 * air_temp * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr +
                       1.62897058e-9 * vel_10m * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr +
                       3.94367674e-8 * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr +
                       -1.18566247e-9 * air_temp * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr +
                       3.34678041e-10 * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr +
                       -1.15606447e-10 * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr +
                       -2.80626406 * pa_pr * pa_pr +
                       0.548712484 * air_temp * pa_pr * pa_pr +
                       -0.00399428410 * air_temp * air_temp * pa_pr * pa_pr +
                       -9.54009191e-4 * air_temp * air_temp * air_temp * pa_pr * pa_pr +
                       1.93090978e-5 * air_temp * air_temp * air_temp * air_temp * pa_pr * pa_pr +
                       -0.308806365 * vel_10m * pa_pr * pa_pr +
                       0.0116952364 * air_temp * vel_10m * pa_pr * pa_pr +
                       4.95271903e-4 * air_temp * air_temp * vel_10m * pa_pr * pa_pr +
                       -1.90710882e-5 * air_temp * air_temp * air_temp * vel_10m * pa_pr * pa_pr +
                       0.00210787756 * vel_10m * vel_10m * pa_pr * pa_pr +
                       -6.98445738e-4 * air_temp * vel_10m * vel_10m * pa_pr * pa_pr +
                       2.30109073e-5 * air_temp * air_temp * vel_10m * vel_10m * pa_pr * pa_pr +
                       4.17856590e-4 * vel_10m * vel_10m * vel_10m * pa_pr * pa_pr +
                       -1.27043871e-5 * air_temp * vel_10m * vel_10m * vel_10m * pa_pr * pa_pr +
                       -3.04620472e-6 * vel_10m * vel_10m * vel_10m * vel_10m * pa_pr * pa_pr +
                       0.0514507424 * d_Tmrt * pa_pr * pa_pr +
                       -0.00432510997 * air_temp * d_Tmrt * pa_pr * pa_pr +
                       8.99281156e-5 * air_temp * air_temp * d_Tmrt * pa_pr * pa_pr +
                       -7.14663943e-7 * air_temp * air_temp * air_temp * d_Tmrt * pa_pr * pa_pr +
                       -2.66016305e-4 * vel_10m * d_Tmrt * pa_pr * pa_pr +
                       2.63789586e-4 * air_temp * vel_10m * d_Tmrt * pa_pr * pa_pr +
                       -7.01199003e-6 * air_temp * air_temp * vel_10m * d_Tmrt * pa_pr * pa_pr +
                       -1.06823306e-4 * vel_10m * vel_10m * d_Tmrt * pa_pr * pa_pr +
                       3.61341136e-6 * air_temp * vel_10m * vel_10m * d_Tmrt * pa_pr * pa_pr +
                       2.29748967e-7 * vel_10m * vel_10m * vel_10m * d_Tmrt * pa_pr * pa_pr +
                       3.04788893e-4 * d_Tmrt * d_Tmrt * pa_pr * pa_pr +
                       -6.42070836e-5 * air_temp * d_Tmrt * d_Tmrt * pa_pr * pa_pr +
                       1.16257971e-6 * air_temp * air_temp * d_Tmrt * d_Tmrt * pa_pr * pa_pr +
                       7.68023384e-6 * vel_10m * d_Tmrt * d_Tmrt * pa_pr * pa_pr +
                       -5.47446896e-7 * air_temp * vel_10m * d_Tmrt * d_Tmrt * pa_pr * pa_pr +
                       -3.59937910e-8 * vel_10m * vel_10m * d_Tmrt * d_Tmrt * pa_pr * pa_pr +
                       -4.36497725e-6 * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr * pa_pr +
                       1.68737969e-7 * air_temp * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr * pa_pr +
                       2.67489271e-8 * vel_10m * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr * pa_pr +
                       3.23926897e-9 * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr * pa_pr +
                       -0.0353874123 * pa_pr * pa_pr * pa_pr +
                       -0.221201190 * air_temp * pa_pr * pa_pr * pa_pr +
                       0.0155126038 * air_temp * air_temp * pa_pr * pa_pr * pa_pr +
                       -2.63917279e-4 * air_temp * air_temp * air_temp * pa_pr * pa_pr * pa_pr +
                       0.0453433455 * vel_10m * pa_pr * pa_pr * pa_pr +
                       -0.00432943862 * air_temp * vel_10m * pa_pr * pa_pr * pa_pr +
                       1.45389826e-4 * air_temp * air_temp * vel_10m * pa_pr * pa_pr * pa_pr +
                       2.17508610e-4 * vel_10m * vel_10m * pa_pr * pa_pr * pa_pr +
                       -6.66724702e-5 * air_temp * vel_10m * vel_10m * pa_pr * pa_pr * pa_pr +
                       3.33217140e-5 * vel_10m * vel_10m * vel_10m * pa_pr * pa_pr * pa_pr +
                       -0.00226921615 * d_Tmrt * pa_pr * pa_pr * pa_pr +
                       3.80261982e-4 * air_temp * d_Tmrt * pa_pr * pa_pr * pa_pr +
                       -5.45314314e-9 * air_temp * air_temp * d_Tmrt * pa_pr * pa_pr * pa_pr +
                       -7.96355448e-4 * vel_10m * d_Tmrt * pa_pr * pa_pr * pa_pr +
                       2.53458034e-5 * air_temp * vel_10m * d_Tmrt * pa_pr * pa_pr * pa_pr +
                       -6.31223658e-6 * vel_10m * vel_10m * d_Tmrt * pa_pr * pa_pr * pa_pr +
                       3.02122035e-4 * d_Tmrt * d_Tmrt * pa_pr * pa_pr * pa_pr +
                       -4.77403547e-6 * air_temp * d_Tmrt * d_Tmrt * pa_pr * pa_pr * pa_pr +
                       1.73825715e-6 * vel_10m * d_Tmrt * d_Tmrt * pa_pr * pa_pr * pa_pr +
                       -4.09087898e-7 * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr * pa_pr * pa_pr +
                       0.614155345 * pa_pr * pa_pr * pa_pr * pa_pr +
                       -0.0616755931 * air_temp * pa_pr * pa_pr * pa_pr * pa_pr +
                       0.00133374846 * air_temp * air_temp * pa_pr * pa_pr * pa_pr * pa_pr +
                       0.00355375387 * vel_10m * pa_pr * pa_pr * pa_pr * pa_pr +
                       -5.13027851e-4 * air_temp * vel_10m * pa_pr * pa_pr * pa_pr * pa_pr +
                       1.02449757e-4 * vel_10m * vel_10m * pa_pr * pa_pr * pa_pr * pa_pr +
                       -0.00148526421 * d_Tmrt * pa_pr * pa_pr * pa_pr * pa_pr +
                       -4.11469183e-5 * air_temp * d_Tmrt * pa_pr * pa_pr * pa_pr * pa_pr +
                       -6.80434415e-6 * vel_10m * d_Tmrt * pa_pr * pa_pr * pa_pr * pa_pr +
                       -9.77675906e-6 * d_Tmrt * d_Tmrt * pa_pr * pa_pr * pa_pr * pa_pr +
                       0.0882773108 * pa_pr * pa_pr * pa_pr * pa_pr * pa_pr +
                       -0.00301859306 * air_temp * pa_pr * pa_pr * pa_pr * pa_pr * pa_pr +
                       0.00104452989 * vel_10m * pa_pr * pa_pr * pa_pr * pa_pr * pa_pr +
                       2.47090539e-4 * d_Tmrt * pa_pr * pa_pr * pa_pr * pa_pr * pa_pr +
                       0.00148348065 * pa_pr * pa_pr * pa_pr * pa_pr * pa_pr * pa_pr;

  return utci_approx;
}

double saturated_air_velpor_pressure_hpa(double db_temp)
{
  //  Calculate saturated air_velpor pressure (hPa) at temperature (C).

  //  This equation of saturation air_velpor pressure is specific to the UTCI model.
  double g[] = { -2836.5744, -6028.076559, 19.54263612, -0.02737830188, 0.000016261698, 7.0229056e-10, -1.8680009e-13};
  double tk = db_temp + 273.15; // air temp in K;
  double es = 2.7150305 * log(tk);
  for (int i = 0; i < 7; i++)
  {
    es = es + (g[i] * pow(tk, i - 2));
  }
  es = exp(es) * 0.01;
  return es;
}
