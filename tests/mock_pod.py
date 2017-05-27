import socketserver


RESPONSES = {
  b'ping': b'PONG:1\n'
}


class MockPodHandler(socketserver.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        # self.request is the TCP socket connected to the client
        while True:
            self.data = self.request.recv(1024).strip()
            print("{} wrote: '{}'".format(self.client_address[0], self.data))
            if not self.data:
                break
            if self.data in RESPONSES:
                # just send back the same data, but upper-cased
                print("Sending {}".format(RESPONSES[self.data]))
                self.request.sendall(RESPONSES[self.data])

if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 7779

    # Create the server, binding to localhost on port 9999
    server = socketserver.TCPServer((HOST, PORT), MockPodHandler)
    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
