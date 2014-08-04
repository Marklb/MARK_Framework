from wsgiref.simple_server import make_server
import re
import inspect
import string
from http.cookies import SimpleCookie
import itsdangerous

routing_table = {}  # {route_key: {func: ?, params: ?}}
image_types = {"jpg": "image/jpg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif"}
script_types = {"css": "text/css", "js": "text/javascript"}
errors = [] # Removed this part when updating code and need to re implement the error messages.
cookie_pending = []
secret_key = '34856383'


def route(url, func):
    """Add a route to the routing table"""
    route_key, route_params = get_route_key(url)
    if route_params:
        routing_table[route_key] = {'func': func, 'params': route_params}
    else:
        routing_table[route_key] = {'func': func, 'params': []}


def get_route_key(url):
    """
    Used for the route
    Gets the static part of the url, which is the key for a route
        return key, additional parameters
    """
    route_key = re.findall(r"(.*?)/<[a-zA-Z_][a-zA-Z0-9_]*>", url)
    if route_key:
        route_params = re.findall(r"<([a-zA-Z_][a-zA-Z0-9_]*)>", url)
        return route_key[0], route_params
    else:
        return url, None


def get_url_key(url):
    """
    Used for the requested url
    Gets the static part of the url, which is the key for a route
        return key, additional parameters
    """
    url_key = url
    #Start at the full url and cut off a /+ each time if is not found in the routing table
    #Find if there is a valid key from the requested url
    while url_key.count('/') > 0:
        if find_path(url_key):
            url_params = [x for x in url[len(url_key)+1:].split('/')]
            if url_params == ['']:
                url_params = []
            return url_key, url_params
        url_key = url_key[:url_key.rfind('/')]
    return None, None


def find_path(url):
    """
    Gets the requested route from the routing table
        returns [function, params]
    """
    if url in routing_table:
        return routing_table[url]
    else:
        return None


def handle(url, environ):
    """Handles what do with the requested url"""
    url_key, url_params = get_url_key(url)
    route_value = find_path(url_key)
    route_key = url_key
    if not route_value:
        return None
    route_params = route_value['params']
    #If there are params in the url
    if len(url_params) > len(route_params):
        return None
    param_dict = {}
    for i in range(len(url_params)):
        param_dict[route_params[i]] = url_params[i]
    request_type = environ['REQUEST_METHOD']
    body = None
    if request_type == 'GET':
        body = handle_get(url, environ, url_key, url_params, route_params, param_dict)
    if request_type == 'POST':
        body = handle_post(url, environ, url_key, url_params, route_params, param_dict)
    return body


def handle_get(url, environ, url_key, url_params, route_params, param_dict):
    """Called when a GET request is identified"""
    route_obj = find_path(url_key)
    func = route_obj['func']()
    sig = inspect.signature(func.get)
    for param in sig.parameters.values():
        if param.default is param.empty:
            if param.name not in param_dict:
                return None
    func.session_id = -1
    if 'HTTP_COOKIE' in environ:
        cookie = SimpleCookie(environ['HTTP_COOKIE'])
        if 'sessionid' in cookie:
            func.session_id = cookie['sessionid'].value
    func.request = {}
    func.environment = environ
    return func.get(**param_dict)


def handle_post(url, environ, url_key, url_params, route_params, param_dict):
    """Called when a POST request is identified"""
    request_input = []
    try:
        length = int(environ.get('CONTENT_LENGTH', '0'))
    except ValueError:
        length = 0
    if length != 0:
        request_input = environ['wsgi.input'].read(length).decode('UTF-8')
        request_input = request_input.split('&')
    route_obj = find_path(url_key)
    func = route_obj['func']()
    sig = inspect.signature(func.get)
    for param in sig.parameters.values():
        if param.default is param.empty:
            if param.name not in route_params:
                return None
    func.session_id = -1
    if 'HTTP_COOKIE' in environ:
        cookie = SimpleCookie(environ['HTTP_COOKIE'])
        # print('Cookie:', cookie)
        if 'sessionid' in cookie:
            func.session_id = cookie['sessionid'].value
    func.request = {}
    for req in request_input:
        req = req.split('=')
        func.request[req[0]] = req[1]
    func.environment = environ
    return func.post(**param_dict)


def return_404(error_msg=''):
    """Returns the 404 page and inserts the error msg if $error_msg is found in the page"""
    with open('404.html') as f:
        body = f.read()
        temp = string.Template(body)
        body = temp.safe_substitute({'error_msg': error_msg})
        return body


def add_cookie(cookie):
    cookie_pending.append(cookie)


def check_asset(path, start_response):
    """
    ~Very basic temporary function to be able to use these files without routing every image etc~
    Handles assets if they are in the root of the directory static/
	
	I made this very simple and separate from everything else because it wasn't a part of the 
		assignment, but I wanted to use this stuff, so I did this quickly to make them work
		without taking a chance of messing up the code required for the project
    """
    types_list = None
    if path[path.rfind(".")+1:].lower() in image_types:
        types_list = image_types
    elif path[path.rfind(".")+1:].lower() in script_types:
        types_list = script_types
    if types_list:
        try:
            with open("static/"+path[path.rfind("/")+1:], "rb") as f:
                body = f.read()
            status = '200 OK'
            headers = [('Content-type', types_list[path[path.rfind(".")+1:]])]
            start_response(status, headers)
            return body
        except FileNotFoundError:
            return None


def app(environ, start_response):
    """Called when the web server starts"""
    path = environ['PATH_INFO']
    body = check_asset(path, start_response)
    #If not an asset, attempt to handle from routes
    if not body:
        body = handle(path, environ)
        if body:
            body = body.encode("utf-8")
            headers = [('Content-type', 'text/html; charset=utf-8')]
            for x in cookie_pending:
                # s = itsdangerous.Signer(secret_key)
                # x = str(s.sign(x.encode("utf-8")))
                c = ('Set-Cookie', x)
                headers.append(c)
            status = '200 OK'
            start_response(status, headers)
        else:
            body = return_404()
            body = body.encode("utf-8")
            headers = [('Content-type', 'text/html; charset=utf-8')]
            status = '404 Not Found'
            start_response(status, headers)
    return [body]


def run(ip="127.0.0.1", port=8000):
    """Starts the MARK framework"""
    print("\n\n\nRunning MARK. at " + ip + ":" + str(port))
    print("Routing table:")
    print(routing_table)
    myserver = make_server(ip, port, app)
    myserver.serve_forever()