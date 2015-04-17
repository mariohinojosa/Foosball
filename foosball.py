# ===========================================================================
# Basic integration of modules for football project
# ===========================================================================

from time import sleep, time
import datetime
import Adafruit_MCP230xx as Ada
import matrix_kp
import RPi.GPIO as GPIO
import MFRC522
import signal
from Adafruit_CharLCD  import Adafruit_CharLCD
from Adafruit_7Segment import SevenSegment
import gspread

bus = 1         # Change the bus number to 0 if running on a revision 1 Raspberry Pi.
address = 0x20  # I2C address of the MCP230xx chip.
gpio_count = 16  # Number of GPIOs exposed by the MCP230xx chip, should be 8 or 16 depending on chip.

segment = SevenSegment(address = 0x70)

kp = matrix_kp.keypad(address = 0x20, num_gpios = 16, columnCount = 4)

# Create MCP230xx GPIO adapter.
mcp = Ada.MCP230XX_GPIO(bus, address, gpio_count)

# Create LCD, passing in MCP GPIO adapter.
lcd = Adafruit_CharLCD(pin_rs=1, pin_e=2, pins_db=[3,4,5,6], GPIO=mcp)

# Prepare pins 11 & 13 as input to read pulse from infrared modules
GPIO.setmode(GPIO.BOARD)
GPIO.setup(11,GPIO.IN)
GPIO.setup(12,GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(13,GPIO.IN)

score_A = 0
score_B = 0
score_time_A = []
score_time_B = []
max_score = 5

last_action = "C"

interrupt = False

def is_id_in_list(list, id):
        if(id in list):
                return True
        return False

def clear_seven_segment():
    segment.writeDigitRaw(0,0x00)
    segment.writeDigitRaw(1,0x00)
    segment.writeDigitRaw(3,0x00)
    segment.writeDigitRaw(4,0x00)

def my_callback_A(chanel):
    global score_A
    global score_time_A
    global segment
    global lcd
    global last_action
    global max_score
    if(score_A < max_score):
            score_A += 1
            score_time_A.append(time())
            last_action = "A"
            segment.writeDigit(0,score_A)

def my_callback_B(chanel):
    global score_B
    global score_time_B
    global segment
    global lcd
    global last_action
    global max_score
    if(score_B < max_score):
            score_B += 1
            score_time_B.append(time())
            last_action = "B"
            segment.writeDigit(3,score_B)

def callback_interrupt(chanel):
        global interrupt
        interrupt = True

GPIO.add_event_detect(12,GPIO.RISING,callback=callback_interrupt,bouncetime=500)

GPIO.add_event_detect(11,GPIO.RISING,callback=my_callback_A,bouncetime=800)
GPIO.add_event_detect(13,GPIO.RISING,callback=my_callback_B,bouncetime=800)

# Create digit() which polls the keypad looking for a digit (0-9) to be pressed
def digit():
    # Loop while waiting for a keypress
    r = None
    while r == None or r in ['A','B','C','D','*','#']:
        r = kp.getKey()
    return r

def symbol():
    r = None
    while r == None or r not in ['*','#']:
        r = kp.getKey()
    return r

def readNfc():
    reading = True
    while reading:
        MIFAREReader = MFRC522.MFRC522()

        (status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

        (status,backData) = MIFAREReader.MFRC522_Anticoll()
        if status == MIFAREReader.MI_OK:
            MIFAREReader.AntennaOff()
            reading=False
            return backData[0]

def WriteToTrix(num_players, players, total_time, score_A, score_B):
        gc = gspread.login('futbolinmx@gmail.com', 'futbolingoogle')
        now = datetime.datetime.now()
        sheet = gc.open('Futbolin').sheet1
        row_number = len(sheet.col_values(1)) + 1
        sheet.update_acell('B'+str(row_number), now)
        sheet.update_acell('C'+str(row_number), num_players)

        if num_players == 2:
                sheet.update_acell('D'+str(row_number), players[0])
                sheet.update_acell('E'+str(row_number), players[1])
        else:
                sheet.update_acell('D'+str(row_number), players[0])
                sheet.update_acell('E'+str(row_number), players[1])
                sheet.update_acell('F'+str(row_number), players[2])
                sheet.update_acell('G'+str(row_number), players[3])

        sheet.update_acell('T'+str(row_number), total_time)

def jugar():
    global score_A
    global score_B
    global score_time_A
    global score_time_B
    global secs
    global last_action
    global interrupt

    # List of players
    # First two players are from team A (yellow)
    # Second two players are from team B (red)
    players = []
    print "Look at LCD for instructions"

    lcd.clear()
    lcd.message("How many players?\npress 1 or 2")

    d1 = digit()
    lcd.clear()
    lcd.message("You pressed %d" % d1)
    sleep(1)

    i = 0
    while(i < d1):
        lcd.clear()
        lcd.message("Player %d badge" % (i + 1))
        id = readNfc()
        if(is_id_in_list(players, id)):
                lcd.clear()
                lcd.message("Badge already\nscanned")
                sleep(2)
        else:
                players.append(id)
                lcd.clear()
                lcd.message("Player added\nId: %d" % id)
                sleep(2)
                lcd.clear()
                i += 1
        print(i)
        sleep(1)

    continue_playing = True

    while(continue_playing):
        score_A = 0
        score_B = 0

        del score_time_A[:]
        del score_time_B[:]

        last_action = "C"

        #Display initial score
        segment.writeDigit(0,score_A)
        segment.writeDigit(3,score_B)
        segment.writeDigit(2,1)

        lcd.clear()
        lcd.message("  Game is on!")
        sleep(1)

        secs = 0
        max_score = 4
        start = time()

        while ((score_A < max_score) and (score_B < max_score)):
            # print("before interrupt"+str(interrupt))
            if(interrupt):
                lcd.clear()
                lcd.message("Interrupt")
                sleep(2)
                if(last_action == "A"):
                    score_A -= 1
                    score_time_A.pop()
                    segment.writeDigit(0,score_A)
                if(last_action == "B"):
                    score_B -= 1
                    score_time_B.pop()
                    segment.writeDigit(3,score_B)
                if(last_action == "C"):
                    lcd.clear()
                    lcd.message("No goals yet")
                    sleep(2)
                interrupt = False
            secs += 1
            lcd.clear()
            lcd.message("TIME PLAYED:\n%d seconds" %secs)
            sleep(1)
        stop = time()
        game_time = stop - start

        if score_A > score_B:
            lcd.clear()
            lcd.message("   GAME OVER\n  Yellow won!")
        else:
            lcd.clear()
            lcd.message("   GAME OVER\n   Red won!")
        sleep(2)
        lcd.message("   GAME OVER\nDuration: %d s" %game_time)

        sleep(3)

        WriteToTrix(d1, players, game_time, score_A, score_B)
        lcd.clear()
        lcd.message("Continue?\n*=yes #=no")
        sym = symbol()

        if sym == '*':
            lcd.clear()
            lcd.message("Here we go again")
        else:
            continue_playing = False
            lcd.clear()
            lcd.message("Ok, bye bye")
            clear_seven_segment()
            #GPIO.cleanup()




# WriteToTrix()

try:
    while True:
        lcd.clear()
        clear_seven_segment()
        lcd.message("To start a game\npress *")
        input = symbol()
        if(input == '*'):
            jugar()
        sleep(1)
except:
    lcd.clear()
    clear_seven_segment()
    GPIO.cleanup()

