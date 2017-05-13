import json
from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler


class ODSHTTPRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def _respond(self, string):
        self.wfile.write(string.encode('utf-8'))

    def do_GET(self):
        parsed_path = urlparse(self.path)

        command = parsed_path.path.lstrip('/').split('/')[0]

        handler = "do_GET_%s" % command
        invert_op = getattr(self, handler, None)
        if callable(invert_op):
            invert_op()
        else:
            self._set_headers(500)
            self._respond("No Handler named: %s" % handler)

    def do_GET_shutdown(self):
        self._set_headers(200)
        self._respond("Shutdown Command Sent! - Not really")

    def do_GET_state(self):
        state = self.server.ods_server.state
        self._set_headers(200)
        self._respond(json.dumps(state))

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        self._set_headers()
        form = cgi.FieldStorage(fp=self.rfile,
                                headers=self.headers,
                                environ={
                                    'REQUEST_METHOD': 'POST',
                                    'CONTENT_TYPE': self.headers['Content-Type']})  # noqa

        # Begin the response
        self.send_response(200)
        self.end_headers()
        self.wfile.write('Client: %s\n' % str(self.client_address))
        self.wfile.write('User-agent: %s\n' % str(self.headers['user-agent']))
        self.wfile.write('Path: %s\n' % self.path)
        self.wfile.write('Form data:\n')

        # Echo back information about what was posted in the form
        for field in form.keys():
            field_item = form[field]
            if field_item.filename:
                # The field contains an uploaded file
                file_data = field_item.file.read()
                file_len = len(file_data)
                del file_data
                self.wfile.write('\tUploaded %s as "%s" (%d bytes)\n' %
                                 (field, field_item.filename, file_len))
            else:
                # Regular form value
                self.wfile.write('\t%s=%s\n' % (field, form[field].value))
