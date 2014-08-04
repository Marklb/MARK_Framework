import mark
import mark_template
import argparse
import database_handlers
from http.cookies import SimpleCookie
import hashlib

def load_index(session_id, environment):
    template = mark_template.Template()
    logged_in = True
    username = ''
    if session_id != -1:
        resp = database_handlers.is_session_valid(session_id, environment['REMOTE_ADDR'])
        if not resp:
            logged_in = False
        else:
            username = database_handlers.get_name_of_session_user(session_id)
    return template.render("index.html", is_logged_in=logged_in, username=username)


################################
# Controllers
################################
class Index(object):
    def get(self):
        return load_index(self.session_id, self.environment)


class UserPage(object):
    def get(self, name, page_num=1):
        template = mark_template.Template()
        return template.render("user_page.html", name=name, page_num=page_num)


class Login(object):
    def get(self):
        template = mark_template.Template()
        return template.render("login.html")

    def post(self):
        username = self.request['username']
        password = self.request['password']
        ip_address = self.environment['REMOTE_ADDR']
        response = database_handlers.login(username, password, ip_address)
        if not response:
            print("Problem logging in")
        cookie = SimpleCookie()
        session_id = database_handlers.get_session_key(username=username.lower())
        if not session_id:
            return load_index(self.session_id, self.environment)
        cookie['sessionid'] = session_id
        cookie['sessionid']['path'] = '/'
        out = cookie['sessionid'].OutputString()
        mark.add_cookie(out)
        return load_index(session_id, self.environment)


class Logout(object):
    def get(self):
        return load_index(self.session_id, self.environment)

    def post(self):
        database_handlers.terminate_session(session_id=self.session_id)
        return load_index(self.session_id, self.environment)


class Register(object):
    def get(self):
        template = mark_template.Template()
        return template.render("register.html")

    def post(self):
        username = self.request['username']
        password = self.request['password']
        email = self.request['email']
        response = database_handlers.register(username, password, email)
        return load_index(self.session_id, self.environment)


def main(address="127.0.0.1", port=8000):
    mark.route("/", Index)
    mark.route("/index", Index)
    mark.route("/user/<name>/<page_num>", UserPage)
    mark.route("/user/edit/<name>/<page_num>", UserPage)
    mark.route("/member/<name>", UserPage)
    mark.route("/login", Login)
    mark.route("/logout", Logout)
    mark.route("/register", Register)
    mark.run(address, port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="web_framework")
    parser.add_argument("-address", type=str, default="127.0.0.1")
    parser.add_argument("-port", type=int, default=8000)
    args = parser.parse_args()
    main(args.address, args.port)