Protocol description
====================

**dcnnt** uses both UDP and TCP transport layers 
(usualy port `5040`). 

Device search
-------------

To search server in network client should send broadcast UDP 
datagram (implying client and server are in same broadcast domain) 
containing JSON dictionary.

Search request fields:

* *plugin* - string constant, must be `search`
* *action* - string constant, must be `request`
* *uin* - unique identifier of device, integer from 0x0F to 0x0FFFFFFF
* *name* - short name of device, 1 to 40 characters
* *role* - role of device, must be `client` in most cases

Example of search request (formatted for readability):

    {
      "plugin": "search",
      "action": "request",
      "role": "client",
      "uin": 239,
      "name": "My phone"
    }

Watch [config.md]() for additional information about some of this fields.

After receiving and processing of request server sends response data 
to client in unicast UDP datagram. This datagram also contains 
JSON dictionary.

Search response fields:

* *plugin* - string constant, must be `search`
* *action* - string constant, must be `response`
* *uin* - unique identifier of device, integer from 0x0F to 0x0FFFFFFF
* *name* - short name of device, 1 to 40 characters
* *role* - role of device, must be `server` in most cases

Example of search response (formatted for readability):

    {
      "plugin": "search",
      "action": "request",
      "role": "server",
      "uin": 541,
      "name": "Workstation"
    }

Pairing
-------

*ToDo*

Data transmission
-----------------

### About encryption keys

Each pair of devices have two keys. 
Receive key used to decrypt received message from device.
Send key used to encrypt message sent to device.
If passwords on both devices are correct, then send key of 
device "Alice" on device "Bob" will be equal receive key 
of device "Bob" on device "Alice" and vice versa.

Keys derivation (for "Bob" at "Alice"):

    receive key = SHA-256(<UIN of "Alice" as decimal string> + 
                          <UIN of "Bob" as decimal string> + 
                          <Password of "Alice"> + 
                          <Password of "Bob">)
    send key = SHA-256(<UIN of "Bob" as decimal string> +  
                       <UIN of "Alice" as decimal string> +
                       <Password of "Bob"> + 
                       <Password of "Alice">)

Keys are 256-bits values, "+" stands for string concatenation here.

### Handshake

Connection between devices starts with handshake. 

Tasks on handshake:

1. Determine protocol version (only one available now).
2. Determine data encryption and encoding (only one available now).
3. Check source and destination UINs, select encryption/decryption keys.
4. Check if keys are correct.
5. Determine plugin to process next messages.

Client opens TCP connection and send handshake binary message.

Format of handshake message:

1. *ver* - version info, 8 bytes, all zeros now.
2. *enc* - encryption and encoding method, 8 bytes, all zeros now.
3. *dst* - destination UIN, 4 bytes, 32-bit unsigned integer in big-endian.
4. *src* - source UIN, 4 bytes, 32-bit unsigned integer in big-endian.
5. *plg* - encrypted plugin code of 4 ASCII characters, 36 bytes (depends on encryption method, but only one available now).

After handshake message processing server sends to client handshake response in same format

### Messages

Data exchange in dcnnt consists of binary messages.

Format of message is simple:

1. *length* - length of *data* field, 4 bytes, 32-bit unsigned integer in big-endian.
2. *data* - encrypted/encoded message data, *length* bytes.

While length of message may be up to 4 Gigabytes, it should be rather short to process.

### Disconnect

Client or server just closes TCP connection.
