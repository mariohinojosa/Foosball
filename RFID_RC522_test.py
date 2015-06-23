import MFRC522

def readNfc():
    reading = True
    while reading:
        MIFAREReader = MFRC522.MFRC522()

        (status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

        (status,backData) = MIFAREReader.MFRC522_Anticoll()
        if status == MIFAREReader.MI_OK:
            #print "Card detected"
            MIFAREReader.AntennaOff()
            reading=False
            return backData[0]


print "Welcome to the MFRC522 data read example"

id = readNfc()
print "Card detected: " + id

