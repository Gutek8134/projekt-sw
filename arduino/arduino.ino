#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9
MFRC522 myRFID(SS_PIN, RST_PIN);

const int trigPin = 3;
const int echoPin = 2;
float duration, distance;

void setup() {
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  Serial.begin(9600);
  SPI.begin();        // Initiate  SPI bus
  myRFID.PCD_Init();  // Initiate MFRC522
  Serial.println("Please scan your RFID card...");
  Serial.println();
}

void loop() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  duration = pulseIn(echoPin, HIGH);
  distance = (duration * .0343) / 2;
  Serial.print("Distance: ");
  Serial.println(distance);

  // See if RFID card has been scanned
  if (myRFID.PICC_IsNewCardPresent()) {

    // an RFID card has been scanned and has UID
    if (myRFID.PICC_ReadCardSerial()) {

      //Show UID on serial monitor
      Serial.print("USER ID tag :");
      String content = "";

      for (byte i = 0; i < myRFID.uid.size; i++) {
        Serial.print(myRFID.uid.uidByte[i] < 0x10 ? " 0" : " ");
        Serial.print(myRFID.uid.uidByte[i], HEX);
        content.concat(String(myRFID.uid.uidByte[i] < 0x10 ? " 0" : " "));
        content.concat(String(myRFID.uid.uidByte[i], HEX));
      }
      Serial.println();
      delay(1000);
    }
  } else delay(100);
}
