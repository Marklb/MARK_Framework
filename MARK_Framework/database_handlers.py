import redis
import hashlib

rdb = redis.StrictRedis(host='localhost', port=6379, db=0)


def register(username, password, email):
    response = rdb.exists('username:{0}:uid'.format(username.lower()))
    if response:
        print('User already exists')
        return False
    uid = rdb.incr('nextUserId')
    #Set the uid accessor
    if not rdb.set('username:{0}:uid'.format(username.lower()), uid):
        print('uid error')
        return False
    #Set the users information
    if not rdb.set('uid:{0}:username'.format(uid), username):
        print('username error')
        return False
    hash = hashlib.md5(password.encode())
    # print(hash.hexdigest())
    if not rdb.set('uid:{0}:password'.format(uid), hash.hexdigest()):
        print('pass error')
        return False
    if not rdb.set('uid:{0}:email'.format(uid), email):
        print('email error')
        return False
    return True


def login(username, password, ip_address):
    if is_logged_in(username):
        print("{0} already logged in.".format(username))
        return False
    uid = rdb.get('username:{0}:uid'.format(username.lower()))
    if not uid:
        print("User {0} does not exist.".format(username.lower()));
        return False
    uid = uid.decode(encoding='UTF-8')
    stored_pass = rdb.get('uid:{0}:password'.format(uid))
    if not stored_pass:
        print("Invalid username or password");
        return False
    stored_pass = stored_pass.decode(encoding='UTF-8')
    hash = hashlib.md5(password.encode())
    # print(hash.hexdigest())
    if hash.hexdigest() != stored_pass:
        print("Invalid username or password");
        return False
    create_session(uid, ip_address)
    username = rdb.get('uid:{0}:username'.format(uid)).decode(encoding='UTF-8')
    print("Logged in {0}".format(username))
    return True


def logout(username):
    #get uid
    uid = rdb.get('username:{0}:uid'.format(username.lower())).decode(encoding='UTF-8')
    #terminate session
    success = terminate_session(uid)
    if success:
        print('{0} logged out.'.format(username))
    else:
        print('Error logging out {0}.'.format(username))
    return True


def create_session(uid, ip_address):
    session_key = generate_session_key(uid)
    if not rdb.set('session_key:{0}:uid'.format(session_key), uid):
        print("Error creating session.")
        return
    if not rdb.set('session_key:{0}:ip_address'.format(session_key), ip_address):
        print("Error creating session.")
        return
    return True


def terminate_session(uid='', session_id=''):
    if uid != '':
        sessions = get_sessions()
        for session_key in sessions:
            session_uid = rdb.get('session_key:{0}:uid'.format(session_key)).decode(encoding='UTF-8')
            if uid == session_uid:
                rdb.delete('session_key:{0}:uid'.format(session_key))
                return True
    elif session_id != '':
        response = rdb.delete('session_key:{0}:ip_address'.format(session_id))
        response = rdb.delete('session_key:{0}:uid'.format(session_id))
        if response:
            return True
    return False


def get_session_key(uid='', username=''):
    if username != '':
        uid = rdb.get('username:{0}:uid'.format(username.lower())).decode(encoding='UTF-8')
    if not uid:
        uid = -1
    sessions = get_sessions()
    for sess_key in sessions:
        uid_sess = rdb.get('session_key:{0}:uid'.format(sess_key)).decode(encoding='UTF-8')
        if uid == uid_sess:
            return sess_key


def is_session_valid(session_id, ip_address):
    response = rdb.exists('session_key:{0}:uid'.format(session_id))
    if not response:
        return False
    response = rdb.exists('session_key:{0}:ip_address'.format(session_id))
    if not response:
        return False
    return True


def get_sessions():
    session_keys = rdb.keys('session_key:*')
    sess_list = []
    for session in session_keys:
        session = session.decode(encoding='UTF-8').split(':')
        sess_list.append(session[1])
    return sess_list


def generate_session_key(uid):
    return rdb.incr('nextSessionKey')


def is_logged_in(username):
    uid_user = rdb.get('username:{0}:uid'.format(username.lower()))
    if not uid_user:
        return False
    uid_user = uid_user.decode(encoding='UTF-8')
    session_key = get_session_key(uid=uid_user)
    if session_key:
        return True
    return False


def get_name_of_session_user(session_id):
    uid = rdb.get('session_key:{0}:uid'.format(session_id))
    if not uid:
        return None
    uid = uid.decode(encoding='UTF-8')
    username = rdb.get('uid:{0}:username'.format(uid))
    if not username:
        return None
    username = username.decode(encoding='UTF-8')
    return username


def print_user_names():
    keys = rdb.keys('uid:*:username')
    for user in keys:
        usr = rdb.get(user).decode(encoding='UTF-8')
        print("User:", str(usr))


def print_logged_in_usernames():
    keys = rdb.keys('session_key:*:uid')
    for user in keys:
        usr = rdb.get(user).decode(encoding='UTF-8')
        print("Logged in:", str(usr))
