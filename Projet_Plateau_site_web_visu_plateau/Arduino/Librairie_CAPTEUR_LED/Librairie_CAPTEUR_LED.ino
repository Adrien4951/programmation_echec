#include <Wire.h>
#include <Adafruit_NeoPixel.h>
#include "A31301.h"
#include "config.h"

#define LED_PIN     2   // Broche GPIO de l'ESP32 --> A4 et Arduino UNO --> 2
#define LED_COUNT    64   // Nombre de leds par module





//-----------variables globales------------
uint8_t ADDR_AFFICHAGE[16]={0x04,0x03,0x02,0x63,
                            0x05,0x06,0x07,0x08,
                            0x0C,0x0B,0x0A,0x09,
                            0x0D,0x0E,0x0F,0x10};
/*uint8_t tab_LED[16]={4,3,2,1,
                     5,6,7,8,
                     12,11,10,9,
                     13,14,15,16};


                     /*uint8_t A31301_ADDR[16]={0x04,0x03,0x02,0x02,0x05,0x06,0x07,0x08,0x0C,0x0B,0x0A,0x09,0x0D,0x0E,0x0F,0x0F}; // 4 : 0x63 et 16 : 0x10
int16_t SEUIL_CAPT[16]={-10,20,38,29,-20,-35,2,-4,-4,7,3,-16,9,-10,-7,-10};
uint8_t tab_LED[16]={4,3,2,1,
                     5,6,7,8,
                     12,11,10,9,
                     13,14,15,16};*/

//int16_t SEUIL_CAPT_NOIR[16]={0x04,0x03,0x02,0x63,0x05,0x06,0x07,0x08,0x0C,0x0B,0x0A,0x09,0x0D,0x0E,0x0F,0x10};
uint8_t msg =' ';
uint8_t a=0;

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);





// Fonction pour remplir les pixels un par un
void colorWipe(uint32_t color, int wait) {
  for(int i=0; i<strip.numPixels(); i++) {
    strip.setPixelColor(i, color);
    strip.show();
    delay(wait);
  }
}

void setuLED(uint8_t addr_led, uint32_t color) {
  strip.setPixelColor(tab_LED[addr_led]-1, color);
  strip.show();
  //delay(10);
}



void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  while (!Serial){
    Serial.println("pas de serial");
  }
  Serial.println("Setup");
  // I²C initialization
  Wire.begin();  

  strip.begin();           // Initialise la communication avec les LEDs
  strip.show();            // Éteint tout au démarrage
  strip.setBrightness(255); // Luminosité à environ 20% pour 50 (pour économiser le courant via USB)
}

void loop() {


if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "test_I2C") {
      // On envoie un header spécial pour le scan I2C
      Serial.write(0xCC); 
      Serial.write(0xDD);

      for (byte address = 1; address < 127; address++) {
        Wire.beginTransmission(address);
        byte error = Wire.endTransmission();

        if (error == 0) {
          Serial.write(address); // On envoie l'adresse trouvée
        }
      }
      Serial.write(0xFF); // Fin du scan
      delay(500);
      return;
    }
  }





  uint8_t n=4;
  static uint8_t umit=0;
  bool pion=false;

  //uint8_t tabX[n];
  //uint8_t tabY[n];
  int16_t tabZ[n];

  //uint16_t sommeX=0;
  //uint16_t sommeY=0;  
  int16_t sommeZ=0;

  //float resultX=0;
  //float resultY=0;  
  float resultZ=0;

  for(uint8_t i=0;i<n;i++){
    //tabX[i]=getX(0);
    //tabY[i]=getY(0);
    tabZ[i]=getZ(a);

    //sommeX+=tabX[i];
    //sommeY+=tabY[i];
    sommeZ+=tabZ[i];
  }
  
  //resultX=sommeX/n;
  //resultY=sommeY/n;
  resultZ=sommeZ/n;

  // Send data on serial
  //Serial.println(resultX);
  //Serial.print(",");
  //Serial.print(resultY);
  //Serial.print(",");
  
  //---------Affichage détection des pions-------- 
    //Serial.println("-----------------");
  Serial.write(0xAA); 
  Serial.write(0xBB);
  uint8_t checksum = 0;
  int16_t ValeurZ=0;
  //Etat = 0 (Noir), 1 (Blanc), 2 (Rien)
  uint8_t etat = 0;

    for(uint8_t k=0;k<8;k++){
      for(uint8_t j=0;j<8;j++){  
        if(presence_pion_blanc((j+(k*8)))){
          //Serial.print("| B ");
          setuLED((j+(k*8)),strip.Color(255, 255, 255));
          etat = 1;
        }
        else if(presence_pion_noir((j+(k*8)))){
          //Serial.print("| N ");
          setuLED((j+(k*8)),strip.Color(255, 255, 0));
          etat = 0;
        }
        else{
          //Serial.print("| - ");
          setuLED((j+(k*8)),strip.Color(0, 0, 0));
          etat = 2;
        }
        ValeurZ = getZ((j+(k*8)));
        uint8_t highZ = (ValeurZ >> 8) & 0xFF;
        uint8_t lowZ = ValeurZ & 0xFF;
        Serial.write((j+(k*8)));
        Serial.write(highZ);  // Valeur Z (partie haute)
        Serial.write(lowZ);   // Valeur Z (partie basse)
        Serial.write(etat);   // État du pion
        checksum += ((j+(k*8)) + highZ + lowZ + etat);
      }
      //Serial.print("|\n");
      //Serial.println("-----------------");  
    }
    Serial.write(checksum);

    //Serial.print("\n\n\n");
  

  /*//---------Affichage détection d'un pion-------- 
    if(presence_pion_blanc(a)){
      //Serial.print("| Pion blanc");
      Serial.print("\t adress capt : ");
      Serial.print(A31301_ADDR[a]);
      Serial.print("\t num led : ");
      Serial.print(tab_LED[a]-1);
      setuLED(a,strip.Color(255, 255, 255));
    }
    else if(presence_pion_noir(a)){
      //Serial.print("| Pion noir ");
      Serial.print("\t adress capt : ");
      Serial.print(A31301_ADDR[a]);
      Serial.print("\t num led : ");
      Serial.print(tab_LED[a]-1);
      setuLED(a,strip.Color(255, 0, 0));
    }
    else{
      //Serial.print("|Pas de pion");
      Serial.print("\t adress capt : ");
      Serial.print(A31301_ADDR[a]);
      Serial.print("\t num led : ");
      Serial.print(tab_LED[a]-1);
      setuLED(a,strip.Color(0, 0, 0));
    }
    if (Serial.available()) {
      msg = Serial.read();
    }
    if(msg=='+'){
      a++;
    }
    else if(msg=='-'){
      a--;
    }
    Serial.print("\t a : ");
    Serial.println(a);
  */

  /*//---------Affichage de la valeur de l'axe Z du magnétomètre-------- 

    //Serial.print("\ta = ");
    //Serial.print(a);
    //Serial.print("\tValeur du champ magnetique : ");
    Serial.println(getZ(a)); 
    
    if (Serial.available()) {
      msg = Serial.read();
    }
    if(msg=='+'){
      a++;
    }
    else if(msg=='-'){
      a--;
    }
  */
}