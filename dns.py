import socket
import glob
import json

# Default dns port
port = 53

ip = '127.0.0.1'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ip, port))


def loadZones():
    jsonZone = {}
    zoneFiles = glob.glob('zones/*.zone')

    for zone in zoneFiles:
        with open(zone) as zoneData:
            data = json.load(zoneData)
            zoneName = data["$origin"]
            jsonZone[zoneName] = data

    return jsonZone


def getFlags(data):
    firstByte = bytes(data[0:1])
    qr = '1'

    opcode = ''
    for i in range(1, 5):
        # Append (i+1)th bit of data to opcode
        opcode += str(ord(firstByte) & (1 << i))

    aa = '1'
    tc = '0'
    rd = '0'
    ra = '0'
    z = '000'
    rcode = '0000'
    return int(qr+opcode+aa+tc+rd, 2).to_bytes(1, byteorder='big') + int(ra+z+rcode, 2).to_bytes(1, byteorder='big')


def getQuestionDomain(data):
    isReadingLength = True
    expectedLength = 0
    length = 0
    offset = 0
    domainString = ''
    domainParts = []

    for byte in data:
        if byte == 0:
            domainParts.append(domainString)
            break
        if isReadingLength == True:
            # Read length
            expectedLength = byte
            isReadingLength = False
        else:
            # Read actual data
            domainString += chr(byte)
            length += 1
            if length == expectedLength:
                domainParts.append(domainString)
                domainString = ''
                length = 0
                isReadingLength = True
        offset += 1

    questionType = data[offset+1:offset+3]
    return (domainParts, questionType)


def getZone(domainParts):
    zoneData = loadZones()
    zoneName = '.'.join(domainParts)
    return zoneData[zoneName]


def getRecs(data):
    domainParts, questionType = getQuestionDomain(data)
    qt = ''
    if questionType == b'\x00\x01':
        qt = 'a'

    zone = getZone(domainParts)
    return (zone[qt], qt, domainParts)


def buildQuestion(domainParts, recType):
    qbytes = b''

    for part in domainParts:
        # Add length
        length = len(part)
        qbytes += bytes([length])
        # Add name
        for char in part:
            qbytes += ord(char).to_bytes(1, byteorder='big')

    # Add type A
    if recType == 'a':
        qbytes += (1).to_bytes(2, byteorder='big')
    # Add class IN
    qbytes += (1).to_bytes(2, byteorder='big')
    return qbytes


def buildRecBytes(recType, recttl, recval):
    # Compression result of length of header
    rbytes = b'\xc0\x0c'

    if recType == 'a':
        rbytes = rbytes + bytes([0]) + bytes([1])

    rbytes = rbytes + bytes([0]) + bytes([1])

    rbytes += int(recttl).to_bytes(4, byteorder='big')

    if recType == 'a':
        rbytes = rbytes + bytes([0]) + bytes([4])

        for part in recval.split('.'):
            rbytes += bytes([int(part)])

    return rbytes


def buildResponse(data):
    # Building dns header

    # Get transaction ID
    transactionID = data[0:2]
    tid = ''
    for byte in transactionID:
        tid += hex(byte)[2:]

    # Get flags
    flags = getFlags(data[2:4])

    # Question count is one
    qdcount = b'\x00\x01'

    # Answer count
    ancount = len(getRecs(data[12:])[0]).to_bytes(2, byteorder='big')

    # Nameserver count is zero
    nscount = (0).to_bytes(2, byteorder='big')

    # Additional count is zero
    arcount = (0).to_bytes(2, byteorder='big')

    dnsHeader = transactionID + flags + qdcount + ancount + nscount + arcount

    # Building dns body
    dnsBody = b''

    records, recType, domainParts = getRecs(data[12:])
    dnsQuestion = buildQuestion(domainParts, recType)

    for record in records:
        dnsBody += buildRecBytes(recType, record["ttl"], record["value"])

    return dnsHeader + dnsQuestion + dnsBody


# Start listening
while True:
    data, addr = sock.recvfrom(512)
    response = buildResponse(data)
    sock.sendto(response, addr)
