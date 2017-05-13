from http.server import HTTPServer


class ODSHTTPServer(HTTPServer):
    def __init__(self, addr, handler, ods_server):
        self.ods_server = ods_server
        super().__init__(addr, handler)
