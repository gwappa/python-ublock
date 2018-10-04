/**
 * SampleTask
 * 
 * a 'mock' task for communicating with ublock.sample.
 */

#define BAUD 9600

#define CFG_CHR_PAIR  'P'
#define CFG_CHR_TEST  'T'
#define CFG_CHR_STIM  'd'
#define CFG_CHR_RESP  'f'
#define CMD_CHR_EXEC  'X'

// #define DEBUG_GENRESP
#ifdef DEBUG_GENRESP
#define LOGDEBUG(X) Serial.print(X)
#define LOGDEBUGLN(X) Serial.println(X)
#else
#define LOGDEBUG(X)
#define LOGDEBUGLN(X) 
#endif

inline bool isRecognizable(const int& ch) {
  return ((ch >= 33) && (ch <= 91)) ||
          ((ch >= 93) && (ch <= 122));
}

enum Mode {
  Pair,
  Test,
};

struct Duration {
  uint16_t stim = 100;
  uint16_t resp = 1000;
};

Mode mode = Pair;
Duration dur;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(BAUD);
  writeSettings();
  randomSeed(analogRead(0));
}

void loop() {
  // put your main code here, to run repeatedly:
  if (Serial.available() > 0) {
     int c = Serial.read();
     if (c > 0) {
       parseFromSerial((char)c);
     }
  }
}

void writeMode(const bool& standalone=false);
void writeStimDur(const bool& standalone=false);
void writeRespDur(const bool& standalone=false);

void writeMode(const bool& standalone) {
  if (standalone) {
    Serial.print("@");
  }
  Serial.print((mode == Pair)? "[P]":"P");
  Serial.print((mode == Test)? "[T]":"T");
  if (standalone) {
    Serial.println();
  } else {
    Serial.print(';');
  }
}

void writeStimDur(const bool& standalone) {
  if (standalone) {
    Serial.print("@");
  }
  Serial.print(CFG_CHR_STIM);
  Serial.print(dur.stim);
  if (standalone) {
    Serial.println();
  } else {
    Serial.print(';');
  }
}


void writeRespDur(const bool& standalone) {
  if (standalone) {
    Serial.print("@");
  }
  Serial.print(CFG_CHR_RESP);
  Serial.print(dur.resp);
  if (standalone) {
    Serial.println();
  } else {
    Serial.print(';');
  }
}

void writeSettings() {
  Serial.print("@<SampleTask>;");
  writeMode();
  writeStimDur();
  writeRespDur();
  Serial.println();
}

void parseFromSerial(const char& ch) {
  if (!isRecognizable(ch)) {
    return;
  }

  switch(ch) {
    case '?':
    writeSettings();
    break;

    case CFG_CHR_PAIR:
    mode = Pair;
    writeMode(true);
    break;

    case CFG_CHR_TEST:
    mode = Test;
    writeMode(true);
    break;

    case CFG_CHR_STIM:
    dur.stim = parseUnsignedFromSerial(dur.stim);
    writeStimDur(true);
    break;

    case CFG_CHR_RESP:
    dur.resp = parseUnsignedFromSerial(dur.resp);
    writeRespDur(true);
    break;

    case CMD_CHR_EXEC:
    runOnce();
    break;

    case ';':
    break;

    default:
    Serial.print("*error: ");
    Serial.println(ch);
    break;
  }
}

uint16_t parseUnsignedFromSerial(const uint16_t& orig)
{
  uint16_t value = 0;
  while(true) {
    
    // wait until some input is available
    while (Serial.available() == 0);
    
    int readChar = Serial.read();

    // only accepts digits
    if ((readChar >= 48) && (readChar <= 57)) {
      value = value * 10 + (readChar - 48);
      // continues parsing
      
    } else if ( !isRecognizable(readChar) || (readChar == 59) ) {
      // space or ';'
      // ends parsing
      break;
      
    } else {
      Serial.print("*error: ");
      Serial.println((char)readChar);
      // set value to original
      value = orig;
      break;
      
    }
  }
  
  return value;
}

void genResponse(int* response, const int& len, const int& limit) {
  for (int i=0; i<limit; i++) {
    response[i] = -1;
  }
  int nresp = 0;
  
  for (int i=0; i<limit; i++) {
    int val = (int)random(0, len);
    bool added = false;

    // find a place for val to sit
    for (int j=0; j<i; j++) {
      
      // must have been sorted in an ascending order
      
      LOGDEBUG("i=");
      LOGDEBUG(i);
      LOGDEBUG(", j=");
      LOGDEBUG(j);
      LOGDEBUG("; ");
      LOGDEBUG(val);
      LOGDEBUG(" vs ");
      LOGDEBUG(response[j]);
      
      if (response[j] == val) {
        LOGDEBUG("; ***duplicate");
        added = true;
        nresp--;
        break;
      }
      else if (response[j] > val) {
        LOGDEBUG("; insert");
        // shift
        for (int k=i; k>j; k--) {
          response[k] = response[k-1];
        }
        response[j] = val;
        added = true;
        break;
      } else {
        LOGDEBUGLN();
      }
    }

    if (!added) {
      LOGDEBUG("append ");
      LOGDEBUGLN(val);
      response[i] = val;
    }

    // data has been inserted (if any)
  }
}

void runOnce() {
  bool cued = (mode == Pair);
  bool responded = false;
  int response[50];
  int nresp = (int)random(0,20);

  long _start, _stop;
  _start = millis();
  Serial.println(">Delay");
  genResponse(response, 5000, nresp);
  delay(1000);
  _stop = millis();
  
  Serial.println(">Cued");
  if ((!cued) and (random(0,10) > 0)) {
    cued = true;
  }
  for (int i=0; i<nresp; i++) {
    responded = responded || ((response[i] > 2500) && (response[i] < 3500));
  }
  delay(500);
  if (responded) {
    Serial.println(">WithResp");
  } else {
    Serial.println(">NoResp");
  }
  delay(dur.resp);

  writeResults(cued, responded, _stop - _start, response, nresp);
}

void writeResults(const bool& cued, const bool& resp, const long& wait, const int* response, const int& nresp)
{
  if (cued) {
    if (resp) {
      Serial.print("+hit;");
    } else if (mode == Pair) {
      Serial.print("+noresp;");
    } else {
      Serial.print("+miss;");
    }
  } else {
    if (resp) {
      Serial.print("+catch;");
    } else if (mode == Pair){
      Serial.print("+noresp;");
    } else {
      Serial.print("+reject;");
    }
  }

  Serial.print("wait");
  Serial.print(wait);

  Serial.print(";lick[");
  for (int i=0; i<nresp; i++) {
    Serial.print(response[i]);
    if (i < (nresp-1) ) {
      Serial.print(',');
    }
  }
  Serial.println("];");
}

