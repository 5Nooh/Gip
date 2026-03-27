#include <Arduino.h>
#line 1 "C:\\Users\\49045\\OneDrive - KOBArT vzw\\ALLES\\25-26\\IC\\Gip\\GIP_arduino\\GIP_arduino.ino"
int sensorPin = A0;
int threshold = 50;

bool piekGedetecteerd = false;

unsigned long piekTijden[5] = {0,0,0,0,0};
int piekIndex = 0;
bool bufferVol = false;

unsigned long vorigePiekTijd = 0;
unsigned long vorigeSeconde = 0;

int cooldown = 400; // ms

#line 15 "C:\\Users\\49045\\OneDrive - KOBArT vzw\\ALLES\\25-26\\IC\\Gip\\GIP_arduino\\GIP_arduino.ino"
void setup();
#line 19 "C:\\Users\\49045\\OneDrive - KOBArT vzw\\ALLES\\25-26\\IC\\Gip\\GIP_arduino\\GIP_arduino.ino"
void loop();
#line 15 "C:\\Users\\49045\\OneDrive - KOBArT vzw\\ALLES\\25-26\\IC\\Gip\\GIP_arduino\\GIP_arduino.ino"
void setup() {
  Serial.begin(9600);
}

void loop() {
  unsigned long nu = millis();
  int waarde = analogRead(sensorPin);

  // --- Piekdetectie ---
  if (waarde > threshold && !piekGedetecteerd) {
    if (nu - vorigePiekTijd > (unsigned long)cooldown) {

      // Intervaltijd opslaan
      piekTijden[piekIndex] = nu - vorigePiekTijd;
      vorigePiekTijd = nu;

      piekIndex++;
      if (piekIndex >= 5) {
        piekIndex = 0;
        bufferVol = true;
      }
    }
    piekGedetecteerd = true;
  }

  if (waarde < threshold) {
    piekGedetecteerd = false;
  }

  // --- Output elke seconde (CSV) ---
  if (nu - vorigeSeconde >= 1000) {
    int bpmOut = -1;

    if (bufferVol) {
      unsigned long som = 0;
      for (int i = 0; i < 5; i++) som += piekTijden[i];
      float gemiddeldInterval = som / 5.0;
      bpmOut = (int)(60000.0 / gemiddeldInterval);
    }

    // CSV: tijd_ms,waarde,bpm  (bpm=-1 als nog niet beschikbaar)
    Serial.print(nu);
    Serial.print(",");
    Serial.print(waarde);
    Serial.print(",");
    Serial.println(bpmOut);

    vorigeSeconde = nu;
  }
}

