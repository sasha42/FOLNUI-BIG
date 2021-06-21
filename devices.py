# coding: utf-8
from flux_led_v4 import BulbScanner
import flux_led_v4 as flux_led
from contextlib import contextmanager
import signal


def raise_timeout(signum, frame):
    #print('LED timedout')
    #raise TimeoutError
    raise RuntimeError


@contextmanager
def timeout(time):
    # Register a function to raise a TimeoutError on the signal.
    signal.signal(signal.SIGALRM, raise_timeout)
    # Schedule the signal to be sent after ``time``.
    signal.alarm(time)

    try:
        yield
    except TimeoutError:
        pass
    finally:
        # Unregister the signal so it won't be triggered
        # if the timeout is not reached.
        signal.signal(signal.SIGALRM, signal.SIG_IGN)


def loadLEDs():
    '''Loads IPs from ip.order.txt into memory, and attemps to connect
    to them.'''

    # Open ip.order.txt and read the IPs of the bulbs. It expects a list
    # of IPs like 192.168.1.1, with one IP per line. The file should end
    # with one empty line.
    filepath = '/home/pi/FOLNUI/ip.order.txt'

    # Define variables
    ips = []
    bulbs = {}
    lastOrder = {}
    cnt = 1

    # Try to open local list of IPs, if not, scan the network for list
    try:
        with open(filepath) as fp:
            line = fp.readline()
            while line:
                line = fp.readline()
                if line.strip() == "":
                    continue
                ip = line.strip()

                ips.append(ip)
    except:
        ips = getBulbs()

    # Once the file has been read, the script will attempt to create
    # objects for each bulb.
    print(f"💡 Connected to {len(ips)} LED strips")

    for ip in ips:
        with timeout(1):
            try:
                bulb = flux_led.WifiLedBulb(ip, timeout=0.1)
                #print(vars(bulb))
                #print(bulb._WifiLedBulb__state_str)
                bulbs[cnt] = bulb
                lastOrder[cnt] = ""
                cnt = cnt + 1

            except Exception as e:
                print ("Unable to connect to bulb at [{}]: {}".format(ip,e))
                continue
    
    #for bulb in bulbs:
    #    bulbs[bulb].getBulbInfo()
    # Return the bulbs that were successfully innitiated
    return bulbs


def getBulbs():
    """Gets bulbs from the local network using a scan"""

    # Initialize bulb scanner
    s = BulbScanner()
    
    # Scan the local network with timeout of 1
    result = s.scan(timeout=1)

    # Return just the IPs
    ips = []
    for i in result:
        ips.append(i['ipaddr'])

    return ips


def simpleBulbList(bulbs):
    """Pretty prints a list of bulbs"""

    return f"💡 found {len(bulbs)} bulbs"


if __name__ == "__main__":
    bulbs = getBulbs()
    simple_bulbs = simpleBulbList(bulbs)   

    print(simple_bulbs)
