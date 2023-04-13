import socket

# Default dns port
port = 53

ip = '127.0.0.1'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ip, port))


def getFlags(data):

    firstByte = bytes(data[0:1])
    secondByte = bytes(data[1:2])

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


def buildResponse(data):

    # Get transaction ID
    transactionID = data[0:2]
    tid = ''
    for byte in transactionID:
        tid += hex(byte)[2:]

    # Get flags
    flags = getFlags(data[2:4])


# Start listening
while True:
    data, addr = sock.recvfrom(512)
    response = buildResponse(data)
    sock.sendto(response, addr)
