#include <Arduino.h>

void setup() {
  // Utilisation de la vitesse définie dans ton programme original
  Serial.begin(115200); //[cite: 9]
  while (!Serial);
}

void loop() {
  // 1. Envoi du Header (Synchronisation)
  Serial.write(0xAA); 
  Serial.write(0xBB);

  uint8_t checksum = 0;

  for (uint8_t i = 0; i < 64; i++) {
    // Génération d'une fausse valeur Z entre -100 et 100
    int16_t fakeZ = random(-100, 100);
    
    // Détermination d'un état aléatoire : 0 (Noir), 1 (Blanc), 2 (Rien)
    // On simule un changement d'état pour tester l'affichage dynamique
    uint8_t etat = random(0, 3); 

    // Découpage de l'int16 en deux octets (MSB / LSB)
    uint8_t highZ = (fakeZ >> 8) & 0xFF;
    uint8_t lowZ = fakeZ & 0xFF;

    // Envoi des 4 octets par case
    Serial.write(i);      // Index de la case (0-63)
    Serial.write(highZ);  // Valeur Z (partie haute)
    Serial.write(lowZ);   // Valeur Z (partie basse)
    Serial.write(etat);   // État du pion

    // Calcul du checksum pour la vérification côté Python
    checksum += (i + highZ + lowZ + etat);
  }

  // Envoi du checksum final
  Serial.write(checksum);

  // Pause d'une seconde entre chaque rafraîchissement
  delay(1);
}